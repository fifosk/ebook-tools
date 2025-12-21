"""Utilities for refreshing pipeline job metadata."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from ... import config_manager as cfg
from ... import metadata_manager
from ...core import ingestion
from ...core.config import build_pipeline_config
from ..file_locator import FileLocator
from ..pipeline_service import (
    serialize_pipeline_request,
    serialize_pipeline_response,
)
from ..pipeline_types import PipelineMetadata
from .job import PipelineJob


class PipelineJobMetadataRefresher:
    """Reconcile metadata for persisted pipeline jobs."""

    def __init__(self, file_locator: Optional[FileLocator] = None) -> None:
        self._file_locator = file_locator or FileLocator()

    def refresh(self, job: PipelineJob) -> Dict[str, Any]:
        """Update ``job`` metadata in-place and return the inferred payload."""

        request_payload = self._resolve_request_payload(job)
        inputs_payload = dict(request_payload.get("inputs", {}))
        input_file = str(inputs_payload.get("input_file") or "").strip()

        existing_metadata = inputs_payload.get("book_metadata")
        if not isinstance(existing_metadata, dict):
            existing_metadata = {}

        config_payload = request_payload.get("config")
        if not isinstance(config_payload, dict):
            config_payload = {}

        environment_overrides = request_payload.get("environment_overrides")
        if not isinstance(environment_overrides, dict):
            environment_overrides = {}

        pipeline_overrides = request_payload.get("pipeline_overrides")
        if not isinstance(pipeline_overrides, dict):
            pipeline_overrides = {}

        overrides = {**environment_overrides, **pipeline_overrides}

        context = cfg.build_runtime_context(
            dict(config_payload),
            dict(environment_overrides),
        )
        cfg.set_runtime_context(context)
        try:
            resolved_input = self._resolve_input_path(
                input_file,
                existing_metadata,
                context=context,
                job_id=job.job_id,
            )
            metadata_input = resolved_input or input_file
            if not metadata_input:
                raise ValueError(
                    f"Job {job.job_id} does not include an input file for metadata refresh"
                )

            metadata_updates = metadata_manager.infer_metadata(
                metadata_input,
                existing_metadata=dict(existing_metadata),
                force_refresh=True,
            )
            merged_metadata = dict(existing_metadata)
            for key, value in metadata_updates.items():
                if value is not None:
                    merged_metadata[key] = value

            content_index = self._resolve_content_index(
                job=job,
                metadata=merged_metadata,
                input_file=resolved_input,
                context=context,
                config_payload=config_payload,
                overrides=overrides,
            )
            if content_index is not None:
                merged_metadata["content_index"] = content_index
            else:
                merged_metadata.pop("content_index", None)
                merged_metadata.pop("content_index_path", None)
                merged_metadata.pop("content_index_url", None)
                merged_metadata.pop("content_index_summary", None)
        finally:
            try:
                cfg.cleanup_environment(context)
            finally:
                cfg.clear_runtime_context()

        inputs_payload["book_metadata"] = dict(merged_metadata)
        request_payload["inputs"] = inputs_payload

        if job.request is not None:
            job.request.inputs.book_metadata = PipelineMetadata.from_mapping(merged_metadata)
        job.request_payload = request_payload
        job.resume_context = copy.deepcopy(request_payload)

        if job.result is not None:
            job.result.metadata = PipelineMetadata.from_mapping(merged_metadata)
            job.result_payload = serialize_pipeline_response(job.result)
        else:
            result_payload = dict(job.result_payload or {})
            result_payload["book_metadata"] = dict(merged_metadata)
            job.result_payload = result_payload

        return dict(merged_metadata)

    def _resolve_input_path(
        self,
        input_file: str,
        metadata: Mapping[str, Any],
        *,
        context: cfg.RuntimeContext,
        job_id: str,
    ) -> Optional[str]:
        if input_file:
            resolved = cfg.resolve_file_path(input_file, context.books_dir)
            if resolved is not None and resolved.exists():
                return str(resolved)
            expanded = Path(input_file).expanduser()
            if expanded.is_absolute() and expanded.exists():
                return str(expanded)

        for key in ("source_path", "source_file"):
            source_value = metadata.get(key)
            if not isinstance(source_value, str) or not source_value.strip():
                continue
            source_path = Path(source_value).expanduser()
            if source_path.is_absolute():
                if source_path.exists():
                    return str(source_path)
                continue
            try:
                candidate = self._file_locator.resolve_path(job_id, source_path)
            except ValueError:
                continue
            if candidate.exists():
                return str(candidate)
        return None

    def _resolve_content_index(
        self,
        *,
        job: PipelineJob,
        metadata: Mapping[str, Any],
        input_file: Optional[str],
        context: cfg.RuntimeContext,
        config_payload: Mapping[str, Any],
        overrides: Mapping[str, Any],
    ) -> Optional[Dict[str, Any]]:
        existing_index = metadata.get("content_index")
        if isinstance(existing_index, Mapping):
            return dict(existing_index)

        on_disk = self._load_content_index(job.job_id)
        if on_disk is not None:
            return on_disk

        if not input_file:
            return None

        refined_sentences = self._load_refined_sentences(job)
        if not refined_sentences:
            return None

        pipeline_config = build_pipeline_config(context, config_payload, overrides=overrides)
        return ingestion.build_content_index(
            input_file,
            pipeline_config,
            refined_sentences,
        )

    def _load_content_index(self, job_id: str) -> Optional[Dict[str, Any]]:
        path = self._file_locator.resolve_metadata_path(job_id, "content_index.json")
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        return dict(payload) if isinstance(payload, Mapping) else None

    def _load_refined_sentences(self, job: PipelineJob) -> Sequence[str]:
        path = self._file_locator.resolve_metadata_path(job.job_id, "sentences.json")
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                payload = None
            if isinstance(payload, list):
                return [entry for entry in payload if isinstance(entry, str)]

        if job.result is not None and job.result.refined_sentences:
            return list(job.result.refined_sentences)

        result_payload = job.result_payload or {}
        if isinstance(result_payload, Mapping):
            payload = result_payload.get("refined_sentences")
            if isinstance(payload, list):
                return [entry for entry in payload if isinstance(entry, str)]

        return []

    def _resolve_request_payload(self, job: PipelineJob) -> Dict[str, Any]:
        if job.request is not None:
            return serialize_pipeline_request(job.request)
        if job.request_payload is not None:
            return dict(job.request_payload)
        raise KeyError(job.job_id)


__all__ = ["PipelineJobMetadataRefresher"]
