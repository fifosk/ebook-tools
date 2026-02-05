# Interactive Reader (iOS, iPadOS, tvOS)

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
2. Select the `InteractiveReader` (iOS/iPadOS) or `InteractiveReaderTV` (tvOS) scheme and a target device.
3. Run (`⌘R`).
4. In the UI, set the API base URL (defaults to `https://api.langtools.fifosk.synology.me`), sign in, and open a Library item.

### Library media URLs

The client streams library files from `/api/library/media/{job_id}/file/...` and appends the `access_token` query parameter so AVPlayer can fetch protected media without custom headers. Ensure the API host is reachable from your device (LAN IP or Bonjour hostname).

### Authentication

The app uses `/api/auth/login` and stores the bearer token locally. Media URLs append `access_token` in the query string for streaming.

## Limitations / TODOs

- Live-updating jobs (`/media/live`) are not wired yet—load completed jobs only.
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
- [ ] Prefetch chunk metadata for adjacent chunks during playback
- [ ] Cache decoded tokens to avoid re-parsing on chunk revisits
- [ ] Batch sentence image prefetching based on scroll position

#### UX
- [x] Add playback speed control (50%-150% in 10% increments) - Added speed pill in header
- [x] Add jump-to-sentence navigation - Added jump pill with sentence input and chapter picker
- [ ] Support background audio playback with lock screen controls
- [ ] Add sleep timer functionality
- [ ] Improve sentence tap-to-seek precision on dense text

#### Robustness
- [ ] Add retry logic for failed chunk metadata loads
- [ ] Handle network interruption during streaming more gracefully
- [ ] Validate token timing data and fall back to whitespace splitting on invalid data

#### Testing
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
- **iPhone Portrait Layout**: Progress pills (time/progress) now stack vertically; full-width pills row below header
- **tvOS Focus Consistency**: Music, speed, and jump pills now use unified focus style matching language pills

### Playback Fixes
- **Jump-to-Sentence Audio Loading**: Fixed issue where jumping to a sentence within the same chunk wouldn't seek to the correct audio position - now passes `targetSentenceIndex` directly to `prepareAudio()`
- **iPad Tap-to-Toggle Play/Pause**: Fixed issue where tapping outside tokens wouldn't toggle playback when bubble is pinned - now respects pinned state and always toggles playback

### Keyboard Navigation (iOS)
- **Ctrl+Arrow Sentence Navigation**: When paused, Ctrl+Left/Right now navigates to previous/next sentence while keeping the bubble visible (if shown). When playing, it navigates words.

### UI/UX
- **Music Overlay Light Mode**: Added `.regularMaterial` background for better visibility in non-dark mode
- **Collapsed Header**: Music pill now shown in collapsed header state across all Apple devices
