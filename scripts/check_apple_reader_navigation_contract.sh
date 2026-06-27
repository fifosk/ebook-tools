#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 - <<'PY' "${ROOT_DIR}"
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
interactive_content = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerView+InteractiveContent.swift"
input_handlers = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerView+InputHandlers.swift"
transcript = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerView+Transcript.swift"
linguist = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerView+Linguist.swift"
shortcut_support = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerShortcutSupport.swift"
shortcut_dispatch = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerShortcutDispatch.swift"
shortcut_hardware = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerShortcutHardwareFallback.swift"
shortcut_focus = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerShortcutFocus.swift"
global_shortcuts = root / "ios/InteractiveReader/InteractiveReader/App/GlobalKeyboardShortcuts.swift"
platform_adapter = root / "ios/InteractiveReader/InteractiveReader/Features/Shared/PlatformAdapter.swift"


def fail(message: str) -> None:
    print(f"apple reader navigation contract failed: {message}", file=sys.stderr)
    sys.exit(1)


def read(path: Path) -> str:
    try:
        return path.read_text()
    except OSError as exc:
        fail(f"could not read {path}: {exc}")


def function_body(source: str, signature: str) -> str:
    start = source.find(signature)
    if start < 0:
        fail(f"missing function signature: {signature}")
    brace_start = source.find("{", start)
    if brace_start < 0:
        fail(f"missing function body for: {signature}")
    depth = 0
    for index in range(brace_start, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace_start + 1:index]
    fail(f"unterminated function body for: {signature}")


interactive_source = read(interactive_content)
input_source = read(input_handlers)
transcript_source = read(transcript)
linguist_source = read(linguist)
shortcut_support_source = read(shortcut_support)
shortcut_dispatch_source = read(shortcut_dispatch)
hardware_source = read(shortcut_hardware)
shortcut_focus_source = read(shortcut_focus)
global_shortcuts_source = read(global_shortcuts)
platform_adapter_source = read(platform_adapter)

keyboard_layer_start = input_source.find("var keyboardShortcutLayer: some View")
if keyboard_layer_start < 0:
    fail("missing keyboardShortcutLayer")
keyboard_layer_end = input_source.find("@ViewBuilder\n    var trackpadSwipeLayer", keyboard_layer_start)
if keyboard_layer_end < 0:
    fail("missing trackpadSwipeLayer after keyboardShortcutLayer")
keyboard_layer_body = input_source[keyboard_layer_start:keyboard_layer_end]
if "KeyboardCommandHandler(" not in keyboard_layer_body:
    fail("interactive reader must install a physical-key host")
if "if isPad" in keyboard_layer_body:
    fail("physical-key host must be installed on iPhone as well as iPad")

request_focus_body = function_body(input_source, "func requestKeyboardShortcutFocus()")
if "guard isPad else" in request_focus_body:
    fail("keyboard focus reclaim must not skip iPhone external keyboards")
if "focusedArea = .transcript" not in request_focus_body:
    fail("keyboard focus reclaim must restore transcript focus")

if "UIDevice.current.userInterfaceIdiom == .pad || UIDevice.current.userInterfaceIdiom == .phone" not in platform_adapter_source:
    fail("shared keyboard-shortcut capability must include iPhone external keyboards")

previous_pattern = r"onBubblePreviousToken:\s*\{\s*handleWordNavigation\(-1, in: chunk\)\s*\}"
next_pattern = r"onBubbleNextToken:\s*\{\s*handleWordNavigation\(1, in: chunk\)\s*\}"
if not re.search(previous_pattern, interactive_source):
    fail("lookup bubble previous-token callback must delegate directly to handleWordNavigation(-1)")
if not re.search(next_pattern, interactive_source):
    fail("lookup bubble next-token callback must delegate directly to handleWordNavigation(1)")

previous_window = interactive_source[
    interactive_source.find("onBubblePreviousToken:"):interactive_source.find("onBubbleNextToken:")
]
next_window = interactive_source[
    interactive_source.find("onBubbleNextToken:"):interactive_source.find("iPadSplitDirection:")
]
for label, window in (("previous", previous_window), ("next", next_window)):
    if "handleLinguistLookupForCurrentSelection" in window:
        fail(f"lookup bubble {label}-token callback must not start a duplicate lookup")
    if "autoLookupTask" in window:
        fail(f"lookup bubble {label}-token callback must not cancel lookup tasks directly")

