# Audio Track & Sentence Highlight Refactoring Plan

## Progress Status

### ✅ Completed (Phase 1)
- **AudioModeManager.swift** - Created as central source of truth for toggle state
- **SentencePositionProvider.swift** - Created to consolidate position lookup strategies
- **InteractivePlayerView.swift** - Replaced `@AppStorage` toggles with `@StateObject audioModeManager`
- **InteractivePlayerView+Tracks.swift** - Updated toggle handlers to use AudioModeManager
- **InteractivePlayerView+Layout.swift** - Updated sync logic to use AudioModeManager

### ✅ Completed (Phase 2)
- **SequencePlaybackController.swift** - Converted `isOriginalAudioEnabled`/`isTranslationAudioEnabled` from settable properties to computed properties derived from `audioMode`
- Added `audioMode: AudioMode` property to SequencePlaybackController (set by View layer)
- Updated `buildPlan()` to accept optional `mode` parameter
- Updated all sync code to set `audioMode` instead of individual toggle booleans

### ✅ Completed (Phase 3)
- `AudioModeManager.resolveAudioInstruction(...)` now chooses sequence versus single-track playback before `prepareAudio(...)` loads anything.
- `InteractivePlayerViewModel+Selection.swift` routes sequence setup and single-track URL loading through dedicated helpers.
- Single-track navigation avoids combined-queue offsets so translation-only/original-only playback stays aligned with rendered sentences.

### ✅ Completed (Testing)
- `scripts/check_apple_audio_mode_manager.sh` compiles the real manager with lightweight stubs and checks toggle normalization, preserved positions, preferred tracks, instruction resolution, and timing-track routing.
- `scripts/check_apple_sentence_position_provider.sh` compiles the real provider with a stub sequence controller and checks sequence, transcript, time fallback, and nil behavior.
- `scripts/check_apple_playback_mode_switch_integration.sh` checks mode-switch position preservation and single-track navigation boundaries.
- These checks are wired into `make test-apple-playback-state-swift`, `make test-apple-contracts`, and the shared pipeline manifest contract.

### ⏳ Remaining (Optional Future Work)
- Continue splitting large SwiftUI playback/header files into smaller views as behavior stabilizes.
- Keep adding focused script-level Swift checks when playback bugs are fixed outside a full simulator run.

---

## Original Problem Statement

The current implementation of audio track toggling and sentence position tracking has become complex and tangled across multiple files. Key issues:

1. **Scattered Logic**: Audio playback logic is spread across 5+ files
2. ~~**Multiple Sources of Truth**: Toggle state exists in both View (`@AppStorage`) and `SequencePlaybackController`~~ **FIXED**: AudioModeManager is now the single source of truth
3. **Complex Position Tracking**: Finding current sentence requires 3 fallback strategies (consolidated in SentencePositionProvider)
4. **Tight Coupling**: View state and model state are intertwined
5. ~~**Bug**: Sentence position jumps to first sentence when toggling audio tracks (OFF→ON)~~ **FIXED**: position capture and single-track navigation are covered by focused Swift checks

## Current Architecture

```
AudioModeManager (SINGLE SOURCE OF TRUTH)
├── isOriginalEnabled, isTranslationEnabled (always starts both ON)
├── currentMode: .sequence | .singleTrack(.original) | .singleTrack(.translation)
├── toggle(), setTracks(), enableSequenceMode()
└── onModeChange callback

InteractivePlayerView
├── @StateObject audioModeManager: AudioModeManager
├── toggleAudioTrack() → captures position → toggles via manager → reconfigures
└── InteractivePlayerView+Tracks.swift
    ├── showOriginalAudio/showTranslationAudio (computed, delegate to manager)
    └── captureCurrentSentenceIndex() using SentencePositionProvider

InteractivePlayerViewModel
├── +Selection.swift: prepareAudio(), prepareSequenceAudio(), prepareSingleTrackAudio()
├── +Sequence.swift: configureSequencePlayback(), loadSequenceTrack()
├── +Playback.swift: activeTimingTrack(), highlightingTime, activeSentence()
├── audioModeManager: AudioModeManager?
└── sequenceController: SequencePlaybackController

SequencePlaybackController
├── audioMode: AudioMode (set by View layer from AudioModeManager)
├── isOriginalAudioEnabled, isTranslationAudioEnabled (COMPUTED from audioMode)
├── plan: [SequenceSegment]
├── currentSegmentIndex, currentTrack
├── buildPlan(mode:), seekToSentence(), advanceToNextSegment()
└── isEnabled (computed from audioMode + plan validity)

SentencePositionProvider
├── Consolidates position lookup strategies
└── Returns index + strategy used
```

