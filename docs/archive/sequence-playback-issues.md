# Sequence Playback Issues - Debug Session 2026.01.30

> **Note:** Debug log retained for historical context. Consider moving to
> `log/` if you want to keep docs/ focused on reference material.

## Test Jobs
- Job ID: `8720ebe4-ff99-4d5f-8316-8411febd4c02` - Chunk: `3385-3394_Freida_McFadden_The_Housemaid_EN_AR`
- Job ID: `86eb2766-3096-45d5-8bdb-a4a87d5e1f45` - Current test job

## Current State

### What's Working
1. **Skip function registration** - Now using refs instead of state in PlayerPanel to avoid re-render cycles
2. **Skip function calls succeed** - `sequenceSkipFn returned: true` in logs
3. **Sequence mode enables correctly** - When both audio tracks are enabled, `sequenceEnabled: true`

### Issues Fixed (2026.01.30 Session 2)

#### 1. Sentence Index Flicker During Track Transitions
**Symptom**: When only translation audio plays in sequence mode, the displayed sentence flickered between the first batch sentence and the current playing sentence.

**Root Cause**: When `applySequenceSegment` changed tracks, it called `setSequenceTrack()` which triggered:
1. `resolvedTimingTrack` to change
2. `timelineSentences` to rebuild with different time ranges
3. `timelineDisplay` to recalculate `activeIndex` using old `chunkTime` with new timeline
4. The effect at lines 396-425 would then set a wrong `activeSentenceIndex`

**Fix Applied**: In `applySequenceSegment`, when switching tracks, immediately update `chunkTime` and `activeSentenceIndex` to the segment's values BEFORE calling `setSequenceTrack()`. This ensures the timeline calculations use correct values before the new audio loads.

#### 2. Token Highlighting Flicker Between Tracks
**Symptom**: Token word highlighting flickered between the spoken token and the first sentence token.

**Root Cause**: `setPayloadPreservingHit` and `AudioSyncController.ensureTimeline` tried to preserve the highlight hit if the segment index was valid in the new payload. However, when switching between 'original_only' and 'translation_only' tracks, both payloads have segments starting from index 0, so the index appeared valid even though it referred to completely different content with different time ranges.

**Fix Applied**:
- Modified `timingStore.setPayloadPreservingHit()` to NOT preserve the hit when `trackKind` changes
- Modified `AudioSyncController.ensureTimeline()` with the same check
- When the track type changes, the hit is cleared so the `AudioSyncController` can properly recalculate the highlight position based on the new timeline.

### Issues Fixed (2026.01.30 Session 3)

#### 3. Audio Not Loading When Track Changes (Critical)
**Symptom**: When sequence mode switches from original to translation track (or vice versa), the new audio doesn't play. Only translation audio plays for all sentences.

**Root Cause**: The `PlayerCore` component didn't call `element.load()` when the `src` attribute changed. In HTML5 audio elements, changing the `src` attribute alone doesn't cause the browser to load the new source - you must explicitly call `load()`.

**Fix Applied**: Added an effect in `PlayerCore.tsx` that detects `src` prop changes and calls `element.load()` to reload the audio element with the new source.

#### 4. Debug Logging Error in handleLoadedMetadata
**Symptom**: Console error `sequenceIndexRef is not defined` prevented the `handleLoadedMetadata` function from completing, which meant `pendingSequenceSeekRef.current` was never cleared.

**Root Cause**: Debug logging in `useInlineAudioHandlers.ts` referenced `sequenceIndexRef` and `sequenceTrackRef` which don't exist in that hook's scope.

**Fix Applied**: Removed the undefined variable references from the debug logging.

### Outstanding Issues (May Be Fixed - Needs Testing)

#### 1. Infinite Loop on Translation Track
**Status**: Should be fixed by the `PlayerCore.load()` fix. Needs verification.

#### 2. Sentence Skip Resets to First Sentence
**Status**: Should be fixed by the above changes. Needs verification.

## Files Modified This Session

### Session 1