previous_handler_body = function_body(input_source, "func handleKeyboardPrevious()")
next_handler_body = function_body(input_source, "func handleKeyboardNext()")
previous_sentence_handler_body = function_body(input_source, "func handleKeyboardPreviousSentence()")
next_sentence_handler_body = function_body(input_source, "func handleKeyboardNextSentence()")
for label, body, navigation in (
    ("previous", previous_handler_body, "handleKeyboardBubbleNavigateLeft()"),
    ("next", next_handler_body, "handleKeyboardBubbleNavigateRight()"),
    ("previous sentence", previous_sentence_handler_body, "handleKeyboardBubbleNavigateLeft()"),
    ("next sentence", next_sentence_handler_body, "handleKeyboardBubbleNavigateRight()"),
):
    bubble_index = body.find("if linguistBubble != nil")
    playback_index = body.find("audioCoordinator.isPlaying")
    if bubble_index < 0 or playback_index < 0 or bubble_index > playback_index:
        fail(f"iPad {label} arrow must let an open lookup bubble own navigation before playback transport")
    if navigation not in body:
        fail(f"iPad {label} arrow must route open lookup bubbles through {navigation}")

should_route_start = input_source.find("shouldNavigateBubbleWords: {")
if should_route_start < 0:
    fail("missing shouldNavigateBubbleWords broker hook")
should_route_end = input_source.find("},", should_route_start)
should_route_body = input_source[should_route_start:should_route_end]
if "linguistBubble != nil" not in should_route_body:
    fail("broker plain-arrow routing must depend on the open lookup bubble")
if "audioCoordinator.isPlaying" in should_route_body:
    fail("broker plain-arrow routing must not depend on transient playback state while a lookup bubble is open")

if "var lastPhysicalArrowDispatch: (direction: Int, timestamp: TimeInterval)?" not in shortcut_support_source:
    fail("iPad keyboard controller must keep a physical-arrow latch across duplicate input channels")
if "var physicalArrowDirection: Int?" not in shortcut_dispatch_source:
    fail("shortcut dispatch must map arrow-like shortcuts to a physical direction")
if "case .previous, .previousSentence, .extendSelectionBackward, .bubbleNavigateLeft:" not in shortcut_dispatch_source:
    fail("left-arrow physical latch must cover transport, sentence, selection, and bubble shortcuts")
if "case .next, .nextSentence, .extendSelectionForward, .bubbleNavigateRight:" not in shortcut_dispatch_source:
    fail("right-arrow physical latch must cover transport, sentence, selection, and bubble shortcuts")
if "func shouldSuppressPhysicalArrowDuplicate(" not in shortcut_dispatch_source:
    fail("shortcut dispatch must suppress duplicate physical arrow delivery")
if "now - lastPhysicalArrowDispatch.timestamp < 0.16" not in shortcut_dispatch_source:
    fail("physical-arrow duplicate suppression must use the same short dispatch window as iPad key delivery")

fallback_gate = 'source != "gc", source != "broker", hardwareKeyboardInput != nil'
immediate_latch = "shouldSuppressPhysicalArrowDuplicate(shortcut, source: source)"
fallback_index = shortcut_dispatch_source.find(fallback_gate)
latch_index = shortcut_dispatch_source.find(immediate_latch)
if fallback_index < 0 or latch_index < 0 or fallback_index > latch_index:
    fail("UIKit fallback must be scheduled before marking a physical arrow handled")
if 'shouldSuppressPhysicalArrowDuplicate(shortcut, source: "ui-backup")' not in shortcut_dispatch_source:
    fail("deferred UIKit backup must also honor the physical-arrow duplicate latch")

if "dispatchShortcut(.playPause, source: \"ui\")" not in shortcut_support_source:
    fail("Space play/pause must keep the UIKeyCommand path")
if "dispatchShortcut(.playPause, source: \"press\")" not in shortcut_support_source:
    fail("Space play/pause must keep the raw UIPress path")
if "dispatchShortcut(.playPause, source: \"input\")" not in shortcut_support_source:
    fail("Space play/pause must keep the hidden text-input fallback path")
if "post(.keyboardShortcutPlayPause)" not in global_shortcuts_source:
    fail("global keyboard broker must post Space play/pause")
if "case .keyboardSpacebar:" not in global_shortcuts_source:
    fail("global UIKit event bridge must handle Space play/pause")
if "func resetModifierState()" not in global_shortcuts_source:
    fail("global keyboard broker must expose modifier-state reset for focus reclaim")
if "refreshModifierStateFromKeyboardInput()" not in global_shortcuts_source:
    fail("global keyboard broker must resync stale GameController modifiers before routing arrows")
if "leftControlDown = keyboardInput.button(forKeyCode: .leftControl)?.isPressed == true" not in global_shortcuts_source:
    fail("global keyboard broker must clear stale left-control state from live keyboard input")
if global_shortcuts_source.find("refreshModifierStateFromKeyboardInput()") > global_shortcuts_source.find("case .spacebar:"):
    fail("global keyboard broker must resync modifiers before handling Space/arrows")
if "case .ended, .cancelled:" not in global_shortcuts_source:
    fail("global keyboard broker must observe modifier key-up/cancelled events")
if "_ = updateModifier(key.keyCode, pressed: false)" not in global_shortcuts_source:
    fail("global keyboard broker must clear modifiers from UIKit key-up events")
if "private func updateModifier(_ keyCode: UIKeyboardHIDUsage, pressed: Bool) -> Bool" not in global_shortcuts_source:
    fail("global keyboard broker must understand UIKit modifier key codes")
