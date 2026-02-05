# Interactive Player Refactoring & Optimization Plan v2

**Date:** 2026-02-05
**Scope:** Metadata optimization, modular separation, audio management, chunk prefetching, and cross-component logic reuse across Web UI and Apple apps.

---

## Status of Previous Plans

| Plan | Status | Key Outcome |
|------|--------|-------------|
| Web Component Refactoring (REFACTORING_PLAN.md) | Complete | 69% line reduction across 4 components |
| Translation Engine (REFACTORING_SUMMARY.md) | Complete | 5 modules, 202 tests |
| iOS Audio/Highlight (ios REFACTORING_PLAN.md) | Phase 2 complete | AudioModeManager, SentencePositionProvider |
| Interactive Player Optimization (Phases 1-4) | Complete | timing_version:2, multi-file support, platform parity |
| Multi-Sentence Chunks | Implemented | `sentences_per_chunk` is live alias |
| Sequence Playback Issues | All 8 fixed | Timeline scaling root cause resolved |

---

## Part 1: Metadata Format Optimization

### 1.1 Eliminate Dual-Case Field Redundancy ✅ COMPLETED

**Problem:** Chunk metadata stores the same data under both snake_case and camelCase keys (`audio_tracks`/`audioTracks`, `timing_tracks`/`timingTracks`, `start_gate`/`startGate`). This adds ~15-20% bloat per chunk file.

**Implementation:**
- Chunk files now written with `"version": 3` and camelCase-only fields
- Backend writers (10 files) updated to produce camelCase only: `audioTracks`, `timingTracks`, `timingVersion`, `startGate`, `endGate`, `originalStartGate`, `originalEndGate`, `pauseBeforeMs`, `pauseAfterMs`, `originalPauseBeforeMs`, `originalPauseAfterMs`, `imagePath`
- All backend readers maintain dual-case fallback chains for v1/v2 backward compat
- MetadataLoader no longer generates dual keys in returned payloads
- Pydantic schema uses `alias` for camelCase serialization with `populate_by_name=True`
- Web client: already uses camelCase (no changes needed)
- iOS client: CodingKeys already handle both variants (no changes needed)

**Files changed:**
- `modules/services/job_manager/chunk_persistence.py` - version 3, camelCase-only writes
- `modules/services/job_manager/persistence.py` - camelCase-only writes
- `modules/core/rendering/exporters.py` - camelCase-only sentence metadata output
- `modules/render/audio_pipeline.py` - camelCase-only pause fields
- `modules/core/rendering/pipeline_image_state.py` - camelCase-only imagePath
- `modules/core/rendering/pipeline_images.py` - camelCase-only imagePath
- `modules/metadata_manager.py` - Single-key output from MetadataLoader
- `modules/services/export_service.py` - camelCase-only audioTracks
- `modules/webapi/routes/media/images.py` - camelCase-only imagePath
- `modules/webapi/schemas/pipeline_media.py` - alias-based serialization

**Risk:** Low. Backward compatible — all readers still accept both forms.

### 1.2 Deduplicate Sentence Text Storage ✅ COMPLETED

**Problem:** `sentence.text` duplicates `sentence.translation.text` (or `sentence.original.text`). For a 14,000-sentence book this is significant.

**Implementation:**
- Backend exporters (`exporters.py`, `pipeline_processing.py`) no longer write top-level `sentence.text` for v3 chunks
- `serialize_sentence_chunk()` accepts `include_top_level_text` parameter (default `True` for backward compat)
- `_build_sentence_metadata()` passes `include_top_level_text=False` — text lives only in `original.text` / `translation.text`
- Backend readers updated with robust fallback chains:
  - `images.py`: `_extract_sentence_text()` prefers `original.text`, falls back to top-level `text`
  - `lookup_cache_phase.py`: new `_extract_lookup_text()` helper handles v3 dicts, v1/v2 strings, and top-level `text`
  - `search/service.py`: already checks variant texts first — no changes needed
- Frontend (`ChunkSentenceMetadata` DTO): no top-level `text` field — already used variant-specific text
- iOS: already uses `sentence.original.text` / `sentence.translation.text` — no changes needed

