# Interactive Reader (iOS, iPadOS, macOS iPad-style, tvOS)

A SwiftUI app that authenticates against the ebook-tools FastAPI backend, lists Library entries, and plays book, subtitle, and video items with an interactive reader experience similar to the web client. Library playback relies on `/api/library/media/{job_id}` plus `/api/jobs/{job_id}/timing`, and uses the same access-token query pattern as the web player for media URLs.

## Requirements

- Xcode 15.0+ (iOS 17 SDK) with Swift Concurrency support.
- An accessible ebook-tools API (defaults to `https://api.langtools.fifosk.synology.me` on both iOS/iPadOS and tvOS).
- Library files exposed through `/api/library/media/{job_id}` (the app appends `access_token` for media streaming).

## Project layout

```
ios/InteractiveReader
├── InteractiveReader.xcodeproj
├── InteractiveReader/        # Swift sources & resources
│   ├── App/                  # Entry point
│   ├── Features/             # UI flows (auth, library, playback)
│   ├── Models/               # Codable contracts shared with the backend
│   ├── Services/             # API + audio playback helpers
│   ├── Utilities/            # Cross-cutting helpers (storage resolver, string utils)
│   └── Resources/            # Assets + Info.plist
```

## Running the app

1. Open `ios/InteractiveReader/InteractiveReader.xcodeproj` in Xcode.
2. Select the `InteractiveReader` (iOS/iPadOS, or local macOS "Designed for iPad/iPhone") or `InteractiveReaderTV` (tvOS) scheme and a target device.
3. Run (`⌘R`).
4. Sign in, then open a Library item or completed Job.

### Local macOS iPad-style build

The iOS/iPadOS target exposes a local Mac destination as `platform:macOS` with
the `Designed for [iPad,iPhone]` variant. For unattended compile checks, use:

```bash
make build-apple-macos-ipad-style
make apple-macos-ipad-destination
make build-apple-macos-ipad-style-dry-run
```

The target resolves the local Mac destination from `xcodebuild -showdestinations`
and builds with `CODE_SIGNING_ALLOWED=NO` by default so placeholder local signing
profiles do not block CI-style checks. Override `MACOS_IPAD_DESTINATION`,
`MACOS_IPAD_DERIVED_DATA`, or `CODE_SIGNING_ALLOWED` when a signed local run is
needed. The helper reports the resolved destination and Xcode-derived app path
before building.

### Unattended iPhone/iPad updates

Physical-device updates can be driven without opening Xcode, but installing to a
device remains explicitly gated. First inspect connected devices:

```bash
make apple-devices
```

Then dry-run the command for the intended device:

```bash
APPLE_DEVICE_ID=<device-id-or-name> bash scripts/apple_unattended_device_update.sh --dry-run --install
```

When a physical update is explicitly desired, build and install with:

```bash
APPLE_DEVICE_ID=<device-id-or-name> CONFIRM_PHYSICAL_DEVICE_UPDATE=YES make apple-device-update
```

Add `--launch` when calling `scripts/apple_unattended_device_update.sh` directly
to launch the installed app after the update. The helper uses `xcodebuild` for
the device build and `xcrun devicectl device install app` for installation.

When Xcode CLI automatic signing reports missing accounts or mismatched
capabilities even though `scripts/ios_profile_capability_check.py` finds a
local full-capability `com.example.InteractiveReader` profile, use the
full-entitlement unattended fallback instead of stripping entitlements. Start
with the repo-owned planner:

```bash
make apple-device-full-entitlement-plan \
  APPLE_DEVICE_ID="<device-id-or-name>" \
  FULL_CAPABILITY_IOS_PROFILE="<app.mobileprovision>" \
  WILDCARD_IOS_EXTENSION_PROFILE="<extension.mobileprovision>" \
  APPLE_DEVELOPMENT_IDENTITY="<Apple Development identity>"
```

The generated plan preserves capabilities by doing the following:

1. Build the app unsigned for `generic/platform=iOS` with
   `CODE_SIGNING_ALLOWED=NO`.
2. Copy the full-capability app profile to
   `InteractiveReader.app/embedded.mobileprovision`, and copy a wildcard iOS
   development profile to
   `InteractiveReader.app/PlugIns/NotificationServiceExtension.appex/embedded.mobileprovision`.
3. Codesign nested dylibs and `NotificationServiceExtension.appex` first, then
   app dylibs and `InteractiveReader.app` last, using the local Apple
   Development identity. Keep the app entitlements aligned with
   `InteractiveReader.entitlements`, including CloudKit, CloudDocuments,
   iCloud KVS, Sign in with Apple, and development push.
4. Install the signed bundle with
   `scripts/apple_unattended_device_update.sh --skip-build --app-path <app> --install --launch --launch-console-timeout 10`.

The launch-console timeout is expected for a healthy foreground app; immediate
termination before the timeout should be treated as a crash to investigate.

### Runtime configuration

The app defaults to `https://api.langtools.fifosk.synology.me`. Simulator and
XCUITest runs can override that base URL through launch environment in this
order: `INTERACTIVE_READER_API_BASE_URL`, `EBOOK_TOOLS_API_BASE_URL`, then
legacy `E2E_API_BASE_URL`.

Settings shows a non-secret connection readout with the resolved API host, the
current signed-in session label, and Keychain token storage status. It never
shows the bearer token.

### Create source loading

The iOS/iPadOS/macOS iPad-style Create surface mirrors the Web creation sources
for editor users. Narrate EPUB loads `/api/pipelines/files`, subtitle jobs load
usable SRT/VTT entries from `/api/subtitles/sources`, defaulting to the latest
modified source and remembering the Show Original option, and YouTube dubbing
loads NAS videos plus adjacent subtitles from `/api/subtitles/youtube/library`,
with an editable remembered NAS base directory plus the last valid
video/subtitle selection for the current API/user scope.
Pipeline EPUB listings include optional file metadata, so the untouched
Narrate EPUB source defaults to the latest modified backend-visible NAS EPUB
with a deterministic path tie-breaker. When recent jobs are available,
untouched Narrate EPUB fields also reuse the latest book/narration input and
base paths, resume near the prior end sentence, and carry forward language and
lookup-cache defaults.
Apple Create also remembers shared input language, target languages, and
lookup-cache defaults per API/user scope across generated book, Narrate EPUB,
subtitle, and video jobs.
Manual path entry remains available when the backend list is empty or a source
is outside the default browser roots. tvOS exposes the same native Create modes
through server/NAS-backed sources; local file import remains iOS/iPadOS-only.

Create also loads `/api/audio/voices` to add language-matched gTTS, macOS, and
Piper choices to source/target narration pickers. Preview buttons call
`/api/audio` with a short sample sentence and play the returned audio in-app.

### Library media URLs

The client streams library files from `/api/library/media/{job_id}/file/...` and appends the `access_token` query parameter so AVPlayer can fetch protected media without custom headers. Ensure the API host is reachable from your device (LAN IP or Bonjour hostname).

### Authentication

The app uses `/api/auth/login` and stores the bearer token in the device Keychain. Existing installs migrate the older UserDefaults token on first launch. Media URLs append `access_token` in the query string for streaming because AVPlayer cannot attach custom headers to all media requests.

## Limitations / TODOs

- Active job playback prefers `/media/live` and falls back to the regular media
  snapshot if the initial live request is unavailable; completed jobs and
  Library items continue to use stable media snapshots.
- Chunk auto-scroll + background refresh subscriptions can be layered on using the existing `AudioPlayerCoordinator` hooks.

## Developer Hints for Future Improvements

### Architecture Overview

The Interactive Player uses a multi-layered architecture:

