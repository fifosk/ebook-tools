import { describe, expect, it } from 'vitest';
import {
  buildSequencePlan,
  findSegmentForSentence,
  findSegmentForTime,
  shouldAdvanceSegment,
  resolveTokenSeekTarget,
  type SequenceSegment,
} from '../sequencePlan';
import type { ChunkSentenceMetadata } from '../../../api/dtos';

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

/**
 * Build a realistic 4-sentence sequence plan with alternating tracks.
 * Represents: original₀, translation₀, original₁, translation₁, ...
 */
function buildFourSentencePlan(): SequenceSegment[] {
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
    makeSentence({
      originalStartGate: 3.0,
      originalEndGate: 4.5,
      startGate: 4.0,
      endGate: 6.0,
    }),
    makeSentence({
      originalStartGate: 4.5,
      originalEndGate: 6.0,
      startGate: 6.0,
      endGate: 8.0,
    }),
  ];
  return buildSequencePlan(sentences, null, { sentenceCount: 4 });
}

// ─── Same-chunk sentence jump scenarios ──────────────────────────────

describe('Same-chunk sentence jump', () => {
  const plan = buildFourSentencePlan();

  it('plan has 8 segments (2 per sentence)', () => {
    expect(plan).toHaveLength(8);
  });

  it('jump from sentence 0 to sentence 2 (same track)', () => {
    // Currently on sentence 0 original (index 0)
    // Want to jump to sentence 2 original
    const targetIndex = findSegmentForSentence(plan, 2, 'original');
    expect(targetIndex).toBeGreaterThan(0);
    expect(plan[targetIndex].sentenceIndex).toBe(2);
    expect(plan[targetIndex].track).toBe('original');
  });

  it('jump from sentence 0 to sentence 3 (same track)', () => {
    const targetIndex = findSegmentForSentence(plan, 3, 'original');
    expect(targetIndex).toBeGreaterThan(0);
    expect(plan[targetIndex].sentenceIndex).toBe(3);
    expect(plan[targetIndex].track).toBe('original');
  });

  it('jump from sentence 0 original to sentence 2 translation (cross-track)', () => {
    const targetIndex = findSegmentForSentence(plan, 2, 'translation');
    expect(targetIndex).toBeGreaterThan(0);
    expect(plan[targetIndex].sentenceIndex).toBe(2);
    expect(plan[targetIndex].track).toBe('translation');
  });

  it('jump backward from sentence 3 to sentence 0', () => {
    const targetIndex = findSegmentForSentence(plan, 0, 'original');
    expect(targetIndex).toBe(0);
    expect(plan[targetIndex].sentenceIndex).toBe(0);
  });
});

// ─── Token seek (tap word) scenarios in sequence mode ────────────────

describe('Token seek in sequence mode', () => {
  const plan = buildFourSentencePlan();

  it('tap original word while playing original track (no switch)', () => {
    const target = resolveTokenSeekTarget(plan, 1, 'original', 2.0, 'original');
    expect(target).not.toBeNull();
    expect(target!.track).toBe('original');
    expect(target!.requiresTrackSwitch).toBe(false);
    expect(target!.seekTime).toBe(2.0);
  });

  it('tap translation word while playing translation track (no switch)', () => {
    const target = resolveTokenSeekTarget(plan, 1, 'translation', 3.0, 'translation');
    expect(target).not.toBeNull();
    expect(target!.track).toBe('translation');
    expect(target!.requiresTrackSwitch).toBe(false);
  });

  it('tap original word while playing translation track (cross-track switch)', () => {
    const target = resolveTokenSeekTarget(plan, 1, 'original', 2.0, 'translation');
    expect(target).not.toBeNull();
    expect(target!.track).toBe('original');
    expect(target!.requiresTrackSwitch).toBe(true);
  });

  it('tap translation word while playing original track (cross-track switch)', () => {
    const target = resolveTokenSeekTarget(plan, 2, 'translation', 5.0, 'original');
    expect(target).not.toBeNull();
    expect(target!.track).toBe('translation');
    expect(target!.requiresTrackSwitch).toBe(true);
  });

  it('tap transliteration word maps to translation track', () => {
    const target = resolveTokenSeekTarget(plan, 0, 'translit', 0.5, 'original');
    expect(target).not.toBeNull();
    expect(target!.track).toBe('translation');
    // Requires switch because current track is 'original'
    expect(target!.requiresTrackSwitch).toBe(true);
  });

  it('tap transliteration while on translation track (no switch)', () => {
    const target = resolveTokenSeekTarget(plan, 0, 'translit', 0.5, 'translation');
    expect(target).not.toBeNull();
    expect(target!.track).toBe('translation');
    expect(target!.requiresTrackSwitch).toBe(false);
  });
});

