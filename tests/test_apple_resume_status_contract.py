from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BROWSE_RESUME_HELPERS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Shared"
    / "BrowseResumeHelpers.swift"
)


def test_browse_resume_status_surfaces_local_cloud_and_synced_badges() -> None:
    source = BROWSE_RESUME_HELPERS.read_text(encoding="utf-8")

    assert "let localEntry = availability.hasLocal ? availability.localEntry : nil" in source
    assert "let cloudEntry = availability.hasCloud ? availability.cloudEntry : nil" in source
    assert 'return .local(label: resumeLabel(prefix: "L", entry: local))' in source
    assert 'return .cloud(label: resumeLabel(prefix: "C", entry: cloud))' in source
    assert 'return .both(label: resumeLabel(prefix: "B", entry: freshestEntry(local, cloud)))' in source


def test_browse_resume_status_uses_freshest_synced_entry() -> None:
    source = BROWSE_RESUME_HELPERS.read_text(encoding="utf-8")

    assert "private static func freshestEntry(" in source
    assert "first.updatedAt >= second.updatedAt ? first : second" in source
