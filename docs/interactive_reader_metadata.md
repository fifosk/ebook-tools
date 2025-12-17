# Interactive Reader Metadata Flow

This guide explains how the Interactive Reader ingests timing metadata, binds it to playback, and renders highlights. Use it when evaluating highlighting accuracy, latency, or UX improvements.

## 1. Data Sources

- **Live job media snapshot.** `useLiveMedia` normalises `/api/pipelines/jobs/{job_id}/media` (and its live variant) into `LiveMediaChunk` records. Each chunk exposes `sentences`, `audioTracks`, and optional `timingTracks` pulled directly from `metadata/chunk_*.json` (`web/src/hooks/useLiveMedia.ts:360-520`).
- **Sentence images.** When a job enables `add_images`, sentence metadata may include `image` payloads (plus `image_path` / `imagePath`) pointing at PNG files stored under `media/images/<range_fragment>/sentence_XXXXX.png`. The Interactive Reader consumes these fields to render an image reel during playback (`modules/core/rendering/pipeline.py`, `web/src/components/InteractiveTextViewer.tsx:4364-4860`).
- **Timing endpoint (legacy/back-compat).** When a job still exposes `/api/jobs/{job_id}/timing`, `fetchJobTiming` hydrates the aggregated payload with both `mix` and `translation` tracks plus audio availability flags (`web/src/api/client.ts:355-382`, `web/src/api/dtos.ts:369-420`). New jobs may not have this endpoint, in which case the viewer relies solely on chunk metadata.
- **Chunk content.** `InteractiveTextViewer` also receives the raw transcript block for the selected chunk (paragraph text, sentence timelines, char-weight flags) via `PlayerPanel` so it can build paragraph/translation views even when word-level timing is absent (`web/src/components/PlayerPanel.tsx:2636-2740`).

## 2. Loading & Selection Logic

1. **Chunk selection.** When the user opens a text chunk, `PlayerPanel` passes the matching `LiveMediaChunk` (including `timingTracks`) and inline audio URLs into `InteractiveTextViewer`.
2. **Timing fetch.** On mount or when `jobId` changes, `InteractiveTextViewer` conditionally calls `fetchJobTiming`. Responses are cached in component state as `jobTimingResponse` (`web/src/components/InteractiveTextViewer.tsx:707-842`).
3. **Local track candidates.** The viewer inspects `chunk.timingTracks`, filters by the active chunk, and prioritises track types based on the currently selected audio lane (combined `orig_trans` vs translation-only) (`web/src/components/InteractiveTextViewer.tsx:1397-1453`).
4. **Word index construction.** For legacy/local tracks, `buildWordIndex` produces sentence → token indexes (lane, tokenIdx, timestamps) that power fallback highlighting and on-click seeking (`web/src/components/InteractiveTextViewer.tsx:1454-1536`).
5. **Remote vs local choice.** If the timing API returned usable data, it wins. Otherwise the viewer falls back to the chunk-level track. Flags (`hasRemoteTiming`, `hasLegacyWordSync`) determine whether word sync can run at all (`web/src/components/InteractiveTextViewer.tsx:1531-1557`).
6. **Payload normalisation.** `buildTimingPayloadFromJobTiming` converts raw API segments into `TimingPayload` objects by bucketing tokens per sentence and sorting them chronologically. The same shape is used for local tracks via `buildTimingPayloadFromWordIndex` (`web/src/components/InteractiveTextViewer.tsx:198-330`, `:1542-1557`).

## 3. Playback + Highlight Synchronisation

- **Timing store.** `timingStore` is a lightweight observable holding the active `TimingPayload`, the most recent hit (segment/token indexes), and the playback rate (`web/src/stores/timingStore.ts:1-53`).
- **Audio synchroniser.** `AudioSyncController` samples the `<audio>` element through `PlayerCore`, maps media time to token windows, and updates `timingStore.setLast(hit)` on every animation frame. It also watches rate/seeks to rebuild the timeline when needed (`web/src/player/AudioSyncController.ts:1-340`).
- **Player core integration.** When the viewer loads a timing payload, it sets `timingStore.setPayload(...)` and syncs the media clock rate. Starting/stopping audio sync is tied to the component’s lifecycle so orphaned listeners are cleaned up (`web/src/components/InteractiveTextViewer.tsx:1688-1716`).
- **Word highlighting hook.** `useWordHighlighting` subscribes to `timingStore`, manages “fences” to prevent backwards highlight jumps during scrubbing, and exposes state to transcript components (`web/src/hooks/useWordHighlighting.ts:1-112`).
- **Transcript virtualization.** `TranscriptView` renders the current segment window, derives word state (`prev`/`now`/`next`), and wires clicks back to `PlayerCore.seek()` while updating the fence via `useWordHighlighting` (`web/src/components/transcript/TranscriptView.tsx:1-220`). `SegmentBlock` splits tokens per lane, and `Word` applies the CSS classes that animate highlights (`web/src/components/transcript/SegmentBlock.tsx:1-150`, `web/src/components/transcript/Word.tsx:1-60`).

## 4. Visualisation Layers Inside the Viewer