**Risk:** Low. Old v1/v2 chunks still contain top-level `text`; all readers maintain fallback.

**Files:**
- `modules/core/rendering/exporters.py` - Conditional export
- Web: `useTextPlayerSentences.ts` - Prefer variant-specific text
- iOS: `InteractivePlayerModels.swift` - Fallback chain

### 1.3 Consolidate Chunk Manifest vs generated_files.chunks

**Problem:** `job.json` contains both `chunk_manifest` (lightweight index) and `generated_files.chunks[]` (full chunk entries with inline data). The manifest is a subset but stored separately.

**Proposal:**
- Merge into single `chunks` array in job.json with two tiers:
  - **Index tier** (always inline): `chunk_id`, `range_fragment`, `start_sentence`, `end_sentence`, `sentence_count`, `metadata_url`
  - **Detail tier** (in external chunk file only): sentences, timing tracks, audio tracks
- Remove `chunk_manifest` as separate structure
- API returns index tier by default, detail tier on demand per-chunk

**Files:**
- `modules/services/job_manager/chunk_persistence.py`
- `modules/webapi/routes/media/media_list.py`
- Web: `useLiveMedia.ts`
- iOS: `InteractivePlayerContextBuilder.swift`

**Risk:** Medium. Requires API versioning. Phase this after v3 metadata is stable.

### 1.4 Lazy Image Metadata

**Problem:** Each sentence embeds full image metadata (path, prompt, negative_prompt, scene_id, etc.) even when images aren't being displayed. For 14K sentences, this adds substantial payload.

**Proposal:**
- Store only `image_path` inline in sentence metadata
- Move full image metadata to a separate `image_manifest.json` per job
- Fetch image details on demand via new endpoint: `GET /api/jobs/{job_id}/media/images/manifest`
- Web `useSentenceImageReel.tsx` fetches manifest lazily on first image view

**Files:**
- `modules/core/rendering/exporters.py` - Split image metadata
- `modules/webapi/routes/media/` - New manifest endpoint
- Web: `useSentenceImageReel.tsx` - Lazy fetch
- iOS: `InteractivePlayerViewModel+Loading.swift` - Lazy fetch

### 1.5 External Book Info Consolidation

**Problem:** Book metadata is scattered across `job.json` top-level fields (`author`, `book_title`, `book_year`, `book_cover_file`) AND nested in `book_metadata` object. The top-level fields are legacy.

**Proposal:**
- For metadata_version 3: single `bookMetadata` object only
- Remove redundant top-level `author`, `book_title`, `book_year`, `book_cover_file`
- `content_index` stays nested in `bookMetadata`
- API normalizes to flat `bookMetadata` for clients

**Risk:** Low with version gating.

---

## Part 2: Modular Separation

### 2.1 Extract Shared Media Primitives ✅ COMPLETED

**Problem:** Audio URL resolution, chunk key resolution, and storage URL building are duplicated across 4+ hooks (`useChunkPrefetch`, `useInteractiveAudioSequence`, `useInteractiveAudioPlayback`, `InteractiveTextViewer`).

**Proposal:** Create `web/src/lib/media/` module:

```
web/src/lib/media/
  chunkResolver.ts      -- Resolve chunkId -> rangeFragment -> metadataPath -> metadataUrl
  audioUrlResolver.ts   -- Resolve track selection to audio URL (orig/trans/combined)
  storageUrl.ts         -- Centralized buildStorageUrl with job context
  gateExtractor.ts      -- Extract sentence gates from metadata (handles all key variants)
  types.ts              -- Shared media types
```

**Impact:**
- `useChunkPrefetch.ts` - Use `chunkResolver` and `storageUrl`
- `useInteractiveAudioSequence.ts` - Use `gateExtractor` and `audioUrlResolver`
- `useInteractiveAudioPlayback.ts` - Use `audioUrlResolver`
- `useTimelineDisplay.ts` - Use `gateExtractor`

### 2.2 Web UI: Unify Subtitle Processing ✅ COMPLETED

**Problem:** Subtitle types and utilities duplicated across `VideoPlayer.tsx`, `video-player/utils.ts`, and `SubtitleTrackOverlay.tsx`.

