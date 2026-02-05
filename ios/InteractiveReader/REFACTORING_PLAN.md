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

### ⏳ Remaining (Optional Future Work)
- Could simplify prepareAudio to be more mode-aware
- Unit tests for AudioModeManager and SentencePositionProvider

---

## Original Problem Statement

The current implementation of audio track toggling and sentence position tracking has become complex and tangled across multiple files. Key issues:

1. **Scattered Logic**: Audio playback logic is spread across 5+ files
2. ~~**Multiple Sources of Truth**: Toggle state exists in both View (`@AppStorage`) and `SequencePlaybackController`~~ **FIXED**: AudioModeManager is now the single source of truth
3. **Complex Position Tracking**: Finding current sentence requires 3 fallback strategies (consolidated in SentencePositionProvider)
4. **Tight Coupling**: View state and model state are intertwined
5. **Bug**: Sentence position jumps to first sentence when toggling audio tracks (OFF→ON) - Should be improved with current refactoring

## Current Architecture (After Phase 2)

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
├── +Selection.swift: prepareAudio(), selectChunk(), seekToSentenceAfterLoad()
├── +Sequence.swift: configureSequencePlayback(), loadSequenceTrack()
├── +Playback.swift: activeTimingTrack(), highlightingTime, activeSentence()
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

### Phase 2: Remove Duplication (Optional Future Work)
1. ⏳ Remove `isOriginalAudioEnabled`/`isTranslationAudioEnabled` from SequencePlaybackController
2. ⏳ Update `buildPlan()` to not check toggle state (caller decides)
3. ⏳ Update all callers to use AudioModeManager

### Phase 3: Simplify prepareAudio (Optional Future Work)
1. ⏳ Refactor `prepareAudio()` to be mode-aware
2. ⏳ Extract single-track loading to dedicated method
3. ⏳ Simplify `configureSequencePlayback()` - remove mode checking

### Phase 4: Clean Up (Optional Future Work)
1. ⏳ Remove deprecated methods
2. ⏳ Update tests
3. ⏳ Documentation

## Files to Modify

### New Files
- `AudioModeManager.swift` - Central mode/toggle management
- `SentencePositionProvider.swift` - Already created

### Major Changes
- `InteractivePlayerView.swift` - Remove @AppStorage toggles, use AudioModeManager
- `InteractivePlayerView+Tracks.swift` - Simplify toggle handlers
- `SequencePlaybackController.swift` - Remove toggle state
- `InteractivePlayerViewModel+Selection.swift` - Simplify prepareAudio
- `InteractivePlayerViewModel+Sequence.swift` - Remove mode checking

### Minor Changes
- `InteractivePlayerViewModel+Playback.swift` - Use AudioModeManager for activeTimingTrack

## Current Bug Analysis

The sentence position jump bug occurs because:

1. When toggling from OFF→ON, `sequenceController.isEnabled` is `false`
2. So `sequenceController.currentSentenceIndex` returns `nil`
3. Fallback to `activeSentenceDisplay` should work but may fail if timing track mismatch
4. Even when index is captured, `seekToSentence()` might fail if plan isn't built yet

**Root Cause**: Toggle state is synced AFTER position capture but BEFORE buildPlan().

**Quick Fix** (before full refactor):
Sync toggle state to sequenceController BEFORE capturing position, so the fallback strategies use consistent state.

## Testing Strategy

1. Unit tests for AudioModeManager mode transitions
2. Unit tests for SentencePositionProvider strategies
3. Integration tests for mode switch with position preservation
4. Manual testing: toggle at various sentences, verify position maintained

## Success Criteria

1. Toggling audio tracks preserves current sentence position
2. Single source of truth for toggle state
3. Clear separation: mode management vs playback vs position tracking
4. Reduced code duplication
5. Easier to reason about and debug
