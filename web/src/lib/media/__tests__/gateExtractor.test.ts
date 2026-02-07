import { describe, expect, it } from 'vitest';
import {
  resolveNumericValue,
  resolveDurationValue,
  readSentenceGate,
  resolveSentenceGate,
  resolveSentenceDuration,
} from '../gateExtractor';
import type { ChunkSentenceMetadata } from '../../../api/dtos';

function makeSentence(
  overrides: Partial<ChunkSentenceMetadata> & Record<string, unknown> = {},
): ChunkSentenceMetadata {
  return {
    original: { text: 'Hello', tokens: ['Hello'] },
    timeline: [],
    ...overrides,
  } as ChunkSentenceMetadata;
}

// ─── resolveNumericValue ──────────────────────────────────────────────

describe('resolveNumericValue', () => {
  it('returns number for finite number', () => {
    expect(resolveNumericValue(42)).toBe(42);
    expect(resolveNumericValue(0)).toBe(0);
    expect(resolveNumericValue(-1.5)).toBe(-1.5);
  });

  it('returns null for NaN and Infinity', () => {
    expect(resolveNumericValue(NaN)).toBeNull();
    expect(resolveNumericValue(Infinity)).toBeNull();
    expect(resolveNumericValue(-Infinity)).toBeNull();
  });

  it('parses numeric strings', () => {
    expect(resolveNumericValue('3.14')).toBe(3.14);
    expect(resolveNumericValue('0')).toBe(0);
    expect(resolveNumericValue(' 42 ')).toBe(42);
  });

  it('returns null for non-numeric strings', () => {
    expect(resolveNumericValue('abc')).toBeNull();
    expect(resolveNumericValue('')).toBeNull();
    expect(resolveNumericValue('   ')).toBeNull();
  });

  it('returns null for non-number/string types', () => {
    expect(resolveNumericValue(null)).toBeNull();
    expect(resolveNumericValue(undefined)).toBeNull();
    expect(resolveNumericValue(true)).toBeNull();
    expect(resolveNumericValue({})).toBeNull();
  });
});

// ─── resolveDurationValue ─────────────────────────────────────────────

describe('resolveDurationValue', () => {
  it('returns positive finite numbers', () => {
    expect(resolveDurationValue(2.5)).toBe(2.5);
    expect(resolveDurationValue(0.001)).toBe(0.001);
  });

  it('rejects zero and negative', () => {
    expect(resolveDurationValue(0)).toBeNull();
    expect(resolveDurationValue(-1)).toBeNull();
  });

  it('rejects non-finite', () => {
    expect(resolveDurationValue(Infinity)).toBeNull();
    expect(resolveDurationValue(NaN)).toBeNull();
  });
});

// ─── readSentenceGate ─────────────────────────────────────────────────

describe('readSentenceGate', () => {
  it('reads a gate value by key', () => {
    const sentence = makeSentence({ startGate: 1.5 });
    expect(readSentenceGate(sentence, ['startGate'])).toBe(1.5);
  });

  it('tries keys in order', () => {
    const sentence = makeSentence({ endGate: 3.0 });
    expect(readSentenceGate(sentence, ['nonExistent', 'endGate'])).toBe(3.0);
  });

  it('returns null for missing keys', () => {
    const sentence = makeSentence({});
    expect(readSentenceGate(sentence, ['nonExistent'])).toBeNull();
  });

  it('returns null for null sentence', () => {
    expect(readSentenceGate(null, ['startGate'])).toBeNull();
  });
});

// ─── resolveSentenceGate ──────────────────────────────────────────────

describe('resolveSentenceGate', () => {
  it('resolves original track gates', () => {
    const sentence = makeSentence({
      originalStartGate: 0.0,
      originalEndGate: 2.5,
    });
    const gate = resolveSentenceGate(sentence, 'original');
    expect(gate).toEqual({ start: 0.0, end: 2.5 });
  });

  it('resolves translation track gates', () => {
    const sentence = makeSentence({
      startGate: 1.0,
      endGate: 3.5,
    });
    const gate = resolveSentenceGate(sentence, 'translation');
    expect(gate).toEqual({ start: 1.0, end: 3.5 });
  });

  it('returns null when start is missing', () => {
    const sentence = makeSentence({ originalEndGate: 2.5 });
    expect(resolveSentenceGate(sentence, 'original')).toBeNull();
  });

  it('returns null when end is missing', () => {
    const sentence = makeSentence({ originalStartGate: 0.0 });
    expect(resolveSentenceGate(sentence, 'original')).toBeNull();
  });

  it('returns null for zero-duration gate', () => {
    const sentence = makeSentence({
      startGate: 1.0,
      endGate: 1.0,
    });
    expect(resolveSentenceGate(sentence, 'translation')).toBeNull();
  });

  it('clamps negative start to 0', () => {
    const sentence = makeSentence({
      startGate: -0.5,
      endGate: 2.0,
    });
    const gate = resolveSentenceGate(sentence, 'translation');
    expect(gate).toEqual({ start: 0.0, end: 2.0 });
  });

  it('returns null for null sentence', () => {
    expect(resolveSentenceGate(null, 'original')).toBeNull();
  });
});

// ─── resolveSentenceDuration ──────────────────────────────────────────

describe('resolveSentenceDuration', () => {
  it('derives duration from gates', () => {
    const sentence = makeSentence({
      originalStartGate: 1.0,
      originalEndGate: 3.5,
    });
    expect(resolveSentenceDuration(sentence, 'original')).toBeCloseTo(2.5);
  });

  it('falls back to phaseDurations for original track', () => {
    const sentence = makeSentence({
      phaseDurations: { original: 1.8 },
    });
    expect(resolveSentenceDuration(sentence, 'original')).toBe(1.8);
  });

  it('falls back to phaseDurations for translation track', () => {
    const sentence = makeSentence({
      phaseDurations: { translation: 2.2 },
    });
    expect(resolveSentenceDuration(sentence, 'translation')).toBe(2.2);
  });

  it('falls back to totalDuration for translation track', () => {
    const sentence = makeSentence({
      totalDuration: 3.0,
    });
    expect(resolveSentenceDuration(sentence, 'translation')).toBe(3.0);
  });

  it('returns totalDuration for combined track', () => {
    const sentence = makeSentence({
      totalDuration: 5.0,
      phaseDurations: { original: 2.0, translation: 3.0 },
    });
    expect(resolveSentenceDuration(sentence, 'combined')).toBe(5.0);
  });

  it('returns null for original track with no data', () => {
    const sentence = makeSentence({});
    expect(resolveSentenceDuration(sentence, 'original')).toBeNull();
  });

  it('returns null for null sentence', () => {
    expect(resolveSentenceDuration(null, 'original')).toBeNull();
  });

  it('prefers gates over phaseDurations', () => {
    const sentence = makeSentence({
      startGate: 0.0,
      endGate: 2.0,
      phaseDurations: { translation: 3.0 },
    });
    // Gates should win
    expect(resolveSentenceDuration(sentence, 'translation')).toBeCloseTo(2.0);
  });
});
