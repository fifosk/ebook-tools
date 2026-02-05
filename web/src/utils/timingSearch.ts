import type { Hit, Segment, TimingPayload, WordToken } from '../types/timing';
import {
  Accessors,
  compareTime as genericCompareTime,
  distanceTo,
  findNearestIndex,
} from '../lib/timing/timeSearch';

const HYSTERESIS_SECONDS = 0.024; // 24ms guard band to avoid flicker
const LARGE_SEEK_THRESHOLD = 0.35; // seconds

const t0t1 = Accessors.t0t1;

/**
 * Compare a time value against a {t0, t1} range.
 *
 * Re-exported for backward compatibility — callers like AudioSyncController
 * import this from `utils/timingSearch`.
 */
export function compareTime(
  t: number,
  range: { t0: number; t1: number }
): -1 | 0 | 1 {
  return genericCompareTime(t, range, t0t1);
}

export function isLargeSeek(prevT: number, t: number): boolean {
  return Math.abs(t - prevT) >= LARGE_SEEK_THRESHOLD;
}

export function clampHit(payload: TimingPayload, hit: Hit): Hit {
  const segments = payload.segments;
  if (!segments.length) {
    return { segIndex: -1, tokIndex: -1 };
  }

  let segIndex = Number.isFinite(hit.segIndex) ? hit.segIndex : 0;
  if (segIndex < 0) {
    segIndex = 0;
  } else if (segIndex >= segments.length) {
    segIndex = segments.length - 1;
  }

  let segment = segments[segIndex];
  if (!segment.tokens.length) {
    let forward = segIndex + 1;
    while (forward < segments.length && !segments[forward].tokens.length) {
      forward += 1;
    }

    if (forward < segments.length) {
      segIndex = forward;
      segment = segments[segIndex];
    } else {
      let backward = segIndex - 1;
      while (backward >= 0 && !segments[backward].tokens.length) {
        backward -= 1;
      }

      if (backward >= 0) {
        segIndex = backward;
        segment = segments[segIndex];
      } else {
        return { segIndex: -1, tokIndex: -1 };
      }
    }
  }

  const tokenCount = segment.tokens.length;
  let tokIndex = Number.isFinite(hit.tokIndex) ? hit.tokIndex : 0;
  if (tokIndex < 0) {
    tokIndex = 0;
  } else if (tokIndex >= tokenCount) {
    tokIndex = tokenCount - 1;
  }

  return { segIndex, tokIndex };
}

export function findNearestToken(
  payload: TimingPayload,
  t: number,
  last?: Hit
): Hit {
  const segments = payload.segments;
  if (!segments.length) {
    return { segIndex: -1, tokIndex: -1 };
  }

  const lastClamped = last ? clampHit(payload, last) : null;
  const lastToken = lastClamped ? getToken(payload, lastClamped) : undefined;
  const lastTime =
    lastToken === undefined ? undefined : (lastToken.t0 + lastToken.t1) / 2;
  if (
    lastToken &&
    t >= lastToken.t0 - HYSTERESIS_SECONDS &&
    t <= lastToken.t1 + HYSTERESIS_SECONDS
  ) {
    return lastClamped as Hit;
  }

  let segIndex = findNearestIndex(segments, t, t0t1);
  segIndex = ensureSegmentWithTokens(segments, segIndex, t);
  if (segIndex === -1) {
    return lastClamped ?? { segIndex: -1, tokIndex: -1 };
  }

  const segment = segments[segIndex];
  const tokIndex = findNearestIndex(segment.tokens, t, t0t1);
  const nextHit = clampHit(payload, { segIndex, tokIndex });

  if (
    lastClamped &&
    lastClamped.segIndex >= 0 &&
    lastClamped.tokIndex >= 0 &&
    lastToken &&
    lastTime !== undefined &&
    !isLargeSeek(lastTime, t)
  ) {
    if (nextHit.segIndex < lastClamped.segIndex) {
      return lastClamped;
    }
    if (
      nextHit.segIndex === lastClamped.segIndex &&
      nextHit.tokIndex < lastClamped.tokIndex
    ) {
      return lastClamped;
    }
  }

  return nextHit;
}

/**
 * Skip to the nearest segment that actually has tokens.
 *
 * This handles the edge case where a segment exists in the timing payload
 * but has an empty token array (e.g. silence-only segments).
 */
function ensureSegmentWithTokens(
  segments: Segment[],
  segIndex: number,
  t: number
): number {
  if (segments[segIndex]?.tokens.length) {
    return segIndex;
  }

  let forward = segIndex;
  while (forward < segments.length && !segments[forward].tokens.length) {
    forward += 1;
  }

  let backward = segIndex;
  while (backward >= 0 && !segments[backward].tokens.length) {
    backward -= 1;
  }

  if (forward < segments.length && backward >= 0) {
    const forwardSeg = segments[forward];
    const backwardSeg = segments[backward];
    return distanceTo(forwardSeg, t, t0t1) <= distanceTo(backwardSeg, t, t0t1)
      ? forward
      : backward;
  }
  if (forward < segments.length) {
    return forward;
  }
  if (backward >= 0) {
    return backward;
  }

  return -1;
}

function getToken(payload: TimingPayload, hit: Hit): WordToken | undefined {
  const segment = payload.segments[hit.segIndex];
  return segment?.tokens[hit.tokIndex];
}