## Proposed Architecture

### 1. AudioModeManager (NEW)

Single source of truth for audio mode and toggle state. Manages transitions between modes.

```swift
@MainActor
final class AudioModeManager: ObservableObject {
    enum Mode {
        case singleTrack(SequenceTrack)  // Only original or translation
        case sequence                      // Both tracks alternating
    }

    // Single source of truth for toggles
    @Published var isOriginalEnabled: Bool = true
    @Published var isTranslationEnabled: Bool = true

    // Computed mode
    var currentMode: Mode {
        if isOriginalEnabled && isTranslationEnabled {
            return .sequence
        } else if isOriginalEnabled {
            return .singleTrack(.original)
        } else {
            return .singleTrack(.translation)
        }
    }

    // Mode transition with position preservation
    func setMode(
        original: Bool,
        translation: Bool,
        currentPosition: SentencePositionProvider.Result?,
        completion: (Mode, Int?) -> Void
    )

    // Callbacks for mode changes
    var onModeChange: ((Mode, Int?) -> Void)?
}
```

### 2. Enhanced SentencePositionProvider

Already created. Consolidates position lookup with clear priority:
1. SequenceController (if sequence mode active)
2. TranscriptDisplay (UI state)
3. Time-based lookup (fallback)

### 3. Simplified SequencePlaybackController

Remove duplicated toggle state - get it from AudioModeManager instead.

```swift
final class SequencePlaybackController {
    // REMOVE: isOriginalAudioEnabled, isTranslationAudioEnabled
    // These now come from AudioModeManager

    // Keep: plan management and segment navigation
    var plan: [SequenceSegment]
    var currentSegmentIndex: Int
    var currentTrack: SequenceTrack

    // Simplified buildPlan - no toggle logic
    func buildPlan(from sentences: [...], originalURL: URL?, translationURL: URL?)

    // Keep: segment navigation
    func seekToSentence(_ index: Int, preferredTrack: SequenceTrack?) -> Target?
    func advanceToNextSegment() -> Bool
}
```

### 4. Simplified View Layer

```swift
struct InteractivePlayerView {
    // REMOVE: @AppStorage for audio toggles
    // Use AudioModeManager instead
    @StateObject var modeManager = AudioModeManager()

    func toggleAudioTrack(_ kind: AudioTrack.Kind) {
        let position = positionProvider.currentSentenceIndex()
        modeManager.toggle(kind, preservingPosition: position)
    }
}
```

### 5. Simplified ViewModel

```swift
class InteractivePlayerViewModel {
    let modeManager: AudioModeManager
    let sequenceController: SequencePlaybackController

    // prepareAudio becomes simpler - mode is already determined
    func prepareAudio(for chunk: Chunk, autoPlay: Bool, targetSentence: Int?) {
        switch modeManager.currentMode {
        case .singleTrack(let track):
            loadSingleTrack(track, seekTo: targetSentence)
        case .sequence:
            configureSequencePlayback(seekTo: targetSentence)
        }
    }
}
```

## Data Flow (Current Implementation)

```
User taps toggle (InteractivePlayerView+Tracks.swift)
    ↓
captureCurrentSentenceIndex() via SentencePositionProvider → captures position FIRST
    ↓
AudioModeManager.toggle(kind:, preservingPosition:)
    ↓
reconfigureAudioForCurrentToggles(preservingSentence:)
    ↓
Sync toggle state to SequencePlaybackController
    ↓
ViewModel.prepareAudio(for:chunk, autoPlay:, targetSentenceIndex:)
    ↓
Either: loadSingleTrack() or configureSequencePlayback()
    ↓
Audio loads → seek to targetSentence → play
```