**Implementation:**
- Created `web/src/lib/subtitles/` module with 6 files:
  - `types.ts` — `SubtitleTrack`, `CueVisibility` interfaces (single source of truth)
  - `assParser.ts` — Full ASS subtitle parser (moved from video-subtitles/)
  - `formatDetection.ts` — `resolveSubtitleFormat`, `isVttSubtitleTrack`, `isAssSubtitleTrack`, `selectPrimarySubtitleTrack`, `selectAssSubtitleTrack`
  - `dataUrl.ts` — `decodeDataUrl`, `EMPTY_VTT_DATA_URL` (eliminated duplicate)
  - `vttStyles.ts` — `injectVttCueStyle`, `filterCueTextByVisibility`
  - `index.ts` — Barrel re-export
- `VideoPlayer.tsx` — Replaced inline `SubtitleTrack` interface with re-export from lib/subtitles
- `video-player/utils.ts` — Removed 10 extracted functions/interfaces, re-exports from lib/subtitles for backward compat; kept video-player-only utils
- `video-subtitles/assParser.ts` — Replaced 174-line body with re-export from lib/subtitles
- `SubtitleTrackOverlay.tsx` — Removed local `isAssSubtitleTrack` (12 lines) and inline `decodeDataUrl` (16 lines), imports from lib/subtitles

**Duplications eliminated:** 3 (`SubtitleTrack` interface x3, `isAssSubtitleTrack` x2, `decodeDataUrl` x2)

### 2.3 iOS: Reduce Platform Conditional Sprawl

**Problem:** `InteractivePlayerView+Layout.swift` and other view files contain deeply nested `#if os(iOS)` / `#if os(tvOS)` blocks, making them hard to read and maintain.

**Proposal:**
- Extract platform-specific view builders into dedicated files:
  - `InteractivePlayerView+Layout_iOS.swift`
  - `InteractivePlayerView+Layout_tvOS.swift`
- Keep shared logic in base `+Layout.swift` that calls platform-specific builders
- Use `PlatformAdapter` protocol more aggressively for layout constants

**Alternative:** ViewBuilder-based approach where each platform provides its own body builder, selected at the call site via a thin `#if` wrapper.

### 2.4 iOS: MyLinguist Bubble ViewModel Extraction ✅ COMPLETED

**Problem:** MyLinguist bubble state was scattered across `InteractivePlayerView` properties: `linguistBubble`, `linguistSelection`, `linguistSelectionRange`, multiple task refs. Similar scatter in video subtitle overlay.

**Implementation:**
- Created `LinguistLookupUtilities.swift` (~120 lines) — pure free functions: `sanitizeLookupQuery`, `nearestLookupTokenIndex`, `normalizeLanguageCode`, `buildLookupLanguageOptions`, `buildLlmModelOptions`, `lookupInputLanguage`, `pronunciationLanguage`
- Created `MyLinguistBubbleViewModel.swift` (~400 lines) — `@Observable` class owning bubble state, lookup tasks, LLM model loading, voice inventory, pronunciation speaker
  - Closure-based DI: `apiConfigProvider`, `jobIdProvider`, `fetchCachedLookupProvider`
  - `configure()` method for post-init setup (SwiftUI `@State` pattern)
  - `startLookup()` implements superset logic: cache check → LLM fallback → error handling + pronunciation
  - UserDefaults-backed preferences (storedLookupLanguage, storedLlmModel, storedTtsVoice)
- Both views use `@State var linguistVM = MyLinguistBubbleViewModel()` + `configure()` in `.onAppear`
- Bridge computed properties maintain backward compat (`linguistBubble`, `subtitleBubble`, etc.)
- Both `MyLinguistBubbleState` and `VideoLinguistBubbleState` now have `cachedAudioRef`

**Line reduction:**
- `InteractivePlayerView+Linguist.swift`: 706 → 347 lines (51% reduction)
- `VideoPlayerView+Linguist.swift`: 342 → 194 lines (43% reduction)
- ~15 scattered `@State` properties consolidated into single ViewModel across both views

