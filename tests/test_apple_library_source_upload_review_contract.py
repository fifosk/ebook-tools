from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIBRARY_ROUTER = ROOT / "modules" / "webapi" / "routers" / "library.py"
WEB_LIBRARY_OVERVIEW_TAB = ROOT / "web" / "src" / "pages" / "library" / "LibraryOverviewTab.tsx"
API_CLIENT_LIBRARY_JOBS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Services"
    / "APIClient+LibraryJobs.swift"
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
LIBRARY_VIEW_MODEL = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Library"
    / "LibraryViewModel.swift"
)


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_library_source_upload_route_and_web_extensions_stay_pinned() -> None:
    router_source = _source(LIBRARY_ROUTER)
    web_source = _source(WEB_LIBRARY_OVERVIEW_TAB)
    client_source = _source(API_CLIENT_LIBRARY_JOBS)

    assert '@router.post("/items/{job_id}/upload-source", response_model=LibraryItemPayload)' in router_source
    assert "file: UploadFile = File(...)" in router_source
    assert "path: AppleLibraryRuntimeContract.sourceUploadPath(encoded)" in client_source
    assert 'method: "POST"' in client_source
    assert "startAccessingSecurityScopedResource()" in client_source

    assert 'accept=".epub,.pdf,.mp4,.mkv,.mov,.webm"' in web_source


def test_apple_library_source_upload_reviews_selected_file_before_upload() -> None:
    view_source = _source(LIBRARY_VIEW)
    model_source = _source(LIBRARY_VIEW_MODEL)

    assert "@Published var isUploadingSource = false" in model_source
    assert "func uploadSource(" in model_source
    assert "uploadLibrarySource(" in model_source
    assert "upsert(updated)" in model_source

    assert "@State private var sourceUploadItem: LibraryItem?" in view_source
    assert "@State private var sourceUploadDraft: LibrarySourceUploadDraft?" in view_source
    assert ".sheet(item: $sourceUploadDraft)" in view_source
    assert "LibrarySourceUploadReviewSheet(draft: draft, viewModel: viewModel)" in view_source
    assert "sourceUploadDraft = LibrarySourceUploadDraft(item: item, fileURL: url)" in view_source
    assert "viewModel.uploadSource(" in view_source
    assert "private struct LibrarySourceUploadDraft: Identifiable" in view_source
    assert "private struct LibrarySourceUploadReviewSheet: View" in view_source

    for identifier in [
        "librarySourceUploadFilenameLabel",
        "librarySourceUploadSizeLabel",
        "librarySourceUploadConfirmButton",
    ]:
        assert identifier in view_source

    for token in [
        "UTType.pdf",
        "UTType.movie",
        "UTType.mpeg4Movie",
        'UTType(filenameExtension: "mkv")',
        'UTType(filenameExtension: "webm")',
    ]:
        assert token in view_source
