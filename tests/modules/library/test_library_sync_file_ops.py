from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.library.sync import file_ops

pytestmark = pytest.mark.library


def test_load_metadata_uses_safe_stat_for_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_root = tmp_path / "job-1"
    metadata_path = job_root / "metadata" / "job.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps({"job_id": "job-1"}), encoding="utf-8")
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path == metadata_path:
            raise AssertionError("library metadata manifest should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    assert file_ops.load_metadata(job_root) == {"job_id": "job-1"}