**Files:**
- New: `ios/.../Utilities/LinguistLookupUtilities.swift`
- New: `ios/.../Features/Shared/MyLinguistBubbleViewModel.swift`
- Modified: `InteractivePlayerView.swift` — replaced 8 `@State` + 1 `@StateObject` with `@State var linguistVM`
- Modified: `InteractivePlayerView+Linguist.swift` — delegates to ViewModel
- Modified: `InteractivePlayerView+Layout.swift` — added `configureLinguistVM()` in `.onAppear`
- Modified: `VideoPlayerView.swift` — replaced 6 `@State` + 1 `@StateObject` with `@State var linguistVM`
- Modified: `VideoPlayerView+Linguist.swift` — delegates to ViewModel
- Modified: `LinguistBubbleView.swift` — added `cachedAudioRef` to `VideoLinguistBubbleState`

### 2.5 iOS: SequencePlaybackController State Machine

**Problem:** Sequence transitions use many callback-based patterns (`onWillBeginTransition`, `onSeekRequest`, `onPauseForDwell`, `onResumeAfterDwell`) with fragile time-based guards (`expectedPosition`, `staleTimeCount`).

**Proposal:**
- Replace callback soup with explicit state machine:
  ```swift
  enum SequenceState {
      case idle
      case playing(segment: SequenceSegment)
      case transitioning(from: SequenceSegment, to: SequenceSegment)
      case dwelling(segment: SequenceSegment, resumeAfter: TimeInterval)
      case seeking(target: SeekTarget)
      case completed
  }
  ```
- Each state has clear entry/exit actions
- Transition validation prevents invalid state changes
- Simplifies debugging (log state transitions instead of callback chains)

**Risk:** Medium. Requires careful testing of all transition paths. Recommend incremental: introduce state enum first, then migrate callbacks one at a time.

---

## Part 3: Audio Management Transparency

### 3.1 Unified Audio Track Abstraction (Web) ✅ COMPLETED (Steps 1 & 2)

**Problem:** Single-track and sequence playback have different code paths in `useInteractiveAudioPlayback.ts` (1647 lines). Track switching, URL resolution, and timing payload generation differ based on mode.

**Implementation (Step 1 — Sequence Playback Controller):**
- Extracted `useSequencePlaybackController.ts` (~850 lines) from `useInteractiveAudioPlayback.ts`
- Parent hook reduced from 1647 → 1029 lines (~618 lines removed)
- Moved: `findSequenceIndexForSentence`, sequence sync effect, `syncSequenceIndexToTime`, `getSequenceIndexForPlayback`, `applySequenceSegment`, `advanceSequenceSegment`, `skipSequenceSentence`, `handleSequenceAwareTokenSeek`, `maybeAdvanceSequence`, `selectedTracks` memo, debug info
- Also moved: `SEQUENCE_SEGMENT_DWELL_MS` constant, `sequenceSegmentDwellRef`, `isDwellPauseRef`, `sequenceOperationInProgressRef`, `prevSequenceEnabledRef`
- `useInlineAudioHandlers` interface unchanged — same 5 callbacks passed through
- Pure mechanical extraction with no behavior changes

**Implementation (Step 2 — Audio Mode Transition):**
- Extracted `useAudioModeTransition.ts` (~390 lines) from `useInteractiveAudioPlayback.ts`
- Parent hook reduced from 1029 → 765 lines (~264 lines removed)
- Moved: `pendingInitialSeek`, `lastReportedPosition`, `prevAudioResetKeyRef`, `pendingSequenceExitSeekRef` refs
- Moved: main `audioResetKey` effect (enter/exit/stay sequence mode, single-track switches, default reset)
- Moved: `emitAudioProgress` callback
- Returns refs and callback consumed by parent's `useInlineAudioHandlers` and timelineDisplay effect
- Pure mechanical extraction with no behavior changes

### 3.2 Unified Audio Track Abstraction (iOS)

**Problem:** Same issue on iOS. `InteractivePlayerViewModel+Selection.swift` has branching logic for single vs sequence modes in `prepareAudio()`.

**Proposal:** Extend `AudioModeManager` to be the track provider:
- `AudioModeManager.effectiveAudioURL(for chunk:)` returns the correct URL
- `AudioModeManager.effectiveTimingTokens(for chunk:)` returns the correct tokens
- `SequencePlaybackController` becomes a delegate of `AudioModeManager` for sequence-specific behavior

