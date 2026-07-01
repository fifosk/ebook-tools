from __future__ import annotations

from pathlib import Path

from modules.services import resume_service
from modules.services.file_locator import FileLocator
from modules.services.resume_service import ResumeService, normalize_resume_job_ids


class _ListLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def warning(self, message: str, *args, **kwargs) -> None:
        self.messages.append(message % args if args else message)


def _service(storage_root: Path) -> ResumeService:
    return ResumeService(file_locator=FileLocator(storage_dir=storage_root))


def test_normalize_resume_job_ids_trims_blanks_and_duplicates() -> None:
    assert normalize_resume_job_ids(
        [" job-1 ", "", "job-2", "job-1", "   ", "job-2", "job-3"]
    ) == ["job-1", "job-2", "job-3"]


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
        job_ids=[
            " job-older ",
            "",
            "job-newer",
            "job-older",
            "   ",
            "job-missing",
        ],
        limit=200,
    )

    assert [entry.job_id for entry in entries] == ["job-newer", "job-older"]
    assert entries[0].sentence == 8
    assert entries[1].position == 10.0


def test_filtered_resume_list_with_only_blank_ids_skips_storage_scan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    service = _service(tmp_path)
    service.save(
        "job-1",
        "alice",
        {
            "kind": "time",
            "updated_at": 100.0,
            "position": 10,
        },
    )

    def fail_glob(self: Path, pattern: str):  # noqa: ANN001 - pathlib monkeypatch
        raise AssertionError(
            f"blank filtered resume listing should not glob {self} with {pattern}"
        )

    monkeypatch.setattr(Path, "glob", fail_glob)

    assert service.list("alice", job_ids=["", "   "], limit=200) == []


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


def test_resume_list_uses_safe_iterdir_without_globbing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    service = _service(tmp_path)
    service.save(
        "job-1",
        "alice",
        {
            "kind": "time",
            "updated_at": 100.0,
            "position": 10,
        },
    )
    service.save(
        "job-2",
        "alice",
        {
            "kind": "sentence",
            "updated_at": 200.0,
            "sentence": 4,
            "position": 12.5,
        },
    )
    noise = service._job_path("ignored", "alice").with_suffix(".tmp")  # noqa: SLF001 - pins storage scan behavior.
    noise.write_text("{bad-json: should-not-be-read", encoding="utf-8")

    def fail_glob(self: Path, pattern: str):  # noqa: ANN001 - pathlib monkeypatch
        raise AssertionError(
            f"unfiltered resume listing should use safe_iterdir, not glob {self} with {pattern}"
        )

    monkeypatch.setattr(Path, "glob", fail_glob)

    entries = service.list("alice", limit=200)

    assert [entry.job_id for entry in entries] == ["job-2", "job-1"]
    assert entries[0].sentence == 4
    assert entries[0].position == 12.5


def test_resume_corrupt_storage_logs_token_safe_recovery_for_get(
    tmp_path: Path,
    monkeypatch,
) -> None:
    service = _service(tmp_path)
    logger = _ListLogger()
    user_id = "alice.secret@example.test"
    job_id = "secret-job-1"
    storage_path = service._job_path(job_id, user_id)  # noqa: SLF001 - pins recovery behavior.
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text("{bad-json: /nas/private/book.epub", encoding="utf-8")
    monkeypatch.setattr(resume_service, "logger", logger)

    assert service.get(job_id, user_id) is None

    logs = "\n".join(logger.messages)
    assert "Resume storage could not be loaded" in logs
    assert user_id not in logs
    assert "alice_secret_example_test" not in logs
    assert job_id not in logs
    assert str(storage_path) not in logs
    assert "/nas/private/book.epub" not in logs
    assert "bad-json" not in logs


def test_resume_corrupt_storage_logs_token_safe_recovery_for_filtered_list(
    tmp_path: Path,
    monkeypatch,
) -> None:
    service = _service(tmp_path)
    logger = _ListLogger()
    user_id = "alice.secret@example.test"
    job_id = "secret-job-2"
    storage_path = service._job_path(job_id, user_id)  # noqa: SLF001 - pins recovery behavior.
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text("{bad-json: /nas/private/episode.mp4", encoding="utf-8")
    monkeypatch.setattr(resume_service, "logger", logger)

    assert service.list(user_id, job_ids=[job_id], limit=200) == []

    logs = "\n".join(logger.messages)
    assert "Resume storage could not be loaded" in logs
    assert user_id not in logs
    assert "alice_secret_example_test" not in logs
    assert job_id not in logs
    assert str(storage_path) not in logs
    assert "/nas/private/episode.mp4" not in logs
    assert "bad-json" not in logs