// ─── Segment advance boundary detection ──────────────────────────────

describe('Segment advance at boundaries', () => {
  const plan = buildFourSentencePlan();

  it('does not advance before segment end', () => {
    // First segment: original, start=0.0, end=1.5
    expect(shouldAdvanceSegment(plan, 0, 1.0)).toBe(false);
  });

  it('advances at exact segment end', () => {
    expect(shouldAdvanceSegment(plan, 0, 1.5)).toBe(true);
  });

  it('advances past segment end', () => {
    expect(shouldAdvanceSegment(plan, 0, 1.8)).toBe(true);
  });

  it('advances within default tolerance (0.03)', () => {
    // 1.5 - 0.03 = 1.47
    expect(shouldAdvanceSegment(plan, 0, 1.48)).toBe(true);
  });

  it('does not advance outside default tolerance', () => {
    // 1.5 - 0.03 = 1.47
    expect(shouldAdvanceSegment(plan, 0, 1.46)).toBe(false);
  });

  it('handles last segment in plan', () => {
    const lastIndex = plan.length - 1;
    const lastSegment = plan[lastIndex];
    expect(shouldAdvanceSegment(plan, lastIndex, lastSegment.end)).toBe(true);
  });
});

// ─── Plan building with only phaseDurations (no gate data) ───────────