1. **Paragraph & timeline assembly.** The viewer parses the raw chunk text into paragraphs/sentences, builds highlight parts for original/translation/transliteration variants, and reconstructs sentence timelines using per-sentence metadata (phase durations, event lists) from chunk files (`web/src/components/InteractiveTextViewer.tsx:880-1360`).
2. **Timeline sentences.** Each chunk sentence becomes a `TimelineSentenceRuntime` structure that records token arrays for the three lanes plus derived per-event durations so the “karaoke” overlay can animate bars even when no timing payload is available (`web/src/components/InteractiveTextViewer.tsx:1110-1360`).
3. **Word Sync controller (legacy).** For older jobs (or when the timing API is unavailable), `WordSyncController` drives DOM-class toggles directly rather than via `TranscriptView`. The controller uses `useMediaClock` to map audio time into track space and still respects fences/diagnostics (`web/src/components/InteractiveTextViewer.tsx:1633-1750`, `web/src/hooks/useLiveMedia.ts:1009-1050`).
4. **Diagnostics.** Highlight policy info (`highlighting_policy`, `has_estimated_segments`) is stored in `timingDiagnostics` for UI/tooling and also logged to the console in dev builds using `computeTimingMetrics` so engineers can inspect drift/tempo ratios quickly (`web/src/components/InteractiveTextViewer.tsx:1559-1615`). For deeper inspection, `enableHighlightDebugOverlay` paints the current segment/token indexes on screen (`web/src/player/AudioSyncController.ts:316-356`).
5. **Sentence image reel.** When sentence images are available, the viewer renders a 7-frame “movie reel” strip (3 previous, active, 3 next) above the text tracks. Visibility is toggled with `R` and persisted in `localStorage` as `player.sentenceImageReelVisible`. Clicking a frame jumps the player to that sentence (`web/src/components/InteractiveTextViewer.tsx:4364-4860`).

## 5. How Metadata Surfaces to Users

- **Inline audio controls.** `InteractiveTextViewer` chooses the most appropriate audio file (`orig_trans` vs `translation`) based on the chosen timing track and whether original-language playback is enabled, ensuring the transcript and audio stay in lock-step (`web/src/components/InteractiveTextViewer.tsx:1380-1441`).
- **Image-assisted playback.** Sentence images are resolved through the same storage URL mechanism as audio (`/storage/jobs/<job_id>/...`). The reel preloads nearby sentences so images appear immediately when scrubbing (`web/src/components/InteractiveTextViewer.tsx:4420-4860`).
- **Dual-lane transcript.** `TranscriptView` (used across the reader and `MediaSearchPanel`) renders interleaved original/translation lanes, with word buttons highlighting as `timingStore.last` advances. Clicking a word seeks playback to `token.t0`, using fences to avoid re-highlighting earlier tokens mid-seek (`web/src/components/transcript/TranscriptView.tsx:150-218`).
- **Timeline overlays & subtitles.** Sentence-level `timeline` data (per `chunk.sentences[].timeline`) powers the timeline cards, subtitle exports, and the optional word-progress bars shown in the UI when `hasTimeline` is true (`web/src/components/InteractiveTextViewer.tsx:1010-1375`).

## 6. Opportunities for Improvement

1. **Surface timing provenance.** The UI currently logs `highlighting_policy` to the console but does not show users whether they are seeing inferred/char-weighted tokens. Exposing `timingDiagnostics` in the reader (or tooltip) would help QA spot fallback cases faster.
2. **Per-chunk caching.** When `/api/jobs/{id}/timing` exists we currently re-fetch it on every chunk swap, even though the payload is job-wide. Caching the promise per job (in context or a SWR-style hook) would shave ~200–400 ms on chunk swaps.
3. **Unify track builders.** There are two parallel code paths: job-level `buildTimingPayloadFromJobTiming` and chunk-level `buildTimingPayloadFromWordIndex`. Harmonising them (e.g., by storing pre-normalised `segments` alongside chunk metadata) would reduce drift and remove the legacy word-index adapter.
4. **Better fallback messaging.** When no timing payload exists the viewer silently disables highlights. Adding a visible badge (“Word sync unavailable for this chunk”) plus links to metadata diagnostics would aid debugging.
5. **Token quality metrics.** `computeTimingMetrics` already emits avg token duration and drift; persisting those metrics (per job/chunk) would enable dashboards spotting problematic pipelines without manual console inspection.
6. **Accessibility hooks.** Token elements are currently `<button>`s without ARIA state updates when highlights move. Publishing the active token via `aria-live` or updating `aria-current` could improve screen-reader support using the same metadata already exposed through `timingStore`.

Keeping these pathways in mind will make it easier to reason about highlight fidelity, timeline lag, and UX regressions whenever the backend metadata changes.

## 7. Backend provenance quick reference

- **Audio generation.** `modules/render/audio_pipeline.py` is the source of truth
  for `word_tokens`. It records whether the tokens came from the TTS backend,
  WhisperX (`modules/align/backends/whisperx_adapter.py`), or the
  char-weighted/uniform heuristics and stores that provenance in every sentence’s
  `highlighting_summary`.
- **Metadata creation.** `modules/services/job_manager/persistence.py` emits
  `metadata/job.json`, `metadata/chunk_manifest.json`, and the per-chunk payloads
  that the frontend hydrates. Client code should always route through
  `MetadataLoader.for_job(job_id)` so the new chunked format and legacy single
  file stay interchangeable.
- **Highlight controls.** `EBOOK_HIGHLIGHT_POLICY`,
  `char_weighted_highlighting_default`,
  `char_weighted_punctuation_boost`, and the forced-alignment toggles determine
  which provenance the reader will see. When QA spots drift, inspect the
  `highlighting_policy` and `highlighting_summary` fields (via chunk metadata or,
  when available, `/api/jobs/{job_id}/timing`) before assuming a frontend bug.

Update this section whenever the audio worker, metadata artefacts, or highlight
policies change—most reader regressions trace back to those touch points.