This builds on the Phase 2 work already done (AudioModeManager as single source of truth).

### 3.3 Audio Preloading Strategy Alignment

**Problem:** Web prefetches audio heads (bytes 0-2047) with radius=2 chunks. iOS prefetches audio URLs but implementation details differ. Neither platform preloads the *other* track (if in sequence mode, preload both orig and trans for adjacent chunks).

**Proposal:**
- Web: Extend `useChunkPrefetch.ts` to preload both audio tracks when sequence mode is active
- iOS: Align prefetch radius and strategy with Web (currently iOS does ±2 sentences, Web does ±2 chunks)
- Both platforms: Prefetch metadata + audio for next/prev chunk based on playback direction

---

## Part 4: Chunk Prefetching Improvements

### 4.1 Direction-Aware Prefetching ✅ COMPLETED

**Problem:** Current prefetch is symmetric (±2 chunks). During linear playback, the user will almost certainly need the next chunk, not the previous one.

**Implementation:**
- `useChunkPrefetch` now accepts `isPlaying` option
- Tracks direction via `prevSentenceNumberRef` / `directionRef` (forward/backward/none)
- When playing forward: asymmetric prefetch (1 backward, 3 forward)
- When paused or moving backward: symmetric ±2 (unchanged)
- Fixed bug: `activeSentenceIndex` was hardcoded to `0` at call site — now synced from audio playback hook via bridging state

**Files changed:**
- `web/src/components/interactive-text/useChunkPrefetch.ts` — direction tracking, asymmetric radius
- `web/src/components/InteractiveTextViewer.tsx` — bridging state for prefetchSentenceIndex + prefetchIsPlaying

### 4.2 Sentence-to-Chunk Mapping Cache

**Problem:** Converting sentence numbers to chunk indices requires scanning `chunk_manifest`. With multi-sentence chunks this is less costly, but still involves repeated lookups.

**Proposal:**
- Build `sentenceToChunk: Map<number, string>` at job load time from chunk manifest
- Use for instant chunk resolution during navigation and prefetching
- Already partially implemented in iOS (`JobContext` has chunk index map); replicate on Web

### 4.3 Progressive Metadata Hydration

**Problem:** `hydrateChunk()` in `useChunkPrefetch.ts` merges prefetched sentences into chunk data. This is all-or-nothing.

**Proposal:**
- Level 1 (index): chunk_id, sentence_count, audio URLs (from manifest, instant)
- Level 2 (sentences): sentence text, tokens, gates (from chunk file, prefetchable)
- Level 3 (timing): full timing tracks (from chunk file, prefetched with audio)
- Level 4 (images): image metadata (lazy, on-demand)

Components render progressively: show sentence text as soon as Level 2 arrives, show highlighting when Level 3 arrives.

### 4.4 Prefetch Failure Recovery

**Problem:** Current retry logic uses fixed intervals (6s for metadata, 12s for audio). No escalation or circuit breaking.

**Proposal:**
- Exponential backoff: 2s, 4s, 8s, 16s (max)
- Circuit breaker: after 3 consecutive failures for a chunk, skip prefetch and load on-demand
- Health indicator in UI: subtle icon if prefetch is degraded
- Share retry state across chunks to detect systemic issues (e.g., offline)

---

## Part 5: Cross-Component Logic Reuse

### 5.1 Shared Time-Indexed Search Utility ✅ COMPLETED

**Problem:** Word highlighting logic exists in 3 places:
- Web: `wordSyncController.ts` + `useInteractiveWordSync.ts` (binary search, DOM class updates)
- iOS: `TextPlayerTimeline.swift` + token `isActive(at:)` (loop-based)
- Video: `SubtitleTrackOverlay.tsx` (binary search for active cue)

All solve the same problem: "given a time, find the active element."

**Proposal:** Define a shared algorithm specification (not cross-platform code, but consistent interface):

```
TimeIndexedSearch<T>:
  items: T[]                    // sorted by start time
  getStart(item: T): number
  getEnd(item: T): number

  findActive(time: number): T | null      // binary search
  findRange(start, end): T[]              // range query
  findNearest(time: number): T | null     // snap to closest
```

