#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 - <<'PY' "${ROOT_DIR}"
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
interactive_content = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerView+InteractiveContent.swift"
interactive_view = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerView.swift"
interactive_layout = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerView+Layout.swift"
input_handlers = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerView+InputHandlers.swift"
transcript = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerView+Transcript.swift"
linguist = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerView+Linguist.swift"
selection = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerViewModel+Selection.swift"
sequence = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerViewModel+Sequence.swift"
shortcut_support = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerShortcutSupport.swift"
shortcut_dispatch = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerShortcutDispatch.swift"
shortcut_hardware = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerShortcutHardwareFallback.swift"
shortcut_focus = root / "ios/InteractiveReader/InteractiveReader/Features/InteractivePlayer/InteractivePlayerShortcutFocus.swift"
global_shortcuts = root / "ios/InteractiveReader/InteractiveReader/App/GlobalKeyboardShortcuts.swift"
platform_adapter = root / "ios/InteractiveReader/InteractiveReader/Features/Shared/PlatformAdapter.swift"
progress_footer = root / "ios/InteractiveReader/InteractiveReader/Features/Shared/PlayerProgressFooterView.swift"
transport_resolver = root / "ios/InteractiveReader/InteractiveReader/Features/Playback/ReaderTransportCommandResolver.swift"
job_now_playing = root / "ios/InteractiveReader/InteractiveReader/Features/Playback/JobPlaybackView+NowPlaying.swift"
library_now_playing = root / "ios/InteractiveReader/InteractiveReader/Features/Playback/LibraryPlaybackView+NowPlaying.swift"
xcode_project = root / "ios/InteractiveReader/InteractiveReader.xcodeproj/project.pbxproj"


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
interactive_view_source = read(interactive_view)
interactive_layout_source = read(interactive_layout)
input_source = read(input_handlers)
transcript_source = read(transcript)
linguist_source = read(linguist)
selection_source = read(selection)
sequence_source = read(sequence)
shortcut_support_source = read(shortcut_support)
shortcut_dispatch_source = read(shortcut_dispatch)
hardware_source = read(shortcut_hardware)
shortcut_focus_source = read(shortcut_focus)
global_shortcuts_source = read(global_shortcuts)
platform_adapter_source = read(platform_adapter)
progress_footer_source = read(progress_footer)
transport_resolver_source = read(transport_resolver)
job_now_playing_source = read(job_now_playing)
library_now_playing_source = read(library_now_playing)
xcode_project_source = read(xcode_project)

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

if "Date().timeIntervalSince(started) > 12.0" not in transcript_source:
    fail("single-track explicit sentence jump display anchor must stay alive through audio/metadata settling")
handle_sentence_skip_body = function_body(
    transcript_source,
    "func handleSentenceSkip(_ delta: Int, in chunk: InteractiveChunk)",
)
if "let explicitAnchorSentenceID = pendingExplicitSentenceJumpID.flatMap" not in handle_sentence_skip_body:
    fail("sentence skip must derive an explicit slider/search/bookmark anchor before falling back to playback time")
if handle_sentence_skip_body.count("anchorSentenceNumber: explicitAnchorSentenceID") < 4:
    fail("all sentence-skip fallbacks must preserve the explicit single-track anchor")
if "viewModel.skipSentence(forward: delta > 0, preferredTrack: preferredSequenceTrack)" in handle_sentence_skip_body:
    fail("sentence skip must not call the model fallback without passing the explicit anchor")
if "private let recentSingleTrackSentenceAnchorLifetime: TimeInterval = 12.0" not in selection_source:
    fail("single-track model anchor lifetime must match the explicit jump display window")
jump_to_sentence_body = function_body(
    selection_source,
    "func jumpToSentence(_ sentenceNumber: Int, autoPlay: Bool = false)",
)
if "if audioModeManager?.isSequenceMode == false" not in jump_to_sentence_body:
    fail("single-track jumps must remember their sentence anchor immediately before async metadata/audio work")
if "rememberSingleTrackSentenceAnchor(\n                chunkID: targetChunk.id,\n                sentenceNumber: sentenceNumber" not in jump_to_sentence_body:
    fail("single-track jump anchor must be keyed by target chunk and visible sentence number")