```
InteractivePlayerView (SwiftUI View layer)
├── @StateObject audioModeManager: AudioModeManager (toggle state source of truth)
├── @StateObject viewModel: InteractivePlayerViewModel
│   ├── +Selection.swift: prepareAudio(), chunk selection, seek after load
│   ├── +Sequence.swift: configureSequencePlayback(), track switching
│   ├── +Playback.swift: activeTimingTrack(), highlightingTime, sentence lookup
│   └── +Loading.swift: loadChunkMetadataIfNeeded(), token loading
├── sequenceController: SequencePlaybackController (segment navigation)
└── audioCoordinator: AudioPlayerCoordinator (AVPlayer wrapper)
```

### Debug Flags

Verbose logging is hidden behind debug flags (all default to `false`):

| File | Flag | Logs |
|------|------|------|
| `SequencePlaybackController.swift` | `debug` | `[SequencePlayback]` segment transitions, stale time handling |
| `InteractivePlayerViewModel+Sequence.swift` | `sequenceDebug` | `[Sequence]` track loading, playback configuration |
| `InteractivePlayerView+Layout.swift` | `transcriptDebug` | `[InteractiveContent]` transcript building, `[TranscriptFreeze]` state |
| `InteractivePlayerViewModel+Loading.swift` | `chunkMetadataDebug` | `[ChunkMetadata]` token loading, decoding |

To enable logging for debugging, set the respective flag to `true` in the source file.

### Known Complexity Areas

#### 1. Transcript Display During Transitions

The `interactiveContent()` function in `InteractivePlayerView+Layout.swift` handles multiple states:

- **Transitioning**: Uses `TextPlayerTimeline.buildTrackSwitchDisplay()` or `buildInitialDisplay()`
- **Same-sentence track switch**: Shows previous track fully revealed, new track ready
- **Sentence change**: Shows previous sentence during settling window
- **Dwelling**: Paused at segment end to show last word before advancing
- **Normal playback**: Time-based lookup via `transcriptSentences(for:)`

The `effectiveIsLoading` computed property handles the race condition where metadata loads but tokens haven't propagated to the view yet.

#### 2. Stale Time Handling

AVPlayer can report stale time values after seeks/track switches. `SequencePlaybackController.updateForTime()` handles this with:

- `expectedPosition`: Expected time after a seek
- `staleTimeCount`: Consecutive stale/valid time counter
- `isSettling`: Initial load state waiting for time to stabilize
- `reseekAttempts`: Re-seek counter to prevent infinite loops

#### 3. Audio Mode Management

`AudioModeManager` is the single source of truth for track toggle state. The sequence controller derives `isOriginalAudioEnabled`/`isTranslationAudioEnabled` from `audioMode`.

### Future Improvement Ideas

#### Performance
- [x] Prefetch chunk metadata for adjacent chunks during playback - Direction-aware prefetch loads nearby chunk metadata and audio while playback advances.
- [x] Cache decoded tokens to avoid re-parsing on chunk revisits - Context builds now reuse a bounded, per-player token normalization cache across live refreshes and metadata rebuilds, keyed by text plus explicit token arrays and reset on new job loads.
- [x] Batch sentence image prefetching based on scroll position - The adjacent-sentence prefetch pass now resolves and warms a bounded batch of nearby sentence image URLs around the active/visible sentence after metadata refresh, sharing the same image path resolver as the reel.

#### UX
- [x] Add playback speed control (50%-150% in 10% increments) - Added speed pill in header
- [x] Add jump-to-sentence navigation - Added jump pill with sentence input and chapter picker
- [x] Support background audio playback with lock screen controls - `NowPlayingCoordinator` publishes metadata, elapsed time, duration, artwork, seek/play/pause/skip/bookmark commands, and audio background mode for Apple narration/video playback while yielding when Apple Music owns the lock screen.
- [x] Add sleep timer functionality - Interactive text playback and video playback now share a sleep timer pill with 5/15/30/45 minute presets across iPhone, iPad, Apple TV, and Mac Designed for iPad; expiration pauses narration plus the active reading bed for text and pauses video playback for video.
- [x] Add cross-surface progress footer - Interactive Reader and video playback now share a thin footer scrubber for sentence/time progress across iPhone, iPad, Apple TV, and Mac Designed for iPad, keeping the identity header compact.
- [x] Improve sentence tap-to-seek precision on dense text - Near-token taps now use row-aware hit testing and route through the same seek/lookup path as exact token taps.

