import contextlib
import json
import re
import shutil
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterator, Sequence

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

from modules import config_manager as cfg
from modules.cli import context as cli_context
from modules.epub_utils import create_epub_from_sentences
from modules.llm_client import create_client

DEFAULT_OUTPUT_DIR = Path("output/ebook")


@contextlib.contextmanager
def _cli_configuration(epub_path: Path, output_dir: Path):
    """Load CLI configuration and activate a runtime context for the test."""

    previous_context = cfg.get_runtime_context(None)
    config = cfg.load_configuration(verbose=False)

    resolved_output = output_dir.resolve()
    resolved_books = epub_path.parent.resolve()
    resolved_working = resolved_output.parent
    resolved_tmp = resolved_working / "tmp"
    resolved_tmp.mkdir(parents=True, exist_ok=True)

    overrides: Dict[str, Any] = {
        "ebooks_dir": str(resolved_books),
        "output_dir": str(resolved_output),
        "working_dir": str(resolved_working),
        "tmp_dir": str(resolved_tmp),
    }

    runtime_context = cli_context.refresh_runtime_context(config, overrides)

    config = dict(config)
    config["input_file"] = str(epub_path)
    config["ebooks_dir"] = str(resolved_books)
    config["book_title"] = config.get("book_title") or "Sample EPUB"
    config["book_author"] = config.get("book_author") or "Automated Integration Test"
    config["book_year"] = str(config.get("book_year") or "2025")
    config.setdefault(
        "book_summary", "Synthetic EPUB generated for integration verification."
    )
    config["target_languages"] = ["Arabic"]
    config["input_language"] = "English"
    config["sentences_per_output_file"] = 10
    config["start_sentence"] = 1
    config["end_sentence"] = None
    config["stitch_full"] = True
    config["generate_audio"] = True
    config["generate_video"] = True
    config["output_html"] = True
    config["output_pdf"] = False
    config["include_transliteration"] = False
    config["use_ramdisk"] = False

    config = cli_context.update_book_cover_file_in_config(
        config,
        config.get("ebooks_dir"),
        debug_enabled=config.get("debug", False),
        context=runtime_context,
    )

    try:
        yield config, overrides
    finally:
        if previous_context is None:
            cfg.clear_runtime_context()
        else:
            cfg.set_runtime_context(previous_context)


