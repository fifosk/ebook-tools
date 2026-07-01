from __future__ import annotations

import json
from pathlib import Path

import pytest

import modules.services.job_manager.highlighting_policy as highlighting_policy_module
from modules.services.job_manager.highlighting_policy import resolve_highlighting_policy

pytestmark = pytest.mark.services


def test_resolve_highlighting_policy_uses_safe_stat_for_metadata_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_root = tmp_path / "job-with-highlights"
    metadata_dir = job_root / "metadata"
    metadata_dir.mkdir(parents=True)
    (metadata_dir / "chunk_0000.json").write_text(
        json.dumps({"highlighting_policy": "estimated-char-weighted"}),
        encoding="utf-8",
    )
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs):
        if path == metadata_dir:
            raise AssertionError("highlighting metadata dirs should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    def fake_safe_stat(path: Path):
        if path == metadata_dir:
            return path.stat()
        return None

    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(highlighting_policy_module, "safe_stat", fake_safe_stat)

    assert resolve_highlighting_policy(job_root) == "estimated-char-weighted"


def test_resolve_highlighting_policy_missing_metadata_uses_safe_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_root = tmp_path / "job-without-highlights"
    metadata_dir = job_root / "metadata"
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs):
        if path == metadata_dir:
            raise AssertionError("missing highlighting metadata dirs should use safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(highlighting_policy_module, "safe_stat", lambda path: None)

    assert resolve_highlighting_policy(job_root) is None
