# Interactive Player Optimization Plan

**Status:** Phase 4 Complete (2026.01.30)

## Overview

This document outlines optimization opportunities identified across the Web UI and Apple platforms for the Interactive Player experience, focusing on:
1. Dead code removal (character highlighting, legacy metadata formats)
2. Shared highlighting logic opportunities
3. iOS playback control updates for multi-sentence chunks

---

## Completed Work (2026.01.30)

### Phase 1: Dead Code Removal ✓

1. **Character highlighting** (`highlight_granularity: "character"`):
   - Removed "character" from UI config choices (now only "word")
   - Added deprecation comments in `timeline.py` and `config.py`
   - Kept internal code for backward compatibility
   - Files: `modules/config_manager/groups.py`, `modules/audio/highlight/timeline.py`

2. **Legacy config key aliases**:
   - Added `DeprecationWarning` for `forced_alignment_backend`, `forced_alignment_model`, `forced_alignment_model_overrides`
   - Kept fallback logic for backward compatibility
   - File: `modules/core/config.py`

3. **Validation scripts updated**:
   - `scripts/validate_alignment_quality.py` - now supports `--job-dir` for new chunk format
   - `scripts/validate_word_timing.py` - now supports `--job-dir` and `--chunk` for new format
   - Both scripts maintain backward compatibility with legacy formats

### Phase 2: timing_version: 2 Implementation ✓ (Complete)

1. **Backend pre-scaled timing** (already implemented):
   - `modules/core/rendering/timeline.py` - `scale_timing_to_audio_duration()` scales tokens to actual audio duration
   - `modules/core/rendering/exporters.py` - `BatchExporter.export()` applies scaling and sets `timing_version="2"`
   - Includes validation data: expected vs actual duration, scale factor, drift

2. **Backend timing_version persistence**:
   - `modules/progress_tracker.py` - accepts `timing_version` and `highlighting_policy` in `record_generated_chunk()`
   - `modules/core/rendering/pipeline.py` - passes `timing_version` from `BatchExportResult` to progress tracker
   - `modules/services/job_manager/chunk_persistence.py` - persists `timingVersion` to chunk JSON

3. **API endpoint updates**:
   - `modules/webapi/schemas/pipeline_media.py` - added `timing_version` field to `PipelineMediaChunk`
   - `modules/webapi/routes/media/media_list.py` - extracts and returns `timing_version` in chunk responses

4. **Web client updates**:
   - `web/src/hooks/useLiveMedia.ts` - extracts `timingVersion` from API response into `LiveMediaChunk`
   - `web/src/components/interactive-text/useTimelineDisplay.ts` - already had logic to skip scaling when `timingVersion === '2'`

5. **iOS client updates**:
   - `ios/.../Models/ApiModels.swift` - added `timingVersion` to `PipelineMediaChunk`
   - `ios/.../InteractivePlayerModels.swift` - added `timingVersion` to `InteractiveChunk`
   - `ios/.../InteractivePlayerContextBuilder.swift` - passes `timingVersion` through
   - `ios/.../TextPlayerTimeline.swift` - added `timingVersion` parameter to `buildTimelineSentences()`, skips scaling when "2"
   - Updated all call sites: `InteractivePlayerViewModel+Selection.swift`, `InteractivePlayerView+Transcript.swift`, `InteractivePlayerViewModel+Playback.swift`

### Phase 3: iOS Model Updates for Multi-Sentence Chunks ✓ (Complete)

1. **Added `fileDurations` to `AudioOption`**:
   - `ios/.../InteractivePlayerModels.swift` - added `fileDurations: [Double]?` property
   - Added helper methods `duration(at:)` and `offsetBefore(_:)` for per-file duration access
   - `ios/.../InteractivePlayerContextBuilder.swift` - populates `fileDurations` when creating combined tracks

2. **Added `fileIndex` to `WordTimingToken`**:
   - `ios/.../InteractivePlayerModels.swift` - added `fileIndex: Int?` property
   - Added helper methods `adjustedStartTime(fileOffset:)` and `adjustedEndTime(fileOffset:)`
   - Updated `init?(entry:)` to accept optional `fileIndex` parameter
   - `ios/.../InteractivePlayerContextBuilder.swift` - parses `fileIndex`/`file_index` from timing track entries

