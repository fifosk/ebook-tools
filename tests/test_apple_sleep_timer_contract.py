from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLE = ROOT / "ios" / "InteractiveReader" / "InteractiveReader"
SHARED = APPLE / "Features" / "Shared"
INTERACTIVE = APPLE / "Features" / "InteractivePlayer"
PROJECT = ROOT / "ios" / "InteractiveReader" / "InteractiveReader.xcodeproj" / "project.pbxproj"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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


def test_sleep_timer_controller_counts_down_and_expires_on_main_actor() -> None:
    source = _source(SHARED / "SleepTimerControls.swift")

    assert "struct SleepTimerOption: Identifiable, Equatable" in source
    assert "static let presets: [SleepTimerOption]" in source
    assert 'SleepTimerOption(id: "5m", label: "5 min", seconds: 5 * 60)' in source
    assert 'SleepTimerOption(id: "45m", label: "45 min", seconds: 45 * 60)' in source
    assert "@MainActor\nfinal class SleepTimerController: ObservableObject" in source
    assert "@Published private(set) var activeOption: SleepTimerOption?" in source
    assert "@Published private(set) var remainingSeconds: Int?" in source
    assert "private var timerTask: Task<Void, Never>?" in source

    start_body = _function_body(
        source,
        "func start(option: SleepTimerOption, onExpire: @escaping @MainActor () -> Void)",
    )
    assert "cancel()" in start_body
    assert "remainingSeconds = option.seconds" in start_body
    assert "try await Task.sleep(nanoseconds: 1_000_000_000)" in start_body
    assert "self.remainingSeconds = remaining" in start_body
    assert "onExpire()" in start_body

    cancel_body = _function_body(source, "func cancel()")
    assert "timerTask?.cancel()" in cancel_body
    assert "activeOption = nil" in cancel_body
    assert "remainingSeconds = nil" in cancel_body

    assert "struct SleepTimerMenu: View" in source
    assert '.accessibilityIdentifier("sleepTimerPill")' in source


def test_interactive_player_wires_sleep_timer_across_header_and_lifecycle() -> None:
    root = _source(INTERACTIVE / "InteractivePlayerView.swift")
    pills = _source(INTERACTIVE / "InteractivePlayerView+HeaderPills.swift")
    header = _source(INTERACTIVE / "InteractivePlayerView+HeaderOverlay.swift")
    lifecycle = _source(INTERACTIVE / "InteractivePlayerView+LifecycleObservers.swift")

    assert "@StateObject var sleepTimer = SleepTimerController()" in root
    assert "var sleepTimerPillView: some View" in pills
    assert "SleepTimerMenu(" in pills
    assert "onStart: startSleepTimer" in pills
    assert "onCancel: cancelSleepTimer" in pills
    assert "func startSleepTimer(_ option: SleepTimerOption)" in pills
    assert "sleepTimer.start(option: option, onExpire: handleSleepTimerExpired)" in pills
    assert "func handleSleepTimerExpired()" in pills
    assert "audioCoordinator.pause()" in pills
    assert "readingBedCoordinator.pause()" in pills
    assert "musicCoordinator.pause()" in pills

    assert "sleepTimerPillView" in header
    assert "sleepTimer.cancel()" in lifecycle


def test_sleep_timer_file_is_registered_for_ios_and_tvos_targets() -> None:
    project = _source(PROJECT)

    assert "SleepTimerControls.swift" in project
    assert "SleepTimerControls.swift in Sources" in project
    assert project.count("SleepTimerControls.swift in Sources") >= 2
