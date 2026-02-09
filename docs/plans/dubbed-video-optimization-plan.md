# Dubbed Video Pipeline: Optimization & Alignment Improvement Plan

## Current Architecture Summary

The dubbing pipeline lives in `modules/services/youtube_dubbing/` and follows this flow:

```
Subtitles -> Parse Dialogues -> Translate -> Synthesize TTS -> Schedule Timeline
  -> Trim/Pad Video Segments -> Mix Audio -> Mux -> Concat Batches -> Stitch
```

**Key files:**
- `generation.py` - Main orchestrator (`generate_dubbed_video()`)
- `audio_utils.py` - Time-stretching, mixing, active window detection
- `video_utils.py` - FFmpeg wrappers for trim, mux, concat, pad
- `dialogues.py` - Subtitle parsing, pace estimation, gap enforcement
- `stitching.py` - Multi-batch concatenation and validation
- `translation.py` - Parallel LLM translation with batching
- `common.py` - Shared data models (`_AssDialogue`) and constants

---

## Problem Analysis: Audio-to-Video Timeline Misalignment

The core challenge is that TTS-generated audio rarely matches the original dialogue window duration. The current pipeline has several structural weaknesses that compound into timeline drift:

### 1. No per-sentence duration targeting

TTS synthesis (`generation.py:274-286`) generates audio without any target duration. The `_fit_segment_to_window()` function (`audio_utils.py:150-165`) is effectively a no-op - it explicitly avoids stretching:

```python
def _fit_segment_to_window(segment, target_seconds, *, max_speedup=1.0):
    # "We avoid stretching or padding; any gating happens via scheduling downstream."
    return segment
```

This means a 2-second original dialogue window might produce a 3.5-second dubbed audio, pushing everything downstream.

### 2. Coarse pace estimation

`_compute_pace_factor()` (`dialogues.py:134-148`) computes a single multiplier for an entire batch using a flat 2.8 words/sec target. It only adjusts macOS reading speed, not per-segment timing. Languages with different syllabic density (e.g., Japanese vs. Spanish) get the same treatment.

### 3. Dubbed timeline is audio-driven, not source-driven

The scheduling loop (`generation.py:506-556`) builds the output timeline from the actual TTS audio length rather than anchoring to original subtitle windows. The cursor advances by `audio_duration`, not by the original `entry.end - entry.start`. This design choice preserves audio quality (no aggressive stretching) but sacrifices temporal alignment with the original video.

### 4. Batch boundary drift

When `flush_block` splits dialogues into batches (`generation.py:467`), each batch computes its own pace factor independently. There is no correction mechanism across batch boundaries, so small drifts accumulate over long videos.

### 5. Gap handling loses precision

Inter-dialogue gaps are preserved from the source timeline, but their insertion is fragile:
- Gap clips are trimmed from the source video and padded to fit (`generation.py:583-606`)
- If gap extraction fails, the gap is silently skipped (`generation.py:599-606`)
- Trailing gap computation (`generation.py:788-810`) can introduce drift if block boundaries don't align precisely

---

## Improvement Plan

### Phase 1: Per-Sentence Duration-Aware TTS

**Goal:** Make each synthesized audio segment fit its original dialogue window.

**Files to modify:**
- `audio_utils.py` - Revive `_fit_segment_to_window()` with actual time-stretch logic
- `generation.py` - Pass original window duration to the synthesis step

**Implementation:**

1. **Add per-sentence time-stretching after TTS synthesis** (`audio_utils.py`):
   - Replace the no-op `_fit_segment_to_window()` with a bounded time-stretch
   - Use `_time_stretch_to_duration()` (already implemented at `audio_utils.py:89`) when the TTS output exceeds the dialogue window
   - Define acceptable stretch bounds (e.g., 0.75x to 1.4x) - beyond those limits, allow overflow with a logged warning
   - Add a new function `_fit_to_dialogue_window()` that:
     a. Measures the ratio of `tts_duration / original_window`
     b. If within bounds, stretches to fit exactly
     c. If TTS is too long and beyond max speedup, stretches to max and lets the remainder overflow
     d. If TTS is too short, optionally pads with silence or leaves as-is

2. **Wire duration targets into `_synthesise_batch()`** (`generation.py:253-311`):
   - Each `_worker()` call already has the `entry` with `start`/`end` timestamps
   - After `generate_audio()`, call `_fit_to_dialogue_window(audio, entry.duration)`
   - This requires moving time-stretch into the per-sentence worker so it runs in parallel

