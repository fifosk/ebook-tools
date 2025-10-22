import contextlib
import json
import shutil
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterator, Sequence, Tuple

import pytest

# Ensure the local ``modules`` package is imported even if another dependency
# injected a top-level ``modules`` module into ``sys.modules`` earlier in the
# session (which can confuse Python into thinking the package is not
# importable). Removing any pre-existing entry guarantees the repository's
# package is the one that gets imported below.
sys.modules.pop("modules", None)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

requests = pytest.importorskip("requests")
uvicorn = pytest.importorskip("uvicorn")

from modules.epub_utils import create_epub_from_sentences
from modules.services.job_manager import PipelineJobStatus
from modules.webapi.application import create_app
from modules.webapi import dependencies as webapi_dependencies

CONFIG_PATH = Path("conf/config.local.json")
FALLBACK_CONFIG_PATH = Path("conf/config.json")

DEFAULT_OUTPUT_DIR = Path("output/ebook")


def _load_config() -> Dict[str, Any]:
    config_path = CONFIG_PATH if CONFIG_PATH.exists() else FALLBACK_CONFIG_PATH
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as handle:
            loaded_config: Dict[str, Any] = json.load(handle)
        return loaded_config
    return {}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextlib.contextmanager
def _run_webapi(app, host: str, port: int) -> Iterator[uvicorn.Server]:
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, name="uvicorn-test-server", daemon=True)
    thread.start()

    try:
        started = getattr(server, "started", None)
        deadline = time.time() + 30
        while time.time() < deadline:
            if started is not None and getattr(started, "is_set", lambda: False)():
                break
            try:
                with socket.create_connection((host, port), timeout=0.5):
                    break
            except OSError:
                pass
            if not thread.is_alive():
                raise RuntimeError("Uvicorn server terminated during startup")
            time.sleep(0.1)
        else:
            raise TimeoutError("Timed out waiting for uvicorn to start")
        yield server
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        if thread.is_alive():  # pragma: no cover - indicates an unexpected shutdown hang
            raise RuntimeError("Uvicorn server thread did not terminate cleanly")


def _wait_for_healthcheck(base_url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    url = f"{base_url}/_health"
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=5)
        except requests.RequestException:
            time.sleep(0.5)
            continue
        if response.status_code == 200:
            return
        time.sleep(0.5)
    raise TimeoutError("Web API healthcheck did not return success in time")


@contextlib.contextmanager
def _patch_media_generation() -> Iterator[None]:
    """Patch translation and TTS layers with deterministic test doubles."""

    monkeypatch = pytest.MonkeyPatch()

    from modules.audio import tts as tts_module
    from modules.core import translation as translation_module
    from modules.translation_engine import TranslationTask
    from pydub.generators import Sine

    def _synthesized_segment(text: str, lang_code: str, selected_voice: str, macos_speed: int):
        duration_ms = max(400, min(len(text.split()) * 180, 2000))
        base_freq = 440 if lang_code.lower().startswith("en") else 554
        tone = Sine(base_freq).to_audio_segment(duration=duration_ms)
        return tone.set_channels(1).set_frame_rate(44100)

    def _translate_batch(
        sentences: Sequence[str],
        input_language: str,
        target_languages: Sequence[str] | str,
        **_: Any,
    ) -> list[str]:
        if isinstance(target_languages, str):
            targets = [target_languages] * len(sentences)
        else:
            targets = list(target_languages)
            if len(targets) < len(sentences):
                if targets:
                    targets.extend([targets[-1]] * (len(sentences) - len(targets)))
                else:
                    targets = [""] * len(sentences)
        results: list[str] = []
        for sentence, target in zip(sentences, targets):
            results.append(sentence if target in {input_language, "", None} else sentence)
        return results

    def _transliterate_sentence(_: str, __: str, **___: Any) -> str:
        return ""

    def _start_translation_pipeline(
        sentences: Sequence[str],
        input_language: str,
        target_sequence: Sequence[str],
        *,
        start_sentence: int,
        output_queue,
        consumer_count: int,
        **__: Any,
    ) -> threading.Thread:
        def _producer() -> None:
            for index, (sentence, target) in enumerate(zip(sentences, target_sequence)):
                task = TranslationTask(
                    index=index,
                    sentence_number=start_sentence + index,
                    sentence=sentence,
                    target_language=target,
                    translation=sentence if target in {input_language, "", None} else sentence,
                )
                output_queue.put(task)
            for _ in range(consumer_count):
                output_queue.put(None)

        thread = threading.Thread(
            target=_producer,
            name="test-translation-producer",
            daemon=True,
        )
        thread.start()
        return thread

    monkeypatch.setattr(tts_module, "synthesize_segment", _synthesized_segment)
    monkeypatch.setattr(translation_module, "translate_batch", _translate_batch)
    monkeypatch.setattr(translation_module, "transliterate_sentence", _transliterate_sentence)
    monkeypatch.setattr(translation_module, "start_translation_pipeline", _start_translation_pipeline)

    try:
        yield
    finally:
        monkeypatch.undo()