## Migration Steps

### Phase 1: AudioModeManager ✅ COMPLETED
1. ✅ Create `AudioModeManager.swift`
2. ✅ Move toggle state from View's `@AppStorage` to manager
3. ✅ Add mode computation and transition handling
4. ✅ Wire up to existing code without breaking changes

### Phase 2: Remove Duplication ✅ COMPLETED
1. ✅ Convert `isOriginalAudioEnabled`/`isTranslationAudioEnabled` in `SequencePlaybackController` to computed values from `audioMode`
2. ✅ Update `buildPlan()` to accept caller-selected mode
3. ✅ Update sync callers to use `AudioModeManager`

### Phase 3: Simplify prepareAudio ✅ COMPLETED
1. ✅ Refactor `prepareAudio()` to route through `AudioModeManager.resolveAudioInstruction(...)`
2. ✅ Extract single-track loading to `prepareSingleTrackAudio(...)` and `loadSingleTrack(...)`
3. ✅ Keep sequence setup in `prepareSequenceAudio(...)` / `configureSequencePlayback(...)`

### Phase 4: Clean Up ✅ PARTIAL
1. ✅ Add focused Swift script checks for manager, provider, mode switching, pause cancellation, transcript display, sentence-jump render locks, context building, and reader navigation
2. ✅ Keep docs aligned with the shipped helper architecture
3. ⏳ Continue reducing large playback/header SwiftUI files once behavior is stable

## Files Changed

### Core Files
- `AudioModeManager.swift` - Central mode/toggle management
- `SentencePositionProvider.swift` - Position and sentence-number/index helpers

### Major Integration Points
- `InteractivePlayerView.swift` - Owns `@StateObject audioModeManager`
- `InteractivePlayerView+Tracks.swift` - Captures position, toggles via manager, and reconfigures playback
- `InteractivePlayerView+AudioManagement.swift` - Uses the same manager-backed track toggles for menu actions
- `SequencePlaybackController.swift` - Derives track enablement from `audioMode`
- `InteractivePlayerViewModel+Selection.swift` - Resolves sequence versus single-track audio and preserves target sentence anchors
- `InteractivePlayerViewModel+Sequence.swift` - Builds and seeks sequence plans for the active mode

### Playback Timing
- `InteractivePlayerViewModel+Playback.swift` - Uses `AudioModeManager` to choose the active timing track and skip combined-queue offsets in single-track mode

## Historical Bug Analysis

The original sentence-position jump bug occurred because:

1. When toggling from OFF→ON, `sequenceController.isEnabled` is `false`
2. So `sequenceController.currentSentenceIndex` returns `nil`
3. Fallback to `activeSentenceDisplay` should work but may fail if timing track mismatch
4. Even when index is captured, `seekToSentence()` might fail if plan isn't built yet

**Root Cause**: Toggle state was synced after position capture but before `buildPlan()`, so fallback strategies could observe inconsistent state.

**Current fix**: `InteractivePlayerView+Tracks.swift` captures the current sentence through `SentencePositionProvider`, passes that index into `AudioModeManager`, and then reconfigures playback through mode-aware sequence/single-track helpers. Focused Swift checks pin the regression cases.

## Testing Strategy

1. `make test-apple-playback-state-swift` for fast script-level Swift checks.
2. `make test-apple-contracts` for source and pipeline contracts.
3. Simulator E2E journeys for Create, playback, music-bed sync, and keyboard paths when behavior changes affect UI flows.
4. Physical-device deploys only after an explicit request.

## Success Criteria

1. Toggling audio tracks preserves current sentence position
2. Single source of truth for toggle state
3. Clear separation: mode management vs playback vs position tracking
4. Reduced code duplication
5. Easier to reason about and debug
