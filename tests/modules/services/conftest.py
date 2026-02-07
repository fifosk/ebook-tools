"""Shared fixtures for service-layer tests (job manager, pipeline, etc.)."""

from __future__ import annotations

from typing import Callable

import pytest

import modules.services.job_manager.manager as manager_module


# ---------------------------------------------------------------------------
# Test doubles shared across job-manager test files
# ---------------------------------------------------------------------------


class DummyExecutor:
    """Drop-in replacement for ``ThreadPoolExecutor`` that records submissions."""

    def __init__(self, *_, **__):
        self.submitted: list[tuple[Callable[..., object], tuple[object, ...], dict[str, object]]] = []

    def submit(self, fn: Callable[..., object], *args: object, **kwargs: object) -> None:
        self.submitted.append((fn, args, kwargs))
        return None

    def shutdown(self, wait: bool = True) -> None:  # noqa: ARG002
        self.submitted.clear()


class DummyWorkerPool:
    """No-op worker pool for tests that don't exercise translation concurrency."""

    def shutdown(self) -> None:
        return None