sequence_mode_active_body = function_body(
    sequence_source,
    "var isSequenceModeActive: Bool",
)
if "guard audioModeManager?.isSequenceMode != false else" not in sequence_mode_active_body:
    fail("single-track mode must beat stale sequence-controller state for slider and skip handling")

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

for label, source in (("Job", job_now_playing_source), ("Library", library_now_playing_source)):
    if "ReaderTransportCommandResolver.resolvedAction(" not in source:
        fail(f"{label} playback must use the shared reader transport command resolver")
    if "ReaderTransportCommandResolver.duplicateWindow" not in source:
        fail(f"{label} playback must use the shared reader transport duplicate window")
    if "shouldPauseReaderTransportForToggle" in source:
        fail(f"{label} playback must not carry a private reader transport toggle policy")

if (
    ".onPlayPauseCommand {\n"
    "                guard playbackToggleOverride == nil else { return }\n"
    "                handlePlaybackToggleCommand()"
) not in interactive_view_source:
    fail("embedded tvOS reader must yield Play/Pause to the parent playback transport override")

progress_move_body = function_body(
    interactive_view_source,
    "private func handleProgressMoveCommand(_ direction: MoveCommandDirection, chunk: InteractiveChunk) -> Bool",
)
footer_move_body = function_body(
    interactive_view_source,
    "func handleTVProgressFooterMoveCommand(_ direction: MoveCommandDirection)",
)
if "case .up, .down:" not in progress_move_body or "case .up, .down:" not in footer_move_body:
    fail("tvOS progress footer outer handlers must keep up/down focus escape")
for label, body in (("progress", progress_move_body), ("footer", footer_move_body)):
    if ".left" in body or ".right" in body:
        fail(f"tvOS {label} progress handler must let TVScrubber own left/right sentence movement")
if "handleTVProgressFooterHorizontalMove" in interactive_view_source:
    fail("tvOS progress footer must not keep a second outer left/right sentence-step helper")
if "TVScrubber(" not in progress_footer_source:
    fail("shared progress footer must keep the tvOS scrubber as left/right owner")
if "onEditingChanged: handleHeaderSentenceProgressEditingChanged" not in interactive_layout_source:
    fail("interactive footer slider must still commit sentence jumps through the shared header progress handler")

if transport_resolver_source.count("static func resolvedAction(") != 1:
    fail("reader transport resolver must expose exactly one resolvedAction policy")
if "command == \"toggle\"" not in transport_resolver_source:
    fail("reader transport resolver must keep toggle command handling")
if "ownershipState == .appleMusicBed" not in transport_resolver_source:
    fail("reader transport resolver must special-case Apple Music bed ownership")
if "guard command == \"toggle\" else { return command }" not in transport_resolver_source:
    fail("reader transport resolver must keep explicit play/pause fallback outside tvOS Music-bed mode")
if "#if os(tvOS)" not in transport_resolver_source:
    fail("reader transport resolver must scope direct play/pause state resolution to tvOS")
resolver_body = function_body(transport_resolver_source, "static func resolvedAction(")
tvos_resolver_body = resolver_body[
    resolver_body.find("#if os(tvOS)"):resolver_body.find("#endif", resolver_body.find("#if os(tvOS)"))
]
if "if command == \"pause\"" not in tvos_resolver_body or "return \"pause\"" not in tvos_resolver_body:
    fail("reader transport resolver must keep direct tvOS pause callbacks idempotent during Music-bed playback")
if "if command == \"play\" || command == \"toggle\"" not in tvos_resolver_body:
    fail("reader transport resolver must resolve tvOS play/toggle callbacks through reader state during Music-bed playback")
if "return 1.25" not in transport_resolver_source or "return 0.25" not in transport_resolver_source:
    fail("reader transport resolver must keep platform-specific duplicate windows")
source_memberships = re.findall(
    r"\n\s+RDRTRNS001A000[12] /\* ReaderTransportCommandResolver\.swift in Sources \*/,",
    xcode_project_source,
)
if len(source_memberships) != 2:
    fail("reader transport resolver must be compiled into both iOS/iPadOS and tvOS app targets")

print("apple reader navigation contract checks passed")
PY
