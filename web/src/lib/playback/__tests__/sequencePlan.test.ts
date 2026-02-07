import { describe, expect, it } from 'vitest';
import {
  buildSequencePlan,
  findSegmentForSentence,
  findSegmentForTime,
  shouldAdvanceSegment,
  resolveTokenSeekTarget,
  type SequenceSegment,
  type SequenceTrack,
} from '../sequencePlan';
import type { ChunkSentenceMetadata, AudioTrackMetadata } from '../../../api/dtos';

// ─── Helpers ──────────────────────────────────────────────────────────

function makeSentence(
  overrides: Partial<ChunkSentenceMetadata> = {},
): ChunkSentenceMetadata {
  return {
    original: { text: 'Hello', tokens: ['Hello'] },
    timeline: [],
    ...overrides,
  };
}

function makeAudioTracks(
  orig?: Partial<AudioTrackMetadata>,
  trans?: Partial<AudioTrackMetadata>,
): Record<string, AudioTrackMetadata> {
  const tracks: Record<string, AudioTrackMetadata> = {};
  if (orig) {
    tracks.orig = { url: 'http://example.com/orig.mp3', ...orig } as AudioTrackMetadata;
  }
  if (trans) {
    tracks.translation = { url: 'http://example.com/trans.mp3', ...trans } as AudioTrackMetadata;
  }
  return tracks;
}

// ─── buildSequencePlan ────────────────────────────────────────────────

describe('buildSequencePlan', () => {
  it('returns empty plan for null sentences and non-single-sentence chunk', () => {
    const plan = buildSequencePlan(null, null, { sentenceCount: 5 });
    expect(plan).toHaveLength(0);
  });

  it('returns empty plan for empty sentences and non-single-sentence chunk', () => {
    const plan = buildSequencePlan([], null, { sentenceCount: 5 });
    expect(plan).toHaveLength(0);
  });

  it('builds fallback plan for single-sentence chunk with no sentences', () => {
    const tracks = makeAudioTracks({ duration: 2.5 }, { duration: 3.0 });
    const plan = buildSequencePlan(null, tracks, { sentenceCount: 1 });
    expect(plan).toHaveLength(2);
    expect(plan[0]).toEqual({ track: 'original', start: 0, end: 2.5, sentenceIndex: 0 });
    expect(plan[1]).toEqual({ track: 'translation', start: 0, end: 3.0, sentenceIndex: 0 });
  });

  it('builds plan from sentence gate data', () => {
    const sentences = [
      makeSentence({
        originalStartGate: 0.0,
        originalEndGate: 1.5,
        startGate: 0.0,
        endGate: 2.0,
      }),
      makeSentence({
        originalStartGate: 1.5,
        originalEndGate: 3.0,
        startGate: 2.0,
        endGate: 4.0,
      }),
    ];
    const plan = buildSequencePlan(sentences, null, { sentenceCount: 2 });
    expect(plan).toHaveLength(4);
    // Sentence 0: original then translation
    expect(plan[0]).toEqual({ track: 'original', start: 0.0, end: 1.5, sentenceIndex: 0 });
    expect(plan[1]).toEqual({ track: 'translation', start: 0.0, end: 2.0, sentenceIndex: 0 });
    // Sentence 1: original then translation
    expect(plan[2]).toEqual({ track: 'original', start: 1.5, end: 3.0, sentenceIndex: 1 });
    expect(plan[3]).toEqual({ track: 'translation', start: 2.0, end: 4.0, sentenceIndex: 1 });
  });

  it('derives gates from phaseDurations when gate data is absent', () => {
    const sentences = [
      makeSentence({
        phaseDurations: { original: 1.0, translation: 1.5 },
      }),
      makeSentence({
        phaseDurations: { original: 0.8, translation: 1.2 },
      }),
    ];
    const plan = buildSequencePlan(sentences, null, { sentenceCount: 2 });
    expect(plan).toHaveLength(4);
    // Original track: cumulative cursor
    expect(plan[0]).toEqual({ track: 'original', start: 0, end: 1.0, sentenceIndex: 0 });
    expect(plan[2]).toEqual({ track: 'original', start: 1.0, end: 1.8, sentenceIndex: 1 });
    // Translation track: separate cumulative cursor
    expect(plan[1]).toEqual({ track: 'translation', start: 0, end: 1.5, sentenceIndex: 0 });
    expect(plan[3]).toEqual({ track: 'translation', start: 1.5, end: 2.7, sentenceIndex: 1 });
  });

  it('falls back to totalDuration for translation when phaseDurations.translation is missing', () => {
    const sentences = [
      makeSentence({
        phaseDurations: { original: 1.0 },
        totalDuration: 2.0,
      }),
    ];
    const plan = buildSequencePlan(sentences, null, { sentenceCount: 1 });
    // Should derive translation from totalDuration
    const translationSegments = plan.filter((s) => s.track === 'translation');
    expect(translationSegments.length).toBeGreaterThan(0);
    expect(translationSegments[0].end - translationSegments[0].start).toBeCloseTo(2.0);
  });

  it('handles single-sentence chunk with only original gates', () => {
    const sentences = [
      makeSentence({
        originalStartGate: 0.0,
        originalEndGate: 1.5,
      }),
    ];
    const tracks = makeAudioTracks(undefined, { duration: 2.0 });
    const plan = buildSequencePlan(sentences, tracks, { sentenceCount: 1 });
    // Should have original from gate + translation from fallback
    expect(plan.some((s) => s.track === 'original')).toBe(true);
    expect(plan.some((s) => s.track === 'translation')).toBe(true);
  });

  it('detects single-sentence via startSentence === endSentence', () => {
    const tracks = makeAudioTracks({ duration: 1.0 }, { duration: 1.5 });
    const plan = buildSequencePlan(null, tracks, {
      startSentence: 5,
      endSentence: 5,
    });
    expect(plan).toHaveLength(2);
  });

  it('rejects gates with zero duration', () => {
    const sentences = [
      makeSentence({
        originalStartGate: 1.0,
        originalEndGate: 1.0, // zero duration
        startGate: 0.0,
        endGate: 2.0,
      }),
    ];
    const plan = buildSequencePlan(sentences, null, { sentenceCount: 2 });
    // Original gate should be rejected (zero duration), translation accepted
    const origSegments = plan.filter((s) => s.track === 'original');
    const transSegments = plan.filter((s) => s.track === 'translation');
    expect(origSegments).toHaveLength(0);
    expect(transSegments).toHaveLength(1);
  });
});

