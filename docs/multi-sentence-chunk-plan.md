# Multi-Sentence Chunk Support: Implementation Plan

> **Status (2026-02-03):** Implemented. `sentences_per_chunk` is now a live
> alias of `sentences_per_output_file` in the configuration model. This document
> is retained for historical context; see `modules/config_manager/settings.py`
> and `modules/core/config.py` for the current behavior.

## Executive Summary

This document outlines the plan to safely support **multi-sentence chunks** (e.g., 10 sentences per chunk) while maintaining word-level highlighting synchronization. The goal is to reduce file count by ~10x while ensuring no drift in token highlighting.

---

## Current State Analysis

### What Already Works

1. **Frontend fully supports multi-sentence chunks**
   - `TrackTimingPayload.words[]` stores all words with `sentenceId` (global sentence index)
   - `WordIndex.bySentence` maps sentence IDs to word IDs
   - Timing is chunk-relative (all words use offsets from chunk audio start)
   - Tests in `wordSync.test.ts` explicitly verify multi-sentence behavior

2. **Backend chunk persistence supports multi-sentence**
   - `chunk_XXXX.json` already stores arrays of sentences
   - `timingTracks` can hold tokens from multiple sentences
   - `audioTracks` holds combined audio for entire chunk

3. **Timeline building supports multi-sentence**
   - `build_separate_track_timings()` iterates over `Sequence[SentenceTimingSpec]`
   - Accumulates `translation_cursor` and `original_cursor` per-sentence
   - Tokens get correct absolute offsets within chunk audio

### Current Problem: Single-Sentence Batching

The pipeline currently generates **1 sentence per chunk** due to:
- `BatchExportRequest` receives individual sentence audio segments
- Each batch export creates one chunk file
- The `sentences_per_file` config parameter affects document output, not chunk granularity

---

## Architecture for Multi-Sentence Chunks

### Key Invariant: Timing Synchronization

**Critical requirement**: Word highlighting must remain synchronized with audio playback. This requires:

1. **Absolute chunk-relative timing**: Each word's `t0`/`t1` must be relative to the chunk audio start (not per-sentence)
2. **Cumulative offset tracking**: When combining N sentences, sentence 2's words start at `offset = sentence_1_duration`
3. **Monotonic timing validation**: `validate_timing_monotonic()` must enforce no overlaps across sentence boundaries
4. **Audio concatenation alignment**: Combined audio must match cumulative timing offsets exactly

### Proposed Data Flow

```
Pipeline Processing
│
├── Process N sentences as a batch
│   ├── Generate TTS for each sentence
│   ├── Collect per-sentence AudioSegments
│   ├── Collect per-sentence metadata (word_tokens, duration)
│   └── Build SentenceTimingSpec per sentence
│
├── Export Multi-Sentence Chunk
│   ├── Concatenate audio: audio_1 + audio_2 + ... + audio_N
│   ├── Build timing with cumulative offsets:
│   │   ├── Sentence 1: offset = 0
│   │   ├── Sentence 2: offset = duration_1
│   │   ├── Sentence 3: offset = duration_1 + duration_2
│   │   └── ...
│   ├── Validate timing monotonicity across all sentences
│   └── Write single chunk_XXXX.json
│
└── Output Structure
    ├── audioTracks.translation: single combined MP3
    ├── audioTracks.original: single combined MP3
    ├── timingTracks.translation: all words with cumulative offsets
    ├── timingTracks.original: all words with cumulative offsets
    └── sentences: array of N sentence metadata objects
```

---

## Implementation Plan

### Phase 1: Backend Core Changes

#### 1.1 Modify BatchExportRequest (modules/core/rendering/exporters.py)

Current:
```python
@dataclass
class BatchExportRequest:
    start_sentence: int
    end_sentence: int
    video_blocks: List[str]
    audio_segments: List[AudioSegment]  # One per sentence
    ...
```

Changes needed:
- Accept `sentence_metadata: List[Dict[str, Any]]` with per-sentence timing info
- Pass through word-level timing data for each sentence

#### 1.2 Enhance build_separate_track_timings (modules/core/rendering/timeline.py)

Already supports multiple sentences, but verify:
- Cumulative offset calculation is correct
- Gates (`start_gate`, `end_gate`) use cumulative offsets
- `validate_timing_monotonic()` is called per-sentence AND across chunk