**Web implementation:** `web/src/lib/timing/timeSearch.ts` - used by both wordSync and subtitle overlay
**iOS implementation:** Extension on `Array where Element: TimeIndexed` protocol

This eliminates the current situation where subtitle cue search and word timing search are separate implementations of the same algorithm.

### 5.2 Shared MyLinguist Integration Layer ✅ COMPLETED (Web)

**Problem:** MyLinguist lookup, caching, and TTS exist in:
- Web interactive text: `useLinguistBubbleLookup.ts` + `useLinguistBubbleNavigation.ts`
- Web video subtitles: Same hooks reused via props (partially shared)
- Web standalone: `MyLinguistAssistant.tsx` (separate implementation)
- iOS interactive player: `InteractivePlayerView+Linguist.swift`
- iOS video player: `VideoPlayerView+Subtitles.swift`

**Implementation (Web):**
- Created `web/src/lib/linguist/` module with 5 files:
  - `constants.ts` — Unified storage keys, defaults, sentinel values (from 2 sources)
  - `storage.ts` — localStorage persistence (loadStored, storeValue, loadStoredBool, loadStoredNumber, storeNumber)
  - `voices.ts` — Voice inventory building (buildVoiceOptionsForLanguage, formatMacOSVoice*)
  - `sanitize.ts` — Query sanitization and tokenization
  - `index.ts` — Barrel export including re-exports from `utils/myLinguistPrompt.ts` and `utils/ttsPlayback.ts`
- `MyLinguistAssistant.tsx`: 931 → 766 lines (165 lines of duplicated code removed)
- `interactive-text/constants.ts`: Re-exports linguist constants from canonical `lib/linguist`
- `interactive-text/utils.tsx`: Delegates linguist functions to `lib/linguist` (backward compat re-exports)
- Zero breaking changes — all existing imports continue to work

**Remaining (iOS):**
- `MyLinguistBubbleViewModel.swift` already created in 2.4
- Future: Extract `Services/MyLinguistService.swift` if further consolidation needed

### 5.3 Shared Playback Controls Pattern

**Problem:** Play/pause, seek, rate, and keyboard shortcuts exist in:
- Interactive text: `useTextPlayerKeyboard.ts`, `useInlineAudioHandlers.ts`
- Video player: `useVideoPlayback.ts`, video keyboard shortcuts
- iOS: `AudioPlayerCoordinator`, `VideoPlayerCoordinator` (both implement `PlayerCoordinating`)

**Proposal:**
- iOS already has `PlayerCoordinating` protocol - this is good. Ensure video keyboard shortcuts use same action dispatch as audio keyboard shortcuts.
- Web: Create `web/src/lib/playback/playbackActions.ts`:
  ```typescript
  interface PlaybackActions {
    play(): void;
    pause(): void;
    togglePlayPause(): void;
    seek(time: number): void;
    seekRelative(delta: number): void;
    setRate(rate: number): void;
    skipSentence(forward: boolean): void;
  }
  ```
  Both `useTextPlayerKeyboard` and video keyboard handler dispatch through this interface.

### 5.4 Shared Bookmark/Resume Logic

**Problem:** Playback bookmarks and resume position exist in:
- Web: `usePlaybackBookmarks.ts`, `useMediaMemory.ts` (localStorage)
- iOS: `PlaybackResumeStore`, `PlaybackBookmarkStore`, `PlaybackResumeManager`

The data model is similar but implementations are entirely separate.

**Proposal:** Align the data model (not the implementation):
- Define shared bookmark schema in API: `POST /api/jobs/{job_id}/bookmarks`
- Server-side bookmark persistence enables cross-device resume
- Local storage remains as offline fallback
- Sync on app launch / periodic

This is a larger feature but addresses the real user pain point of resuming across devices.

---

## Implementation Priority

### Tier 1: Quick Wins (1-2 items per session) — ALL COMPLETED

| # | Item | Status |
|---|------|--------|
| 1 | 2.1 Extract shared media primitives (Web) | ✅ |
| 2 | 5.1 Shared time-indexed search (Web) | ✅ |
| 3 | 1.1 Eliminate dual-case fields (Backend) | ✅ |
| 4 | 4.1 Direction-aware prefetching | ✅ |
| 5 | 1.2 Deduplicate sentence text storage | ✅ |