@pytest.mark.integration
def test_epub_job_artifacts(tmp_path):
    """Start the real web API, submit a job, and validate generated artifacts."""

    config = _load_config()
    output_dir = DEFAULT_OUTPUT_DIR
    if config.get("api", {}).get("output_dir"):
        output_dir = Path(config["api"]["output_dir"]).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    sentences = [f"Sample sentence {i + 1} for testing." for i in range(10)]
    epub_path = tmp_path / "sample.epub"
    create_epub_from_sentences(sentences, epub_path)
    print(f"[test] Created synthetic EPUB at {epub_path}")

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        pytest.skip("ffmpeg executable is required for media artifact validation")
    print(f"[deps] ffmpeg resolved to: {ffmpeg_path}")

    webapi_dependencies.get_pipeline_service.cache_clear()
    app = create_app()

    host = "127.0.0.1"
    port = _free_port()
    base_url = f"http://{host}:{port}"

    payload = {
        "config": {"output_dir": str(output_dir)},
        "environment_overrides": {},
        "pipeline_overrides": {
            "pipeline_enabled": False,
            "ffmpeg_path": ffmpeg_path,
        },
        "inputs": {
            "input_file": str(epub_path),
            "base_output_file": "",
            "input_language": "English",
            "target_languages": ["English"],
            "sentences_per_output_file": 10,
            "start_sentence": 1,
            "end_sentence": None,
            "stitch_full": True,
            "generate_audio": True,
            "audio_mode": "1",
            "written_mode": "4",
            "selected_voice": "gTTS",
            "output_html": True,
            "output_pdf": False,
            "generate_video": True,
            "include_transliteration": False,
            "tempo": 1.0,
            "book_metadata": {},
        },
    }

    print(f"[webapi] Starting FastAPI server at {base_url}")
    print("[webapi] Job payload:")
    print(json.dumps(payload, indent=2))

    job_id: str | None = None
    latest_status: Dict[str, Any] | None = None

    with _patch_media_generation():
        with _run_webapi(app, host, port):
            _wait_for_healthcheck(base_url)

            response = requests.post(f"{base_url}/pipelines", json=payload, timeout=30)
            assert response.status_code == 202, response.text
            submission = response.json()
            job_id = submission["job_id"]
            print(
                f"[webapi] Job accepted with id={job_id}, initial status={submission['status']}"
            )

            status_url = f"{base_url}/pipelines/{job_id}"
            for attempt in range(1, 61):
                poll_response = requests.get(status_url, timeout=30)
                latest_status = poll_response.json()
                status_value = latest_status["status"]
                error_message = latest_status.get("error")
                print(
                    f"[webapi] Poll {attempt}: status={status_value}, error={error_message!r}"
                )
                if status_value == PipelineJobStatus.COMPLETED.value:
                    break
                if status_value == PipelineJobStatus.FAILED.value:
                    pytest.fail(f"Pipeline job failed: {error_message}")
                time.sleep(1)
            else:  # pragma: no cover - indicates timeout behaviour
                pytest.fail("Pipeline job did not complete within expected time")

    assert job_id is not None
    assert latest_status is not None
    job_dir = output_dir / job_id
    expected_files = ["output.html", "output.mp3", "output.mp4"]
    missing: Tuple[str, ...] = tuple(
        name for name in expected_files if not (job_dir / name).exists()
    )
    if missing:
        pytest.fail(f"Missing artifacts in {job_dir}: {missing}")

    html_path, mp3_path, mp4_path = (job_dir / "output.html", job_dir / "output.mp3", job_dir / "output.mp4")
    print(f"[artifacts] HTML generated at {html_path} ({html_path.stat().st_size} bytes)")
    print(f"[artifacts] MP3 generated at {mp3_path} ({mp3_path.stat().st_size} bytes)")
    print(f"[artifacts] MP4 generated at {mp4_path} ({mp4_path.stat().st_size} bytes)")

    print(f"[webapi] Artifact directory ready for inspection: {job_dir}")
    for path in sorted(job_dir.iterdir()):
        print(f"[webapi] - {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":  # pragma: no cover - convenience for direct execution
    raise SystemExit(pytest.main([__file__]))
