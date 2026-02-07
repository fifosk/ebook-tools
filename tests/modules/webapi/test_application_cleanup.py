from pathlib import Path

from modules.webapi.application import _cleanup_empty_job_folders

import pytest

pytestmark = pytest.mark.webapi


def test_cleanup_empty_job_folders_prunes_only_empty_dirs(tmp_path: Path) -> None:
    empty_job = tmp_path / "empty-job"
    empty_job.mkdir()

    populated_job = tmp_path / "populated-job"
    populated_job.mkdir()
    media_dir = populated_job / "media"
    media_dir.mkdir()
    (media_dir / "clip.mp4").write_bytes(b"\x00")

    removed = _cleanup_empty_job_folders(storage_root=tmp_path)

    assert removed == 1
    assert not empty_job.exists()
    assert populated_job.exists()
