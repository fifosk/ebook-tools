from __future__ import annotations

import os
from pathlib import Path

import pytest

from modules.services.youtube_dubbing import service as service_module

pytestmark = pytest.mark.services


@pytest.fixture
def video_translation_probe(monkeypatch):
    from modules.services.youtube_dubbing import translation as video
    from modules.services.youtube_dubbing.common import _AssDialogue

    monkeypatch.setattr(video, "preflight_translation", lambda *args: None)
    entries = [_AssDialogue(start=1, end=3, translation="Wait here.", original="Wait here.",
                            speech_offset=0.2, speech_duration=1.5)]

    def run(batch_size=1, **overrides):
        kwargs = dict(source_language="English", target_language="Finnish",
                      translation_batch_size=batch_size, include_transliteration=False,
                      transliterator=None, llm_model=None, tracker=None, offset=10, total_dialogues=11)
        kwargs.update(overrides)
        return video.translate_dialogues(entries, **kwargs)

    return video, entries, run


@pytest.mark.parametrize("mode", ["single", "batch_repair", "batch_exception"])
@pytest.mark.parametrize("outcome", ["exception", "annotation", "empty", "gibberish"])
@pytest.mark.parametrize("workers", [1, 2])
def test_video_exhausted_translation_never_becomes_original_success(
    monkeypatch, video_translation_probe, mode, outcome, workers,
):
    from modules.retry_annotations import format_retry_failure
    from modules.progress_tracker import ProgressTracker
    from unittest.mock import Mock

    video, entries, run = video_translation_probe
    tracker = ProgressTracker(throttle_interval=0)
    completed = Mock()
    monkeypatch.setattr(tracker, "record_step_completion", completed)
    monkeypatch.setattr(video, "_resolve_llm_worker_count", lambda count: workers)
    def batch(*args, **kwargs):
        if mode == "batch_exception":
            raise RuntimeError("transient batch error")
        return [format_retry_failure("translation", 3, reason="invalid response")]
    def translate(*args, **kwargs):
        if outcome == "exception":
            raise RuntimeError("provider-private-error")
        return {"annotation": format_retry_failure("translation", 3, reason="provider-private-error"),
                "empty": "", "gibberish": "a" * 100}[outcome]
    monkeypatch.setattr(video, "translate_batch", batch)
    monkeypatch.setattr(video, "_translate_subtitle_text", translate)

    with pytest.raises(RuntimeError, match="Translation failed for video cue 11") as error:
        run(1 if mode == "single" else 2, tracker=tracker)
    assert "provider-private-error" not in str(error.value)
    assert entries[0].translation == "Wait here."
    completed.assert_not_called()


@pytest.mark.parametrize("batch_size", [1, 2])
def test_video_translation_repair_preserves_timing_original_and_provider(
    monkeypatch, video_translation_probe, batch_size,
):
    video, entries, run = video_translation_probe
    seen = []
    monkeypatch.setattr(video, "translate_batch", lambda *args, **kwargs: [""])
    def translate(*args, **kwargs):
        seen.append(kwargs["translation_provider"])
        return "Odota täällä."
    monkeypatch.setattr(video, "_translate_subtitle_text", translate)
    result = run(batch_size, translation_provider="llm")
    assert seen == ["llm"]
    assert result[0].translation == "Odota täällä."
    assert result[0].original == entries[0].original
    assert (result[0].start, result[0].end, result[0].speech_offset, result[0].speech_duration) == (1, 3, 0.2, 1.5)


def test_video_same_language_keeps_requested_original_without_translation(monkeypatch, video_translation_probe):
    video, entries, run = video_translation_probe
    monkeypatch.setattr(video, "_translate_subtitle_text", lambda *args, **kwargs: pytest.fail("unexpected translation"))
    result = run(target_language="English")
    assert result[0].translation == entries[0].translation


