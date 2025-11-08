import type { Hit, Segment, TimingPayload, WordToken } from '../types/timing';

const HYSTERESIS_SECONDS = 0.024; // 24ms guard band to avoid flicker
const LARGE_SEEK_THRESHOLD = 0.35; // seconds

export function compareTime(
  t: number,
  range: { t0: number; t1: number }
): -1 | 0 | 1 {
  if (t < range.t0) {
    return -1;
  }
  if (t > range.t1) {
    return 1;
  }
  return 0;
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

  let segIndex = locateSegmentIndex(segments, t);
  segIndex = ensureSegmentWithTokens(segments, segIndex, t);
  if (segIndex === -1) {
    return lastClamped ?? { segIndex: -1, tokIndex: -1 };
  }

  const segment = segments[segIndex];
  const tokIndex = locateTokenIndex(segment.tokens, t);
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

function locateSegmentIndex(segments: Segment[], t: number): number {
  let left = 0;
  let right = segments.length - 1;
  let candidate = 0;

  while (left <= right) {
    const mid = (left + right) >> 1;
    const segment = segments[mid];
    const cmp = compareTime(t, segment);

    if (cmp === 0) {
      return mid;
    }

    candidate = mid;
    if (cmp < 0) {
      right = mid - 1;
    } else {
      left = mid + 1;
    }
  }

  const segment = segments[candidate];
  if (t < segment.t0 && candidate > 0) {
    const prev = segments[candidate - 1];
    return distanceToSegment(prev, t) <= distanceToSegment(segment, t)
      ? candidate - 1
      : candidate;
  }
  if (t > segment.t1 && candidate < segments.length - 1) {
    const next = segments[candidate + 1];
    return distanceToSegment(next, t) < distanceToSegment(segment, t)
      ? candidate + 1
      : candidate;
  }

  return candidate;
}

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
    return distanceToSegment(forwardSeg, t) <= distanceToSegment(backwardSeg, t)
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

function locateTokenIndex(tokens: WordToken[], t: number): number {
  const count = tokens.length;
  if (!count) {
    return -1;
  }

  let left = 0;
  let right = count - 1;
  let candidate = 0;

  while (left <= right) {
    const mid = (left + right) >> 1;
    const token = tokens[mid];
    const cmp = compareTime(t, token);

    if (cmp === 0) {
      return mid;
    }

    candidate = mid;
    if (cmp < 0) {
      right = mid - 1;
    } else {
      left = mid + 1;
    }
  }

  const token = tokens[candidate];
  if (t < token.t0 && candidate > 0) {
    const prev = tokens[candidate - 1];
    return distanceToToken(prev, t) <= distanceToToken(token, t)
      ? candidate - 1
      : candidate;
  }
  if (t > token.t1 && candidate < count - 1) {
    const next = tokens[candidate + 1];
    return distanceToToken(next, t) < distanceToToken(token, t)
      ? candidate + 1
      : candidate;
  }

  return candidate;
}

function getToken(payload: TimingPayload, hit: Hit): WordToken | undefined {
  const segment = payload.segments[hit.segIndex];
  return segment?.tokens[hit.tokIndex];
}

function distanceToSegment(segment: Segment, t: number): number {
  if (t < segment.t0) {
    return segment.t0 - t;
  }
  if (t > segment.t1) {
    return t - segment.t1;
  }
  return 0;
}

function distanceToToken(token: WordToken, t: number): number {
  if (t < token.t0) {
    return token.t0 - t;
  }
  if (t > token.t1) {
    return t - token.t1;
  }
  return 0;
}