#### `web/src/components/InteractiveTextViewer.tsx`
- Added ref-based pattern for skip function registration
- Uses `skipSentenceRef` to hold the actual function
- Uses `stableSkipSentence` (via `useMemo`) as stable wrapper
- Uses `onRegisterSequenceSkipRef` to avoid effect dependencies
- Uses `isRegisteredRef` to track registration state
- Split into two effects: one for registration, one for cleanup on unmount only

#### `web/src/components/PlayerPanel.tsx`
- Changed `sequenceSkipFn` from `useState` to `useRef` (`sequenceSkipFnRef`)
- This prevents re-renders when the skip function is registered/unregistered
- Updated `handleMediaSessionSentenceSkip` to read from ref

#### `web/src/components/interactive-text/useInteractiveAudioPlayback.ts`
- Fixed `maybeAdvanceSequence` to use `sequenceIndexRef.current` directly instead of `getSequenceIndexForPlayback()`
- Simplified sequence index synchronization effect to not reset when index is valid

#### `web/src/components/interactive-text/useInteractiveAudioSequence.ts`
- Removed excessive debug logging that was firing on every render

#### `web/src/stores/timingStore.ts`
- Added `setPayloadPreservingHit()` method to prevent flicker during track transitions

#### `web/src/components/player-panel/playerPanelProps.ts`
- Added `onRegisterSequenceSkip` to the props builder

### Session 2 (2026.01.30 - Flickering Fixes)

#### `web/src/components/interactive-text/useInteractiveAudioPlayback.ts`
- In `applySequenceSegment`: When switching tracks, immediately call `setChunkTime(segment.start)` and `setActiveSentenceIndex(segment.sentenceIndex)` BEFORE calling `setSequenceTrack()`. This ensures timeline calculations use correct values during the transition.
- Added `setActiveSentenceIndex` and `setChunkTime` to the dependency array of `applySequenceSegment`

#### `web/src/stores/timingStore.ts`
- Modified `setPayloadPreservingHit()` to check if `trackKind` has changed
- If `trackKind` changes (e.g., 'original_only' to 'translation_only'), the hit is NOT preserved because segment indices refer to different content with different time ranges

#### `web/src/player/AudioSyncController.ts`
- Modified `ensureTimeline()` to check if `trackKind` has changed
- If `trackKind` changes, the hit is cleared so it can be recalculated for the new timeline

### Session 3 (2026.01.30 - Audio Loading Fix)

#### `web/src/player/PlayerCore.tsx`
- Added effect to detect `src` prop changes and call `element.load()` to reload the audio
- This is critical for sequence mode where the audio URL changes between original and translation tracks
- Without this, the audio element would keep playing the old source even after React updated the `src` attribute

#### `web/src/components/interactive-text/useInlineAudioHandlers.ts`
- Fixed undefined variable references in debug logging
- Added additional debug logging for `handleAudioEnded` to track sequence advancement
- Updated `handleLoadedMetadata` logging to include `sequenceEnabled` and `sequencePlanLength`

#### `web/src/components/interactive-text/useInteractiveAudioPlayback.ts`
- Added `setActiveSentenceIndex(segment.sentenceIndex)` to the same-track branch of `applySequenceSegment`
- Added more detailed debug logging for sequence operations

### Session 4 (2026.01.30 - Position Preservation & Flickering Fixes)

#### 1. Position Preservation When Disabling Sequence Mode
**Symptom**: When toggling off one audio track (going from sequence mode to single-track), playback jumped to the first sentence instead of staying on the current one.

**Root Cause**: The `audioResetKey` changes when `sequenceEnabled` toggles, which triggered an effect that reset `activeSentenceIndex` to 0.

**Fix Applied**:
- Added `prevAudioResetKeyRef` to detect when transitioning from sequence mode to single-track mode
- When transitioning from sequence mode (`sequence:...` key) to single-track mode, skip resetting `activeSentenceIndex`
- Added `pendingSequenceExitSeekRef` to store the target sentence index
- Modified `handleLoadedMetadata` to seek to the correct time position for the preserved sentence

#### 2. Word Highlight Flickering During Track Transitions
**Symptom**: Word highlighting flickered between the spoken word position and the first sentence during track switches in sequence mode.

