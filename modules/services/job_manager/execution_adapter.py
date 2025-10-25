"""Execution adapters for pipeline job scheduling."""

from __future__ import annotations

from typing import Callable

from ..pipeline_service import PipelineRequest, PipelineResponse, run_pipeline


class PipelineExecutionAdapter:
    """Wrap the pipeline runner to allow policy injection."""

    def __init__(
        self, runner: Callable[[PipelineRequest], PipelineResponse] = run_pipeline
    ) -> None:
        self._runner = runner

    def execute(self, request: PipelineRequest) -> PipelineResponse:
        """Execute ``request`` using the configured runner."""

        return self._runner(request)
