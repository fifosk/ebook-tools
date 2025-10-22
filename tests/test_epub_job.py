import contextlib
import json
import socket
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Dict, Iterator, Tuple
from uuid import uuid4

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

from modules.api_client import generate_pipeline_artifacts
from modules.epub_utils import create_epub_from_sentences
from modules.progress_tracker import ProgressEvent, ProgressSnapshot
from modules.services.job_manager import PipelineJobStatus
from modules.services.pipeline_service import PipelineRequest
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


class _StubPipelineJob:
    def __init__(self, job_id: str, request: PipelineRequest) -> None:
        self.job_id = job_id
        self.request = request
        self.status = PipelineJobStatus.PENDING
        now = datetime.now(timezone.utc)
        self.created_at = now
        self.started_at = None
        self.completed_at = None
        self.error_message = None
        self.last_event = None
        self.result = None
        self.result_payload = None


class StubPipelineService:
    """In-memory pipeline service used for exercising the real web API."""

    def __init__(self, output_root: Path) -> None:
        self._output_root = output_root
        self._jobs: Dict[str, _StubPipelineJob] = {}
        self._lock = threading.RLock()

    def enqueue(self, request: PipelineRequest) -> _StubPipelineJob:  # pragma: no cover - exercised in tests
        job_id = uuid4().hex
        job = _StubPipelineJob(job_id, request)
        with self._lock:
            self._jobs[job_id] = job

        worker = threading.Thread(
            target=self._process_job,
            args=(job,),
            name=f"stub-pipeline-{job_id}",
            daemon=True,
        )
        worker.start()
        return job

    def _process_job(self, job: _StubPipelineJob) -> None:
        start_time = time.perf_counter()
        with self._lock:
            job.status = PipelineJobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)

        try:
            job_dir = self._output_root / job.job_id
            sentences, artifacts = generate_pipeline_artifacts(job.request.inputs.input_file, job_dir)
            metadata = {"stage": "complete", "artifacts": {k: str(v) for k, v in artifacts.items()}}
            elapsed = max(0.0, time.perf_counter() - start_time)
            snapshot = ProgressSnapshot(completed=1, total=1, elapsed=elapsed, speed=1.0, eta=0.0)
            job.last_event = ProgressEvent(
                event_type="complete",
                snapshot=snapshot,
                timestamp=time.time(),
                metadata=MappingProxyType(metadata),
            )
            job.result_payload = {
                "success": True,
                "pipeline_config": None,
                "refined_sentences": sentences,
                "refined_updated": False,
                "written_blocks": None,
                "audio_segments": None,
                "batch_video_files": None,
                "base_dir": str(job_dir),
                "base_output_stem": job_dir.name,
                "stitched_documents": {"html": str(artifacts["html"])},
                "stitched_audio_path": str(artifacts["mp3"]),
                "stitched_video_path": str(artifacts["mp4"]),
                "book_metadata": {},
            }
            with self._lock:
                job.status = PipelineJobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
        except Exception as exc:  # pragma: no cover - defensive failure path
            metadata = {"stage": "error", "error": str(exc)}
            snapshot = ProgressSnapshot(completed=0, total=1, elapsed=0.0, speed=0.0, eta=None)
            job.last_event = ProgressEvent(
                event_type="error",
                snapshot=snapshot,
                timestamp=time.time(),
                metadata=MappingProxyType(metadata),
                error=exc,
            )
            with self._lock:
                job.status = PipelineJobStatus.FAILED
                job.completed_at = datetime.now(timezone.utc)
                job.error_message = str(exc)

    def get_job(self, job_id: str) -> _StubPipelineJob:
        with self._lock:
            try:
                return self._jobs[job_id]
            except KeyError as exc:
                raise KeyError(job_id) from exc

    def list_jobs(self) -> Dict[str, _StubPipelineJob]:  # pragma: no cover - unused helper
        with self._lock:
            return dict(self._jobs)

    def refresh_metadata(self, job_id: str) -> _StubPipelineJob:  # pragma: no cover - unused helper
        return self.get_job(job_id)


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

    stub_service = StubPipelineService(output_dir)
    webapi_dependencies.get_pipeline_service.cache_clear()
    app = create_app()
    original_override = app.dependency_overrides.get(
        webapi_dependencies.get_pipeline_service
    )
    app.dependency_overrides[webapi_dependencies.get_pipeline_service] = lambda: stub_service

    host = "127.0.0.1"
    port = _free_port()
    base_url = f"http://{host}:{port}"

    print(f"[webapi] Starting FastAPI server at {base_url}")

    job_id: str | None = None
    latest_status = None

    try:
        with _run_webapi(app, host, port):
            _wait_for_healthcheck(base_url)

            payload = {
                "config": {"output_dir": str(output_dir)},
                "environment_overrides": {},
                "pipeline_overrides": {},
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

            print("[webapi] Submitting job payload:")
            print(json.dumps(payload, indent=2))

            response = requests.post(f"{base_url}/pipelines", json=payload, timeout=30)
            assert response.status_code == 202, response.text
            submission = response.json()
            job_id = submission["job_id"]

            print(
                f"[webapi] Job accepted with id={job_id}, initial status={submission['status']}"
            )

            status_url = f"{base_url}/pipelines/{job_id}"
            max_attempts = 60
            for attempt in range(1, max_attempts + 1):
                poll_response = requests.get(status_url, timeout=15)
                latest_status = poll_response.json()
                status_value = latest_status["status"]
                error_message = latest_status.get("error")
                print(
                    f"[webapi] Poll {attempt}: status={status_value}, "
                    f"error={error_message!r}",
                )
                if status_value == PipelineJobStatus.COMPLETED.value:
                    break
                if status_value == PipelineJobStatus.FAILED.value:
                    pytest.fail(f"Pipeline job failed: {error_message}")
                time.sleep(1)
            else:  # pragma: no cover - indicates timeout behaviour
                pytest.fail("Pipeline job did not complete within expected time")
    finally:
        if original_override is None:
            app.dependency_overrides.pop(webapi_dependencies.get_pipeline_service, None)
        else:
            app.dependency_overrides[webapi_dependencies.get_pipeline_service] = (
                original_override
            )

    assert job_id is not None
    assert latest_status is not None
    job_dir = output_dir / job_id
    expected_files = ["output.html", "output.mp3", "output.mp4"]
    missing: Tuple[str, ...] = tuple(
        fname for fname in expected_files if not (job_dir / fname).exists()
    )
    if missing:
        pytest.fail(f"Missing artifacts in {job_dir}: {missing}")

    print(f"[webapi] Generated artifacts located at: {job_dir}")
    for path in sorted(job_dir.iterdir()):
        print(f"[webapi] - {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":  # pragma: no cover - convenience for direct execution
    raise SystemExit(pytest.main([__file__]))
