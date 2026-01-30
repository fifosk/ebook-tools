/**
 * Tests for multi-sentence chunk word synchronization.
 *
 * These tests verify that word highlighting remains accurate when multiple
 * sentences are combined into a single chunk, preventing timing drift.
 */

import { buildWordIndex, collectActiveWordIds, lowerBound } from '../wordSync';
import type { TrackTimingPayload, WordTiming } from '../../../api/dtos';

/**
 * Generate a multi-sentence chunk payload with realistic timing.
 */
function createMultiSentencePayload(
  sentenceCount: number,
  wordsPerSentence: number = 3,
  durationPerWord: number = 0.4
): TrackTimingPayload {
  const words: WordTiming[] = [];
  let cursor = 0;
  let wordId = 1;

  for (let sid = 0; sid < sentenceCount; sid++) {
    for (let tokenIdx = 0; tokenIdx < wordsPerSentence; tokenIdx++) {
      const t0 = cursor;
      const t1 = cursor + durationPerWord;

      words.push({
        id: `w${wordId}`,
        sentenceId: sid,
        tokenIdx,
        text: `word_s${sid}_t${tokenIdx}`,
        lang: 'trans',
        t0,
        t1,
      });

      cursor = t1;
      wordId++;
    }
  }

  return {
    trackType: 'translated',
    chunkId: `chunk-${sentenceCount}-sentences`,
    trackOffset: 0,
    tempoFactor: 1,
    version: '2',
    pauses: [],
    words,
  };
}

/**
 * Generate payload with global sentence IDs (simulating mid-book chunk).
 */
function createGlobalSentenceIdPayload(
  startSentenceId: number,
  sentenceCount: number
): TrackTimingPayload {
  const words: WordTiming[] = [];
  let cursor = 0;
  let wordId = 1;

  for (let i = 0; i < sentenceCount; i++) {
    const sid = startSentenceId + i;
    const wordsInSentence = 2 + (i % 3); // Vary word count

    for (let tokenIdx = 0; tokenIdx < wordsInSentence; tokenIdx++) {
      const duration = 0.3 + (tokenIdx % 2) * 0.2; // Vary duration
      words.push({
        id: `w${wordId}`,
        sentenceId: sid,
        tokenIdx,
        text: `word_${wordId}`,
        lang: 'trans',
        t0: cursor,
        t1: cursor + duration,
      });
      cursor += duration;
      wordId++;
    }
  }

  return {
    trackType: 'translated',
    chunkId: `chunk-starting-at-${startSentenceId}`,
    trackOffset: 0,
    tempoFactor: 1,
    version: '2',
    pauses: [],
    words,
  };
}

describe('multi-sentence chunk word index', () => {
  it('correctly maps sentences to words for 10-sentence chunk', () => {
    const payload = createMultiSentencePayload(10, 3);
    const index = buildWordIndex(payload);

    // Should have all 10 sentences mapped
    expect(index.bySentence.size).toBe(10);

    // Each sentence should have 3 words
    for (let sid = 0; sid < 10; sid++) {
      const wordIds = index.bySentence.get(sid);
      expect(wordIds).toBeDefined();
      expect(wordIds!.length).toBe(3);
    }
  });

  it('preserves global sentence IDs (not chunk-relative)', () => {
    // Simulate a chunk starting at sentence 500
    const payload = createGlobalSentenceIdPayload(500, 10);
    const index = buildWordIndex(payload);

    // Sentence IDs should be 500-509, not 0-9
    expect(index.bySentence.has(500)).toBe(true);
    expect(index.bySentence.has(509)).toBe(true);
    expect(index.bySentence.has(0)).toBe(false);
    expect(index.bySentence.has(9)).toBe(false);
  });

  it('maintains timing monotonicity across all sentences', () => {
    const payload = createMultiSentencePayload(20, 5);
    const index = buildWordIndex(payload);

    // Words should be sorted by start time
    let lastEnd = 0;
    for (const word of index.words) {
      expect(word.t0).toBeGreaterThanOrEqual(lastEnd - 0.001);
      expect(word.t1).toBeGreaterThan(word.t0);
      lastEnd = word.t1;
    }
  });

  it('has no timing gaps at sentence boundaries', () => {
    const payload = createMultiSentencePayload(5, 3, 0.5);
    const index = buildWordIndex(payload);

    // Find last word of each sentence and first word of next
    for (let sid = 0; sid < 4; sid++) {
      const currentSentenceWords = index.bySentence.get(sid)!;
      const nextSentenceWords = index.bySentence.get(sid + 1)!;

      const lastWordId = currentSentenceWords[currentSentenceWords.length - 1];
      const firstWordId = nextSentenceWords[0];

      const lastWord = index.byId.get(lastWordId)!;
      const firstWord = index.byId.get(firstWordId)!;

      // Gap should be zero (continuous)
      const gap = firstWord.t0 - lastWord.t1;
      expect(Math.abs(gap)).toBeLessThan(0.001);
    }
  });
});