@pytest.mark.parametrize("batch_size,late_preflight", [(1, False), (2, False), (2, True)])
@pytest.mark.parametrize("model", [None, "test-model"])
def test_unavailable_model_stops_video_before_per_cue_fallback(
    tmp_path, monkeypatch, batch_size, late_preflight, model,
):
    from types import SimpleNamespace
    from modules import translation_preflight as pf
    from modules.llm_client import ClientSettings, LLMClient
    from modules.services.youtube_dubbing import translation as video_translation
    from modules.services.youtube_dubbing.common import _AssDialogue

    (tmp_path / "data").mkdir()
    monkeypatch.setattr(pf.cfg, "get_runtime_context", lambda *args: SimpleNamespace(output_dir=tmp_path / "media"))
    statuses = iter(["available", "unavailable"] if late_preflight else ["unavailable"])
    monkeypatch.setattr(pf, "check_model", lambda client: (next(statuses), "Selected model unavailable"))
    client = LLMClient(ClientSettings(
        model="test-model", llm_source="cloud", api_url="https://example.invalid/v1/chat/completions"))
    monkeypatch.setattr(video_translation, "create_client", lambda **kwargs: client)
    monkeypatch.setattr("modules.llm_client_manager.create_client", lambda **kwargs: client)
    monkeypatch.setattr(LLMClient, "send_chat_request", lambda *args, **kwargs: pytest.fail("inference was scheduled"))
    monkeypatch.setattr(video_translation, "_translate_subtitle_text", lambda *args, **kwargs: pytest.fail("per-cue fallback ran"))
    with pytest.raises(pf.TranslationPreflightError, match="Selected model unavailable"):
        video_translation.translate_dialogues(
            [_AssDialogue(start=0, end=2, translation="Wait here.", original="Wait here.")],
            source_language="English", target_language="Finnish",
            translation_batch_size=batch_size, include_transliteration=False,
            transliterator=None, llm_model=model, tracker=None, offset=0, total_dialogues=1,
        )


def test_youtube_dubbing_service_uses_safe_stat_for_file_probes() -> None:
    source = Path(service_module.__file__).read_text(encoding="utf-8")

    assert ".exists(" not in source
    assert ".is_file(" not in source
    assert "_path_exists(" in source
    assert "_path_is_file(" in source


def test_resolve_partial_video_uses_safe_stat_for_completed_download(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    partial_path = tmp_path / "episode.mp4.part"
    completed_path = tmp_path / "episode.mp4"
    completed_path.write_bytes(b"video")
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs):
        if path == completed_path:
            raise AssertionError("completed .part recovery should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(service_module, "safe_stat", lambda path: os.stat(path))

    assert service_module._resolve_partial_video(partial_path) == completed_path


def test_youtube_dubbing_service_validates_inputs_with_safe_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video_path = tmp_path / "source.mp4"
    subtitle_path = tmp_path / "source.txt"
    video_path.write_bytes(b"video")
    subtitle_path.write_text("not a timed subtitle", encoding="utf-8")
    guarded_paths = {video_path, subtitle_path}
    safe_stat_calls: list[Path] = []
    original_exists = Path.exists
    original_is_file = Path.is_file

    def guarded_exists(path: Path, *args, **kwargs):
        if path in guarded_paths:
            raise AssertionError("YouTube dubbing enqueue inputs should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    def guarded_is_file(path: Path, *args, **kwargs):
        if path in guarded_paths:
            raise AssertionError("YouTube dubbing enqueue inputs should be probed via safe_stat")
        return original_is_file(path, *args, **kwargs)

    def fake_safe_stat(path: Path):
        if path in guarded_paths:
            safe_stat_calls.append(path)
        return os.stat(path)

    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(Path, "is_file", guarded_is_file)
    monkeypatch.setattr(service_module, "safe_stat", fake_safe_stat)

    service = service_module.YoutubeDubbingService(job_manager=object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="subtitle_path must reference an ASS, SRT, SUB, or VTT subtitle file"):
        service.enqueue(
            video_path,
            subtitle_path,
            target_language="nl",
            voice="gTTS",
            tempo=1.0,
            macos_reading_speed=100,
            output_dir=None,
        )

    assert safe_stat_calls == [video_path, subtitle_path]
