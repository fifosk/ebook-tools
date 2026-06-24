from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
TESTING_DOC = ROOT / "docs" / "testing.md"
PLAN_DOC = ROOT / "docs" / "plans" / "cross-surface-parity-and-optimization.md"


def _target_block(makefile: str, target: str) -> str:
    return makefile.split(f"{target}:", 1)[1].split("\n\n", 1)[0]


def test_create_book_focused_web_target_covers_create_page_tests() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-web-create-book-focused" in makefile
    block = _target_block(makefile, "test-web-create-book-focused")
    assert "npm --prefix web test -- --run" in block
    assert "src/pages/__tests__/CreateBookPage.test.tsx" in block
    assert "src/pages/__tests__/createBookPageUtils.test.ts" in block


def test_create_intake_focused_web_target_covers_intake_surfaces() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-web-create-intake-focused" in makefile
    block = _target_block(makefile, "test-web-create-intake-focused")
    assert "npm --prefix web test -- --run" in block
    assert "src/components/__tests__/createIntakeStatusUtils.test.ts" in block
    assert "src/components/__tests__/BookNarrationForm.test.tsx" in block
    assert "src/pages/__tests__/VideoDubbingPage.test.tsx" in block


def test_library_focused_web_target_covers_library_metadata() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-web-library-focused" in makefile
    block = _target_block(makefile, "test-web-library-focused")
    assert "npm --prefix web test -- --run" in block
    assert "src/pages/__tests__/libraryPageMetadata.test.ts" in block


def test_video_dubbing_focused_web_target_covers_split_hooks() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-web-video-dubbing-focused" in makefile
    block = _target_block(makefile, "test-web-video-dubbing-focused")
    assert "npm --prefix web test -- --run" in block
    assert "src/pages/__tests__/videoDubbingUtils.test.ts" in block
    assert "src/pages/__tests__/useVideoDubbingSelectionState.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingMetadata.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingLanguageState.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingVoiceState.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingModelState.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingOutputState.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingSubtitleExtraction.test.tsx" in block
    assert "src/pages/__tests__/useVideoDubbingLibraryState.test.tsx" in block


def test_docs_publish_video_dubbing_focused_web_target() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")
    plan = PLAN_DOC.read_text(encoding="utf-8")

    assert "make test-web-video-dubbing-focused" in docs
    assert "test-web-video-dubbing-focused" in plan


def test_subtitle_tool_focused_web_target_covers_split_hooks() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-web-subtitle-tool-focused" in makefile
    block = _target_block(makefile, "test-web-subtitle-tool-focused")
    assert "npm --prefix web test -- --run" in block
    assert "src/pages/__tests__/subtitleToolUtils.test.ts" in block
    assert "src/pages/__tests__/subtitleJobPresentation.test.ts" in block
    assert "src/pages/__tests__/subtitleJobUtils.test.ts" in block
    assert "src/pages/__tests__/subtitleMetadataUtils.test.ts" in block
    assert "src/pages/__tests__/subtitleSourceUtils.test.ts" in block
    assert "src/pages/__tests__/useSubtitleTvMetadata.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleSources.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleJobResults.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleModels.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleLanguageDefaults.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleShowOriginalPreference.test.tsx" in block
    assert "src/pages/__tests__/useSubtitlePrefill.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleLanguageState.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleSubmitFeedback.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleSourceMode.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleProcessingOptions.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleTabState.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleSubmitStatus.test.tsx" in block
    assert "src/pages/__tests__/useSubtitleSubmit.test.tsx" in block


def test_docs_publish_subtitle_tool_focused_web_target() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")
    plan = PLAN_DOC.read_text(encoding="utf-8")

    assert "make test-web-subtitle-tool-focused" in docs
    assert "test-web-subtitle-tool-focused" in plan


def test_app_view_deeplink_focused_web_target_covers_deeplink_utils() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "test-web-app-view-deeplink-focused" in makefile
    block = _target_block(makefile, "test-web-app-view-deeplink-focused")
    assert "npm --prefix web test -- --run" in block
    assert "src/utils/__tests__/appViewDeepLink.test.ts" in block


def test_docs_publish_all_repo_owned_focused_web_targets() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")

    for command in [
        "make test-web-create-book-focused",
        "make test-web-create-intake-focused",
        "make test-web-library-focused",
        "make test-web-video-dubbing-focused",
        "make test-web-subtitle-tool-focused",
        "make test-web-app-view-deeplink-focused",
    ]:
        assert command in docs
