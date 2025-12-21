"""Metadata preparation and ingestion utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ... import metadata_manager
from ... import logging_manager as log_mgr
from ...core import ingestion
from ... import config_manager as cfg
from ..pipeline_types import IngestionResult, MetadataPhaseResult, PipelineMetadata

if TYPE_CHECKING:  # pragma: no cover - import for typing only
    from ..pipeline_service import PipelineRequest
    from ..pipeline_types import ConfigPhaseResult
    from ...progress_tracker import ProgressTracker

logger = log_mgr.logger


def prepare_metadata(
    request: "PipelineRequest", context: "cfg.RuntimeContext"
) -> PipelineMetadata:
    """Return metadata for ``request`` with inferred values merged in."""

    metadata = request.inputs.book_metadata.clone()
    if request.config.get("auto_metadata", True):
        try:
            input_path = cfg.resolve_file_path(
                request.inputs.input_file, context.books_dir
            )
        except Exception:  # pragma: no cover - defensive resolution
            input_path = None
        if input_path:
            existing_metadata: dict[str, Optional[str]] = {}
            for key, value in metadata.as_dict().items():
                if value is None:
                    existing_metadata[key] = None
                elif isinstance(value, str):
                    existing_metadata[key] = value
                elif isinstance(value, bool):
                    continue
                elif isinstance(value, (int, float)):
                    existing_metadata[key] = str(value)
                else:
                    continue
            try:
                inferred = metadata_manager.infer_metadata(
                    str(input_path),
                    existing_metadata=existing_metadata,
                    force_refresh=bool(
                        request.pipeline_overrides.get("force_metadata_refresh")
                        or request.pipeline_overrides.get("refresh_metadata")
                    ),
                )
            except Exception as metadata_error:  # pragma: no cover - defensive logging
                logger.debug(
                    "Metadata inference failed for %s: %s",
                    request.inputs.input_file,
                    metadata_error,
                )
            else:
                metadata.update({k: v for k, v in inferred.items() if v is not None})
    request.inputs.book_metadata = metadata
    return metadata


def run_ingestion(
    request: "PipelineRequest",
    config_result: "ConfigPhaseResult",
    metadata: PipelineMetadata,
    tracker: "ProgressTracker" | None,
) -> MetadataPhaseResult:
    """Execute ingestion and return metadata plus refined sentences."""

    refined_list, refined_updated = ingestion.get_refined_sentences(
        request.inputs.input_file,
        config_result.pipeline_config,
        force_refresh=True,
        metadata={
            "mode": "cli",
            "target_languages": request.inputs.target_languages,
            "max_words": config_result.pipeline_config.max_words,
        },
    )
    content_index = ingestion.build_content_index(
        request.inputs.input_file,
        config_result.pipeline_config,
        refined_list,
    )
    if content_index and not metadata.get("content_index"):
        metadata.update({"content_index": content_index})
    total_fully = len(refined_list)
    if tracker is not None:
        tracker.publish_progress(
            {
                "stage": "ingestion",
                "message": "Sentence ingestion complete.",
                "total_sentences": total_fully,
            }
        )

    return MetadataPhaseResult(
        metadata=metadata,
        ingestion=IngestionResult(
            refined_sentences=refined_list,
            refined_updated=refined_updated,
            total_sentences=total_fully,
        ),
    )
