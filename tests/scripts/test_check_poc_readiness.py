from __future__ import annotations

import importlib.util
from pathlib import Path


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
        "applePipeline": {"manifestId": "ebook-tools"},
        "creation": dict(module.CREATION_DESCRIPTOR),
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
    assert "ebook-tools Apple deploy readiness passed" in capsys.readouterr().out