**Add validation**:
```python
def validate_cross_sentence_continuity(
    track_tokens: list[dict],
    sentence_specs: Sequence[SentenceTimingSpec],
) -> dict[str, Any]:
    """Validate no gaps/overlaps at sentence boundaries."""
    issues = []
    for i in range(len(sentence_specs) - 1):
        current_end = sentence_specs[i].end_gate
        next_start = sentence_specs[i + 1].start_gate
        if abs(next_start - current_end) > 0.01:  # 10ms tolerance
            issues.append({
                "boundary": i,
                "current_end": current_end,
                "next_start": next_start,
                "gap_ms": (next_start - current_end) * 1000
            })
    return {"valid": len(issues) == 0, "issues": issues}
```

#### 1.3 Update Audio Concatenation (modules/core/rendering/exporters.py)

Current audio export already concatenates segments:
```python
for segment in segments:
    combined_track += segment
```

Add **timing metadata preservation**:
```python
def concatenate_with_timing(
    segments: List[AudioSegment],
    sentence_specs: List[SentenceTimingSpec],
) -> Tuple[AudioSegment, List[float]]:
    """Concatenate audio and return cumulative offsets."""
    combined = AudioSegment.empty()
    offsets = [0.0]
    for segment in segments:
        combined += segment
        offsets.append(offsets[-1] + segment.duration_seconds)
    return combined, offsets[:-1]  # Don't include final offset
```

#### 1.4 Add Chunk Grouping Configuration

New config parameter:
```json
{
  "sentences_per_chunk": 10,  // Number of sentences per chunk file
  "chunk_audio_format": "mp3",
  "chunk_audio_bitrate": "64k"
}
```

#### 1.5 Modify Pipeline Processing Loop

In `modules/core/rendering/pipeline_processing.py`:
```python
def process_sentence_batch(
    sentences: List[str],
    batch_start: int,
    chunk_size: int,
) -> Iterator[ChunkExportRequest]:
    """Yield chunk requests with `chunk_size` sentences each."""
    for i in range(0, len(sentences), chunk_size):
        chunk_sentences = sentences[i:i + chunk_size]
        yield ChunkExportRequest(
            start_sentence=batch_start + i,
            end_sentence=batch_start + i + len(chunk_sentences) - 1,
            sentences=chunk_sentences,
            ...
        )
```

---

### Phase 2: Timing Track Generation Changes

#### 2.1 Generate Per-Sentence Word Tokens First

Before combining, each sentence needs complete timing:
```python
per_sentence_tokens = []
for spec in sentence_specs:
    tokens = generate_word_tokens(spec)  # Per-sentence timing
    per_sentence_tokens.append(tokens)
```

#### 2.2 Apply Cumulative Offsets

```python
def apply_chunk_offsets(
    per_sentence_tokens: List[List[Dict]],
    sentence_durations: List[float],
) -> List[Dict]:
    """Shift per-sentence tokens to chunk-relative timing."""
    all_tokens = []
    offset = 0.0
    for i, tokens in enumerate(per_sentence_tokens):
        for token in tokens:
            shifted_token = {
                **token,
                "sentenceIdx": sentence_specs[i].sentence_idx,
                "start": token["start"] + offset,
                "end": token["end"] + offset,
            }
            all_tokens.append(shifted_token)
        offset += sentence_durations[i]
    return all_tokens
```

#### 2.3 Validate Final Timing Track

```python
def validate_chunk_timing(
    tokens: List[Dict],
    audio_duration: float,
) -> Dict[str, Any]:
    """Ensure timing covers full audio without drift."""
    if not tokens:
        return {"valid": False, "error": "no_tokens"}

    first_start = tokens[0]["start"]
    last_end = tokens[-1]["end"]

    start_drift = abs(first_start)
    end_drift = abs(last_end - audio_duration)

    return {
        "valid": start_drift < 0.01 and end_drift < 0.05,
        "start_drift_ms": start_drift * 1000,
        "end_drift_ms": end_drift * 1000,
        "token_count": len(tokens),
        "audio_duration": audio_duration,
    }
```

---

### Phase 3: Frontend Timing Payload Generation

#### 3.1 Generate TrackTimingPayload for Multi-Sentence Chunk