### Tier 2: Architectural Improvements (Next)

| # | Item | Impact | Risk | Effort |
|---|------|--------|------|--------|
| 6 | 3.1 Unified AudioTrackProvider (Web) ✅ Steps 1 & 2 | High (simplifies 1647-line hook) | Medium | High |
| 7 | 2.4 MyLinguist BubbleViewModel (iOS) ✅ | Medium (cleaner state management) | Low | Medium |
| 8 | 5.2 Shared MyLinguist service layer (Web) ✅ | Medium (reduces code paths) | Low | Medium |

### Tier 3: Larger Refactors

| # | Item | Impact | Risk | Effort |
|---|------|--------|------|--------|
| 8 | 2.5 Sequence state machine (iOS) | High (eliminates fragile callbacks) | Medium | High |
| 9 | 3.2 AudioModeManager as track provider (iOS) | Medium (builds on Phase 2) | Medium | Medium |
| 10 | 1.3 Consolidate chunk manifest | Medium (cleaner API) | Medium | High |
| 11 | 4.3 Progressive metadata hydration | Medium (better UX) | Medium | High |

### Tier 4: Feature Enhancements

| # | Item | Impact | Risk | Effort |
|---|------|--------|------|--------|
| 12 | 1.4 Lazy image metadata | Low-Medium (payload reduction) | Low | Medium |
| 13 | 5.4 Server-side bookmarks | High (cross-device) | Medium | High |
| 14 | 2.3 iOS platform conditional cleanup | Medium (maintainability) | Low | Medium |
| 15 | 1.5 External book info consolidation | Low (cleaner schema) | Low | Low |

---

## Testing Strategy

### For Each Tier 1-2 Item
1. **Before refactor:** Capture current behavior as integration test
2. **During refactor:** Unit tests for extracted modules
3. **After refactor:** Run existing test suite, verify no regressions

### Cross-Platform Validation
- After metadata format changes (Part 1): test both Web and iOS against same job
- After audio changes (Part 3): test single-track, sequence, and track switching on both platforms
- After prefetch changes (Part 4): measure time-to-render for chunk transitions

### Specific Test Gaps to Fill
- [ ] iOS: Unit tests for `AudioModeManager` and `SentencePositionProvider`
- [ ] iOS: Multi-file seek tests
- [ ] Web: `useChunkPrefetch` retry and failure recovery tests
- [ ] Web: Sequence segment planning edge cases (single sentence chunks, empty tracks)
- [ ] Backend: metadata_version 3 export round-trip tests

---

## Success Metrics

| Metric | Before | Target | Current |
|--------|--------|--------|---------|
| Chunk metadata size (per sentence) | ~2.5 KB | ~1.8 KB (28% reduction) | ✅ v3 camelCase-only |
| Audio URL resolution code paths | 4+ | 1 shared utility | ✅ `web/src/lib/media/` |
| Subtitle utility duplications | 7 (3 interfaces + 4 functions) | 0 | ✅ `web/src/lib/subtitles/` |
| MyLinguist integration points | 5 separate | 2 (Web service + iOS service) | Web: `lib/linguist` ✅, iOS: ViewModel ✅ |
| `useInteractiveAudioPlayback.ts` lines | 1,647 | ~800 | 765 (Steps 1 & 2) ✅ |
| iOS `InteractivePlayerView+Linguist.swift` lines | 706 | ~300 | 347 ✅ |
| iOS `VideoPlayerView+Linguist.swift` lines | 342 | ~150 | 194 ✅ |
| Chunk transition latency (prefetched) | ~200ms | ~50ms | — |
| Platform-conditional blocks (iOS) | ~40 | ~15 (with view builders) | — |

---

## Open Questions

1. **metadata_version 3 rollout:** Should we version the API endpoint or use content negotiation?
2. **Server-side bookmarks:** Should this be a separate service or integrated into the job API?
3. **State machine library (iOS):** Use a library like `swift-state-machine` or hand-roll?
4. **Progressive hydration UX:** What should the loading state look like between Level 2 and Level 3?
5. **Prefetch budget:** Should we limit total prefetch bandwidth (e.g., 5MB window)?
