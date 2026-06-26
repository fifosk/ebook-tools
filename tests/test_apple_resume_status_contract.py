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
PLAYBACK_RESUME_STORE = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Services"
    / "PlaybackResumeStore.swift"
)
LIBRARY_VIEW = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Library"
    / "LibraryView.swift"
)
JOBS_VIEW = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Jobs"
    / "JobsView.swift"
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
    assert "private static func freshestAvailableEntry(_ availability: PlaybackResumeAvailability)" in source
    assert "let entry = freshestAvailableEntry(availability)" in source
    assert "return freshestEntry(local, cloud)" in source
    assert "availability.cloudEntry ?? availability.localEntry" not in source


def test_browse_resume_refresh_batches_backend_visible_rows() -> None:
    helper_source = BROWSE_RESUME_HELPERS.read_text(encoding="utf-8")
    store_source = PLAYBACK_RESUME_STORE.read_text(encoding="utf-8")
    library_source = LIBRARY_VIEW.read_text(encoding="utf-8")
    jobs_source = JOBS_VIEW.read_text(encoding="utf-8")

    assert "visibleItemTypesByJobID: [String: String] = [:]" in helper_source
    assert "PlaybackResumeStore.shared.refreshFromAPI(" in helper_source
    assert "jobIds: Array(visibleItemTypesByJobID.keys)" in helper_source
    assert "func refreshFromAPI(jobIds: [String], itemTypes: [String: String]) async" in store_source
    assert "client.fetchResumePositions(jobIds: cleanedJobIds)" in store_source
    assert "for apiEntry in response.entries" in store_source
    assert "mergeAPIResumeEntry(apiEntry, itemType: itemType)" in store_source
    assert "visibleItemTypesByJobID: visibleResumeItemTypesByJobID()" in library_source
    assert "viewModel.filteredItems.reduce(into: [:])" in library_source
    assert "visibleItemTypesByJobID: visibleResumeItemTypesByJobID()" in jobs_source
    assert "viewModel.filteredJobs.reduce(into: [:])" in jobs_source