// ─── findSegmentForSentence ───────────────────────────────────────────

describe('findSegmentForSentence', () => {
  const plan: SequenceSegment[] = [
    { track: 'original', start: 0, end: 1, sentenceIndex: 0 },
    { track: 'translation', start: 0, end: 1.5, sentenceIndex: 0 },
    { track: 'original', start: 1, end: 2, sentenceIndex: 1 },
    { track: 'translation', start: 1.5, end: 3, sentenceIndex: 1 },
  ];

  it('returns -1 for empty plan', () => {
    expect(findSegmentForSentence([], 0)).toBe(-1);
  });

  it('returns -1 for negative sentence index', () => {
    expect(findSegmentForSentence(plan, -1)).toBe(-1);
  });

  it('finds first segment for sentence when no track preference', () => {
    expect(findSegmentForSentence(plan, 0)).toBe(0); // original first
    expect(findSegmentForSentence(plan, 1)).toBe(2); // original first
  });

  it('respects preferred track', () => {
    expect(findSegmentForSentence(plan, 0, 'translation')).toBe(1);
    expect(findSegmentForSentence(plan, 1, 'translation')).toBe(3);
  });

  it('falls back to any track if preferred not found', () => {
    // Sentence 0 only has original and translation; if we asked for a track that
    // doesn't exist it would fall back to the first matching sentence
    const sparseplan: SequenceSegment[] = [
      { track: 'original', start: 0, end: 1, sentenceIndex: 0 },
    ];
    // Prefer translation but only original exists
    expect(findSegmentForSentence(sparseplan, 0, 'translation')).toBe(0);
  });

  it('returns -1 for non-existent sentence', () => {
    expect(findSegmentForSentence(plan, 99)).toBe(-1);
  });
});

// ─── findSegmentForTime ───────────────────────────────────────────────

describe('findSegmentForTime', () => {
  const plan: SequenceSegment[] = [
    { track: 'original', start: 0, end: 1.5, sentenceIndex: 0 },
    { track: 'translation', start: 0, end: 2.0, sentenceIndex: 0 },
    { track: 'original', start: 1.5, end: 3.0, sentenceIndex: 1 },
    { track: 'translation', start: 2.0, end: 4.0, sentenceIndex: 1 },
  ];

  it('returns -1 for empty plan', () => {
    expect(findSegmentForTime([], 0.5, 'original')).toBe(-1);
  });

  it('finds segment at start', () => {
    expect(findSegmentForTime(plan, 0.0, 'original')).toBe(0);
  });

  it('finds segment at midpoint', () => {
    expect(findSegmentForTime(plan, 0.75, 'original')).toBe(0);
  });

  it('finds segment near end within tolerance', () => {
    // 1.5 is the end of segment 0, within tolerance (0.05)
    expect(findSegmentForTime(plan, 1.52, 'original')).toBe(0);
  });

  it('finds correct track', () => {
    expect(findSegmentForTime(plan, 0.5, 'translation')).toBe(1);
    expect(findSegmentForTime(plan, 3.0, 'translation')).toBe(3);
  });

  it('falls back to upcoming segment in gap', () => {
    // Time between segments (past original[0].end but before original[1].start)
    // With default tolerance this is within range, but test explicit gap
    const gappedPlan: SequenceSegment[] = [
      { track: 'original', start: 0, end: 1.0, sentenceIndex: 0 },
      { track: 'original', start: 2.0, end: 3.0, sentenceIndex: 1 },
    ];
    expect(findSegmentForTime(gappedPlan, 1.5, 'original')).toBe(1);
  });

  it('falls back to last segment when past all segments', () => {
    expect(findSegmentForTime(plan, 99.0, 'original')).toBe(2);
  });

  it('returns -1 for NaN time', () => {
    expect(findSegmentForTime(plan, NaN, 'original')).toBe(-1);
  });
});