**Root Cause**: When switching tracks, there was a brief window where the old hit was still being displayed before the new timeline was loaded.

**Fix Applied**:
- Added `timingStore.setLast(null)` in `applySequenceSegment` when switching tracks
- This immediately clears the word highlight before the track change, preventing the old highlight from appearing

#### 3. Text/Sentence Flickering During Track Transitions
**Symptom**: The displayed sentence flickered between the first sentence and the current sentence during track switches.

**Root Cause**: The effect that syncs `activeSentenceIndex` from `timelineDisplay` was running during pending sequence seeks, causing it to calculate the wrong index.

**Fix Applied**:
- Added a guard in the `timelineDisplay` effect to skip updates when `pendingSequenceSeekRef.current` is set
- This ensures the sentence index set by `applySequenceSegment` is preserved during track transitions

### Files Modified in Session 4

#### `web/src/components/interactive-text/useInteractiveAudioPlayback.ts`
- Added `prevAudioResetKeyRef` and `pendingSequenceExitSeekRef` refs
- Modified `audioResetKey` effect to detect sequence mode transitions and preserve position
- Added `timingStore.setLast(null)` in `applySequenceSegment` when switching tracks
- Added guard in `timelineDisplay` effect to skip during pending sequence seeks
- Passed `pendingSequenceExitSeekRef` and `timelineSentences` to `useInlineAudioHandlers`

#### `web/src/components/interactive-text/useInlineAudioHandlers.ts`
- Added `pendingSequenceExitSeekRef` and `timelineSentences` to args
- Added logic in `handleLoadedMetadata` to handle pending sequence exit seeks
- When transitioning from sequence mode, seeks to the correct time position for the preserved sentence

### Session 5 (2026.01.30 - Ref Sync & Last Segment Fix)

#### 1. activeSentenceIndexRef Not Syncing Immediately
**Symptom**: When transitioning from sequence mode, `activeSentenceIndex` showed 0 even though we had advanced to sentence 2 or 3.

**Root Cause**: `setActiveSentenceIndex(segment.sentenceIndex)` is asynchronous (React state update), but `activeSentenceIndexRef.current` was only synced via an effect which runs after render. This meant the ref was always one render behind.

**Fix Applied**:
- Created a wrapper `setActiveSentenceIndex` that updates both the state AND the ref synchronously
- This ensures `activeSentenceIndexRef.current` is accurate immediately after calling the setter

#### 2. Sequence Looping After Last Segment
**Symptom**: After playing the last segment (segment 9), the sequence looped back to segment 1 instead of stopping.

**Root Cause**: `maybeAdvanceSequence` was continuously being called from the progress timer. When at the last segment, it would try to advance, fail, but the progress timer continued. Eventually `syncSequenceIndexToTime` would find an earlier segment matching the current time.

**Fix Applied**:
- Added an early return in `maybeAdvanceSequence` when at the last segment (`currentIndex >= sequencePlan.length - 1`)
- This prevents repeated advance attempts and lets `handleAudioEnded` properly handle the end of sequence

### Files Modified in Session 5

#### `web/src/components/interactive-text/useInteractiveAudioPlayback.ts`
- Changed `setActiveSentenceIndex` from simple state setter to wrapper that updates both state and ref synchronously
- Added guard in `maybeAdvanceSequence` to detect last segment and avoid trying to advance

### Session 6 (2026.01.30 - Pending Seek Clearing & Timeline Scaling Fix)

#### 1. pendingSequenceSeekRef Never Cleared
**Symptom**: After sequence track transitions, `pendingSequenceSeekRef` stayed set forever, blocking all progress updates.

**Root Cause**: The timeout-based clearing was removed in a previous session, and the position-based clearing caused infinite loops. No mechanism remained to clear the ref.

**Fix Applied**:
- Added `requestAnimationFrame` (double-raf) clearing in `handleLoadedMetadata` after sequence seeks
- Added same clearing in `applySequenceSegment` for same-track seeks
- Added same clearing in `audioResetKey` effect for same-URL seeks when entering sequence mode
- Each clearing checks that the pending seek value matches before clearing (prevents clearing newer seeks)

