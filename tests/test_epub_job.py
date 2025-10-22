import json
import os
import time
from pathlib import Path
from typing import Any, Dict

import pytest

CONFIG_PATH = Path("conf/config.local.json")

try:
    from modules.api_client import EbookToolsClient  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    EbookToolsClient = None  # type: ignore[assignment]

try:
    from modules.epub_utils import create_epub_from_sentences  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    create_epub_from_sentences = None  # type: ignore[assignment]


def _load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        pytest.skip(
            "conf/config.local.json not available; skipping end-to-end EPUB job test",
            allow_module_level=False,
        )
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.mark.integration
def test_epub_job_artifacts(tmp_path):
    """End-to-end test that synthesises a small EPUB and verifies pipeline outputs."""
    if EbookToolsClient is None:
        pytest.skip(
            "modules.api_client module not available; cannot run EPUB job integration test",
        )

    if create_epub_from_sentences is None:
        pytest.skip(
            "modules.epub_utils module not available; cannot synthesise EPUB",
        )

    if not hasattr(EbookToolsClient, "create_job") or not callable(
        getattr(EbookToolsClient, "create_job")
    ):
        pytest.skip(
            "EbookToolsClient not provided by modules.api_client; skipping end-to-end EPUB job test",
        )

    if not callable(create_epub_from_sentences):
        pytest.skip(
            "create_epub_from_sentences not provided by modules.epub_utils; skipping end-to-end EPUB job test",
        )

    config = _load_config()

    sentences = [f"Sample sentence {i + 1} for testing." for i in range(10)]
    epub_path = tmp_path / "sample.epub"
    create_epub_from_sentences(sentences, epub_path)

    client = EbookToolsClient(**config.get("api", {}))
    job_id = client.create_job(str(epub_path), config.get("job_params", {}))

    for _ in range(60):
        status = client.get_job_status(job_id)
        state = status.get("state")
        if state == "completed":
            break
        if state == "failed":
            pytest.fail(f"Job failed: {status.get('error')}")
        time.sleep(5)
    else:  # pragma: no cover - indicates timeout behaviour
        raise TimeoutError("Job did not complete in expected time")

    output_dir = config.get("output_dir", "dist")
    expected_files = ["output.html", "output.mp3", "output.mp4"]
    for fname in expected_files:
        fpath = os.path.join(output_dir, job_id, fname)
        assert os.path.exists(fpath), f"{fname} was not generated"


if __name__ == "__main__":  # pragma: no cover - convenience for direct execution
    raise SystemExit(pytest.main([__file__]))