3. **Implemented multi-file seek logic**:
   - `ios/.../Services/AudioPlayerCoordinator.swift`:
     - Added `currentFileIndex` published property for tracking active file
     - Added `fileDurations` private property for multi-file duration state
     - Added `setFileDurations(_:)` method to configure per-file durations
     - Added `absoluteTime(forFileDurations:)` method to compute cumulative time
     - Added `seekAcrossFiles(to:fileDurations:completion:)` for cross-file seeking
     - Added private `loadFileAndSeek(at:seekTo:completion:)` helper

4. **Fixed sentence skip consistency**:
   - `ios/.../InteractivePlayerViewModel+Playback.swift`:
     - Updated `seekPlayback(to:in:)` to use `fileDurations` from `AudioOption` when available
     - Simplified multi-file seek to use new `seekAcrossFiles` method

### Phase 4: Web-iOS Parity ✓ (Complete)

**Assessment (2026.01.30):** Most Phase 4 goals were already addressed by earlier phases or existing implementations.

1. **Standardize gate handling (hard constraints)** ✅
   - Achieved via `timing_version: 2` in Phase 2
   - Backend pre-applies gates to timing data before export
   - Both platforms skip client-side gate processing for v2 jobs
   - Web retains soft constraint code (`useWordHighlighting.ts`) for backward compatibility with v1 jobs

2. **Implement shared active word lookup interface** ⏳ (Deferred)
   - Web: `collectActiveWordIds()` in `web/src/lib/timing/wordSync.ts`
   - iOS: `isActive(at:)` on `WordTimingToken`, `resolveActiveIndex` in `TextPlayerTimeline`
   - Both implementations are functionally equivalent but platform-specific
   - **Not urgent**: `timing_version: 2` ensures consistent timing data from backend
   - True cross-platform interface would require shared module or code generation (out of scope)

3. **Add transliteration support to Web (match iOS)** ✅
   - Already implemented in Web:
     - `web/src/text-player/TextPlayer.tsx` - `translit` variant with dedicated styling
     - `web/src/components/interactive-text/useTimelineDisplay.ts` - transliteration reveal times
     - `web/src/components/interactive-text/useTextPlayerSentences.ts` - token handling
     - `web/src/components/interactive-text/useLinguistBubbleNavigation.ts` - navigation support
   - Visibility toggles, styling, and navigation all functional

---

## Phase 2: Gate Standardization via Backend ✓ (Complete)

**Decision (2026.01.30):** Rather than patching client-side gate handling inconsistencies, implement `timing_version: 2` in the backend that exports pre-scaled, gate-applied timing data.

### Current State

| Platform | Gate Handling | Issue |
|----------|---------------|-------|
| **Backend** | Stores gates, doesn't enforce | Clients must interpret |
| **Web** | Soft constraint (filtering) | May show words outside gate |
| **iOS** | Hard constraint (changes calculation) | Different behavior than Web |

### Proposed Solution: `timing_version: 2`

Backend exports timing with gates pre-applied:

```python
# In modules/core/rendering/timeline.py
def build_timing_v2(tokens, gates, audio_duration):
    """Export timing with gates pre-applied and pre-scaled."""
    scaled_tokens = []
    for token in tokens:
        # Skip tokens outside gate
        if token["end"] < gates["start"] or token["start"] > gates["end"]:
            continue
        # Clamp to gate boundaries
        scaled_tokens.append({
            **token,
            "start": max(token["start"], gates["start"]),
            "end": min(token["end"], gates["end"]),
        })
    return {
        "version": 2,
        "prescaled": True,
        "gate_applied": True,
        "tokens": scaled_tokens,
        "audio_duration": audio_duration,
    }
```

### Benefits

1. **Single source of truth** - Backend decides gate semantics
2. **Simpler clients** - No gate interpretation logic needed
3. **Consistent behavior** - Web and iOS get identical data
4. **Eliminates scaling complexity** - iOS timeline scaling becomes trivial

### Implementation Steps

1. Add `timing_version` field to chunk metadata schema
2. Implement `build_timing_v2()` with pre-scaled, gate-applied tokens
3. Update API endpoint to return v2 format for new jobs
4. Update Web client to consume v2 format (simpler code)
5. Update iOS client to consume v2 format (remove scaling logic)
6. Keep v1 support for legacy jobs

### Files to Modify

**Backend:**
- `modules/core/rendering/timeline.py` - Add v2 export
- `modules/core/rendering/exporters.py` - Use v2 for new jobs
- `modules/webapi/routes/media/timing.py` - Return version field

**Web:**
- `web/src/lib/timing/wordSync.ts` - Detect v2, skip gate filtering
- `web/src/hooks/useWordHighlighting.ts` - Simplify gate handling