describe('Plan from phaseDurations only', () => {
  it('builds valid plan from phaseDurations alone', () => {
    const sentences = [
      makeSentence({ phaseDurations: { original: 1.0, translation: 1.5 } }),
      makeSentence({ phaseDurations: { original: 0.8, translation: 1.2 } }),
      makeSentence({ phaseDurations: { original: 1.2, translation: 1.8 } }),
    ];
    const plan = buildSequencePlan(sentences, null, { sentenceCount: 3 });
    expect(plan.length).toBeGreaterThanOrEqual(6); // 2 per sentence

    // Verify original segments have cumulative timing
    const origSegments = plan.filter((s) => s.track === 'original');
    expect(origSegments).toHaveLength(3);
    expect(origSegments[0].start).toBe(0);
    expect(origSegments[0].end).toBeCloseTo(1.0);
    expect(origSegments[1].start).toBeCloseTo(1.0);
    expect(origSegments[1].end).toBeCloseTo(1.8);
    expect(origSegments[2].start).toBeCloseTo(1.8);
    expect(origSegments[2].end).toBeCloseTo(3.0);

    // Translation segments also cumulative
    const transSegments = plan.filter((s) => s.track === 'translation');
    expect(transSegments).toHaveLength(3);
    expect(transSegments[0].start).toBe(0);
    expect(transSegments[0].end).toBeCloseTo(1.5);
  });

  it('handles mixed: gate-based first sentence, phaseDurations-only second', () => {
    // When some sentences have gates, phaseDurations fallback only triggers for tracks
    // with ZERO gate segments across all sentences. If sentence 0 has gates for both
    // tracks, phaseDurations on sentence 1 are ignored (the function treats gates as
    // authoritative when present for a track).
    const sentences = [
      makeSentence({
        originalStartGate: 0.0,
        originalEndGate: 1.5,
        startGate: 0.0,
        endGate: 2.0,
      }),
      // Second sentence has only phaseDurations — these won't produce segments
      // because hasOriginalGate and hasTranslationGate are already true from sentence 0
      makeSentence({
        phaseDurations: { original: 1.0, translation: 1.5 },
      }),
    ];
    const plan = buildSequencePlan(sentences, null, { sentenceCount: 2 });
    // Only sentence 0 produces segments (2 segments: original + translation)
    expect(plan).toHaveLength(2);
    const firstOrig = plan.find((s) => s.sentenceIndex === 0 && s.track === 'original');
    expect(firstOrig).toBeDefined();
    expect(firstOrig!.start).toBe(0.0);
    expect(firstOrig!.end).toBe(1.5);
    const firstTrans = plan.find((s) => s.sentenceIndex === 0 && s.track === 'translation');
    expect(firstTrans).toBeDefined();
    expect(firstTrans!.start).toBe(0.0);
    expect(firstTrans!.end).toBe(2.0);
  });

  it('falls back to phaseDurations when one track has no gates at all', () => {
    // Sentence 0 has only original gates (no translation gates)
    // phaseDurations fallback should fill in translation track
    const sentences = [
      makeSentence({
        originalStartGate: 0.0,
        originalEndGate: 1.5,
        phaseDurations: { original: 1.5, translation: 2.0 },
      }),
      makeSentence({
        originalStartGate: 1.5,
        originalEndGate: 3.0,
        phaseDurations: { original: 1.5, translation: 1.8 },
      }),
    ];
    const plan = buildSequencePlan(sentences, null, { sentenceCount: 2 });
    // Both sentences should have original (from gates) + translation (from phaseDurations)
    const origSegments = plan.filter((s) => s.track === 'original');
    const transSegments = plan.filter((s) => s.track === 'translation');
    expect(origSegments).toHaveLength(2);
    expect(transSegments).toHaveLength(2);
    // Translation derived from phaseDurations with cumulative cursor
    expect(transSegments[0].start).toBe(0);
    expect(transSegments[0].end).toBeCloseTo(2.0);
    expect(transSegments[1].start).toBeCloseTo(2.0);
    expect(transSegments[1].end).toBeCloseTo(3.8);
  });
});

// ─── findSegmentForTime accuracy ─────────────────────────────────────

describe('findSegmentForTime accuracy', () => {
  const plan = buildFourSentencePlan();

  it('finds first original segment at time 0', () => {
    const idx = findSegmentForTime(plan, 0.0, 'original');
    expect(idx).toBeGreaterThanOrEqual(0);
    expect(plan[idx].track).toBe('original');
    expect(plan[idx].sentenceIndex).toBe(0);
  });

  it('finds correct segment for mid-range time', () => {
    // Original segments: [0,1.5], [1.5,3.0], [3.0,4.5], [4.5,6.0]
    const idx = findSegmentForTime(plan, 2.0, 'original');
    expect(idx).toBeGreaterThanOrEqual(0);
    expect(plan[idx].sentenceIndex).toBe(1);
  });

  it('finds translation segment at correct time', () => {
    // Translation segments: [0,2.0], [2.0,4.0], [4.0,6.0], [6.0,8.0]
    const idx = findSegmentForTime(plan, 5.0, 'translation');
    expect(idx).toBeGreaterThanOrEqual(0);
    expect(plan[idx].track).toBe('translation');
    expect(plan[idx].sentenceIndex).toBe(2);
  });

  it('returns last matching segment when past all segments', () => {
    const idx = findSegmentForTime(plan, 100.0, 'original');
    expect(idx).toBeGreaterThanOrEqual(0);
    const segment = plan[idx];
    expect(segment.track).toBe('original');
    // Should be the last original segment
    expect(segment.sentenceIndex).toBe(3);
  });
});
