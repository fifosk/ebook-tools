import { buildWordIndex, collectActiveWordIds, lowerBound } from '../wordSync';
import type { TrackTimingPayload } from '../../../api/dtos';

function createPayload(overrides: Partial<TrackTimingPayload> = {}): TrackTimingPayload {
  return {
    trackType: 'translated',
    chunkId: 'chunk-1',
    trackOffset: 0,
    tempoFactor: 1,
    version: '1',
    pauses: [
      { t0: 2.25, t1: 2.75, reason: 'silence' },
      { t0: 1.5, t1: 1.6 },
    ],
    words: [
      {
        id: 'w1',
        sentenceId: 0,
        tokenIdx: 0,
        text: 'Hello',
        lang: 'trans',
        t0: 0,
        t1: 0.6,
      },
      {
        id: 'w2',
        sentenceId: 0,
        tokenIdx: 1,
        text: 'world',
        lang: 'trans',
        t0: 0.6,
        t1: 1.2,
      },
      {
        id: 'w3',
        sentenceId: 1,
        tokenIdx: 0,
        text: 'Original',
        lang: 'orig',
        t0: 1.2,
        t1: 1.8,
      },
      {
        id: 'w4',
        sentenceId: 1,
        tokenIdx: 0,
        text: 'Translation',
        lang: 'trans',
        t0: 1.8,
        t1: 2.4,
      },
    ],
    ...overrides,
  };
}

describe('wordSync timeline helpers', () => {
  it('orders timeline events with offs preceding ons at the same timestamp', () => {
    const payload = createPayload();
    const index = buildWordIndex(payload);
    const eventKindsAt060 = index.events.filter((event) => event.t === 0.6).map((event) => event.kind);
    expect(eventKindsAt060).toEqual(['off', 'on']);
  });

  it('builds sentence indexes preserving per-lane ordering', () => {
    const payload = createPayload();
    const index = buildWordIndex(payload);
    const sentenceZero = index.bySentence.get(0);
    expect(sentenceZero).toEqual(['w1', 'w2']);
    const sentenceOne = index.bySentence.get(1);
    expect(sentenceOne).toEqual(['w3', 'w4']);
  });

  it('sorts pauses chronologically', () => {
    const payload = createPayload();
    const index = buildWordIndex(payload);
    expect(index.pauses.map((pause) => pause.t0)).toEqual([1.5, 2.25]);
  });

  it('collects active words at a given moment', () => {
    const payload = createPayload();
    const index = buildWordIndex(payload);
    expect(collectActiveWordIds(index, 0.3)).toEqual(['w1']);
    expect(collectActiveWordIds(index, 0.9)).toEqual(['w2']);
    expect(collectActiveWordIds(index, 1.35)).toEqual(['w3']);
    expect(collectActiveWordIds(index, 1.9)).toEqual(['w4']);
    expect(collectActiveWordIds(index, 3)).toEqual([]);
  });

  it('performs a binary search over timeline events', () => {
    const payload = createPayload();
    const index = buildWordIndex(payload);
    expect(lowerBound(index.events, 0)).toBe(0);
    expect(lowerBound(index.events, 0.6)).toBe(1);
    expect(lowerBound(index.events, 1.5)).toBe(5);
    expect(lowerBound(index.events, 10)).toBe(index.events.length);
  });
});
