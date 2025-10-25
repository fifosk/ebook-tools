from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import sys
import types
from typing import Any, Dict, Optional


def install_job_manager_stubs() -> None:
    """Install lightweight stand-ins for optional dependencies."""

    if "modules.services.pipeline_service" not in sys.modules:
        pipeline_module = types.ModuleType("modules.services.pipeline_service")

        @dataclass
        class PipelineInput:
            input_file: str = ""
            base_output_file: str = ""
            input_language: str = "en"
            target_languages: list[str] = field(default_factory=list)
            sentences_per_output_file: int = 0
            start_sentence: int = 0
            end_sentence: Optional[int] = None
            stitch_full: bool = False
            generate_audio: bool = False
            audio_mode: str = "none"
            written_mode: str = "text"
            selected_voice: str = ""
            output_html: bool = False
            output_pdf: bool = False
            generate_video: bool = False
            include_transliteration: bool = False
            tempo: float = 1.0
            book_metadata: Dict[str, Any] = field(default_factory=dict)

        @dataclass
        class PipelineRequest:
            config: Dict[str, Any]
            context: Any
            environment_overrides: Dict[str, Any]
            pipeline_overrides: Dict[str, Any]
            inputs: PipelineInput
            progress_tracker: Any = None
            stop_event: Any = None
            translation_pool: Any = None
            correlation_id: Optional[str] = None
            job_id: Optional[str] = None

        @dataclass
        class PipelineResponse:
            success: bool
            book_metadata: Dict[str, Any] = field(default_factory=dict)

        def serialize_pipeline_request(request: PipelineRequest) -> Dict[str, Any]:
            return {
                "config": dict(request.config),
                "environment_overrides": dict(request.environment_overrides),
                "pipeline_overrides": dict(request.pipeline_overrides),
                "inputs": {
                    "input_file": request.inputs.input_file,
                    "target_languages": list(request.inputs.target_languages),
                    "book_metadata": dict(request.inputs.book_metadata),
                },
            }

        def serialize_pipeline_response(response: PipelineResponse) -> Dict[str, Any]:
            return {"success": response.success, "book_metadata": dict(response.book_metadata)}

        def run_pipeline(request: PipelineRequest) -> PipelineResponse:  # pragma: no cover - defensive stub
            return PipelineResponse(success=True, book_metadata=dict(request.inputs.book_metadata))

        class PipelineService:  # pragma: no cover - minimal API surface for imports
            def __init__(self) -> None:
                self._manager = None

            def enqueue(
                self,
                request: PipelineRequest,
                *,
                user_id: Optional[str] = None,
                user_role: Optional[str] = None,
            ) -> PipelineResponse:
                return run_pipeline(request)

        pipeline_module.PipelineInput = PipelineInput
        pipeline_module.PipelineRequest = PipelineRequest
        pipeline_module.PipelineResponse = PipelineResponse
        pipeline_module.serialize_pipeline_request = serialize_pipeline_request
        pipeline_module.serialize_pipeline_response = serialize_pipeline_response
        pipeline_module.run_pipeline = run_pipeline
        pipeline_module.PipelineService = PipelineService
        sys.modules["modules.services.pipeline_service"] = pipeline_module

    if "modules.metadata_manager" not in sys.modules:
        metadata_module = types.ModuleType("modules.metadata_manager")

        def infer_metadata(*_, **__) -> Dict[str, Any]:
            return {}

        metadata_module.infer_metadata = infer_metadata
        sys.modules["modules.metadata_manager"] = metadata_module

    if "modules.translation_engine" not in sys.modules:
        translation_module = types.ModuleType("modules.translation_engine")

        class ThreadWorkerPool:
            def shutdown(self) -> None:  # pragma: no cover - defensive stub
                return None

        translation_module.ThreadWorkerPool = ThreadWorkerPool
        sys.modules["modules.translation_engine"] = translation_module

    if "modules.observability" not in sys.modules:
        observability_module = types.ModuleType("modules.observability")

        @contextmanager
        def pipeline_operation(*_, **__):
            yield

        def record_metric(*_, **__):
            return None

        def worker_pool_event(*_, **__):
            return None

        observability_module.pipeline_operation = pipeline_operation
        observability_module.record_metric = record_metric
        observability_module.worker_pool_event = worker_pool_event
        sys.modules["modules.observability"] = observability_module