#### Robustness
- [x] Add retry logic for failed chunk metadata loads - Selected chunks now record retryable metadata failures and show a transcript Retry action.
- [x] Handle network interruption during streaming more gracefully - Primary narration now retries one failed stream at the current position and owns stall observers across player rebuilds.
- [x] Validate token timing data and fall back to whitespace splitting on invalid data - Context building now drops invalid timing windows, clamps overlaps within each sentence/file group, and still falls back to text tokens when token arrays are missing.

#### Testing
- [x] Contract coverage for `AudioModeManager` mode transitions - `tests/test_apple_playback_state_helpers_contract.py` pins toggle normalization, preserved sentence positions, preferred track resolution, and timing-track routing.
- [x] Contract coverage for `SentencePositionProvider` strategies - `tests/test_apple_playback_state_helpers_contract.py` pins sequence-controller, transcript-display, then time-based priority and the shared player integration point.
- [ ] Unit tests for `AudioModeManager` mode transitions
- [ ] Unit tests for `SentencePositionProvider` strategies
- [ ] Integration tests for mode switch with position preservation
- [ ] Snapshot tests for transcript display states

#### Architecture (See REFACTORING_PLAN.md)
- [ ] Simplify `prepareAudio()` to be more mode-aware
- [ ] Extract single-track loading to dedicated method
- [ ] Consider consolidating position tracking into `SentencePositionProvider`

### Debugging Tips

1. **Transcript not showing tokens**: Check `[ChunkMetadata]` logs - tokens may not be loading. The `effectiveIsLoading` logic should show "Waiting for transcript" until tokens arrive.

2. **Sentence position jumps**: Enable `sequenceDebug` to trace `seekToSentence()` calls. Position should be captured BEFORE toggle state changes.

3. **Audio cuts off early or bleeds into next sentence**: Check `[SequencePlayback]` logs for segment boundaries. The dwell mechanism (`segmentEndDwellDuration`) pauses briefly at segment end.

4. **Track switch shows wrong sentence**: Enable `transcriptDebug` to see which display path is taken. Same-sentence switches should show `SAME-SENTENCE SWITCH` logs.

## Recent Changes (2026-02-05)

### Header Controls
- **Speed Control Pill**: Added narration speed control (50%-150% in 10% increments) with slider (iOS) or button grid (tvOS)
- **Jump-to-Sentence Pill**: Added quick navigation to specific sentences or chapters
- **Music Pill Enhancements**: Added newsreel (marquee) effect for now-playing info on iPhone portrait
- **Compact Header Layout**: Title, author, and category/type share one identity line where possible; sentence/time progress now lives in the shared footer instead of increasing header height
- **tvOS Focus Consistency**: Music, speed, and jump pills now use unified focus style matching language pills

### Playback Fixes
- **Jump-to-Sentence Audio Loading**: Fixed issue where jumping to a sentence within the same chunk wouldn't seek to the correct audio position - now passes `targetSentenceIndex` directly to `prepareAudio()`
- **iPad Tap-to-Toggle Play/Pause**: Fixed issue where tapping outside tokens wouldn't toggle playback when bubble is pinned - now respects pinned state and always toggles playback

### Keyboard Navigation (iOS)
- **Ctrl+Arrow Sentence Navigation**: When paused, Ctrl+Left/Right now navigates to previous/next sentence while keeping the bubble visible (if shown). When playing, it navigates words.

### UI/UX
- **Music Overlay Light Mode**: Added `.regularMaterial` background for better visibility in non-dark mode
- **Collapsed Header**: Music pill now shown in collapsed header state across all Apple devices
