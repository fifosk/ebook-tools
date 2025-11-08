import { describe, expect, it } from 'vitest';
import type { Segment } from '../../types/timing';
import { interleaveDual } from '../interleave';

function segment(id: string, lane: 'orig' | 'tran', t0: number, t1: number): Segment {
  return {
    id,
    t0,
    t1,
    tokens: [
      {
        id: `${id}-${lane}`,
        text: `${lane}-${id}`,
        t0,
        t1,
        lane,
        segId: id,
      },
    ],
  };
}

describe('interleaveDual', () => {
  it('orders overlapping segments by start time and lane priority', () => {
    const origSegs = [segment('seg-a', 'orig', 0, 1)];
    const tranSegs = [segment('seg-b', 'tran', 0, 1)];

    const merged = interleaveDual(origSegs, tranSegs);

    expect(merged).toHaveLength(2);
    expect(merged[0]!.tokens[0]!.lane).toBe('orig');
    expect(merged[1]!.tokens[0]!.lane).toBe('tran');
  });

  it('inserts pause tokens when gaps exceed the threshold', () => {
    const origSegs = [segment('seg-a', 'orig', 0, 0.5)];
    const tranSegs = [segment('seg-b', 'tran', 1.0, 1.5)];

    const merged = interleaveDual(origSegs, tranSegs, { pauseMin: 0.2 });

    expect(merged).toHaveLength(3);
    const pause = merged[1];
    expect(pause.id.startsWith('pause-')).toBe(true);
    expect(pause.tokens[0]?.text).toBe('');
    expect(pause.tokens[0]?.lane).toBe('orig');
  });
});