**iOS:**
- `TextPlayerTimeline.swift` - Detect v2, skip scaling
- `InteractivePlayerModels.swift` - Add version field

---

## Reference: Original Analysis

## 1. Dead Code Candidates for Removal

### 1.1 Character Highlighting (`highlight_granularity: "character"`)

**Status:** Configuration option exists but provides NO functional difference in rendering.

**Evidence:**
- Config allows `["word", "character"]` choices (`modules/config_manager/groups.py:321`)
- Value is passed through pipeline but never changes actual rendering behavior
- `slide_image_renderer.py` checks `highlight_granularity == "char"` for `char_range` but this path is never exercised in practice
- Video/slide rendering is deprecated; interactive reader only uses word-level timing

**Files to Clean:**
```
modules/config_manager/groups.py:316-323     # Remove "character" from choices
modules/config_manager/settings.py:90        # Keep default "word" only
modules/core/config.py:396                   # Remove "char" validation branch
modules/video/slide_image_renderer.py:374,418,463  # Remove char_range conditionals
tests/modules/test_audio_highlight.py:530,583      # Remove char granularity tests
```

**Risk:** Low - character granularity was never fully implemented for production use.

---

### 1.2 Legacy Configuration Key Aliases

**Status:** Backward-compat aliases for renamed config keys.

**Current Code** (`modules/core/config.py`):
```python
# Old key fallback pattern
raw_alignment_backend = _select_value("alignment_backend", config, overrides, None)
if raw_alignment_backend is None:
    raw_alignment_backend = _select_value("forced_alignment_backend", config, overrides, None)
```

**Keys to Deprecate:**
- `forced_alignment_backend` → `alignment_backend`
- `forced_alignment_model` → `alignment_model`

**Files to Clean:**
```
modules/core/config.py:353-366   # Remove fallback alias checks
```

**Risk:** Low - these are internal config keys, not user-facing.

---

### 1.3 Legacy `timing_index.json` Artifact

**Status:** No longer generated for new jobs; validation scripts still expect it.

**Current State:**
- New jobs use per-chunk `timingTracks` in `chunk_XXXX.json`
- Legacy aggregate `metadata/timing_index.json` only exists for old jobs
- `scripts/validate_alignment_quality.py` and `scripts/validate_word_timing.py` still expect it

**Files to Update:**
```
scripts/validate_alignment_quality.py  # Update to read per-chunk timingTracks
scripts/validate_word_timing.py        # Update to read per-chunk timingTracks
```

**Risk:** Medium - scripts need migration to new format before removal.

---

### 1.4 `_build_legacy_highlight_events` Function

**Status:** Fallback path for when modern metadata-driven highlighting is unavailable.

**Current Usage:**
```python
# modules/audio/highlight/timeline.py:127
if not candidate_events:
    candidate_events = _build_legacy_highlight_events(...)
```

**Recommendation:** KEEP - this is a critical fallback for edge cases and legacy jobs. Document its purpose clearly but do not remove.

---

### 1.5 WhisperX Integration

**Status:** Optional alignment backend, properly isolated.

**Current State:**
- `modules/align/backends/whisperx_adapter.py` - standalone adapter
- Graceful fallback when CLI not found
- Used only when `alignment_backend: "whisperx"` is configured

**Recommendation:** KEEP - well-isolated optional functionality. No cleanup needed.

---

## 2. Word Highlighting Logic Reusability

### 2.1 Current Platform Differences

| Aspect | Backend (Python) | Web (TypeScript) | iOS (Swift) |
|--------|------------------|------------------|-------------|
| **Timing Model** | Grapheme → word mapping | Segment/token flat | Hierarchical (sentence → variant → tokens) |
| **Active Word Lookup** | Sequential event chain | Binary search on timeline | Loop through reveal times |
| **Gate Handling** | Stored, not enforced | Soft constraint (filtering) | Hard constraint (changes calculation) |
| **Scaling** | Implicit in generation | Minimal/none | Explicit in `TextPlayerTimeline` |
| **Fence/Seek Behavior** | N/A | Fence mechanism prevents backward jump | Time-based computation |

### 2.2 Opportunities for Unification

#### A. Standardize Gate Semantics
**Problem:** Web treats gates as soft filters; iOS treats them as hard constraints that change the entire timing calculation strategy.

**Proposal:** Make gates hard constraints everywhere:
```typescript
// Unified gate application (pseudo-code)
function applyGateConstraint(words: WordTiming[], gateStart: number, gateEnd: number): WordTiming[] {
  return words
    .filter(w => w.t0 <= gateEnd && w.t1 >= gateStart)
    .map(w => ({
      ...w,
      t0: Math.max(w.t0, gateStart),
      t1: Math.min(w.t1, gateEnd),
    }));
}
```

