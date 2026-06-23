from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATE_VIEW_MODEL = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateViewModel.swift"
)


def test_create_options_404_keeps_builtin_defaults_message() -> None:
    source = CREATE_VIEW_MODEL.read_text(encoding="utf-8")

    assert "catch APIClientError.httpError(let statusCode, _) where statusCode == 404" in source
    assert "Self.creationOptionsUnavailableMessage" in source
    assert "This backend does not advertise Apple Create defaults yet." in source
    assert "Using built-in defaults" in source
    assert "Create readiness checks" in source
