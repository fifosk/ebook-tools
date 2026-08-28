from __future__ import annotations

import os
from pathlib import Path

import pytest

from modules.services.youtube_dubbing import service as service_module

pytestmark = pytest.mark.services


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