#### 2. pendingSequenceExitSeekRef Never Cleared / Stale Values
**Symptom**: When switching between single tracks (original ↔ translation), the `audioResetKey` effect kept seeing stale `pendingSequenceExitSeekRef` values and thought we were "still transitioning from sequence mode".

**Root Cause**: The "still transitioning" guard checked if `pendingSequenceExitSeekRef` was set, but this ref was also used for single-track switches and wasn't cleared promptly.

**Fix Applied**:
- Removed the "still transitioning from sequence mode" guard entirely
- Each track switch now sets its own fresh `pendingSequenceExitSeekRef`
- Changed clearing from double-raf to 200ms timeout for `pendingSequenceExitSeekRef` to allow React to re-render with new timeline

#### 3. Sentence Index Reset to 0 After Track Switch (Timeline Scaling Mismatch)
**Symptom**: After switching tracks, `activeSentenceIndex` would briefly show the correct value then reset to 0.

**Root Cause**: When switching tracks, the timeline is rebuilt with the new track's `audioDuration`. The seek happens with OLD timeline boundaries, but then the `timelineDisplay` effect runs with NEW timeline boundaries (scaled differently). The time position that was correct for sentence 1 in the old timeline might fall within sentence 0's range in the new timeline.

**Fix Applied**:
- Added `lastManualSeekTimeRef` to track when manual seeks (track switches) occur
- In the `timelineDisplay` effect, prevent backward index movement for 500ms after a manual seek
- This allows the timeline to stabilize before the effect can change the sentence index
- Set `lastManualSeekTimeRef.current = Date.now()` in `handleLoadedMetadata` when processing `pendingSequenceExitSeek`

### Files Modified in Session 6

#### `web/src/components/interactive-text/useInteractiveAudioPlayback.ts`
- Added `lastManualSeekTimeRef` ref to track manual seek timestamps
- Added guard in `timelineDisplay` effect to skip backward movement for 500ms after manual seek
- Removed "still transitioning from sequence mode" guard in `audioResetKey` effect
- Added double-raf clearing for `pendingSequenceSeekRef` in `audioResetKey` effect (same-URL case)
- Added double-raf clearing for `pendingSequenceSeekRef` in `applySequenceSegment` (same-track case)
- Pass `lastManualSeekTimeRef` to `useInlineAudioHandlers`

#### `web/src/components/interactive-text/useInlineAudioHandlers.ts`
- Added `lastManualSeekTimeRef` to args type and destructuring
- Added double-raf clearing for `pendingSequenceSeekRef` in `handleLoadedMetadata`
- Changed `pendingSequenceExitSeekRef` clearing from double-raf to 200ms timeout
- Set `lastManualSeekTimeRef.current = Date.now()` when processing sequence exit seeks

### Session 7 (2026.01.30 - Manual Seek Timestamp Fix)

#### 1. Sentence Index Reset After Track Switch in Sequence Mode
**Symptom**: After track switches in sequence mode (e.g., original→translation for sentence 1), `activeSentenceIndex` would reset to 0 when the `timelineDisplay` effect ran.

**Root Cause**: The `lastManualSeekTimeRef` was only being set for sequence exit seeks (line 488) but NOT for regular sequence seeks during track switches. The 500ms backward movement guard at lines 547-556 was intended to protect against timeline scaling mismatches, but it only works if `lastManualSeekTimeRef` was recently updated.

**Fix Applied**:
- Added `lastManualSeekTimeRef.current = Date.now()` in `handleLoadedMetadata` after sequence seeks (track switch case)
- Added `lastManualSeekTimeRef.current = Date.now()` in `applySequenceSegment` for same-track seeks
- This ensures the 500ms guard protects against backward index movement after ANY sequence operation

### Files Modified in Session 7

#### `web/src/components/interactive-text/useInlineAudioHandlers.ts`
- Added `lastManualSeekTimeRef.current = Date.now()` after line 421 in `handleLoadedMetadata` for sequence seeks