The backend API must return properly formatted `TrackTimingPayload`:

```python
def build_track_timing_payload(
    chunk_id: str,
    track_type: str,
    tokens: List[Dict],
    pauses: List[Dict],
    audio_duration: float,
) -> Dict[str, Any]:
    """Build frontend-compatible timing payload."""
    words = []
    for i, token in enumerate(tokens):
        words.append({
            "id": f"{chunk_id}_{track_type}_{i}",
            "sentenceId": token["sentenceIdx"],
            "tokenIdx": token.get("wordIdx", i),
            "text": token.get("text", ""),
            "lang": "trans" if track_type == "translation" else "orig",
            "t0": token["start"],
            "t1": token["end"],
        })

    return {
        "trackType": track_type_mapping[track_type],
        "chunkId": chunk_id,
        "words": words,
        "pauses": pauses,
        "trackOffset": 0,
        "tempoFactor": 1.0,
        "version": "2",
    }
```

---

### Phase 4: Video Pipeline Adaptation

#### 4.1 Video Rendering with Multi-Sentence Chunks

The video pipeline currently processes one sentence at a time. For multi-sentence chunks:

Option A: **Keep per-sentence video rendering** (recommended)
- Video rendering continues generating per-sentence segments
- Chunk metadata contains multi-sentence info
- Final video concatenates all sentence videos

Option B: **Batch video rendering**
- Generate video slides for all sentences in chunk together
- More complex but potentially more efficient

**Recommendation**: Option A - minimal changes to video pipeline

#### 4.2 Subtitle Timing Adaptation

Subtitles use word timing from chunk metadata. With multi-sentence chunks:
- Subtitle generation iterates over `sentences[]` array
- Each sentence's timing uses cumulative offsets from `timingTracks`
- No changes needed if timing is correctly offset

---

### Phase 5: Integration Tests

#### 5.1 Test: Timing Continuity Across Sentences

```python
def test_multi_sentence_timing_continuity():
    """Verify no timing gaps at sentence boundaries."""
    sentences = [
        {"text": "Hello world.", "duration": 1.5},
        {"text": "How are you?", "duration": 1.2},
        {"text": "I am fine.", "duration": 1.0},
    ]

    result = export_multi_sentence_chunk(sentences)
    timing = result.timing_tracks["translation"]

    # Check continuity
    for i in range(len(timing) - 1):
        current_end = timing[i]["end"]
        next_start = timing[i + 1]["start"]
        assert abs(next_start - current_end) < 0.001, \
            f"Gap at token {i}: {current_end} -> {next_start}"
```

#### 5.2 Test: Frontend Word Index Building

```typescript
describe('multi-sentence chunk word index', () => {
  it('builds correct sentence-to-word mapping', () => {
    const payload = createMultiSentencePayload(10);
    const index = buildWordIndex(payload);

    // Each sentence should have its words
    for (let sid = 0; sid < 10; sid++) {
      const words = index.bySentence.get(sid);
      expect(words).toBeDefined();
      expect(words!.length).toBeGreaterThan(0);
    }
  });

  it('maintains timing monotonicity across sentences', () => {
    const payload = createMultiSentencePayload(10);
    const index = buildWordIndex(payload);

    let lastEnd = 0;
    for (const word of index.words) {
      expect(word.t0).toBeGreaterThanOrEqual(lastEnd - 0.001);
      lastEnd = word.t1;
    }
  });
});
```

#### 5.3 Test: Audio-Timing Alignment

```python
def test_audio_timing_alignment():
    """Verify timing track matches audio duration."""
    chunk = export_multi_sentence_chunk(sentences)

    audio_path = chunk.audio_tracks["translation"]["path"]
    audio = AudioSegment.from_mp3(audio_path)
    audio_duration = audio.duration_seconds

    timing = chunk.timing_tracks["translation"]
    last_token_end = timing[-1]["end"]

    drift_ms = abs(audio_duration - last_token_end) * 1000
    assert drift_ms < 50, f"Audio-timing drift: {drift_ms}ms"
```

#### 5.4 Test: End-to-End Highlighting Sync

