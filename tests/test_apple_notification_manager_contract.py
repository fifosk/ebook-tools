from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTIFICATION_MANAGER = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Services"
    / "NotificationManager.swift"
)
APP_LIFECYCLE = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "App"
    / "InteractiveReaderApp.swift"
)


def _function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        character = source[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : index]
    raise AssertionError(f"Could not find body for {signature}")


def test_notification_manager_keeps_api_configuration_for_late_device_tokens() -> None:
    source = NOTIFICATION_MANAGER.read_text(encoding="utf-8")
    lifecycle = APP_LIFECYCLE.read_text(encoding="utf-8")

    assert "private var apiConfiguration: APIClientConfiguration?" in source
    assert "NotificationManager.shared.configure(with: config)" in lifecycle

    configure_body = _function_body(
        source,
        "func configure(with configuration: APIClientConfiguration)",
    )
    assert "apiConfiguration = configuration" in configure_body
    assert configure_body.index("apiConfiguration = configuration") < configure_body.index(
        "guard let token = deviceToken else { return }"
    )

    get_config_body = _function_body(
        source,
        "private func getAPIConfiguration() async -> APIClientConfiguration?",
    )
    assert "apiConfiguration" in get_config_body
    assert "return nil" not in get_config_body

    registration_body = _function_body(source, "func handleDeviceTokenRegistration(_ token: String) async")
    assert "await registerTokenWithBackend()" in registration_body