if "syncModifierState(from: key.modifierFlags)" not in global_shortcuts_source:
    fail("global keyboard broker must resync stale modifier state from UIKit flags")
if "private func resolvedControlModifierState(for key: UIKey) -> Bool" not in global_shortcuts_source:
    fail("global UIKit event bridge must prefer live keyboard modifier state when deciding Ctrl+Arrow")
if "if keyboardInput != nil" not in global_shortcuts_source:
    fail("global UIKit event bridge must detect when a live keyboard modifier snapshot is available")
if "return controlDown" not in global_shortcuts_source:
    fail("global UIKit event bridge must use the refreshed broker control state for Ctrl+Arrow")
if "let controlDown = resolvedControlModifierState(for: key)" not in global_shortcuts_source:
    fail("global UIKit event bridge must not trust stale UIPress modifier flags for Ctrl+Arrow")
if "case .spacebar, .leftArrow, .rightArrow, .returnOrEnter," not in global_shortcuts_source:
    fail("global GameController path must let Space play/pause through transport routing")
if "case .keyboardSpacebar, .keyboardLeftArrow, .keyboardRightArrow," not in global_shortcuts_source:
    fail("global UIKit event bridge must let Space play/pause through transport routing")
if 'case .keyboardSpacebar:\n            post(.keyboardShortcutPlayPause)' not in global_shortcuts_source:
    fail("global UIKit event bridge must map Space directly to play/pause")

if "refreshHardwareModifierState()" not in hardware_source:
    fail("local hardware fallback must resync stale modifiers before arrow routing")
if "gcLeftControlDown = hardwareKeyboardInput.button(forKeyCode: .leftControl)?.isPressed == true" not in hardware_source:
    fail("local hardware fallback must clear stale left-control state from live keyboard input")
if hardware_source.find("refreshHardwareModifierState()") > hardware_source.find("let controlDown = gcControlDown"):
    fail("local hardware fallback must resync modifiers before reading control/shift state")

reset_body = function_body(
    shortcut_focus_source,
    "func refreshShortcutFocusState()",
)
if "lastPhysicalArrowDispatch = nil" in reset_body:
    fail("focus reclaim must not clear the physical-arrow latch while duplicate key delivery can still arrive")
if "lastShortcutDispatch = nil" in reset_body:
    fail("focus reclaim must not clear recent shortcut dispatch while duplicate key delivery can still arrive")
if "PlayerKeyboardShortcutBroker.shared.resetDispatchDebounce()" in reset_body:
    fail("focus reclaim must not clear global broker debounce while duplicate key delivery can still arrive")
if "PlayerKeyboardShortcutBroker.shared.resetModifierState()" not in reset_body:
    fail("focus reclaim must clear stale global modifier state")

keyboard_lookup_body = function_body(
    input_source,
    "func handleUIKitKeyboardLookup()",
)
if "guard !audioCoordinator.isPlaying else { return }" in keyboard_lookup_body:
    fail("Enter lookup must pause and open lookup instead of being ignored while playback is active")
if "handleLinguistLookupForCurrentSelection(in: chunk)" not in keyboard_lookup_body:
    fail("Enter lookup must use the current keyboard-highlighted word selection")
if "handleLinguistLookup(in: chunk)" in keyboard_lookup_body:
    fail("Enter lookup must not bypass current selection with the generic active-sentence lookup path")

if "func wordNavigationSentenceDisplay(for chunk: InteractiveChunk)" not in transcript_source:
    fail("missing wordNavigationSentenceDisplay fallback for stale active displays")
if "func resolvedSelection(\n        in sentence: TextPlayerSentenceDisplay," not in transcript_source:
    fail("missing resolvedSelection(in:chunk:) helper")

word_navigation_body = function_body(
    transcript_source,
    "func handleWordNavigation(_ delta: Int, in chunk: InteractiveChunk) -> Bool",
)
if "wordNavigationSentenceDisplay(for: chunk)" not in word_navigation_body:
    fail("handleWordNavigation must anchor repeated bubble arrows to the selected sentence display")
if "resolvedSelection(in: sentence, chunk: chunk)" not in word_navigation_body:
    fail("handleWordNavigation must resolve selection against the anchored sentence display")
if word_navigation_body.count("handleLinguistLookupForCurrentSelection(in: chunk)") != 1:
    fail("handleWordNavigation must refresh the open lookup bubble exactly once per navigation event")

lookup_current_body = function_body(
    linguist_source,
    "func handleLinguistLookupForCurrentSelection(in chunk: InteractiveChunk)",
)
if "wordNavigationSentenceDisplay(for: chunk)" not in lookup_current_body:
    fail("current-selection lookup refresh must use wordNavigationSentenceDisplay")
if "handleLinguistLookup(in: chunk)" not in lookup_current_body:
    fail("current-selection lookup refresh must retain the single-word fallback path")

print("apple reader navigation contract checks passed")
PY
