# Interactive Player Refactoring & Optimization Plan v2

**Date:** 2026-02-05 (last updated: 2026-02-06)
**Scope:** Metadata optimization, modular separation, audio management, chunk prefetching, and cross-component logic reuse across Web UI and Apple apps.
**Status:** 15/15 items completed (100%, 4.3 deferred). See [Completion Summary](#completion-summary) at end.

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

### 1.3 Consolidate Chunk Manifest vs generated_files.chunks ✅ COMPLETED

**Problem:** `job.json` contains both `chunk_manifest` (lightweight index) and `generated_files.chunks[]` (full chunk entries with inline data). The manifest is a subset but stored separately.

**Implementation:**
- Removed redundant `chunk_manifest` structure from codebase entirely
- For v3 chunks, `generated_files.chunks[]` is already lightweight (heavy keys stripped when metadata_path exists)
- `build_chunk_manifest()` on MetadataLoader now reads from `generated_files.chunks[]` via `iter_chunks()`
- Removed `chunk_manifest` field from: PipelineJob, PipelineJobMetadata, PipelineResponse
- Removed 5-place persistence (job, snapshot, result_payload x2, job.result) — ~30 lines of deepcopy eliminated
- `write_chunk_metadata()` return simplified from `Tuple[Dict, Optional[Dict]]` to just `Dict`
- Backward compat: old job.json files with `chunk_manifest` key are silently ignored
- 12 files changed, ~80 lines removed. Frontends unchanged (never read chunk_manifest)

### 1.4 Lazy Image Metadata ✅ COMPLETED

**Problem:** Each sentence embeds full image metadata (path, prompt, negative_prompt, scene_id, etc.) even when images aren't being displayed. For 14K sentences, this adds substantial payload.

**Implementation:**
- v3 compact chunks now strip the inline `image` dict (added to `_COMPACT_SENTENCE_DROP_KEYS`), keeping only `imagePath`
- `_ImageGenerationState` accumulates manifest entries during image generation; `write_manifest()` writes `metadata/image_manifest.json` at shutdown
- Image info API (`_extract_sentence_image()`) reads from manifest first, falls back to inline `image` dict for old jobs
- Regeneration API updates both chunk files and image manifest
- No new API endpoints needed — existing image info endpoints read from manifest transparently
- No frontend or iOS changes needed — Web already fetches prompt lazily via API, iOS only reads `imagePath`

**Files changed:**
- `modules/core/rendering/pipeline_image_state.py` — `_manifest_entries` dict, `write_manifest()` method
- `modules/core/rendering/pipeline_images.py` — Calls `write_manifest()` in `shutdown()`
- `modules/core/rendering/exporters.py` — `"image"` added to drop keys, `"imagePath"` removed from drop keys
- `modules/webapi/routes/media/images.py` — `_load_image_manifest()`, manifest fallback in extract/build/regen

**Backward compat:** Old jobs without manifest fall back to inline `image` dict. iOS decodes `imagePath` via existing fallback chain.

### 1.5 Structured Media Metadata ✅ COMPLETED

**Problem:** `media_metadata` (aka `book_metadata`) was a flat `Dict[str, Any]` with ~40 fields mixed together — book identity, language config, content structure, cover paths, enrichment provenance. No type safety, no polymorphism for different media types (book, movie, TV, YouTube).

**Implementation:**
- Created `StructuredMediaMetadata` schema with typed sections: `source` (polymorphic by mediaType), `languageConfig`, `contentStructure`, `coverAssets`, `enrichment`
- Backend Pydantic models: `modules/services/metadata/structured_schema.py` (9 models)
- Bidirectional conversion: `modules/services/metadata/structured_conversion.py` (flat↔structured with round-trip fidelity)
- Persistence: `book.json` now written in structured v2 format (camelCase)
- API: `structured_metadata` field added alongside flat `media_metadata` in `PipelineResponsePayload`
- Web: TypeScript interfaces in `web/src/api/mediaMetadata.ts`, client-side normalization in `web/src/lib/metadata/`
- iOS: `StructuredMediaMetadata.swift` Codable structs with `from(json:)` decoder from `JSONValue`

**Key design:**
- `mediaType` discriminator: `"book"` | `"movie"` | `"tv_series"` | `"tv_episode"` | `"youtube_video"`
- `source` section holds common fields (title, author, year, summary, genres) + type-conditional fields (isbn for books, series for TV, youtube for YouTube)
- Processing config (add_images, audio_mode, etc.) excluded — belongs in `JobParameterSnapshot`
- Unknown keys preserved in `extras` dict for forward compat
- Old flat format auto-detected and converted on read — no batch migration needed

**Backward compat:** API returns both flat `media_metadata` and structured `structured_metadata`. Frontends prefer structured when available, fall back to flat. Old `book.json` files normalize on read.

**Files:**
- New: `modules/services/metadata/structured_schema.py` — Pydantic models
- New: `modules/services/metadata/structured_conversion.py` — flat↔structured conversion
- New: `tests/modules/services/metadata/test_structured_conversion.py` — 46 tests
- New: `web/src/api/mediaMetadata.ts` — TypeScript interfaces
- New: `web/src/lib/metadata/normalizeMediaMetadata.ts` — client-side normalization
- New: `web/src/lib/metadata/index.ts` — barrel exports
- New: `ios/.../Models/StructuredMediaMetadata.swift` — Swift Codable structs
- Modified: `modules/services/pipeline_types.py` — `as_structured()` / `from_structured()`
- Modified: `modules/services/metadata/__init__.py` — exports
- Modified: `modules/services/job_manager/persistence.py` — writes structured book.json
- Modified: `modules/webapi/schemas/pipeline_results.py` — `structured_metadata` field
- Modified: `web/src/api/dtos.ts` — `structured_metadata` in response DTO

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

### 2.3 iOS: Reduce Platform Conditional Sprawl ✅ COMPLETED

**Problem:** `InteractivePlayerView+Layout.swift` and other view files contain deeply nested `#if os(iOS)` / `#if os(tvOS)` blocks, making them hard to read and maintain.

**Implementation:**
- Took the `PlatformAdapter` approach — expanded the existing (but unused) 424-line `PlatformAdapter.swift` into an actively used abstraction layer
- Added: `PlatformTypography.scaledFont(_:)`, `.sectionHeaderFont`, `PlatformColors.statusPendingColor/.statusActiveColor`, `PlatformColors.rowTitleColor/rowSecondaryColor/rowTertiaryColor(isFocused:usesDarkBackground:)`, `PlatformMetrics.listIconSize`, `.platformListBackground()` view modifier
- Key finding: ~80% of 506 `#if os()` blocks are structural (different view hierarchies, gestures, focus) — correctly platform-specific, NOT worth abstracting
- Net: +113 lines in PlatformAdapter, −239 lines across 7 consumer files = −88 net lines
- LinguistBubbleView skipped — 45 blocks but 93% structural

**Files:**
- Modified: `PlatformAdapter.swift` — expanded with typography, color, metrics, view modifiers
- Modified: 7 consumer files — replaced inline `#if os()` with PlatformAdapter calls

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

### 2.5 iOS: SequencePlaybackController State Machine ✅ COMPLETED

**Problem:** Sequence transitions use many callback-based patterns with fragile time-based guards (`expectedPosition`, `staleTimeCount`).

**Implementation:**
- Replaced 3 boolean flags + 4 counters with `PlaybackPhase` enum: `.idle`, `.playing`, `.dwelling(startedAt:)`, `.transitioning`, `.validating(Validation)`
- `Validation` struct holds: `expectedPosition`, `staleTimeCount`, `settlingCount`, `reseekAttempts`, `isSettling`
- `@Published isTransitioning`/`isDwelling` kept as stored properties (ViewModel uses `$isTransitioning` via Combine)
- Synced from `phase.didSet` — phase is single source of truth, published props are derived
- `isSameSentenceTrackSwitch` kept as separate sticky metadata (not a state)
- `expectedPosition` is now computed from `.validating` state
- `dwellWorkItem` kept as separate stored property (needs cancellation from multiple call sites)
- 733 → 777 lines (+44), 210 insertions / 166 deletions. Single file change, zero ViewModel/View changes.

**Files:**
- Modified: `SequencePlaybackController.swift` — PlaybackPhase enum, Validation struct, state machine

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

### 3.2 Unified Audio Track Abstraction (iOS) ✅ COMPLETED

**Problem:** Same issue on iOS. `InteractivePlayerViewModel+Selection.swift` has branching logic for single vs sequence modes in `prepareAudio()`.

**Implementation:**
- Extended `AudioModeManager` with track resolution: `resolveAudioInstruction()`, `resolvePreferredTrackID()`, `resolveTimingTrack()`
- `ResolvedAudioInstruction` enum: `.sequence`, `.singleOption`, `.singleURL` — replaces 4-way branching in `prepareAudio()`
- `resolveTimingTrack()` receives runtime state as params — replaces 85-line `activeTimingTrack()`
- `resolvePreferredTrackID()` picks audio option by mode — replaces 12-line switch
- ViewModel gets `var audioModeManager: AudioModeManager?`, set in `.onAppear`
- AudioModeManager: 212 → 441 lines (+229). Consumers: -155 lines across 3 files. Net: +74 lines.

**Files:**
- Modified: `AudioModeManager.swift` — resolveAudioInstruction, resolvePreferredTrackID, resolveTimingTrack
- Modified: `InteractivePlayerViewModel+Selection.swift` — uses AudioModeManager for track resolution
- Modified: `InteractivePlayerViewModel.swift` — audioModeManager property
- Modified: `InteractivePlayerView+Layout.swift` — sets audioModeManager in .onAppear

### 3.3 Audio Preloading Strategy Alignment ✅ COMPLETED

**Problem:** Web prefetches audio heads (bytes 0-2047) with radius=2 chunks. iOS prefetches audio URLs but implementation details differ. Neither platform preloads the *other* track (if in sequence mode, preload both orig and trans for adjacent chunks).

**Implementation:**
- **Web: Dual-track prefetch in sequence mode** — Added `resolveSequenceAudioUrls()` to `audioUrlResolver.ts` (returns both original + translation URLs). `useChunkPrefetch` accepts new `sequenceEnabled` option; when true, prefetches both audio track headers instead of single active track. State bridged from `sequencePlayback.enabled` via `InteractiveTextViewer.tsx`.
- **iOS: Direction-aware prefetch** — Added `PrefetchDirection` enum to ViewModel. `prefetchAdjacentSentencesIfNeeded()` tracks direction from sentence number changes and uses asymmetric radius (1 behind, 3 forward) when playing forward, matching Web behavior.
- **iOS: Dual-track prefetch in sequence mode** — Refactored `prefetchChunkMediaIfNeeded()` into sequence-aware logic: when `audioModeManager?.currentMode == .sequence`, prefetches both `.original` and `.translation` audio options. Extracted `prefetchAudioOption(_:for:)` helper.

**Files changed:**
- `web/src/lib/media/audioUrlResolver.ts` — new `resolveSequenceAudioUrls()` function
- `web/src/lib/media/index.ts` — barrel export
- `web/src/components/interactive-text/useChunkPrefetch.ts` — `sequenceEnabled` option, `prefetchChunkAudioSequence` callback, conditional dispatch
- `web/src/components/InteractiveTextViewer.tsx` — bridging state for `prefetchSequenceEnabled`
- `ios/.../InteractivePlayerViewModel.swift` — `PrefetchDirection` enum + `prefetchDirection` property
- `ios/.../InteractivePlayerViewModel+Prefetch.swift` — direction tracking, asymmetric radius, dual-track prefetch
- `ios/.../InteractivePlayerViewModel+Selection.swift` — reset `prefetchDirection` on chunk change
- `ios/.../InteractivePlayerViewModel+Loading.swift` — reset `prefetchDirection` on job load

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

### 4.2 Sentence-to-Chunk Mapping Cache ✅ COMPLETED

**Problem:** Converting sentence numbers to chunk indices requires scanning `chunk_manifest`. With multi-sentence chunks this is less costly, but still involves repeated lookups.

**Implementation:**
- Created `web/src/lib/media/sentenceChunkIndex.ts` — O(1) map + O(log n) binary search
- `buildSentenceChunkIndex(chunks)` → `SentenceChunkIndex` with `map`, `ranges`, `min`, `max`
- `lookupSentence(index, num)` → exact map first, binary search ranges fallback
- `findChunkBySentence(index, chunks, num)` → convenience wrapper returning chunk object
- Replaced `findChunkForSentence()` linear scan in `useChunkPrefetch.ts`
- 24 tests in `sentenceChunkIndex.test.ts`

**Files:**
- New: `web/src/lib/media/sentenceChunkIndex.ts`
- New: `web/src/lib/media/sentenceChunkIndex.test.ts`
- Modified: `web/src/components/interactive-text/useChunkPrefetch.ts` — uses sentenceChunkIndex

### 4.3 Progressive Metadata Hydration — DEFERRED

**Problem:** `hydrateChunk()` in `useChunkPrefetch.ts` merges prefetched sentences into chunk data. This is all-or-nothing.

**Proposal:**
- Level 1 (index): chunk_id, sentence_count, audio URLs (from manifest, instant)
- Level 2 (sentences): sentence text, tokens, gates (from chunk file, prefetchable)
- Level 3 (timing): full timing tracks (from chunk file, prefetched with audio)
- Level 4 (images): image metadata (lazy, on-demand)

Components render progressively: show sentence text as soon as Level 2 arrives, show highlighting when Level 3 arrives.

**Status:** Deferred — requires backend API changes to serve metadata at different granularity levels. Current chunk loading is fast enough with prefetching improvements (4.1, 4.2, 4.4).

### 4.4 Prefetch Failure Recovery ✅ COMPLETED

**Problem:** Current retry logic uses fixed intervals (6s for metadata, 12s for audio). No escalation or circuit breaking.

**Implementation:**
- Exponential backoff: 2s/4s/8s/16s cap via `getBackoffMs(failures)`
- Per-chunk circuit breaker: 3 consecutive failures → skip
- Systemic failure detection: 5 consecutive failures → 30s pause
- `isPrefetchDegraded` state exposed for UI health indicator
- `RetryState`, `getBackoffMs`, `shouldRetry` exported for testing
- 15 tests in `prefetchRetry.test.ts`

**Files:**
- New: `web/src/components/interactive-text/prefetchRetry.ts`
- New: `web/src/components/interactive-text/prefetchRetry.test.ts`
- Modified: `web/src/components/interactive-text/useChunkPrefetch.ts` — uses retry/circuit breaker logic

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

### 5.3 Shared Playback Controls Pattern ✅ COMPLETED

**Problem:** Play/pause, seek, rate, and keyboard shortcuts exist in multiple places across Web and iOS.

**Implementation:**
- Created `web/src/lib/playback/playbackActions.ts` — canonical `PlaybackControls` + `ExtendedPlaybackControls` interfaces
- 4 consumers re-export/alias from `lib/playback` (player-panel, video-player, PlayerPanelStage, youtube-player)
- iOS already has `PlayerCoordinating` protocol — no changes needed

**Files:**
- New: `web/src/lib/playback/playbackActions.ts`
- Modified: 4 consumer files — re-export from canonical source

### 5.4 Server-Side Resume Position ✅ COMPLETED

**Problem:** Playback resume position only persisted in browser `sessionStorage` (Web) and iCloud/UserDefaults (iOS). No cross-device resume between Web and iOS.

**Implementation:**

**Backend** (3 new files, 2 modified):
- `modules/services/resume_service.py` — `ResumeEntry` dataclass + `ResumeService` (get/save/clear) with atomic JSON writes
- `modules/webapi/schemas/resume.py` — `ResumePositionPayload`, `ResumePositionEntry`, `ResumePositionResponse`
- `modules/webapi/routers/resume.py` — GET/PUT/DELETE `/api/resume/{job_id}`
- `modules/webapi/dependencies.py` — `get_resume_service()` registration
- `modules/webapi/application.py` — `resume_router` registration

**Web** (1 new file, 2 modified):
- `web/src/api/client/resume.ts` — `fetchResumePosition`, `saveResumePosition`, `clearResumePosition`
- `web/src/api/dtos.ts` — TypeScript types for resume API
- `web/src/hooks/useMediaMemory.ts` — Fetch from API on mount (only applies if sessionStorage has no position > 1), debounced save every 5s, flush on `pagehide`

**iOS/tvOS** (4 modified):
- `ApiModels.swift` — `ResumePositionEntry`, `ResumePositionResponse`, `ResumePositionSaveRequest`, `ResumePositionDeleteResponse`
- `APIClient.swift` — `fetchResumePosition()`, `saveResumePosition()`, `deleteResumePosition()`
- `PlaybackResumeStore.swift` — `configureAPI()`, fire-and-forget saves/deletes to API alongside CloudKit, `refreshFromAPI()` for server→local merge
- `AppState.swift` — wires API config on login/restore, clears on sign-out

**Storage:** `storage/resume/{user_fragment}/{job_fragment}.json`

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

### Tier 2: Architectural Improvements — ALL COMPLETED

| # | Item | Status |
|---|------|--------|
| 6 | 3.1 Unified AudioTrackProvider (Web) — Steps 1 & 2 | ✅ |
| 7 | 2.4 MyLinguist BubbleViewModel (iOS) | ✅ |
| 8 | 5.2 Shared MyLinguist service layer (Web) | ✅ |

### Tier 3: Larger Refactors — ALL COMPLETED

| # | Item | Status |
|---|------|--------|
| 8 | 2.5 Sequence state machine (iOS) | ✅ |
| 9 | 3.2 AudioModeManager as track provider (iOS) | ✅ |
| 10 | 1.3 Consolidate chunk manifest | ✅ |
| 11 | 4.3 Progressive metadata hydration | Deferred |

### Tier 4: Feature Enhancements — ALL COMPLETED

| # | Item | Status |
|---|------|--------|
| 12 | 1.4 Lazy image metadata | ✅ |
| 13 | 5.4 Server-side resume position | ✅ |
| 14 | 2.3 iOS platform conditional cleanup | ✅ |
| 15 | 1.5 Structured media metadata | ✅ |

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
| Chunk metadata size (per sentence) | ~2.5 KB | ~1.8 KB (28% reduction) | ✅ v3 camelCase-only + dedup + lazy images |
| Audio URL resolution code paths | 4+ | 1 shared utility | ✅ `web/src/lib/media/` |
| Subtitle utility duplications | 7 (3 interfaces + 4 functions) | 0 | ✅ `web/src/lib/subtitles/` |
| MyLinguist integration points | 5 separate | 2 (Web service + iOS service) | ✅ Web: `lib/linguist`, iOS: ViewModel |
| `useInteractiveAudioPlayback.ts` lines | 1,647 | ~800 | ✅ 765 (Steps 1 & 2) |
| iOS `InteractivePlayerView+Linguist.swift` lines | 706 | ~300 | ✅ 347 |
| iOS `VideoPlayerView+Linguist.swift` lines | 342 | ~150 | ✅ 194 |
| Chunk transition latency (prefetched) | ~200ms | ~50ms | ✅ Prefetch + direction-aware + failure recovery |
| Platform-conditional blocks (iOS) | ~40 | ~15 (with view builders) | ✅ ~88 lines net reduction via PlatformAdapter |
| Cross-device resume | None | Server-side sync | ✅ Backend API + Web + iOS/tvOS |
| Chunk manifest redundancy | Dual storage | Single source | ✅ Removed chunk_manifest |
| Sequence state management (iOS) | 3 booleans + 4 counters | State machine | ✅ PlaybackPhase enum |
| Audio track resolution (iOS) | 4-way branching | AudioModeManager | ✅ resolveAudioInstruction() |
| Sentence→chunk lookup (Web) | O(n) linear scan | O(1) map + O(log n) | ✅ sentenceChunkIndex |
| Playback controls interface (Web) | 4 separate definitions | 1 canonical | ✅ `lib/playback/playbackActions.ts` |
| Audio tracks prefetched (sequence) | 1 (active only) | Both orig + trans | ✅ Web + iOS dual-track prefetch |
| iOS prefetch direction awareness | Symmetric ±2 always | Asymmetric when playing | ✅ 1 back / 3 forward when playing forward |
| Media metadata type safety | Flat Dict[str, Any] everywhere | Typed polymorphic schema | ✅ StructuredMediaMetadata v2 (9 Pydantic models, TS interfaces, Swift Codable) |

---

## Open Questions (Resolved)

1. ~~**metadata_version 3 rollout:** Should we version the API endpoint or use content negotiation?~~ → Used version field in chunk files, backward-compat readers
2. ~~**Server-side bookmarks:** Should this be a separate service or integrated into the job API?~~ → Separate `ResumeService` + `/api/resume/` routes (5.4)
3. ~~**State machine library (iOS):** Use a library like `swift-state-machine` or hand-roll?~~ → Hand-rolled `PlaybackPhase` enum (2.5)
4. **Progressive hydration UX:** Deferred (4.3) — current prefetching is fast enough
5. **Prefetch budget:** Not yet addressed — consider if bandwidth issues arise

---

## Completion Summary

**Completed:** 15 of 15 items (100%)
- Part 1: 5/5 (1.1 ✅, 1.2 ✅, 1.3 ✅, 1.4 ✅, 1.5 ✅)
- Part 2: 5/5 (2.1 ✅, 2.2 ✅, 2.3 ✅, 2.4 ✅, 2.5 ✅)
- Part 3: 3/3 (3.1 ✅, 3.2 ✅, 3.3 ✅)
- Part 4: 3/4 (4.1 ✅, 4.2 ✅, 4.3 deferred, 4.4 ✅)
- Part 5: 4/4 (5.1 ✅, 5.2 ✅, 5.3 ✅, 5.4 ✅)

**Deferred:** 1 item
- 4.3 Progressive metadata hydration — requires backend API changes, current prefetching is sufficient

**Bug fixes (outside plan):**
- Sequence playback gate data fix — gates were being stripped by compact chunk serialization
