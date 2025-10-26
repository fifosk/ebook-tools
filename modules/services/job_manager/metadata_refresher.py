"""Utilities for refreshing pipeline job metadata."""

from __future__ import annotations

import copy
from typing import Any, Dict

from ... import config_manager as cfg
from ... import metadata_manager
from ..pipeline_service import (
    serialize_pipeline_request,
    serialize_pipeline_response,
)
from ..pipeline_types import PipelineMetadata
from .job import PipelineJob


class PipelineJobMetadataRefresher:
    """Reconcile metadata for persisted pipeline jobs."""

    def refresh(self, job: PipelineJob) -> Dict[str, Any]:
        """Update ``job`` metadata in-place and return the inferred payload."""

        request_payload = self._resolve_request_payload(job)
        inputs_payload = dict(request_payload.get("inputs", {}))
        input_file = str(inputs_payload.get("input_file") or "").strip()
        if not input_file:
            raise ValueError(
                f"Job {job.job_id} does not include an input file for metadata refresh"
            )

        existing_metadata = inputs_payload.get("book_metadata")
        if not isinstance(existing_metadata, dict):
            existing_metadata = {}

        config_payload = request_payload.get("config")
        if not isinstance(config_payload, dict):
            config_payload = {}

        environment_overrides = request_payload.get("environment_overrides")
        if not isinstance(environment_overrides, dict):
            environment_overrides = {}

        context = cfg.build_runtime_context(
            dict(config_payload),
            dict(environment_overrides),
        )
        cfg.set_runtime_context(context)
        try:
            metadata = metadata_manager.infer_metadata(
                input_file,
                existing_metadata=dict(existing_metadata),
                force_refresh=True,
            )
        finally:
            try:
                cfg.cleanup_environment(context)
            finally:
                cfg.clear_runtime_context()

        inputs_payload["book_metadata"] = dict(metadata)
        request_payload["inputs"] = inputs_payload

        if job.request is not None:
            job.request.inputs.book_metadata = PipelineMetadata.from_mapping(metadata)
        job.request_payload = request_payload
        job.resume_context = copy.deepcopy(request_payload)

        if job.result is not None:
            job.result.metadata = PipelineMetadata.from_mapping(metadata)
            job.result_payload = serialize_pipeline_response(job.result)
        else:
            result_payload = dict(job.result_payload or {})
            result_payload["book_metadata"] = dict(metadata)
            job.result_payload = result_payload

        return dict(metadata)

    def _resolve_request_payload(self, job: PipelineJob) -> Dict[str, Any]:
        if job.request is not None:
            return serialize_pipeline_request(job.request)
        if job.request_payload is not None:
            return dict(job.request_payload)
        raise KeyError(job.job_id)


__all__ = ["PipelineJobMetadataRefresher"]