describe('multi-sentence timing accuracy', () => {
  it('finds correct word at any point in 10-sentence chunk', () => {
    const payload = createMultiSentencePayload(10, 3, 0.4);
    const index = buildWordIndex(payload);

    // Total duration should be 10 * 3 * 0.4 = 12 seconds
    const totalDuration = 10 * 3 * 0.4;

    // Sample at multiple points throughout the chunk
    const sampleTimes = [0.2, 1.5, 4.7, 8.3, 11.5];

    for (const time of sampleTimes) {
      if (time >= totalDuration) continue;

      const activeIds = collectActiveWordIds(index, time);
      expect(activeIds.length).toBe(1);

      // Verify the word's timing actually contains this time
      const word = index.byId.get(activeIds[0])!;
      expect(word.t0).toBeLessThanOrEqual(time);
      expect(word.t1).toBeGreaterThan(time);
    }
  });

  it('handles transition between sentences correctly', () => {
    const payload = createMultiSentencePayload(3, 2, 1.0);
    const index = buildWordIndex(payload);

    // At t=1.99, should be in sentence 0, word 1
    const atEndOfS0 = collectActiveWordIds(index, 1.99);
    expect(atEndOfS0.length).toBe(1);
    const wordAtEndOfS0 = index.byId.get(atEndOfS0[0])!;
    expect(wordAtEndOfS0.sentenceId).toBe(0);
    expect(wordAtEndOfS0.tokenIdx).toBe(1);

    // At t=2.01, should be in sentence 1, word 0
    const atStartOfS1 = collectActiveWordIds(index, 2.01);
    expect(atStartOfS1.length).toBe(1);
    const wordAtStartOfS1 = index.byId.get(atStartOfS1[0])!;
    expect(wordAtStartOfS1.sentenceId).toBe(1);
    expect(wordAtStartOfS1.tokenIdx).toBe(0);
  });

  it('binary search works correctly across 50-sentence chunk', () => {
    const payload = createMultiSentencePayload(50, 4);
    const index = buildWordIndex(payload);

    // Test binary search at various points
    const testTimes = [0, 10.5, 40.2, 79.9];

    for (const time of testTimes) {
      const lowerIdx = lowerBound(index.events, time);

      // lowerBound should find first event >= time
      if (lowerIdx < index.events.length) {
        expect(index.events[lowerIdx].t).toBeGreaterThanOrEqual(time);
      }
      if (lowerIdx > 0) {
        expect(index.events[lowerIdx - 1].t).toBeLessThan(time);
      }
    }
  });
});

