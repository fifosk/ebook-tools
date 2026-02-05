import { describe, expect, it } from 'vitest';
import {
  Accessors,
  compareTime,
  distanceTo,
  findActiveIndex,
  findActiveWithHysteresis,
  findInsertIndex,
  findNearestIndex,
  lowerBound,
} from '../timeSearch';

// ---------- test data helpers -----------------------------------------------

type Range = { start: number; end: number };
type T0T1 = { t0: number; t1: number };

const ranges: Range[] = [
  { start: 0, end: 1 },
  { start: 1.5, end: 2.5 },
  { start: 3, end: 4 },
  { start: 5, end: 6 },
];

const t0t1Items: T0T1[] = [
  { t0: 0, t1: 0.5 },
  { t0: 0.5, t1: 1.1 },
  { t0: 1.1, t1: 1.6 },
  { t0: 2, t1: 2.6 },
];

const acc = Accessors.startEnd;
const t0acc = Accessors.t0t1;

// ---------- compareTime -----------------------------------------------------

describe('compareTime', () => {
  it('returns -1 when time is before range', () => {
    expect(compareTime(-0.5, ranges[0], acc)).toBe(-1);
  });

  it('returns 0 when time is inside range', () => {
    expect(compareTime(0.5, ranges[0], acc)).toBe(0);
  });

  it('returns 0 at range boundaries', () => {
    expect(compareTime(0, ranges[0], acc)).toBe(0);
    expect(compareTime(1, ranges[0], acc)).toBe(0);
  });

  it('returns 1 when time is after range', () => {
    expect(compareTime(1.2, ranges[0], acc)).toBe(1);
  });

  it('works with t0/t1 accessor', () => {
    expect(compareTime(0.3, t0t1Items[0], t0acc)).toBe(0);
    expect(compareTime(0.6, t0t1Items[0], t0acc)).toBe(1);
  });
});

// ---------- findActiveIndex -------------------------------------------------

describe('findActiveIndex', () => {
  it('finds item containing the time', () => {
    expect(findActiveIndex(ranges, 0.5, acc)).toBe(0);
    expect(findActiveIndex(ranges, 2, acc)).toBe(1);
    expect(findActiveIndex(ranges, 3.5, acc)).toBe(2);
    expect(findActiveIndex(ranges, 5.5, acc)).toBe(3);
  });

  it('returns -1 when time is in a gap', () => {
    expect(findActiveIndex(ranges, 1.2, acc)).toBe(-1);
    expect(findActiveIndex(ranges, 4.5, acc)).toBe(-1);
  });

  it('returns -1 for empty array', () => {
    expect(findActiveIndex([], 1, acc)).toBe(-1);
  });

  it('finds at exact start boundary', () => {
    expect(findActiveIndex(ranges, 0, acc)).toBe(0);
    expect(findActiveIndex(ranges, 1.5, acc)).toBe(1);
  });

  it('finds at exact end boundary', () => {
    expect(findActiveIndex(ranges, 1, acc)).toBe(0);
    expect(findActiveIndex(ranges, 2.5, acc)).toBe(1);
  });

  it('works with t0/t1 items', () => {
    expect(findActiveIndex(t0t1Items, 0.3, t0acc)).toBe(0);
    expect(findActiveIndex(t0t1Items, 0.7, t0acc)).toBe(1);
    expect(findActiveIndex(t0t1Items, 2.3, t0acc)).toBe(3);
  });
});

// ---------- findNearestIndex ------------------------------------------------