#### B. Pre-Scale Timing at Backend Export
**Problem:** iOS scales timelines explicitly; Web assumes pre-scaled; Backend doesn't export scale factor.

**Proposal:** Backend exports `timing_version: "2"` with pre-scaled timing:
- All word timings are absolute audio-time
- No client-side scaling needed
- Eliminates sequence mode guard complexity in iOS

**Implementation:**
```python
# In build_separate_track_timings()
def export_prescaled_timing(tokens, audio_duration):
    """Export timing already scaled to audio duration."""
    # ... scale and validate ...
    return {
        "version": 2,
        "prescaled": True,
        "tokens": scaled_tokens,
        "audio_duration": audio_duration,
    }
```

#### C. Shared Active Word Lookup Interface
**Current Implementations:**
- Web: `collectActiveWordIds()` with binary search
- iOS: Manual loop through reveal times per variant
- Backend: Sequential event chain

**Proposal:** Define shared lookup protocol:
```typescript
interface WordTimingIndex {
  findActiveWords(time: number, tolerance?: number): ActiveWordResult;
  findWordAtIndex(sentenceId: number, tokenIdx: number): WordTiming | null;
  getSentenceRange(sentenceId: number): { start: number; end: number };
}
```

iOS and Web can both implement this interface, ensuring consistent behavior.

---

## 3. iOS Playback Control Updates for Multi-Sentence Chunks

### 3.1 Current Issues Identified

#### A. Single Duration Per Track Assumption
**Problem:** `AudioOption.duration: Double?` stores a single value, but aggregate audio has multiple files.

**Current Code:**
```swift
struct AudioOption {
    let duration: Double?  // Single value, not per-file
}
```

**Impact:** Cannot accurately represent `[audio_chunk_1.mp3: 3s, audio_chunk_2.mp3: 2s]`

#### B. Timing URL Assumption
**Problem:** Combined track assumes timing applies to translation file only.

**Current Code:**
```swift
streamURLs: [original.primaryURL, translation.primaryURL],
timingURL: translation.primaryURL,  // Hardcoded: assumes translation is 2nd
```

**Impact:** Word timing can't be mapped across multiple aggregate files.

#### C. Single Gate Pair Per Sentence
**Problem:** Each sentence stores one pair of gates, but multi-sentence chunks may have multiple gate ranges.

**Current Model:**
```swift
struct Sentence {
    let startGate, endGate: Double?           // One pair only
    let originalStartGate, originalEndGate: Double?  // One pair only
}
```

**Impact:** Sentence spanning multiple files can't have per-file gates.

### 3.2 Proposed iOS Model Updates

#### A. Per-File Duration Tracking
```swift
struct AudioOption {
    let duration: Double?           // Total duration (existing)
    let fileDurations: [Double]?    // NEW: Per-file durations for aggregate
    let streamURLs: [URL]

    /// Get duration for specific file index
    func duration(at index: Int) -> Double? {
        fileDurations?[safe: index]
    }

    /// Get cumulative offset before file at index
    func offsetBefore(_ index: Int) -> Double {
        guard let durations = fileDurations, index > 0 else { return 0 }
        return durations.prefix(index).reduce(0, +)
    }
}
```

#### B. Timing Token File Mapping
```swift
struct WordTimingToken {
    let id: String
    let text: String
    let startTime, endTime: Double
    let sentenceIndex: Int?
    let fileIndex: Int?  // NEW: Which file this token belongs to

    /// Adjusted start time accounting for file offset
    func adjustedStartTime(fileOffset: Double) -> Double {
        startTime + fileOffset
    }
}
```

#### C. Multi-File Seek Logic
```swift
extension AudioPlayerCoordinator {
    /// Seek to absolute time across multiple files
    func seekAcrossFiles(to absoluteTime: Double, in track: AudioTrack) {
        guard let option = currentAudioOption(for: track),
              let durations = option.fileDurations else {
            // Fallback: single-file seek
            seek(to: absoluteTime)
            return
        }

        var accumulated = 0.0
        for (index, fileDuration) in durations.enumerated() {
            if absoluteTime < accumulated + fileDuration {
                // Target is in this file
                let offsetWithinFile = absoluteTime - accumulated
                loadFile(at: index, seekTo: offsetWithinFile)
                return
            }
            accumulated += fileDuration
        }

        // Past end, seek to last file end
        loadFile(at: durations.count - 1, seekTo: durations.last ?? 0)
    }
}
```

