from pathlib import Path

from modules.webapi.routes import _resolve_job_file_path


def _write_file(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"data")
    return path


def test_resolve_job_file_path_includes_files_prefix(tmp_path):
    base_dir = tmp_path / "job"
    job_id = "job-identifier"
    target = _write_file(base_dir / "files" / "segment.mp3")

    resolved = _resolve_job_file_path(base_dir, job_id, "segment.mp3")

    assert resolved == target


def test_resolve_job_file_path_handles_nested_directories(tmp_path):
    base_dir = tmp_path / "job"
    job_id = "job-identifier"
    target = _write_file(base_dir / "files" / "audio" / "clip.mp3")

    resolved = _resolve_job_file_path(base_dir, job_id, "audio/clip.mp3")

    assert resolved == target


def test_resolve_job_file_path_falls_back_to_absolute_reference(tmp_path):
    base_dir = tmp_path / "job"
    job_id = "job-identifier"
    target = _write_file(base_dir / "files" / "text" / "chapter.html")

    resolved = _resolve_job_file_path(base_dir, job_id, str(target))

    assert resolved == target


def test_resolve_job_file_path_searches_within_job_folder(tmp_path):
    base_dir = tmp_path / "job"
    job_id = "job-identifier"
    target = _write_file(base_dir / "Morgan_Housel" / "0001-0010_file.mp3")

    resolved = _resolve_job_file_path(base_dir, job_id, "0001-0010_file.mp3")

    assert resolved == target