```python
def test_highlighting_sync_e2e():
    """Simulate playback and verify highlighting accuracy."""
    chunk = load_test_chunk()
    audio = load_chunk_audio(chunk)
    timing = chunk.timing_tracks["translation"]

    # Sample at multiple points
    sample_times = [0.5, 1.5, 2.5, 3.5, 4.5]

    for t in sample_times:
        # Find expected highlighted word
        expected_word = None
        for token in timing:
            if token["start"] <= t < token["end"]:
                expected_word = token
                break

        # Verify word matches audio content at this time
        assert expected_word is not None, f"No word at t={t}"
        assert audio_matches_word(audio, t, expected_word["text"])
```

---

### Phase 6: Migration & Rollout

#### 6.1 Backward Compatibility

- Keep support for single-sentence chunks
- Add version field to chunk metadata: `"version": 2`
- `MetadataLoader` handles both formats transparently

#### 6.2 Configuration Migration

```json
{
  "sentences_per_chunk": 1,      // Current default (backward compatible)
  "sentences_per_chunk_v2": 10   // New multi-sentence mode
}
```

#### 6.3 Gradual Rollout

1. **Phase 6.3.1**: Deploy with `sentences_per_chunk: 1` (no change)
2. **Phase 6.3.2**: Enable `sentences_per_chunk: 5` for new jobs
3. **Phase 6.3.3**: Increase to `sentences_per_chunk: 10`
4. **Phase 6.3.4**: Optional migration script for existing jobs

---

## Risk Analysis

### High Risk Areas

1. **Timing Drift Accumulation**
   - Risk: Small errors per sentence compound over 10 sentences
   - Mitigation: Validate end-of-chunk timing against audio duration

2. **Audio Concatenation Quality**
   - Risk: Audible clicks/pops at sentence boundaries
   - Mitigation: Use crossfade or ensure clean boundaries

3. **Video Pipeline Regression**
   - Risk: Video rendering assumes single-sentence chunks
   - Mitigation: Keep video rendering per-sentence, only change metadata grouping

4. **Memory Usage**
   - Risk: Larger chunks mean more data in memory
   - Mitigation: Stream processing, don't load all at once

### Medium Risk Areas

1. **Frontend Performance**
   - Risk: Larger timing payloads slow down UI
   - Mitigation: Binary search already O(log n), indexes are Map-based O(1)

2. **Error Recovery**
   - Risk: If chunk export fails, lose more work
   - Mitigation: Transaction-like export with rollback

---

## File Changes Summary

### Backend Files to Modify

| File | Changes |
|------|---------|
| `modules/core/rendering/exporters.py` | Add multi-sentence batching, cumulative timing |
| `modules/core/rendering/timeline.py` | Add cross-sentence validation |
| `modules/core/rendering/pipeline_processing.py` | Chunk grouping logic |
| `modules/services/job_manager/chunk_persistence.py` | Version 2 chunk format |
| `conf/config.json` | New `sentences_per_chunk` parameter |

### New Files

| File | Purpose |
|------|---------|
| `tests/modules/core/test_multi_sentence_chunks.py` | Integration tests |
| `web/src/lib/timing/__tests__/multiSentenceWordSync.test.ts` | Frontend timing tests |

### Files Unchanged (Already Support Multi-Sentence)

- `web/src/lib/timing/wordSync.ts` - ✅ Already handles multi-sentence
- `web/src/api/dtos.ts` - ✅ Types support arrays
- `modules/metadata_manager.py` - ✅ Iterates sentences array

---

## Success Criteria

1. **File Count Reduction**: 10x fewer chunk files for same content
2. **Zero Timing Drift**: Word highlighting stays synchronized (< 50ms drift at chunk end)
3. **Backward Compatible**: Existing single-sentence chunks continue working
4. **Test Coverage**: New integration tests pass for 10-sentence chunks
5. **Performance**: No degradation in frontend playback smoothness

---

## Open Questions

1. Should we implement chunk-level audio caching for faster random access?
2. Do iOS apps need any changes for multi-sentence chunk support?
3. Should we support variable chunk sizes (e.g., split at paragraph boundaries)?

---

## Next Steps

1. Review and approve this plan
2. Implement Phase 1 (backend core changes) with tests
3. Implement Phase 2 (timing track generation)
4. Add integration tests (Phase 5)
5. Test with existing frontend (should work without changes)
6. Roll out gradually with monitoring