3. **Configurable stretch tolerance** (`common.py`):
   - Add constants: `_MAX_SPEEDUP_RATIO = 1.35`, `_MAX_SLOWDOWN_RATIO = 0.75`
   - Expose as CLI/API parameters for fine-tuning per-language

**Expected impact:** Dubbed audio segments stay close to their original windows, drastically reducing cumulative drift.

---

### Phase 2: Source-Anchored Timeline Scheduling

**Goal:** Build the dubbed timeline from original timestamps, not from TTS output length.

**Files to modify:**
- `generation.py` - Rework scheduling loop (lines 502-556)

**Implementation:**

1. **Dual-mode scheduling** - Add a `timeline_mode` parameter:
   - `"audio-driven"` (current behavior): cursor advances by TTS audio length
   - `"source-anchored"` (new): cursor anchors to original `start`/`end` timestamps, with stretch/compression to fit

2. **Source-anchored scheduling logic:**
   ```
   for each (entry, audio) in synthesized:
       target_start = entry.original_start - block_source_start  # relative to block
       target_duration = entry.original_end - entry.original_start
       fitted_audio = _fit_to_dialogue_window(audio, target_duration)
       scheduled_start = block_start + target_start
       scheduled_end = scheduled_start + len(fitted_audio) / 1000.0
   ```
   This keeps dubbed segments temporally aligned with the source video frames they correspond to.

3. **Handle overflow gracefully:**
   - When fitted audio still exceeds the window (beyond max stretch), allow it to bleed into the subsequent gap
   - Reduce the next gap duration by the overflow amount
   - If no gap is available, log a warning and accept the drift for that segment

**Expected impact:** Lip sync with the original video improves significantly. Visual cues (gestures, scene cuts) stay aligned with corresponding audio.

---

### Phase 3: Language-Adaptive Pace Model

**Goal:** Replace the flat 2.8 wps heuristic with a language-aware pace model.

**Files to modify:**
- `dialogues.py` - Enhance `_compute_pace_factor()`
- New file: `modules/services/youtube_dubbing/pace.py`

**Implementation:**

1. **Language-specific target speech rates** (`pace.py`):
   ```python
   _LANGUAGE_SPEECH_RATES = {
       "en": 2.8,   # words per second
       "es": 3.2,   # Spanish tends to use more words
       "ja": 5.0,   # Japanese: characters per second (different metric)
       "de": 2.5,   # German: longer compound words
       "zh": 4.5,   # Chinese: characters per second
       "ar": 2.6,   # Arabic
       "ko": 3.5,   # Korean: syllables per second
       # ...
   }
   ```

2. **Per-sentence pace estimation:**
   - Instead of batch-level pace, compute per-dialogue: `sentence_pace = word_count / window_duration`
   - Compare against language target to determine reading speed adjustment
   - Adjust TTS speed parameter per-sentence, not per-batch

3. **Syllable-aware counting for CJK languages:**
   - Current `_count_words()` (`dialogues.py:128-131`) uses whitespace splitting - wrong for CJK
   - Add character-count or mora-count mode for languages that don't use spaces
   - Use `modules/align/backends/whisperx_adapter.py`'s existing language classification to pick the right metric

**Expected impact:** More natural-sounding dubbed audio across all target languages. Fewer extreme stretch/compress operations needed.

---

### Phase 4: Post-Synthesis Alignment Verification

**Goal:** Detect and correct timeline drift before muxing.

**Files to modify:**
- `generation.py` - Add verification step after scheduling
- `audio_utils.py` - Add drift correction utility

**Implementation:**

1. **Per-sentence drift tracking:**
   - After scheduling, compute `drift_ms = (scheduled_end - scheduled_start) - (orig_end - orig_start)` for each sentence
   - Track cumulative drift across the batch
   - Log drift statistics per batch

2. **Cumulative drift correction:**
   - If cumulative drift exceeds a threshold (e.g., 500ms), insert a correction point:
     a. Find the next gap >= 200ms
     b. Adjust gap duration to absorb the drift
     c. Reset cumulative drift counter

3. **Drift report in progress tracker:**
   - Add drift metrics to the SSE progress events so the UI can display alignment quality
   - Include per-batch and cumulative drift values

**Expected impact:** Self-correcting pipeline that doesn't accumulate drift over long videos. Visible quality metrics for users.

---

### Phase 5: Audio Crossfade at Segment Boundaries

**Goal:** Eliminate hard audio cuts between dubbed segments and gap regions.

**Files to modify:**
- `audio_utils.py` - Add crossfade utility
- `generation.py` - Apply crossfades during scheduling

**Implementation:**

