/**
 * Generic time-indexed binary search utilities.
 *
 * These functions work on any sorted array of items that have a start/end
 * time range.  They are used by word-level highlighting, subtitle cue
 * lookup, and the audio-sync timeline — each of which previously had its
 * own copy of essentially the same binary search.
 */

// ---------------------------------------------------------------------------
// Public interface
// ---------------------------------------------------------------------------

/** Anything with a numeric time range. */
export interface TimeRange {
  readonly start: number;
  readonly end: number;
}

/** Accessor that extracts start/end from an arbitrary item. */
export interface TimeRangeAccessor<T> {
  start(item: T): number;
  end(item: T): number;
}

/** Pre-built accessors for common shapes. */
export const Accessors: {
  /** { start, end } — e.g. TimelineEntry, subtitle cues. */
  readonly startEnd: TimeRangeAccessor<{ start: number; end: number }>;
  /** { t0, t1 } — e.g. WordToken, Segment. */
  readonly t0t1: TimeRangeAccessor<{ t0: number; t1: number }>;
} = {
  startEnd: {
    start: (item) => item.start,
    end: (item) => item.end,
  },
  t0t1: {
    start: (item) => item.t0,
    end: (item) => item.t1,
  },
};

// ---------------------------------------------------------------------------
// Core search functions
// ---------------------------------------------------------------------------

/**
 * Compare a time value against a range.
 *
 * Returns:
 * - `-1` if `t` is before the range
 * - `0` if `t` is inside the range (start <= t <= end)
 * - `1` if `t` is after the range
 */
export function compareTime<T>(
  t: number,
  item: T,
  acc: TimeRangeAccessor<T>,
): -1 | 0 | 1 {
  if (t < acc.start(item)) return -1;
  if (t > acc.end(item)) return 1;
  return 0;
}

/**
 * Find the index of the item whose range contains `t`, using binary search.
 *
 * Returns the index, or `-1` if no range contains the time.
 * Items **must** be sorted by start time.
 *
 * This is the "exact" variant — it does not snap to the nearest item.
 */
export function findActiveIndex<T>(
  items: readonly T[],
  t: number,
  acc: TimeRangeAccessor<T>,
): number {
  let low = 0;
  let high = items.length - 1;
  while (low <= high) {
    const mid = (low + high) >> 1;
    const cmp = compareTime(t, items[mid], acc);
    if (cmp === 0) return mid;
    if (cmp < 0) {
      high = mid - 1;
    } else {
      low = mid + 1;
    }
  }
  return -1;
}

/**
 * Find the active item, falling back to the nearest neighbour when `t`
 * falls in a gap between items.
 *
 * Returns the index (always >= 0 when items is non-empty).
 */
export function findNearestIndex<T>(
  items: readonly T[],
  t: number,
  acc: TimeRangeAccessor<T>,
): number {
  if (!items.length) return -1;

  let left = 0;
  let right = items.length - 1;
  let candidate = 0;

  while (left <= right) {
    const mid = (left + right) >> 1;
    const cmp = compareTime(t, items[mid], acc);
    if (cmp === 0) return mid;
    candidate = mid;
    if (cmp < 0) {
      right = mid - 1;
    } else {
      left = mid + 1;
    }
  }

  // candidate is the last tested index; check its neighbours
  const item = items[candidate];
  if (t < acc.start(item) && candidate > 0) {
    const prev = items[candidate - 1];
    return distanceTo(prev, t, acc) <= distanceTo(item, t, acc)
      ? candidate - 1
      : candidate;
  }
  if (t > acc.end(item) && candidate < items.length - 1) {
    const next = items[candidate + 1];
    return distanceTo(next, t, acc) < distanceTo(item, t, acc)
      ? candidate + 1
      : candidate;
  }

  return candidate;
}

/**
 * Find the active item with a hysteresis guard (fast-path reuse of
 * `lastIndex`).
 *
 * When the time is still within `hysteresis` seconds of the previously
 * active item, `lastIndex` is returned immediately.  This prevents
 * flicker at item boundaries.
 *
 * Returns the index, or `-1` if items is empty.
 */
export function findActiveWithHysteresis<T>(
  items: readonly T[],
  t: number,
  acc: TimeRangeAccessor<T>,
  lastIndex: number,
  hysteresis: number,
): number {
  if (!items.length) return -1;

  // Fast path — time is still close to last item
  if (lastIndex >= 0 && lastIndex < items.length) {
    const last = items[lastIndex];
    if (
      t >= acc.start(last) - hysteresis &&
      t <= acc.end(last) + hysteresis
    ) {
      return lastIndex;
    }
  }

  return findActiveIndex(items, t, acc);
}

/**
 * Lower-bound search: find the first index where `accessor(item) >= time`.
 *
 * Useful for insertion-point searches (e.g. "find the next cue after this
 * time").  Items must be sorted by the value returned by `accessor`.
 */
export function lowerBound<T>(
  items: readonly T[],
  time: number,
  accessor: (item: T) => number,
): number {
  let low = 0;
  let high = items.length;
  while (low < high) {
    const mid = (low + high) >> 1;
    if (accessor(items[mid]) < time) {
      low = mid + 1;
    } else {
      high = mid;
    }
  }
  return low;
}

/**
 * Find the insertion index — the first item whose start is > `time`.
 *
 * Useful for seek-to-next-cue operations.
 */
export function findInsertIndex<T>(
  items: readonly T[],
  time: number,
  acc: TimeRangeAccessor<T>,
): number {
  let low = 0;
  let high = items.length - 1;
  let result = items.length;
  while (low <= high) {
    const mid = (low + high) >> 1;
    if (time < acc.start(items[mid])) {
      result = mid;
      high = mid - 1;
    } else {
      low = mid + 1;
    }
  }
  return result;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Distance from `t` to the nearest edge of an item's range. */
export function distanceTo<T>(
  item: T,
  t: number,
  acc: TimeRangeAccessor<T>,
): number {
  const s = acc.start(item);
  const e = acc.end(item);
  if (t < s) return s - t;
  if (t > e) return t - e;
  return 0;
}