describe('edge cases in multi-sentence chunks', () => {
  it('handles single-word sentences', () => {
    const payload: TrackTimingPayload = {
      trackType: 'translated',
      chunkId: 'single-word-sentences',
      trackOffset: 0,
      tempoFactor: 1,
      version: '2',
      pauses: [],
      words: [
        { id: 'w1', sentenceId: 0, tokenIdx: 0, text: 'One', lang: 'trans', t0: 0, t1: 0.5 },
        { id: 'w2', sentenceId: 1, tokenIdx: 0, text: 'Two', lang: 'trans', t0: 0.5, t1: 1.0 },
        { id: 'w3', sentenceId: 2, tokenIdx: 0, text: 'Three', lang: 'trans', t0: 1.0, t1: 1.5 },
      ],
    };

    const index = buildWordIndex(payload);

    expect(index.bySentence.size).toBe(3);
    expect(collectActiveWordIds(index, 0.25)).toEqual(['w1']);
    expect(collectActiveWordIds(index, 0.75)).toEqual(['w2']);
    expect(collectActiveWordIds(index, 1.25)).toEqual(['w3']);
  });

  it('handles varying word counts per sentence', () => {
    const payload: TrackTimingPayload = {
      trackType: 'translated',
      chunkId: 'varying-words',
      trackOffset: 0,
      tempoFactor: 1,
      version: '2',
      pauses: [],
      words: [
        // Sentence 0: 1 word
        { id: 'w1', sentenceId: 0, tokenIdx: 0, text: 'Hi', lang: 'trans', t0: 0, t1: 0.3 },
        // Sentence 1: 4 words
        { id: 'w2', sentenceId: 1, tokenIdx: 0, text: 'How', lang: 'trans', t0: 0.3, t1: 0.5 },
        { id: 'w3', sentenceId: 1, tokenIdx: 1, text: 'are', lang: 'trans', t0: 0.5, t1: 0.7 },
        { id: 'w4', sentenceId: 1, tokenIdx: 2, text: 'you', lang: 'trans', t0: 0.7, t1: 0.9 },
        { id: 'w5', sentenceId: 1, tokenIdx: 3, text: 'today', lang: 'trans', t0: 0.9, t1: 1.2 },
        // Sentence 2: 2 words
        { id: 'w6', sentenceId: 2, tokenIdx: 0, text: 'Fine', lang: 'trans', t0: 1.2, t1: 1.5 },
        { id: 'w7', sentenceId: 2, tokenIdx: 1, text: 'thanks', lang: 'trans', t0: 1.5, t1: 1.9 },
      ],
    };

    const index = buildWordIndex(payload);

    expect(index.bySentence.get(0)!.length).toBe(1);
    expect(index.bySentence.get(1)!.length).toBe(4);
    expect(index.bySentence.get(2)!.length).toBe(2);

    // Verify timing works across varying word counts
    expect(collectActiveWordIds(index, 0.15)).toEqual(['w1']);
    expect(collectActiveWordIds(index, 0.6)).toEqual(['w3']);
    expect(collectActiveWordIds(index, 1.7)).toEqual(['w7']);
  });

  it('handles large sentence IDs without memory issues', () => {
    // Simulate a chunk from very late in a large book
    const payload = createGlobalSentenceIdPayload(99990, 10);
    const index = buildWordIndex(payload);

    // Should handle large sentence IDs efficiently
    expect(index.bySentence.has(99990)).toBe(true);
    expect(index.bySentence.has(99999)).toBe(true);

    // Timing should still work
    const activeAt0_1 = collectActiveWordIds(index, 0.1);
    expect(activeAt0_1.length).toBe(1);
    const word = index.byId.get(activeAt0_1[0])!;
    expect(word.sentenceId).toBe(99990);
  });
});

describe('timing drift prevention', () => {
  it('last word ends at expected chunk duration', () => {
    const sentenceCount = 10;
    const wordsPerSentence = 5;
    const durationPerWord = 0.4;
    const expectedDuration = sentenceCount * wordsPerSentence * durationPerWord;

    const payload = createMultiSentencePayload(sentenceCount, wordsPerSentence, durationPerWord);
    const index = buildWordIndex(payload);

    // Find last word
    const lastWord = index.words[index.words.length - 1];
    const actualEndTime = lastWord.t1;

    // Drift should be effectively zero for synthetic data
    const driftMs = Math.abs(actualEndTime - expectedDuration) * 1000;
    expect(driftMs).toBeLessThan(1); // Less than 1ms drift
  });

  it('no word overlaps in multi-sentence chunk', () => {
    const payload = createMultiSentencePayload(20, 4);
    const index = buildWordIndex(payload);

    // Check for overlaps
    for (let i = 0; i < index.words.length - 1; i++) {
      const current = index.words[i];
      const next = index.words[i + 1];

      // Next word should start at or after current word ends
      expect(next.t0).toBeGreaterThanOrEqual(current.t1 - 0.0001);
    }
  });

  it('timing events are in strictly ascending order', () => {
    const payload = createMultiSentencePayload(15, 3);
    const index = buildWordIndex(payload);

    let lastTime = -Infinity;
    for (const event of index.events) {
      expect(event.t).toBeGreaterThanOrEqual(lastTime);
      lastTime = event.t;
    }
  });
});