1. **Short crossfade function** (`audio_utils.py`):
   ```python
   def _crossfade_segments(seg_a: AudioSegment, seg_b: AudioSegment, overlap_ms: int = 30) -> AudioSegment:
       # Apply a short fade-out on seg_a's tail and fade-in on seg_b's head
       # Overlap them by overlap_ms
   ```

2. **Apply at gap boundaries** (`generation.py`):
   - When inserting a gap clip between two dubbed segments, crossfade the transition
   - Crossfade duration: 20-50ms (imperceptible but eliminates clicks/pops)

3. **Apply within stitching** (`stitching.py`):
   - When concatenating batches, apply audio crossfade at batch boundaries
   - This eliminates the audible "seam" between batch outputs

**Expected impact:** Smoother audio transitions, especially noticeable with headphones.

---

### Phase 6: Smarter Video Segment Stretching

**Goal:** When dubbed audio is longer than the source window, stretch the video segment instead of just padding with a frozen frame.

**Files to modify:**
- `video_utils.py` - Add video tempo adjustment
- `generation.py` - Use video stretch instead of pad

**Implementation:**

1. **Replace `_pad_clip_to_duration()` with `_stretch_clip_to_duration()`:**
   - Instead of `tpad=stop_mode=clone` (which freezes the last frame), use `setpts` to slow down the video
   - Within reasonable bounds (0.8x to 1.25x speed), this looks natural
   - Beyond bounds, fall back to the current pad behavior

2. **Selective application:**
   - Only stretch video when the ratio is within the natural-looking range
   - For large mismatches, keep current pad+trim behavior
   - Add a config option: `video_stretch_enabled: bool = True`

3. **Scene-cut awareness** (advanced):
   - Before stretching, detect if the source window contains a scene cut (significant frame difference)
   - If yes, avoid stretching across the cut - split at the cut point and handle each part separately

**Expected impact:** More natural-looking video during dubbed segments. Eliminates frozen frames that are jarring to viewers.

---

### Phase 7: Translation Length Feedback Loop

**Goal:** Adapt TTS parameters based on how much longer/shorter the translation is compared to the original.

**Files to modify:**
- `translation.py` - Add length comparison
- `generation.py` - Feed length ratio into TTS

**Implementation:**

1. **Compute translation expansion ratio:**
   ```python
   expansion_ratio = len(translated_text.split()) / max(1, len(original_text.split()))
   ```
   - Typical ratios: EN->ES ~1.2, EN->DE ~1.3, EN->JA ~0.7 (character-based)

2. **Adjust TTS speed parameter based on expansion:**
   - If translation is 30% longer than original, increase TTS speed by ~15%
   - This pre-compensates for the expansion before time-stretching kicks in
   - Reduces the stretch ratio needed, preserving audio quality

3. **LLM-guided concise translation mode:**
   - When expansion ratio exceeds 1.4x, retry translation with a system prompt requesting concise output
   - "Translate the following dialogue for dubbing. The translation must fit within N seconds of speech."
   - This is more natural than aggressive time-stretching

**Expected impact:** Translations that naturally fit their windows better, requiring less post-synthesis manipulation.

---

### Phase 8: Improved Active Window Detection

**Goal:** More precise speech boundary detection for better subtitle timing.

**Files to modify:**
- `audio_utils.py` - Enhance `_measure_active_window()`

**Implementation:**

1. **Finer step resolution:**
   - Current: 20ms steps (`audio_utils.py:47`)
   - Change to 10ms or 5ms for more precise boundary detection
   - Use a sliding window energy computation instead of per-frame dBFS

2. **Adaptive threshold:**
   - Current threshold: `max(silence_floor, audio.dBFS - 18.0)`
   - Use a percentile-based approach: voiced threshold = P25 of frame energies
   - This adapts better to recordings with varying noise floors

3. **Multi-pass detection:**
   - First pass: coarse detection (20ms) to find approximate boundaries
   - Second pass: fine detection (5ms) around the boundaries
   - This is fast (only scans small regions at high resolution)

4. **Onset detection using zero-crossing rate:**
   - Supplement dBFS with zero-crossing rate for better speech onset detection
   - Speech typically has lower ZCR than noise/silence

**Expected impact:** More accurate subtitle start/end times, tighter audio-to-subtitle sync.

---

### Phase 9: FFmpeg Process Pool

**Goal:** Reduce per-call overhead for the many FFmpeg invocations during dubbing.

**Files to modify:**
- New file: `modules/services/youtube_dubbing/ffmpeg_pool.py`
- `video_utils.py` - Use pool instead of direct `subprocess.run()`

**Implementation:**

1. **FFmpeg command batching:**
   - Group independent FFmpeg operations (sentence trims, audio conversions) into a single `ffmpeg` invocation with multiple outputs where possible
   - Use `-filter_complex` with split/overlay for parallel audio processing

