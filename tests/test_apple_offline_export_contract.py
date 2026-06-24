from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPORT_SCHEMA = ROOT / "modules" / "webapi" / "schemas" / "exports.py"
API_CLIENT_LIBRARY_JOBS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Services"
    / "APIClient+LibraryJobs.swift"
)
LIBRARY_MODELS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Models"
    / "LibraryJobApiModels.swift"
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
JOBS_VIEW = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Jobs"
    / "JobsView.swift"
)
JOBS_VIEW_MODEL = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Jobs"
    / "JobsViewModel.swift"
)


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_backend_export_contract_stays_apple_compatible() -> None:
    source = _source(EXPORT_SCHEMA)

    assert 'Literal["job", "library"]' in source
    assert 'source_kind: Literal["job", "library"]' in source
    assert 'player_type: Literal["interactive-text"]' in source
    assert "download_url: str" in source
    assert "filename: str" in source


def test_apple_client_creates_offline_exports_with_backend_payload_keys() -> None:
    client_source = _source(API_CLIENT_LIBRARY_JOBS)
    model_source = _source(LIBRARY_MODELS)

    assert "struct OfflineExportResponse: Decodable, Equatable" in model_source
    assert "let exportId: String" in model_source
    assert "let downloadUrl: String" in model_source
    assert "let filename: String" in model_source
    assert "func createOfflineExport(sourceKind: String, sourceId: String)" in client_source
    assert 'path: "/api/exports"' in client_source
    assert 'case sourceKind = "source_kind"' in client_source
    assert 'case sourceId = "source_id"' in client_source
    assert 'case playerType = "player_type"' in client_source
    assert 'playerType: "interactive-text"' in client_source


def test_apple_client_supports_library_metadata_enrichment_contract() -> None:
    client_source = _source(API_CLIENT_LIBRARY_JOBS)
    model_source = _source(LIBRARY_MODELS)
    route_source = _source(ROOT / "modules" / "webapi" / "routers" / "library.py")
    schema_source = _source(ROOT / "modules" / "webapi" / "schemas" / "library.py")

    assert '@router.post("/items/{job_id}/enrich", response_model=LibraryMetadataEnrichResponse)' in route_source
    assert "class LibraryMetadataEnrichResponse(BaseModel)" in schema_source
    assert "item: LibraryItemPayload" in schema_source
    assert "enriched: bool" in schema_source
    assert "struct LibraryMetadataEnrichResponse: Decodable, Equatable" in model_source
    assert "let item: LibraryItem" in model_source
    assert "let enriched: Bool" in model_source
    assert "let confidence: String?" in model_source
    assert "let source: String?" in model_source
    assert "func enrichLibraryMetadata(jobId: String, force: Bool = false)" in client_source
    assert 'path: "/api/library/items/\\(encoded)/enrich"' in client_source
    assert "LibraryMetadataEnrichRequest(force: force)" in client_source


def test_apple_library_rows_surface_offline_export_action() -> None:
    view_source = _source(LIBRARY_VIEW)
    model_source = _source(LIBRARY_VIEW_MODEL)

    assert "@Environment(\\.openURL) private var openURL" in view_source
    assert "@Published var isCreatingExport = false" in model_source
    assert "@Published var isEnrichingMetadata = false" in model_source
    assert "func createOfflineExport(" in model_source
    assert "func enrichMetadata(" in model_source
    assert "enrichLibraryMetadata(jobId: item.jobId, force: true)" in model_source
    assert "upsert(response.item)" in model_source
    assert 'sourceKind: "library"' in model_source
    assert "resolveExportDownloadURL" in model_source
    assert "enrichMetadataAction(for: item)" in view_source
    assert "offlineExportAction(for: item)" in view_source
    assert 'Label("Enrich Metadata", systemImage: "sparkles")' in view_source
    assert 'Label("Export Offline Player", systemImage: "square.and.arrow.down")' in view_source
    assert "viewModel.isEnrichingMetadata" in view_source
    assert "!item.mediaCompleted || viewModel.isCreatingExport" in view_source
    assert 'ProgressView("Creating offline export…")' in view_source
    assert 'accessibilityIdentifier("libraryOfflineExportLoadingView")' in view_source
    assert "openURL(url)" in view_source


def test_apple_job_rows_surface_offline_export_action() -> None:
    view_source = _source(JOBS_VIEW)
    model_source = _source(JOBS_VIEW_MODEL)

    assert "@Environment(\\.openURL) private var openURL" in view_source
    assert "@Published var isCreatingExport = false" in model_source
    assert "func createOfflineExport(" in model_source
    assert 'sourceKind: "job"' in model_source
    assert "resolveExportDownloadURL" in model_source
    assert "offlineExportAction(for: job)" in view_source
    assert 'Label("Export Offline Player", systemImage: "square.and.arrow.down")' in view_source
    assert "job.isFinishedForDisplay && job.mediaCompleted == true" in view_source
    assert 'ProgressView("Creating offline export…")' in view_source
    assert 'accessibilityIdentifier("jobsOfflineExportLoadingView")' in view_source
    assert "openURL(url)" in view_source
