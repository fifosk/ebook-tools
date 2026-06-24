from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIBRARY_MODEL = (
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


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_library_item_decodes_source_fields_for_apple_diagnostics() -> None:
    model_source = _source(LIBRARY_MODEL)

    assert "struct LibraryItem: Decodable, Identifiable" in model_source
    for field in [
        "let itemType: String",
        "let status: String",
        "let mediaCompleted: Bool",
        "let updatedAt: String",
        "let sourcePath: String?",
        "let metadata: [String: JSONValue]?",
    ]:
        assert field in model_source


def test_apple_library_rows_surface_read_only_source_diagnostics() -> None:
    view_source = _source(LIBRARY_VIEW)

    assert "@State private var sourceDiagnosticsItem: LibrarySourceDiagnosticsDraft?" in view_source
    assert ".sheet(item: $sourceDiagnosticsItem)" in view_source
    assert "LibrarySourceDiagnosticsSheet(draft: draft)" in view_source
    assert "sourceDiagnosticsAction(for: item)" in view_source
    assert 'Label("Source Details", systemImage: "info.circle")' in view_source
    assert "sourceDiagnosticsItem = LibrarySourceDiagnosticsDraft(item: item)" in view_source
    assert "private struct LibrarySourceDiagnosticsDraft: Identifiable" in view_source
    assert "private struct LibrarySourceDiagnosticsSheet: View" in view_source

    diagnostics_sheet = view_source.split("private struct LibrarySourceDiagnosticsSheet: View", 1)[1].split(
        "#if os(iOS)",
        1,
    )[0]
    assert "viewModel.uploadSource(" not in diagnostics_sheet
    assert "Replace Source File" not in diagnostics_sheet

    for label in [
        'LabeledContent("Stored"',
        'LabeledContent("File"',
        'LabeledContent("Type"',
        'LabeledContent("Relative path"',
        'LabeledContent("Updated"',
    ]:
        assert label in view_source

    for identifier in [
        "librarySourceDiagnosticsStoredLabel",
        "librarySourceDiagnosticsFilenameLabel",
        "librarySourceDiagnosticsTypeLabel",
        "librarySourceDiagnosticsPathLabel",
    ]:
        assert identifier in view_source
