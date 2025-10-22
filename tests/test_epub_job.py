import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.api_client import EbookToolsClient
from modules.epub_utils import create_epub_from_sentences

CONFIG_PATH = Path("conf/config.local.json")
FALLBACK_CONFIG_PATH = Path("conf/config.json")

DEFAULT_CONFIG = {
    "api": {
        "output_dir": "output/ebook",
    },
    "job_params": {},
}


def _load_config() -> Dict[str, Any]:
    config_path = CONFIG_PATH if CONFIG_PATH.exists() else FALLBACK_CONFIG_PATH
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as handle:
            loaded_config: Dict[str, Any] = json.load(handle)
        return loaded_config
    return DEFAULT_CONFIG.copy()


@pytest.mark.integration
def test_epub_job_artifacts(tmp_path):
    """End-to-end test that synthesises a small EPUB and verifies pipeline outputs."""
    config = _load_config()

    sentences = [f"Sample sentence {i + 1} for testing." for i in range(10)]
    epub_path = tmp_path / "sample.epub"
    create_epub_from_sentences(sentences, epub_path)

    api_config = dict(config.get("api") or {})
    api_config.setdefault("output_dir", DEFAULT_CONFIG["api"]["output_dir"])
    job_params = dict(config.get("job_params") or {})

    job_params.setdefault("input_file", str(epub_path))

    client = EbookToolsClient(**api_config)
    job_id = client.create_job(str(epub_path), job_params)

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

    output_dir = Path(api_config["output_dir"]).expanduser()
    expected_files = ["output.html", "output.mp3", "output.mp4"]
    for fname in expected_files:
        fpath = output_dir / job_id / fname
        assert fpath.exists(), f"{fname} was not generated"

    print(f"Generated artifacts available for review at: {output_dir / job_id}")


if __name__ == "__main__":  # pragma: no cover - convenience for direct execution
    raise SystemExit(pytest.main([__file__]))
