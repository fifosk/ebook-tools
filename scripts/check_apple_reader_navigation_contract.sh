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
for label, body, navigation in (
    ("previous", previous_handler_body, "handleKeyboardBubbleNavigateLeft()"),
    ("next", next_handler_body, "handleKeyboardBubbleNavigateRight()"),
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
