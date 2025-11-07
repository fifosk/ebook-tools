# Sentence Data & Highlighting Reference

This document summarises how the pipeline generates sentence-level timing data, merges it into the **mix** and **translation** tracks, persists the artefacts, and replays them for highlighting. The goal is to outline the moving parts so we can reason about future accuracy work.

## 1. End-to-end path (bird’s-eye)

1. **Translation + audio synthesis** – `audio_worker_body` consumes `TranslationTask` objects, calls the configured TTS backend, and collects the emitted `AudioSegment` plus any timing metadata (`modules/render/audio_pipeline.py:640-964`).
2. **Word-token derivation** – multiple strategies fill `metadata["word_tokens"]` (backend timings, forced alignment, char-timing extraction, or character-weighted inference) and annotate `highlighting_summary`.
3. **Sentence payloads** – the exporter builds per-sentence highlight timelines (for slide/video rendering) and `SentenceTimingSpec` entries that capture original/translation durations per sentence (`modules/core/rendering/exporters.py:300-420`, `:598-740`).
4. **Dual-track merge** – `build_dual_track_timings` converts the sentence specs into two flattened tracks, `mix` and `translation`, with per-word offsets (`modules/core/rendering/timeline.py:419-780`).
5. **Persistence** – `modules/services/job_manager/persistence.py` writes `metadata/chunk_XXXX.json`, a compact `metadata/job.json` (holding the chunk manifest + sentence summaries), and a `metadata/timing_index.json` aggregate for quick lookup.
6. **Playback** – the frontend loads `timing_index.json` (via `/api/jobs/{job_id}/timing`) to drive transcript highlights, while the video slide renderer reuses the per-sentence timelines to animate word fills in rendered media (`README.md:385-417`, `docs/architecture.md:98-135`).

## 2. Sentence-level generation

### 2.1 Translation task ingestion

- Every translation unit contains the original sentence, fluent translation, transliteration (when available), indexes, and target language metadata. `audio_worker_body` receives the task alongside context such as `tempo`, selected voice, and alignment preferences (`modules/render/audio_pipeline.py:480-720`).
- When audio generation is enabled, the worker invokes the configured backend. Backends may return a plain `AudioSegment` or a `SynthesisResult` bundle that includes `word_tokens`, `char_timings`, or backend-specific alignment blobs.

### 2.2 Word timing sources (ordered by priority)

1. **Backend-supplied word tokens** – Many TTS engines emit `(text, start, end)` tuples. The worker normalises them, enforces monotonicity, and records a `forced` alignment policy, as long as the token count matches the translated word count (`modules/render/audio_pipeline.py:755-788`).
2. **Forced alignment backend** – If no tokens exist and `forced_alignment_enabled` is on, the worker shells out to the WhisperX adapter (or whichever backend is configured) and converts the response into tokens (`modules/render/audio_pipeline.py:800-846`). The selected WhisperX model is logged per sentence for drift investigations.
3. **Per-character timings** – `_extract_word_tokens` searches the `AudioSegment` for character timing arrays (e.g., macOS `char_timings`) or metadata-provided arrays, collapses them into words/graphemes, and marks the policy as `forced` when available (`modules/render/audio_pipeline.py:481-560` together with `modules/audio/highlight/core.py:270-360`).
4. **Character-weighted inference** – When no concrete timings exist, the worker falls back to `compute_char_weighted_timings` to distribute the sentence duration across words proportional to their character counts, optionally applying the punctuation boost heuristic if `char_weighted_punctuation_boost` is enabled (`modules/render/audio_pipeline.py:722-753`, `modules/core/rendering/timeline.py:180-238`).
5. **Uniform fallbacks** – If there is neither audio nor duration metadata, `_evenly_distributed_tokens` (via `_extract_word_tokens`) emits equally spaced tokens and labels the policy `uniform`.

All successful strategies update:

- `metadata["word_tokens"]` – monotonic `[{"text","start","end"}, …]`.
- `metadata["highlighting_summary"]` – includes `policy`, `tempo`, `token_count`, `duration`, `source`, whether char-weighted inference ran, and the active punctuation boost flag (`modules/render/audio_pipeline.py:909-925`).
- `metadata["highlighting_policy"]` – echoed later in chunk files and enforceable through `EBOOK_HIGHLIGHT_POLICY`.

Audio segments that carry character timings or word tokens retain those lists via attribute assignments so downstream consumers (timeline builder, dual-track assembly) can reuse them (`modules/render/audio_pipeline.py:936-939`).

