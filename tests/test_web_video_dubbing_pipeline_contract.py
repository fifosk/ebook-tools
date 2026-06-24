from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
TESTING_DOC = ROOT / "docs" / "testing.md"
PLAN_DOC = ROOT / "docs" / "plans" / "cross-surface-parity-and-optimization.md"


def _target_block(makefile: str, target: str) -> str:
    return makefile.split(f"{target}:", 1)[1].split("\n\n", 1)[0]


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
