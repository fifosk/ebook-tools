from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIBRARY_ROUTER = ROOT / "modules" / "webapi" / "routers" / "library.py"
LIBRARY_SCHEMA = ROOT / "modules" / "webapi" / "schemas" / "library.py"
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


def test_backend_library_metadata_patch_contract_matches_apple_client() -> None:
    router_source = _source(LIBRARY_ROUTER)
    schema_source = _source(LIBRARY_SCHEMA)
    client_source = _source(API_CLIENT_LIBRARY_JOBS)

    assert '@router.patch("/items/{job_id}", response_model=LibraryItemPayload)' in router_source
    assert "class LibraryMetadataUpdateRequest(BaseModel)" in schema_source
    for field in ["title", "author", "genre", "language", "isbn"]:
        assert f"{field}: Optional[str]" in schema_source
        assert f"{field}: String?" in client_source
    assert "func updateLibraryMetadata(" in client_source
    assert "path: AppleLibraryRuntimeContract.itemPath(encoded)" in client_source
    assert 'method: "PATCH"' in client_source
    assert "LibraryMetadataUpdateRequest(" in client_source
    assert "return try decode(LibraryItem.self, from: data)" in client_source


def test_apple_library_metadata_edit_sheet_updates_rows() -> None:
    view_source = _source(LIBRARY_VIEW)
    model_source = _source(LIBRARY_VIEW_MODEL)

    assert "@Published var isUpdatingMetadata = false" in model_source
    assert "func updateMetadata(" in model_source
    assert "updateLibraryMetadata(" in model_source
    assert "upsert(updated)" in model_source
    assert "normalizedRequiredText" in model_source
    assert "normalizedOptionalText" in model_source

    assert "@State private var metadataEditDraft: LibraryMetadataEditDraft?" in view_source
    assert ".sheet(item: $metadataEditDraft)" in view_source
    assert "LibraryMetadataEditSheet(item: draft.item, viewModel: viewModel)" in view_source
    assert "metadataEditAction(for: item)" in view_source
    assert 'Label("Edit Metadata", systemImage: "pencil")' in view_source
    assert "private struct LibraryMetadataEditSheet: View" in view_source
    for identifier in [
        "libraryMetadataTitleField",
        "libraryMetadataAuthorField",
        "libraryMetadataGenreField",
        "libraryMetadataLanguageField",
        "libraryMetadataIsbnField",
        "libraryMetadataSaveButton",
    ]:
        assert identifier in view_source
    assert "viewModel.isUpdatingMetadata" in view_source