2. **Subprocess pool:**
   - Pre-spawn a pool of FFmpeg processes with persistent pipes
   - Reuse processes across invocations to avoid startup overhead
   - Especially beneficial for the many small sentence-level trim operations

3. **Hardware acceleration detection:**
   - Probe for available hardware encoders on startup (NVENC, VideoToolbox, VAAPI)
   - Prefer hardware encoding when available, with fallback to `libx264`
   - Add config option: `ffmpeg_hwaccel: Optional[str] = None`

**Expected impact:** Significant speedup for long videos with many dialogue segments. Lower CPU usage.

---

### Phase 10: Codebase Quality Improvements

These are general improvements not specific to timeline alignment but will improve maintainability and reliability.

#### 10a. Extract FFmpeg binary resolution

Every function independently resolves the FFmpeg path:
```python
ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
```

This appears 15+ times across `video_utils.py` and `audio_utils.py`. Extract to a shared utility:
```python
# common.py
@functools.lru_cache(maxsize=1)
def _resolve_ffmpeg_bin() -> str:
    return os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"

@functools.lru_cache(maxsize=1)
def _resolve_ffprobe_bin() -> str:
    return _resolve_ffmpeg_bin().replace("ffmpeg", "ffprobe")
```

#### 10b. Reduce `generate_dubbed_video()` complexity

The main function is ~900 lines with deeply nested closures. Refactor into:
- `_schedule_dubbed_timeline()` - Timeline computation
- `_synthesize_and_stretch()` - TTS + alignment
- `_encode_scheduled_batch()` - Video encoding
- `_finalize_single_output()` - Single-output mode mux

#### 10c. Add structured timeline dataclass

Replace the ad-hoc tuple-based scheduling (`List[Tuple[_AssDialogue, AudioSegment, float, float]]`) with a proper dataclass:
```python
@dataclass
class ScheduledSegment:
    dialogue: _AssDialogue          # Scheduled dialogue with adjusted timestamps
    audio: AudioSegment             # Synthesized audio
    original_start: float           # Source video timestamp
    original_end: float             # Source video timestamp
    drift_ms: float = 0.0           # Accumulated drift at this point
    stretch_ratio: float = 1.0      # Applied stretch factor
```

#### 10d. Integration test for timeline accuracy

Add a test that:
1. Creates a known-duration video with timed subtitle cues
2. Runs the dubbing pipeline
3. Verifies that each dubbed segment starts within Xms of its original timestamp
4. Measures cumulative drift at the end

---

## Suggested Implementation Order

| Priority | Phase | Effort | Impact |
|----------|-------|--------|--------|
| 1 | Phase 1: Per-Sentence Duration-Aware TTS | Medium | High |
| 2 | Phase 2: Source-Anchored Timeline | Medium | High |
| 3 | Phase 7: Translation Length Feedback | Low | Medium |
| 4 | Phase 10a-c: Code quality | Low | Medium (maintainability) |
| 5 | Phase 4: Drift Verification | Low | Medium |
| 6 | Phase 3: Language-Adaptive Pace | Medium | Medium |
| 7 | Phase 5: Audio Crossfade | Low | Low-Medium |
| 8 | Phase 8: Active Window Detection | Low | Low-Medium |
| 9 | Phase 6: Video Stretching | Medium | Medium |
| 10 | Phase 9: FFmpeg Pool | High | Medium (perf) |
| 11 | Phase 10d: Timeline accuracy test | Medium | High (reliability) |

Phases 1 and 2 together will deliver the biggest improvement in audio-video alignment. Phase 7 is low-effort and synergizes well with the first two. The code quality items (10a-c) should be done alongside any phase to keep the codebase manageable.

---

## Quick Wins (Can Be Done Independently)

1. **Revive `_fit_segment_to_window()`** - The infrastructure for time-stretching already exists (`_time_stretch_to_duration()`, `_build_atempo_filters()`). Just wire it into the synthesis worker.

2. **Per-sentence pace factor** - Change `_compute_pace_factor()` to operate per-sentence instead of per-batch. Minimal code change, meaningful improvement.

3. **FFmpeg path deduplication** - Pure refactor, no behavior change, reduces 15+ duplicate lines.

4. **Drift logging** - Add cumulative drift tracking to the scheduling loop. Zero risk, provides immediate visibility into alignment quality.

5. **Configurable stretch bounds** - Expose `_MAX_SPEEDUP_RATIO` and `_MAX_SLOWDOWN_RATIO` as config parameters so users can tune per their use case.
