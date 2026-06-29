import { describe, expect, it } from 'vitest';
import { resolveInlineSentenceSkip } from '../inlineSentenceSkip';
import type { TimelineSentenceRuntime } from '../types';

function sentence(index: number, startTime: number): TimelineSentenceRuntime {
  return {
    index,
    startTime,
    endTime: startTime + 1,
    variants: {
      original: {
        tokens: [`sentence-${index}`],
        revealTimes: [startTime],
      },
    },
  };
}

describe('resolveInlineSentenceSkip', () => {
  const sentences = [sentence(0, 0), sentence(1, 1.25), sentence(2, 2.5)];

  it('resolves adjacent sentence seeks within the current chunk', () => {
    expect(resolveInlineSentenceSkip(sentences, 1, sentences.length, 1)).toEqual({
      targetIndex: 2,
      startTime: 2.5,
    });
    expect(resolveInlineSentenceSkip(sentences, 1, sentences.length, -1)).toEqual({
      targetIndex: 0,
      startTime: 0,
    });
  });

  it('returns null at chunk boundaries so the caller can use cross-chunk fallback', () => {
    expect(resolveInlineSentenceSkip(sentences, 0, sentences.length, -1)).toBeNull();
    expect(resolveInlineSentenceSkip(sentences, 2, sentences.length, 1)).toBeNull();
  });

  it('returns null when timeline data cannot drive a precise seek', () => {
    expect(resolveInlineSentenceSkip(null, 0, 3, 1)).toBeNull();
    expect(resolveInlineSentenceSkip([], 0, 3, 1)).toBeNull();
    expect(resolveInlineSentenceSkip(sentences, 0, 0, 1)).toBeNull();
    expect(resolveInlineSentenceSkip([sentence(0, 0), sentence(1, Number.NaN)], 0, 2, 1)).toBeNull();
  });
});
