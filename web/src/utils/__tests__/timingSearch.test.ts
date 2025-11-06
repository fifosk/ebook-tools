import { describe, expect, it } from 'vitest';
import type { TimingPayload } from '../../types/timing';
import { findNearestToken, isLargeSeek } from '../timingSearch';

function buildPayload(): TimingPayload {
  return {
    trackKind: 'original_translation_combined',
    segments: [
      {
        id: 'seg-0',
        t0: 0,
        t1: 2,
        tokens: [
          {
            id: 'o-0',
            text: 'Hello',
            t0: 0,
            t1: 0.5,
            lane: 'orig',
            segId: 'seg-0',
          },
          {
            id: 't-0',
            text: 'Hola',
            t0: 0.5,
            t1: 1.1,
            lane: 'tran',
            segId: 'seg-0',
          },
          {
            id: 'o-1',
            text: 'world',
            t0: 1.1,
            t1: 1.6,
            lane: 'orig',
            segId: 'seg-0',
          },
        ],
      },
      {
        id: 'seg-1',
        t0: 2,
        t1: 4,
        tokens: [
          {
            id: 't-1',
            text: 'mundo',
            t0: 2,
            t1: 2.6,
            lane: 'tran',
            segId: 'seg-1',
          },
          {
            id: 'o-2',
            text: 'again',
            t0: 2.6,
            t1: 3.4,
            lane: 'orig',
            segId: 'seg-1',
          },
        ],
      },
    ],
  };
}

describe('findNearestToken', () => {
  it('locates the closest token within the appropriate segment', () => {
    const payload = buildPayload();
    const hit = findNearestToken(payload, 0.6);
    expect(hit.segIndex).toBe(0);
    expect(hit.tokIndex).toBe(1); // Hola token
  });

  it('sticks to previous token when time stays inside hysteresis window', () => {
    const payload = buildPayload();
    const last = { segIndex: 0, tokIndex: 2 };
    const hit = findNearestToken(payload, 1.58, last);
    expect(hit).toEqual(last);
  });

  it('allows backwards navigation after a large seek', () => {
    const payload = buildPayload();
    const last = { segIndex: 1, tokIndex: 1 };

    const before = findNearestToken(payload, 3.1, last);
    expect(before).toEqual(last);

    const afterSeek = findNearestToken(payload, 0.2, last);
    expect(afterSeek.segIndex).toBe(0);
    expect(afterSeek.tokIndex).toBe(0);
  });
});

describe('isLargeSeek', () => {
  it('identifies seeks above the threshold', () => {
    expect(isLargeSeek(10, 10.2)).toBe(false);
    expect(isLargeSeek(10, 10.5)).toBe(true);
  });
});
