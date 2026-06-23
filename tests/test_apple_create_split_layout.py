from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATE_VIEW = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateView.swift"
)
CREATE_SECTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateSections.swift"
)
LIBRARY_SHELL = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Library"
    / "LibraryShellView.swift"
)


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _call_arguments(source: str, start: int) -> str:
    depth = 0
    for index in range(start, len(source)):
        character = source[index]
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError("Could not parse AppleBookCreateView call arguments")


def test_create_view_uses_shell_owned_mode_binding() -> None:
    source = _source(CREATE_VIEW)

    assert "@Binding var creationMode: AppleCreateMode" in source
    assert "@State private var creationMode = AppleCreateMode.generatedBook" not in source
    assert "showsInlineJobTypePicker: Bool" in source
    assert "showsJobTypePicker: showsInlineJobTypePicker" in source


def test_source_section_can_move_job_type_picker_out_of_detail_form() -> None:
    source = _source(CREATE_SECTIONS)

    assert "let showsJobTypePicker: Bool" in source
    assert "if showsJobTypePicker || creationMode != .generatedBook" in source
    assert 'Picker("Job type", selection: $creationMode)' in source
    assert '.accessibilityIdentifier("createJobTypePicker")' in source


def test_ipad_split_view_keeps_create_picker_in_detail_panel() -> None:
    source = _source(LIBRARY_SHELL)

    assert "@State private var createMode = AppleCreateMode.generatedBook" in source
    assert "createModeSidebarList" not in source
    assert 'Label("Create", systemImage: "square.and.pencil")' in source

    call_positions = [
        match.start()
        for match in re.finditer(r"AppleBookCreateView\(", source)
    ]
    assert len(call_positions) == 2
    calls = [_call_arguments(source, position) for position in call_positions]

    detail_call = next(call for call in calls if "sectionPicker: nil" in call)
    compact_call = next(call for call in calls if "sectionPicker: sectionPickerForHeader" in call)

    assert "creationMode: $createMode" in detail_call
    assert "showsInlineJobTypePicker: true" in detail_call
    assert "creationMode: $createMode" in compact_call
    assert "showsInlineJobTypePicker: true" in compact_call


def test_ipad_split_view_keeps_settings_in_detail_panel() -> None:
    source = _source(LIBRARY_SHELL)

    assert "private var detailView: some View" in source
    assert "private func browseList() -> some View" in source

    detail_settings = re.search(
        r"case \.settings:\s+PlaybackSettingsView\(",
        source,
    )
    browse_placeholder = re.search(
        r"case \.settings:\s+if isSplitLayout \{\s+placeholderView\(\s+title: \"Settings\",\s+systemImage: \"gearshape\",\s+subtitle: \"Adjust playback options in the detail panel\.\"",
        source,
    )
    browse_compact_settings = re.search(
        r"case \.settings:\s+if isSplitLayout \{.*?\} else \{\s+PlaybackSettingsView\(\s+sectionPicker: sectionPickerForHeader",
        source,
        re.DOTALL,
    )

    assert detail_settings
    assert browse_placeholder
    assert browse_compact_settings
