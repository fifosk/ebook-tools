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
APP_STATE = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "App"
    / "AppState.swift"
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
    assert "guard notificationsEnabled else { return }" in configure_body
    assert "await registerTokenWithBackend()" in configure_body
    assert configure_body.index("apiConfiguration = configuration") < configure_body.index(
        "guard notificationsEnabled else { return }"
    )

    get_config_body = _function_body(
        source,
        "private func getAPIConfiguration() async -> APIClientConfiguration?",
    )
    assert "apiConfiguration" in get_config_body
    assert "return nil" not in get_config_body

    registration_body = _function_body(source, "func handleDeviceTokenRegistration(_ token: String) async")
    assert "await registerTokenWithBackend()" in registration_body


def test_notification_toggle_controls_backend_registration_state() -> None:
    source = NOTIFICATION_MANAGER.read_text(encoding="utf-8")

    assert "let previous = oldValue" in source
    assert "await handleNotificationsEnabledChange(from: previous, to: enabled)" in source
    change_body = _function_body(
        source,
        "private func handleNotificationsEnabledChange(from oldValue: Bool, to newValue: Bool) async",
    )
    assert "guard oldValue != newValue else { return }" in change_body
    assert "registerForPushNotificationsIfNeeded()" in change_body
    assert "await registerTokenWithBackend()" in change_body
    assert "await unregisterTokenFromBackendIfPossible()" in change_body
    assert change_body.index("if newValue") < change_body.index("await unregisterTokenFromBackendIfPossible()")

    unregister_body = _function_body(
        source,
        "private func unregisterTokenFromBackendIfPossible() async",
    )
    assert "guard let token = deviceToken else" in unregister_body
    assert "guard let config = apiConfiguration else" in unregister_body
    assert "let client = APIClient(configuration: config)" in unregister_body
    assert "try await client.unregisterDeviceToken(token)" in unregister_body


def test_notification_api_configuration_is_cleared_on_sign_out() -> None:
    source = NOTIFICATION_MANAGER.read_text(encoding="utf-8")
    app_state = APP_STATE.read_text(encoding="utf-8")

    clear_body = _function_body(source, "func clearConfiguration()")
    assert "apiConfiguration = nil" in clear_body

    sign_out_body = _function_body(app_state, "func signOut()")
    assert "PlaybackResumeStore.shared.configureAPI(nil)" in sign_out_body
    assert "NotificationManager.shared.clearConfiguration()" in sign_out_body
    assert sign_out_body.index("PlaybackResumeStore.shared.configureAPI(nil)") < sign_out_body.index(
        "NotificationManager.shared.clearConfiguration()"
    )