### 2.3 Per-sentence highlight timelines

The exporter calls `timeline.build` for each sentence (`modules/core/rendering/exporters.py:330-390`). The timeline builder:

- Parses the triple (original, translation, transliteration) from the block representation.
- Looks up `SentenceAudioMetadata` that the audio worker stored on each `AudioSegment`. This metadata describes every contiguous audio part (original speech, translation speech, silence) along with low-level `HighlightStep`s derived from character timings or forced alignment (`modules/audio/highlight/core.py:34-220`).
- Builds `HighlightEvent`s with cumulative original/translation/transliteration indexes that describe how many tokens should be highlighted after each event, accounting for silence pads and, when available, character-level ranges (`modules/audio/highlight/core.py:200-360`, `timeline.py:35-120`).
- Falls back to sentence-duration proportional events when there is no per-character data.

Each sentence payload now carries:

- `timeline` – the event list consumed by slide renderers and subtitle generation.
- `highlight_granularity` – `char` when character ranges exist and char-highlighting is requested, otherwise `word`.
- `counts` + token arrays for original/translation/transliteration segments.

These payloads feed both human-readable metadata (e.g., `phase_durations`, `charWeighted` summary) and the later dual-track builder via `SentenceTimingSpec`.

## 3. Dual-track assembly (mix + translation)

### 3.1 Sentence specs

`BatchExporter` converts each sentence payload into a `SentenceTimingSpec`, capturing:

- `original_duration`, `translation_duration`, `gap_before_translation`, `gap_after_translation`.
- `original_words`, `translation_words`, plus the computed `word_tokens` (per translation).
- Highlight policy flags (`char_weighted_enabled`, `punctuation_boost`, `policy`, `source`).

These specs are stored in `sentence_specs` (`modules/core/rendering/exporters.py:598-688`).

### 3.2 Building tracks

`build_dual_track_timings(sentence_specs, mix_duration, translation_duration)` performs:

1. **Translation track** – re-fit the `word_tokens` to the track’s total duration (`_fit_tokens_to_duration`) so the translation-only audio file can scrub precisely. When tokens are missing it reuses `compute_char_weighted_timings` over the translation text, labeling the entries with `policy="char_weighted"` and `source="char_weighted"` (`modules/core/rendering/timeline.py:419-552`).
2. **Mix track** – create two interleaved lanes in a single array:
   - `lane="orig"` entries cover the original speech using char-weighted timings across `original_words`. They always mark `policy="char_weighted"` and `source="original"`.
   - `lane="trans"` entries reuse the fitted translation tokens but shift them by (`original_duration` + `gap_before_translation`). The `fallback` flag marks when the translation lane had to be char-weighted instead of using measured tokens (`modules/core/rendering/timeline.py:560-720`).
3. **Clamping** – `_clamp_track_tokens` ensures both tracks terminate exactly at their rendered durations to avoid drift when concatenating multiple chunks (`modules/core/rendering/timeline.py:360-418`, `:700-748`).

Track entries look like:

```json
{
  "lane": "trans",
  "sentenceIdx": 12,
  "wordIdx": 3,
  "start": 75.123,
  "end": 76.432,
  "text": "library",
  "policy": "forced",
  "source": "word_tokens",
  "fallback": false
}
```

Both tracks are stored under `chunk["timingTracks"] = {"mix": [...], "translation": [...]}` before persistence.

## 4. Persistence & lookup

### 4.1 Chunk files

- `_write_chunk_metadata` materialises each chunk as `metadata/chunk_0000.json`, embedding:
  - Sentence payloads (with timelines, counts, char-weighting summaries).
  - `timingTracks.mix` and `.translation`.
  - `audioTracks` metadata describing the mix/translation MP3 paths when generated.
- The corresponding chunk entry in `job.json` stores pointers (`metadata_path`, `metadata_url`) so clients can lazily load sentence payloads (`modules/services/job_manager/persistence.py:639-759`).

### 4.2 Chunk manifest & job.json

`job.json` contains:

- Global job attributes (languages, cover, total sentence counts, etc.).
- `chunk_manifest`: `{ "chunk_count": N, "chunks": [{ "index": 0, "chunk_id": "...", "path": "metadata/chunk_0000.json", ...}, ...] }`.

`MetadataLoader.build_chunk_manifest()` reconstructs the manifest even for legacy inline payloads to provide a consistent API (`modules/metadata_manager.py:826-864`).