def _generate_sentences_via_ollama(count: int, config: Dict[str, Any]) -> Sequence[str]:
    """Request sample sentences from the configured Ollama endpoint."""

    model = config.get("ollama_model") or cfg.DEFAULT_MODEL
    llm_source = config.get("llm_source") or cfg.DEFAULT_LLM_SOURCE
    primary_url = config.get("ollama_url")
    local_url = config.get("ollama_local_url")
    cloud_url = config.get("ollama_cloud_url")

    placeholder_phrases = {
        "this is a sample sentence",
        "this is a sample sentense",
        "sample sentence",
    }

    with create_client(
        model=model,
        api_url=primary_url,
        llm_source=llm_source,
        local_api_url=local_url,
        cloud_api_url=cloud_url,
        allow_fallback=False,
    ) as client:
        if not client.health_check():
            pytest.skip("Ollama service unavailable; cannot generate sample sentences")

        system_prompt = (
            "You generate evaluation data for an e-book processing pipeline. "
            "Respond with JSON only."
        )
        user_prompt = (
            "Create a JSON array named sentences containing exactly "
            f"{count} distinctive English sentences about modern technology. "
            "Ensure every sentence is unique, avoids filler text, and stays under 12 words. "
            "Return only the array with no commentary."
        )

        last_error: str | None = None
        for attempt in range(1, 4):
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.8, "top_p": 0.9},
            }

            def _validator(text: str) -> bool:
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    return False
                if isinstance(data, dict) and "sentences" in data:
                    data = data["sentences"]
                if not isinstance(data, list):
                    return False
                cleaned = [
                    str(item).strip()
                    for item in data
                    if str(item).strip() and str(item).strip().lower() not in placeholder_phrases
                ]
                unique_count = len({sentence.lower() for sentence in cleaned})
                return unique_count >= count

            response = client.send_chat_request(payload, validator=_validator, timeout=180)
            if response.error:
                pytest.fail(f"Ollama sentence generation failed: {response.error}")

            raw_text = response.text.strip()
            parsed: Any
            try:
                parsed = json.loads(raw_text)
            except json.JSONDecodeError:
                start = raw_text.find("[")
                end = raw_text.rfind("]")
                if start == -1 or end == -1:
                    pytest.fail(f"Unexpected Ollama response format: {raw_text}")
                parsed = json.loads(raw_text[start : end + 1])

            if isinstance(parsed, dict):
                parsed = parsed.get("sentences")

            if not isinstance(parsed, list):
                pytest.fail(f"Ollama response missing sentence list: {parsed}")

            sentences: list[str] = []
            seen_lower: set[str] = set()
            for item in parsed:
                sentence = str(item).strip()
                if not sentence:
                    continue
                lowered = sentence.lower()
                if lowered in placeholder_phrases:
                    continue
                if lowered in seen_lower:
                    continue
                seen_lower.add(lowered)
                sentences.append(sentence)

            if len(sentences) >= count:
                print(
                    f"[ollama] Generated {len(sentences)} unique sentences on attempt {attempt}"
                )
                return sentences[:count]

            last_error = (
                f"attempt {attempt} produced {len(sentences)} unique sentences"
            )
            print(
                f"[ollama] Regenerating sentences due to insufficient variety ({last_error})"
            )

        pytest.fail(
            "Ollama returned insufficient unique sentences after multiple attempts: "
            f"{last_error}"
        )


def _purge_previous_artifacts(
    epub_path: Path, config: Dict[str, Any], overrides: Dict[str, Any]
) -> None:
    """Remove cached runtime/output artifacts from prior sample EPUB runs."""

    base_stem = epub_path.stem
    sanitized_stem = re.sub(r"[^A-Za-z0-9_.-]", "_", base_stem) or "book"

    runtime_dirname = (
        overrides.get("derived_runtime_dirname")
        or config.get("derived_runtime_dirname")
        or cfg.DERIVED_RUNTIME_DIRNAME
    )
    working_dir = Path(
        overrides.get("working_dir")
        or config.get("working_dir")
        or DEFAULT_OUTPUT_DIR.parent
    ).expanduser().resolve()
    runtime_dir = working_dir / runtime_dirname

    removed_runtime: list[Path] = []
    if runtime_dir.exists():
        refined_filename = cfg.DERIVED_REFINED_FILENAME_TEMPLATE.format(
            base_name=base_stem
        )
        candidates = {
            runtime_dir / refined_filename,
            runtime_dir / f"{sanitized_stem}_cover.jpg",
        }
        for prefix in {base_stem, sanitized_stem}:
            candidates.update(runtime_dir.glob(f"{prefix}*.json"))
        cover_path_value = config.get("book_cover_file")
        if cover_path_value:
            cover_path = Path(cover_path_value)
            potential_cover_paths = []
            if cover_path.is_absolute():
                potential_cover_paths.append(cover_path)
            else:
                potential_cover_paths.append(runtime_dir / cover_path)
            for candidate_cover in potential_cover_paths:
                if candidate_cover.exists() and candidate_cover.parent == runtime_dir:
                    candidates.add(candidate_cover)

        for candidate in candidates:
            try:
                candidate_path = Path(candidate)
            except TypeError:
                continue
            if candidate_path.exists() and candidate_path.is_file():
                candidate_path.unlink()
                removed_runtime.append(candidate_path)

    if removed_runtime:
        print(
            "[cleanup] Removed runtime artifacts: "
            + ", ".join(str(path) for path in removed_runtime)
        )

    output_dir = Path(
        overrides.get("output_dir")
        or config.get("output_dir")
        or DEFAULT_OUTPUT_DIR
    ).expanduser().resolve()

    tokens = {
        base_stem.lower(),
        sanitized_stem.lower(),
        "sample_epub",
    }
    for key in ("book_title", "book_author"):
        value = config.get(key)
        if value:
            tokens.add(value.lower())
            tokens.add(re.sub(r"\s+", "_", value).lower())

    removed_output: list[Path] = []
    if output_dir.exists():
        for child in output_dir.iterdir():
            try:
                name_lower = child.name.lower()
            except FileNotFoundError:
                continue
            if not any(token and token in name_lower for token in tokens):
                continue
            try:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
            except FileNotFoundError:
                continue
            removed_output.append(child)

    if removed_output:
        print(
            "[cleanup] Removed prior output artifacts: "
            + ", ".join(str(path) for path in removed_output)
        )


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