// ─── shouldAdvanceSegment ─────────────────────────────────────────────

describe('shouldAdvanceSegment', () => {
  const plan: SequenceSegment[] = [
    { track: 'original', start: 0, end: 1.5, sentenceIndex: 0 },
    { track: 'translation', start: 0, end: 2.0, sentenceIndex: 0 },
  ];

  it('returns false for invalid index', () => {
    expect(shouldAdvanceSegment(plan, -1, 1.0)).toBe(false);
    expect(shouldAdvanceSegment(plan, 99, 1.0)).toBe(false);
  });

  it('returns false when time is before segment end', () => {
    expect(shouldAdvanceSegment(plan, 0, 1.0)).toBe(false);
  });

  it('returns true when time reaches segment end', () => {
    expect(shouldAdvanceSegment(plan, 0, 1.5)).toBe(true);
  });

  it('returns true when time is past segment end', () => {
    expect(shouldAdvanceSegment(plan, 0, 2.0)).toBe(true);
  });

  it('returns true within tolerance of segment end', () => {
    // 1.5 - 0.03 = 1.47
    expect(shouldAdvanceSegment(plan, 0, 1.48)).toBe(true);
  });

  it('returns false just outside tolerance', () => {
    // 1.5 - 0.03 = 1.47, so 1.46 should be false
    expect(shouldAdvanceSegment(plan, 0, 1.46)).toBe(false);
  });

  it('respects custom tolerance', () => {
    expect(shouldAdvanceSegment(plan, 0, 1.4, 0.2)).toBe(true); // 1.5 - 0.2 = 1.3
    expect(shouldAdvanceSegment(plan, 0, 1.4, 0.05)).toBe(false); // 1.5 - 0.05 = 1.45
  });
});

// ─── resolveTokenSeekTarget ───────────────────────────────────────────

describe('resolveTokenSeekTarget', () => {
  const plan: SequenceSegment[] = [
    { track: 'original', start: 0, end: 1.5, sentenceIndex: 0 },
    { track: 'translation', start: 0, end: 2.0, sentenceIndex: 0 },
    { track: 'original', start: 1.5, end: 3.0, sentenceIndex: 1 },
    { track: 'translation', start: 2.0, end: 4.0, sentenceIndex: 1 },
  ];

  it('returns null for empty plan', () => {
    expect(resolveTokenSeekTarget([], 0, 'original', 0.5, 'original')).toBeNull();
  });

  it('returns null for invalid sentence index', () => {
    expect(resolveTokenSeekTarget(plan, -1, 'original', 0.5, 'original')).toBeNull();
  });

  it('returns null for NaN time', () => {
    expect(resolveTokenSeekTarget(plan, 0, 'original', NaN, 'original')).toBeNull();
  });

  it('resolves original variant to original track', () => {
    const target = resolveTokenSeekTarget(plan, 0, 'original', 0.5, 'original');
    expect(target).not.toBeNull();
    expect(target!.track).toBe('original');
    expect(target!.segmentIndex).toBe(0);
    expect(target!.seekTime).toBe(0.5);
    expect(target!.requiresTrackSwitch).toBe(false);
  });

  it('resolves translation variant to translation track', () => {
    const target = resolveTokenSeekTarget(plan, 0, 'translation', 1.0, 'translation');
    expect(target).not.toBeNull();
    expect(target!.track).toBe('translation');
    expect(target!.segmentIndex).toBe(1);
    expect(target!.seekTime).toBe(1.0);
    expect(target!.requiresTrackSwitch).toBe(false);
  });

  it('maps transliteration to translation track', () => {
    const target = resolveTokenSeekTarget(plan, 0, 'translit', 1.0, 'translation');
    expect(target).not.toBeNull();
    expect(target!.track).toBe('translation');
    expect(target!.segmentIndex).toBe(1);
    expect(target!.requiresTrackSwitch).toBe(false);
  });

  it('detects track switch needed (tap original while on translation)', () => {
    const target = resolveTokenSeekTarget(plan, 0, 'original', 0.5, 'translation');
    expect(target).not.toBeNull();
    expect(target!.track).toBe('original');
    expect(target!.requiresTrackSwitch).toBe(true);
  });

  it('detects track switch needed (tap translation while on original)', () => {
    const target = resolveTokenSeekTarget(plan, 1, 'translation', 2.5, 'original');
    expect(target).not.toBeNull();
    expect(target!.track).toBe('translation');
    expect(target!.segmentIndex).toBe(3);
    expect(target!.requiresTrackSwitch).toBe(true);
  });

  it('handles null currentTrack (sequence not yet started)', () => {
    const target = resolveTokenSeekTarget(plan, 0, 'original', 0.5, null);
    expect(target).not.toBeNull();
    expect(target!.requiresTrackSwitch).toBe(true);
  });

  it('returns null for non-existent sentence', () => {
    expect(resolveTokenSeekTarget(plan, 99, 'original', 0.5, 'original')).toBeNull();
  });
});