#### D. Sentence Skip Consistency Fix
**Current Issue:** `skipSentence(forward:)` builds timeline from `chunk.sentences` but doesn't account for multi-sentence chunk boundaries consistently.

**Fix:** Ensure sentence indices are chunk-relative and timeline building uses cumulative offsets:

```swift
func skipSentence(forward: Bool) {
    guard let chunk = selectedChunk else { return }

    // Build timeline with proper multi-sentence support
    let timelineSentences = TextPlayerTimeline.buildTimelineSentences(
        sentences: chunk.sentences,
        activeTimingTrack: activeTimingTrack(for: chunk),
        audioDuration: playbackDuration(for: chunk),
        useCombinedPhases: useCombinedPhases(for: chunk)
    )

    // Use sentence displayIndex (global) not array index (local)
    let sorted = timelineSentences?.map {
        (sentence: $0, globalIndex: chunk.sentences[$0.index].displayIndex ?? $0.index)
    }.sorted { $0.sentence.startTime < $1.sentence.startTime }

    // ... rest of navigation logic using globalIndex for display
}
```

---

## 4. Implementation Phases

### Phase 1: Dead Code Removal (Low Risk)
1. Remove `highlight_granularity: "character"` option
2. Remove legacy config key aliases
3. Update validation scripts for new chunk format

### Phase 2: Backend Timing Export Improvements
1. Add `timing_version: 2` with pre-scaled timing
2. Ensure gates are exported as hard constraints
3. Add per-file duration metadata for aggregate audio

### Phase 3: iOS Model Updates
1. Add `fileDurations` to `AudioOption`
2. Add `fileIndex` to `WordTimingToken`
3. Implement multi-file seek logic
4. Fix sentence skip consistency

### Phase 4: Web-iOS Parity ✓
1. ~~Standardize gate handling (hard constraints)~~ - Achieved via timing_version: 2
2. Implement shared active word lookup interface - Deferred (not urgent with v2 timing)
3. ~~Add transliteration support to Web (match iOS)~~ - Already implemented

---

## 5. Testing Requirements

### Unit Tests
- [x] Remove char granularity tests (Phase 1)
- [ ] Add multi-file duration calculation tests (iOS) - Phase 3 infrastructure in place
- [ ] Add multi-file seek tests (iOS) - Phase 3 infrastructure in place
- [ ] Add gate constraint tests (both platforms)

### Integration Tests
- [ ] Multi-sentence chunk playback (iOS)
- [ ] Sentence skip across chunk boundaries
- [ ] Timeline scaling consistency
- [ ] Word highlighting sync at sentence boundaries

### Regression Tests
- [ ] Legacy single-sentence chunk support
- [ ] Legacy `timing_index.json` jobs (until fully migrated)
- [ ] WhisperX alignment (optional path)

---

## 6. Open Questions

1. **Should we remove WhisperX support entirely?** Current assessment: No, it's properly isolated and optional.

2. **Should gates be soft or hard constraints?** Recommendation: Hard constraints for predictability.

3. **Timeline scaling: backend or client?** Recommendation: Backend pre-scales for `timing_version: 2`.

4. **Transliteration on Web:** Should we add full support or deprecate? iOS has it; Web doesn't.

---

## 7. Files Reference

### Dead Code Removal Targets
```
modules/config_manager/groups.py
modules/config_manager/settings.py
modules/core/config.py
modules/video/slide_image_renderer.py
tests/modules/test_audio_highlight.py
scripts/validate_alignment_quality.py
scripts/validate_word_timing.py
```

### iOS Files to Update
```
ios/InteractiveReader/.../Features/InteractivePlayer/InteractivePlayerModels.swift
ios/InteractiveReader/.../Features/InteractivePlayer/InteractivePlayerViewModel+Playback.swift
ios/InteractiveReader/.../Features/InteractivePlayer/TextPlayerTimeline.swift
ios/InteractiveReader/.../Services/AudioPlayerCoordinator.swift
ios/InteractiveReader/.../Services/SequencePlaybackController.swift
```

### Web Files (Reference)
```
web/src/hooks/useWordHighlighting.ts
web/src/lib/timing/wordSync.ts
web/src/stores/timingStore.ts
web/src/components/transcript/TranscriptView.tsx
```

### Backend Files (Reference)
```
modules/audio/highlight/core.py
modules/audio/highlight/timeline.py
modules/core/rendering/timeline.py
modules/core/rendering/exporters.py
```