describe('findNearestIndex', () => {
  it('returns exact index when time is inside a range', () => {
    expect(findNearestIndex(ranges, 2, acc)).toBe(1);
  });

  it('snaps to nearest when time is in a gap', () => {
    // Gap between [0,1] and [1.5,2.5]: midpoint is 1.25
    expect(findNearestIndex(ranges, 1.1, acc)).toBe(0); // closer to range[0] end=1
    expect(findNearestIndex(ranges, 1.4, acc)).toBe(1); // closer to range[1] start=1.5
  });

  it('snaps to first item when time is before all', () => {
    expect(findNearestIndex(ranges, -1, acc)).toBe(0);
  });

  it('snaps to last item when time is after all', () => {
    expect(findNearestIndex(ranges, 100, acc)).toBe(3);
  });

  it('returns -1 for empty array', () => {
    expect(findNearestIndex([], 1, acc)).toBe(-1);
  });

  it('works with single-item array', () => {
    expect(findNearestIndex([ranges[0]], 0.5, acc)).toBe(0);
    expect(findNearestIndex([ranges[0]], 5, acc)).toBe(0);
  });
});

// ---------- findActiveWithHysteresis ----------------------------------------

describe('findActiveWithHysteresis', () => {
  it('returns lastIndex when time is within hysteresis', () => {
    // t=1.05 is 0.05 past ranges[0].end=1, within hysteresis=0.1
    expect(findActiveWithHysteresis(ranges, 1.05, acc, 0, 0.1)).toBe(0);
  });

  it('falls through to search when time is outside hysteresis', () => {
    // t=2.0 is far from ranges[0], should find ranges[1]
    expect(findActiveWithHysteresis(ranges, 2.0, acc, 0, 0.1)).toBe(1);
  });

  it('returns -1 when time is in a gap and no lastIndex match', () => {
    expect(findActiveWithHysteresis(ranges, 4.5, acc, -1, 0.1)).toBe(-1);
  });

  it('returns -1 for empty array', () => {
    expect(findActiveWithHysteresis([], 1, acc, 0, 0.1)).toBe(-1);
  });

  it('handles lastIndex out of bounds', () => {
    expect(findActiveWithHysteresis(ranges, 2.0, acc, 99, 0.1)).toBe(1);
  });
});

// ---------- lowerBound ------------------------------------------------------

describe('lowerBound', () => {
  const starts = ranges.map((r) => r.start); // [0, 1.5, 3, 5]
  const getVal = (item: Range) => item.start;

  it('returns 0 when time is before all items', () => {
    expect(lowerBound(ranges, -1, getVal)).toBe(0);
  });

  it('returns exact index for matching value', () => {
    expect(lowerBound(ranges, 1.5, getVal)).toBe(1);
    expect(lowerBound(ranges, 3, getVal)).toBe(2);
  });

  it('returns insertion point for gap values', () => {
    expect(lowerBound(ranges, 2, getVal)).toBe(2); // first item with start >= 2 is ranges[2]
  });

  it('returns length when time is past all items', () => {
    expect(lowerBound(ranges, 100, getVal)).toBe(4);
  });
});

// ---------- findInsertIndex -------------------------------------------------

describe('findInsertIndex', () => {
  it('returns index of first item starting after time', () => {
    expect(findInsertIndex(ranges, 0.5, acc)).toBe(1); // ranges[1].start=1.5 > 0.5
  });

  it('returns length when time is past all items', () => {
    expect(findInsertIndex(ranges, 100, acc)).toBe(4);
  });

  it('skips items starting at or before time', () => {
    // time=1.5 matches ranges[1].start exactly; insert index should be 2
    expect(findInsertIndex(ranges, 1.5, acc)).toBe(2);
  });

  it('returns 0 when time is before all items', () => {
    expect(findInsertIndex(ranges, -1, acc)).toBe(0);
  });
});

// ---------- distanceTo ------------------------------------------------------

describe('distanceTo', () => {
  it('returns 0 when time is inside range', () => {
    expect(distanceTo(ranges[0], 0.5, acc)).toBe(0);
  });

  it('returns distance before range', () => {
    expect(distanceTo(ranges[1], 1, acc)).toBeCloseTo(0.5);
  });

  it('returns distance after range', () => {
    expect(distanceTo(ranges[0], 1.5, acc)).toBeCloseTo(0.5);
  });
});