### 4.3 Timing index

`build_timing_index` scans every `chunk_*.json` for `timingTracks`. It concatenates both tracks into `metadata/timing_index.json`, preserving lane metadata, `policy`, `source`, sentences IDs, and the `fallback` bit so downstream tooling (QA scripts, frontend) can reason about the provenance of each timing (`modules/services/job_manager/persistence.py:135-193`). The job snapshot stores pointers back to this index so `/api/jobs/{job_id}/timing` can stream it.

## 5. Highlight playback

### 5.1 Video/subtitle rendering

- Slide video rendering uses the per-sentence `timeline` payload. The renderer coalesces `HighlightEvent`s via `coalesce_highlight_events` to reduce frames, then synchronises them with the actual slide audio.
- `SubtitlesPage` can request colourised subtitle exports via `modules/subtitles/processing.py`, which reads the same timelines and word tokens to generate ASS/SRT with word-level highlighting states.

### 5.2 Frontend interactive transcript

- `useWordHighlighting` pulls `metadata/timing_index.json`, hydrates a MobX-like store, and keeps the audio player’s `currentTime` in lock-step with `mix`/`translation` tracks (`README.md:360-417`).
- `InteractiveTextViewer` (and `MediaSearchPanel`) subscribe to the track store to highlight the right tokens, showing original vs translation lanes exactly as produced by the backend manifest. The `fallback` flag is surfaced in the debug overlay to spot char-weighted segments quickly.

## 6. Accuracy levers & investigation hooks

1. **Instrument mismatches** – we currently log when backend token counts diverge from translation word counts (`modules/render/audio_pipeline.py:789-795`), but that information is lost after the log. Persisting a per-sentence `token_mismatch` flag in chunk metadata would help dashboards highlight problematic sentences.
2. **Char-weighted heuristics** – `compute_char_weighted_timings` treats every grapheme equally unless punctuation weighting is toggled. Languages without whitespace (Chinese, Japanese) may still receive per-character timing even when the backend supplied word-level units because `_split_translation_units` falls back to characters (`modules/audio/highlight/timeline.py:27-40`). Consider language-specific segmentation (e.g., Jieba) before char weighting to avoid jitter.
3. **Alignment backend selection** – `_resolve_alignment_model_choice` (inside `audio_pipeline`) picks WhisperX models per ISO code but does not record failures beyond log lines. Recording the final `alignment_model` into `highlighting_summary` (already partially done via `alignment_model_used`) and exposing it in `timing_index` entries could make cross-job analysis simpler.
4. **Mix-track gaps** – The mix track assumes a single silence pad (`SILENCE_DURATION_MS`) between original and translation audio when generating combined MP3s (`modules/core/rendering/exporters.py:540-620`). If TTS backends start inserting dynamic pauses, we should capture the actual measured `gap_before_translation`/`gap_after_translation` per sentence rather than relying on static silence.
5. **Validation tooling** – `scripts/validate_alignment_quality.py` and `scripts/validate_word_timing.py` already parse `timing_index.json`. Extending them to highlight how many tokens were char-weighted (`fallback=true`) per job would quantify how often we fall back to heuristics.

Keeping the above flow documented should make it easier to reason about highlighting drift, experiment with new aligners, or bolt on analytics without reverse-engineering the code paths every time.

## 7. Configuration summary

- **`EBOOK_HIGHLIGHT_POLICY` / `highlighting_policy`** – `forced` fails jobs when
  neither backend timings nor forced alignment succeed,
  `prefer_char_weighted` allows heuristics, and `allow_uniform` tolerates evenly
  distributed tokens.
- **`char_weighted_highlighting_default` /
  `EBOOK_CHAR_WEIGHTED_HIGHLIGHTING_DEFAULT`** – toggles the character-weighted
  inference path whenever no concrete tokens are available.
- **`char_weighted_punctuation_boost` /
  `EBOOK_CHAR_WEIGHTED_PUNCTUATION_BOOST`** – enables punctuation-aware padding
  so pauses feel more natural during inferred timings.
- **`forced_alignment_enabled`, `alignment_backend`,
  `alignment_model_overrides`** – control WhisperX usage and per-language model
  selection. The chosen model is recorded in each chunk’s
  `highlighting_summary.alignment_model_used`.

Revisit this table any time audio generation, metadata layouts, or highlighting
logic change so regression triage has a single authoritative reference.
