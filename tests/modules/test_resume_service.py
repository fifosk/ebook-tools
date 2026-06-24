from __future__ import annotations

from pathlib import Path

from modules.services.file_locator import FileLocator
from modules.services.resume_service import ResumeService


def _service(storage_root: Path) -> ResumeService:
    return ResumeService(file_locator=FileLocator(storage_dir=storage_root))


def test_filtered_resume_list_reads_requested_job_files_without_globbing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    service = _service(tmp_path)
    service.save(
        "job-older",
        "alice",
        {
            "kind": "time",
            "updated_at": 100.0,
            "position": 10,
            "media_type": "audio",
        },
    )
    service.save(
        "job-newer",
        "alice",
        {
            "kind": "sentence",
            "updated_at": 300.0,
            "sentence": 8,
            "media_type": "text",
        },
    )
    service.save(
        "job-unrequested",
        "alice",
        {
            "kind": "time",
            "updated_at": 500.0,
            "position": 50,
            "media_type": "video",
        },
    )

    def fail_glob(self: Path, pattern: str):  # noqa: ANN001 - pathlib monkeypatch
        raise AssertionError(
            f"filtered resume listing should not glob {self} with {pattern}"
        )

    monkeypatch.setattr(Path, "glob", fail_glob)

    entries = service.list(
        "alice",
        job_ids=["job-older", "job-newer", "job-older", "job-missing"],
        limit=200,
    )

    assert [entry.job_id for entry in entries] == ["job-newer", "job-older"]
    assert entries[0].sentence == 8
    assert entries[1].position == 10.0


def test_resume_list_honors_limit_and_sorts_newest_first(tmp_path: Path) -> None:
    service = _service(tmp_path)
    for index, updated_at in enumerate([100.0, 300.0, 200.0], start=1):
        service.save(
            f"job-{index}",
            "alice",
            {
                "kind": "time",
                "updated_at": updated_at,
                "position": index,
            },
        )

    entries = service.list("alice", limit=2)

    assert [entry.job_id for entry in entries] == ["job-2", "job-3"]
