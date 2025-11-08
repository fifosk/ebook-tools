import type { Segment, WordToken } from '../types/timing';

const DEFAULT_PAUSE_THRESHOLD = 0.09; // seconds (90ms)
const MIN_STEP = 0.008; // seconds (8ms)
const EPSILON = 1e-6;

interface InterleaveOptions {
  pauseMin?: number;
}

type Lane = WordToken['lane'];

export function interleaveDual(
  origSegs: Segment[],
  tranSegs: Segment[],
  options?: InterleaveOptions
): Segment[] {
  const hasOrig = Array.isArray(origSegs) && origSegs.length > 0;
  const hasTran = Array.isArray(tranSegs) && tranSegs.length > 0;

  if (!hasOrig || !hasTran) {
    return hasOrig ? origSegs : tranSegs;
  }

  const pauseThreshold = sanitisePauseThreshold(options?.pauseMin);
  const result: Segment[] = [];
  let pauseCounter = 0;
  let origIndex = 0;
  let tranIndex = 0;

  while (origIndex < origSegs.length || tranIndex < tranSegs.length) {
    let source: Segment | null = null;
    let lane: Lane = 'orig';

    if (origIndex < origSegs.length && tranIndex < tranSegs.length) {
      const orig = origSegs[origIndex];
      const tran = tranSegs[tranIndex];
      if (compareStart(orig, tran) <= 0) {
        source = orig;
        lane = 'orig';
        origIndex += 1;
      } else {
        source = tran;
        lane = 'tran';
        tranIndex += 1;
      }
    } else if (origIndex < origSegs.length) {
      source = origSegs[origIndex];
      lane = 'orig';
      origIndex += 1;
    } else if (tranIndex < tranSegs.length) {
      source = tranSegs[tranIndex];
      lane = 'tran';
      tranIndex += 1;
    }

    if (!source) {
      break;
    }

    const cloned = cloneSegment(source, lane);
    appendSegment(result, cloned, pauseThreshold, () => {
      const previous = result[result.length - 1];
      if (!previous) {
        return;
      }
      const gap = cloned.t0 - previous.t1;
      if (gap <= pauseThreshold) {
        return;
      }

      const midpoint = previous.t1 + gap / 2;
      const pauseId = `pause-${pauseCounter}`;
      pauseCounter += 1;
      const pauseToken: WordToken = {
        id: pauseId,
        text: '',
        t0: midpoint,
        t1: midpoint,
        lane: 'orig',
        segId: pauseId,
      };
      const pauseSegment: Segment = {
        id: pauseId,
        t0: midpoint,
        t1: midpoint,
        tokens: [pauseToken],
      };
      emitSegment(result, pauseSegment);
    });
  }

  return result;
}

function appendSegment(
  target: Segment[],
  segment: Segment,
  pauseThreshold: number,
  handlePause: () => void
): void {
  if (target.length > 0) {
    const previous = target[target.length - 1];
    if (segment.t0 - previous.t1 > pauseThreshold) {
      handlePause();
    }
  }
  emitSegment(target, segment);
}

function emitSegment(target: Segment[], segment: Segment): void {
  if (target.length > 0) {
    const previous = target[target.length - 1];
    if (segment.t0 <= previous.t1) {
      const shift = previous.t1 + MIN_STEP - segment.t0;
      if (shift > 0) {
        shiftSegment(segment, shift);
      }
    }
  }

  if (segment.tokens.length > 0) {
    segment.tokens.sort(tokenComparator);
    updateSegmentBounds(segment);
  } else if (!Number.isFinite(segment.t0)) {
    segment.t0 = target.length > 0 ? target[target.length - 1].t1 + MIN_STEP : 0;
    segment.t1 = segment.t0;
  }

  target.push(segment);
}

function cloneSegment(source: Segment, fallbackLane: Lane): Segment {
  const tokens: WordToken[] = source.tokens.map((token) => {
    const baseT0 = sanitiseTime(token.t0, source.t0);
    let baseT1 = sanitiseTime(token.t1, baseT0);
    if (baseT1 - baseT0 < MIN_STEP) {
      baseT1 = baseT0 + MIN_STEP;
    }

    const lane: Lane = token.lane === 'orig' || token.lane === 'tran' ? token.lane : fallbackLane;

    return {
      ...token,
      lane,
      segId: token.segId ?? source.id,
      t0: baseT0,
      t1: baseT1,
    };
  });

  tokens.sort(tokenComparator);

  const clone: Segment = {
    id: source.id,
    t0: sanitiseTime(source.t0, tokens[0]?.t0 ?? 0),
    t1: sanitiseTime(source.t1, tokens[tokens.length - 1]?.t1 ?? source.t0),
    tokens,
  };

  updateSegmentBounds(clone);
  return clone;
}

function shiftSegment(segment: Segment, delta: number): void {
  if (!(delta > 0)) {
    return;
  }

  segment.t0 += delta;
  segment.t1 += delta;
  for (const token of segment.tokens) {
    token.t0 += delta;
    token.t1 += delta;
  }
}

function updateSegmentBounds(segment: Segment): void {
  if (segment.tokens.length === 0) {
    if (!Number.isFinite(segment.t0)) {
      segment.t0 = 0;
    }
    if (!Number.isFinite(segment.t1) || segment.t1 < segment.t0) {
      segment.t1 = segment.t0;
    }
    return;
  }

  let min = segment.tokens[0].t0;
  let max = segment.tokens[0].t1;
  for (const token of segment.tokens) {
    if (token.t0 < min) {
      min = token.t0;
    }
    if (token.t1 > max) {
      max = token.t1;
    }
  }
  if (max - min < MIN_STEP) {
    max = min + MIN_STEP;
  }
  segment.t0 = min;
  segment.t1 = max;
}

function tokenComparator(left: WordToken, right: WordToken): number {
  if (Math.abs(left.t0 - right.t0) > EPSILON) {
    return left.t0 - right.t0;
  }
  if (Math.abs(left.t1 - right.t1) > EPSILON) {
    return left.t1 - right.t1;
  }
  if (left.lane !== right.lane) {
    return left.lane === 'orig' ? -1 : 1;
  }
  return left.id.localeCompare(right.id);
}

function sanitisePauseThreshold(value: number | undefined): number {
  if (typeof value !== 'number' || Number.isNaN(value) || value <= 0) {
    return DEFAULT_PAUSE_THRESHOLD;
  }
  return value;
}

function sanitiseTime(value: number | undefined, fallback: number): number {
  if (typeof value !== 'number' || Number.isNaN(value) || !Number.isFinite(value)) {
    return fallback;
  }
  return value;
}

function compareStart(left: Segment, right: Segment): number {
  const diff = (left.t0 ?? 0) - (right.t0 ?? 0);
  if (Math.abs(diff) > EPSILON) {
    return diff;
  }
  return -1;
}
