from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BROWSE_ACTION_ROW = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Shared"
    / "BrowseActionRow.swift"
)


def test_browse_action_row_keeps_sync_status_out_of_primary_chrome() -> None:
    source = BROWSE_ACTION_ROW.read_text(encoding="utf-8")

    assert "cloudStatusLabel" not in source
    assert 'Text("Online")' not in source
    assert 'Text("Offline")' not in source
    assert 'accessibilityLabel("Sync resume positions")' not in source
    assert 'Label("Sync Resume Positions", systemImage: "arrow.triangle.2.circlepath")' in source
    assert "refreshButton" in source
    assert "accountMenu(showsUserLabel: showsUserLabel)" in source