#### `web/src/components/interactive-text/useInteractiveAudioPlayback.ts`
- Added `lastManualSeekTimeRef.current = Date.now()` in `applySequenceSegment` for same-track seeks (after `emitAudioProgress`)

### Session 8 (2026.01.30 - Sequence Mode Backward Movement Block)

#### 1. Sentence Index Reset After 500ms Guard Expires
**Symptom**: Even with the 500ms guard, sentence index would reset after the guard expired because the timeline scaling mismatch persisted.

**Root Cause**: The 500ms guard was only delaying the problem. After it expired, the condition at lines 562-565 allowed backward movement if the effective time was within the candidate sentence's range. Due to different scaling factors between tracks:
- Original track: `scale: 1.1137`
- Translation track: `scale: 0.7718`

The scaled timeline would map the seek position to an earlier sentence's range.

**Fix Applied**:
- Changed the sequence mode guard to completely block backward movement from timeline calculations
- In sequence mode, the sequence system (via `skipSequenceSentence`) is the only way to navigate backward
- This prevents timeline scaling mismatches from incorrectly resetting the sentence index

### Files Modified in Session 8

#### `web/src/components/interactive-text/useInteractiveAudioPlayback.ts`
- Strengthened the sequence mode guard in `timelineDisplay` effect to block ALL backward movement
- Removed the condition checking `effectiveTime > currentRuntime.startTime - 0.2`
- The sequence system is now the sole authority for sentence progression in sequence mode

## Outstanding Issues

### Verified Working (Session 8)
All sequence playback issues have been resolved and verified:

1. ✅ Sequence playback advances correctly through all sentences (0→1→2→3→4)
2. ✅ Position is preserved when disabling one audio track (exit sequence mode)
3. ✅ Position is preserved when switching between single tracks (original ↔ translation)
4. ✅ No word highlight flickering during track transitions
5. ✅ No text/sentence flickering during track transitions
6. ✅ Sequence stops properly at the last segment (doesn't loop back)
7. ✅ Forward/backward skip via keyboard works correctly in sequence mode
8. ✅ Track switches (original↔translation) preserve sentence index correctly

### Solution Summary
The root cause was **timeline scaling mismatches** between original and translation audio tracks. When switching tracks, the frontend applies different scaling factors:
- Original track: `scale: 1.1137`
- Translation track: `scale: 0.7718`

The `timelineDisplay` effect was calculating sentence index based on scaled timeline positions, which caused incorrect backward movement after track switches.

**Final Fix**: In sequence mode, completely block backward movement from timeline calculations. The sequence system (`skipSequenceSentence`) is the sole authority for sentence navigation. This is implemented in `useInteractiveAudioPlayback.ts` lines 530-543.

### Future Improvements (Optional)
- Implement backend `timing_version: "2"` to pre-scale timing at export time, eliminating frontend scaling entirely
- This would allow removing the sequence mode guard and simplifying the highlighting system

## Sequence Plan Structure
For reference, the sequence plan is an array of segments:
```typescript
type SequenceSegment = {
  track: 'original' | 'translation';
  start: number;  // start time in the track's audio file
  end: number;    // end time in the track's audio file
  sentenceIndex: number;  // which sentence this segment belongs to
};
```

The plan alternates: sentence 0 original, sentence 0 translation, sentence 1 original, sentence 1 translation, etc.

## Console Log Patterns to Watch For

### Good Pattern (skip working correctly)
```
[PlayerPanel] handleMediaSessionSentenceSkip called, direction: 1 sequenceSkipFn: set
[PlayerPanel] sequenceSkipFn returned: true
[Highlight diagnostics] trackKind: 'original_only'  // stays on new sentence
```

### Bad Pattern (loop/reset)
```
[PlayerPanel] handleMediaSessionSentenceSkip called, direction: 1 sequenceSkipFn: set
[PlayerPanel] sequenceSkipFn returned: true
[Highlight diagnostics] trackKind: 'translation_only'  // jumps to translation
[Highlight diagnostics] trackKind: 'original_only'    // back to original sentence 0
[Highlight diagnostics] trackKind: 'translation_only' // loops on sentence 0
```