@pytest.mark.integration
def test_epub_job_artifacts(tmp_path):
    """Start the real web API, submit a job, and validate generated artifacts."""

    from modules.services.job_manager import PipelineJobStatus
    from modules.webapi.application import create_app
    from modules.webapi import dependencies as webapi_dependencies

    output_dir = DEFAULT_OUTPUT_DIR.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    epub_path = tmp_path / "sample.epub"

    with _cli_configuration(epub_path, output_dir) as (config, overrides):
        _purge_previous_artifacts(epub_path, config, overrides)
        sentences = _generate_sentences_via_ollama(10, config)
        for index, sentence in enumerate(sentences, start=1):
            print(f"[ollama] Sentence {index}: {sentence}")
        create_epub_from_sentences(sentences, epub_path)
        print(f"[test] Created synthetic EPUB at {epub_path}")

        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            pytest.skip("ffmpeg executable is required for media artifact validation")
        print(f"[deps] ffmpeg resolved to: {ffmpeg_path}")
        config["ffmpeg_path"] = ffmpeg_path

        environment_overrides = dict(overrides)
        environment_overrides["output_dir"] = str(output_dir)
        environment_overrides.setdefault("ebooks_dir", str(epub_path.parent.resolve()))
        environment_overrides.setdefault("working_dir", str(output_dir.parent))
        environment_overrides.setdefault(
            "tmp_dir", str((output_dir.parent / "tmp").resolve())
        )
        environment_overrides["use_ramdisk"] = False
        environment_overrides["ffmpeg_path"] = ffmpeg_path

        pipeline_overrides = {
            "pipeline_enabled": False,
            "ffmpeg_path": ffmpeg_path,
        }

        inputs = {
            "input_file": config["input_file"],
            "base_output_file": config.get("base_output_file", ""),
            "input_language": config.get("input_language"),
            "target_languages": config.get("target_languages", ["Arabic"]),
            "sentences_per_output_file": config.get("sentences_per_output_file", 10),
            "start_sentence": config.get("start_sentence", 1),
            "end_sentence": config.get("end_sentence"),
            "stitch_full": config.get("stitch_full", True),
            "generate_audio": config.get("generate_audio", True),
            "audio_mode": config.get("audio_mode", "1"),
            "written_mode": config.get("written_mode", "4"),
            "selected_voice": config.get("selected_voice", "gTTS"),
            "output_html": config.get("output_html", True),
            "output_pdf": config.get("output_pdf", False),
            "generate_video": config.get("generate_video", True),
            "include_transliteration": config.get("include_transliteration", False),
            "tempo": config.get("tempo", 1.0),
            "book_metadata": {
                "book_title": config.get("book_title"),
                "book_author": config.get("book_author"),
                "book_year": config.get("book_year"),
                "book_summary": config.get("book_summary"),
                "book_cover_file": config.get("book_cover_file"),
            },
        }

        if inputs["target_languages"] != ["Arabic"]:
            pytest.fail(
                "Integration test must submit Arabic as the target language for verification"
            )

        payload = {
            "config": config,
            "environment_overrides": environment_overrides,
            "pipeline_overrides": pipeline_overrides,
            "inputs": inputs,
        }

        webapi_dependencies.get_pipeline_service.cache_clear()
        app = create_app()

        host = "127.0.0.1"
        port = _free_port()
        base_url = f"http://{host}:{port}"

        print(f"[webapi] Starting FastAPI server at {base_url}")
        print("[webapi] Job payload:")
        print(json.dumps(payload, indent=2, default=str))

        job_id: str | None = None
        latest_status: Dict[str, Any] | None = None

        with _run_webapi(app, host, port):
            _wait_for_healthcheck(base_url)

            response = requests.post(f"{base_url}/pipelines/", json=payload, timeout=30)
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
    result_payload = latest_status.get("result")
    if not result_payload:
        pytest.fail(f"Pipeline status missing result payload: {latest_status}")

    base_dir_value = result_payload.get("base_dir")
    if not base_dir_value:
        pytest.fail(f"Pipeline result missing base directory: {result_payload}")
    base_dir = Path(base_dir_value).resolve()
    if not base_dir.exists():
        pytest.fail(f"Pipeline base directory does not exist: {base_dir}")

    stitched_documents = result_payload.get("stitched_documents") or {}
    html_path_value = stitched_documents.get("html") or stitched_documents.get("epub")
    html_path: Path | None = Path(html_path_value) if html_path_value else None
    if not html_path or not html_path.exists():
        candidates = list(base_dir.glob("*.html")) or list(base_dir.glob("*.epub"))
        html_path = candidates[0] if candidates else None
    if not html_path:
        pytest.fail(
            "Pipeline result missing stitched document paths and no HTML/EPUB files were "
            f"found in {base_dir}: {stitched_documents}"
        )
    if not html_path.exists():
        pytest.fail(f"HTML artifact not found at {html_path}")

    audio_path_value = result_payload.get("stitched_audio_path")
    mp3_path: Path | None = Path(audio_path_value) if audio_path_value else None
    if not mp3_path or not mp3_path.exists():
        mp3_candidates = sorted(base_dir.glob("*.mp3"))
        mp3_path = mp3_candidates[0] if mp3_candidates else None
    if not mp3_path:
        pytest.fail(
            "Pipeline result missing stitched audio path and no MP3 files were found "
            f"in {base_dir}: {result_payload}"
        )
    if not mp3_path.exists():
        pytest.fail(f"MP3 artifact not found at {mp3_path}")

    video_path_value = result_payload.get("stitched_video_path")
    mp4_path: Path | None = Path(video_path_value) if video_path_value else None
    if not mp4_path or not mp4_path.exists():
        mp4_candidates = sorted(base_dir.glob("*.mp4"))
        mp4_path = mp4_candidates[0] if mp4_candidates else None
    if not mp4_path:
        pytest.fail(
            "Pipeline result missing stitched video path and no MP4 files were found "
            f"in {base_dir}: {result_payload}"
        )
    if not mp4_path.exists():
        pytest.fail(f"MP4 artifact not found at {mp4_path}")

    batch_videos = result_payload.get("batch_video_files") or []
    if batch_videos:
        existing_batches = [path for path in batch_videos if Path(path).exists()]
        print(f"[artifacts] Batch video segments located: {existing_batches}")

    print(
        f"[artifacts] HTML generated at {html_path} ({html_path.stat().st_size} bytes)"
    )
    print(f"[artifacts] MP3 generated at {mp3_path} ({mp3_path.stat().st_size} bytes)")
    print(f"[artifacts] MP4 generated at {mp4_path} ({mp4_path.stat().st_size} bytes)")

    print(f"[webapi] Artifact directory ready for inspection: {base_dir}")
    for path in sorted(base_dir.iterdir()):
        print(f"[webapi] - {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":  # pragma: no cover - convenience for direct execution
    raise SystemExit(pytest.main([__file__]))
