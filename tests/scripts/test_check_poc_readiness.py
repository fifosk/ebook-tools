from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "src" / "check_poc_readiness.py"
SPEC = importlib.util.spec_from_file_location("check_poc_readiness", SCRIPT_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def build_runtime_descriptor() -> dict[str, object]:
    return {
        "status": "ok",
        "app": "ebook-tools",
        "service": "ebook-tools-api",
        "auth": dict(module.AUTH_DESCRIPTOR),
        "clientConfig": dict(module.CLIENT_CONFIG_DESCRIPTOR),
        "applePipeline": dict(module.APPLE_PIPELINE_DESCRIPTOR),
        "creation": dict(module.CREATION_DESCRIPTOR),
        "libraryActions": dict(module.LIBRARY_ACTIONS_DESCRIPTOR),
        "offlineExports": dict(module.OFFLINE_EXPORTS_DESCRIPTOR),
        "playbackState": dict(module.PLAYBACK_STATE_DESCRIPTOR),
    }


def test_runtime_descriptor_validation_accepts_public_contract() -> None:
    assert module.validate_runtime_descriptor(build_runtime_descriptor()) == []


def test_runtime_descriptor_validation_reports_missing_create_paths() -> None:
    payload = build_runtime_descriptor()
    del payload["creation"]["youtubeDubPath"]

    assert module.validate_runtime_descriptor(payload) == [
        "runtime.creation.youtubeDubPath=None expected '/api/subtitles/youtube/dub'"
    ]


def test_deploy_readiness_contract_includes_subtitle_source_cleanup_path() -> None:
    assert module.CREATION_DESCRIPTOR["subtitleDeleteSourcePath"] == "/api/subtitles/delete-source"

    payload = build_runtime_descriptor()
    del payload["creation"]["subtitleDeleteSourcePath"]

    assert module.validate_runtime_descriptor(payload) == [
        "runtime.creation.subtitleDeleteSourcePath=None expected '/api/subtitles/delete-source'"
    ]


def test_deploy_readiness_validates_library_offline_and_playback_sections() -> None:
    payload = build_runtime_descriptor()
    del payload["libraryActions"]["isbnLookupPath"]
    del payload["offlineExports"]["downloadPathTemplate"]
    del payload["playbackState"]["resumeListPath"]

    assert module.validate_runtime_descriptor(payload) == [
        "runtime.libraryActions.isbnLookupPath=None expected '/api/library/isbn/lookup'",
        "runtime.offlineExports.downloadPathTemplate=None expected '/api/exports/{export_id}/download'",
        "runtime.playbackState.resumeListPath=None expected '/api/resume'",
    ]


def test_deploy_readiness_reports_missing_runtime_sections() -> None:
    payload = build_runtime_descriptor()
    del payload["offlineExports"]

    assert module.validate_runtime_descriptor(payload) == [
        "runtime.offlineExports=<missing>"
    ]


def test_check_readiness_uses_health_then_runtime(monkeypatch) -> None:
    paths: list[str] = []

    def fake_json_request(base_url: str, path: str, *, timeout: float):
        paths.append(path)
        assert base_url == "https://api.example.test"
        assert timeout == 3.0
        if path == "/_health":
            return {"status": "ok"}
        if path == "/api/system/runtime":
            return build_runtime_descriptor()
        raise AssertionError(f"unexpected path {path}")

    monkeypatch.setattr(module, "json_request", fake_json_request)

    summary = module.check_readiness("https://api.example.test", timeout=3.0)

    assert paths == ["/_health", "/api/system/runtime"]
    assert summary["creation_paths"] == len(module.CREATION_DESCRIPTOR)
    assert summary["library_action_paths"] == len(module.LIBRARY_ACTIONS_DESCRIPTOR)
    assert summary["offline_export_paths"] == len(module.OFFLINE_EXPORTS_DESCRIPTOR)
    assert summary["playback_state_paths"] == len(module.PLAYBACK_STATE_DESCRIPTOR)
    assert summary["runtime_sections"] == len(module.RUNTIME_SECTION_DESCRIPTORS)


def test_main_accepts_legacy_shared_deploy_arguments(monkeypatch, capsys) -> None:
    seen: dict[str, object] = {}

    def fake_check_readiness(base_url: str, *, health_path: str, runtime_path: str, timeout: float):
        seen.update(
            {
                "base_url": base_url,
                "health_path": health_path,
                "runtime_path": runtime_path,
                "timeout": timeout,
            }
        )
        return {
            "base_url": base_url,
            "health_path": health_path,
            "runtime_path": runtime_path,
            "creation_paths": 21,
            "library_action_paths": 6,
            "offline_export_paths": 4,
            "playback_state_paths": 5,
            "runtime_sections": 7,
        }

    monkeypatch.setattr(module, "check_readiness", fake_check_readiness)

    status = module.main(
        [
            "--base-url",
            "https://api.example.test",
            "--remote-host",
            "mac-studio.local",
            "--use-remote-env-tokens",
            "--require-separate-read-token",
            "--require-write-token",
            "--skip-apple-build",
            "--timeout",
            "2.5",
        ]
    )

    assert status == 0
    assert seen == {
        "base_url": "https://api.example.test",
        "health_path": "/_health",
        "runtime_path": "/api/system/runtime",
        "timeout": 2.5,
    }
    output = capsys.readouterr().out
    assert "ebook-tools Apple deploy readiness passed" in output
    assert "advertised 7 Apple runtime sections" in output


def test_script_invocation_loads_runtime_descriptor_without_importing_webapi_package() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--base-url",
            "http://127.0.0.1:9",
            "--timeout",
            "0.1",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "ebook-tools Apple deploy readiness failed" in result.stderr
    assert "Traceback" not in result.stderr
    assert "ModuleNotFoundError" not in result.stderr
