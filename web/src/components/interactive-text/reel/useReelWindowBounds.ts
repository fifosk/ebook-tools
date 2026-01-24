import { useMemo } from 'react';
import { REEL_WINDOW_SIZE, REEL_PREFETCH_BUFFER, REEL_EAGER_PRELOAD_BUFFER } from './constants';
import type { ReelWindowBounds } from './types';

interface UseReelWindowBoundsArgs {
  activeSentenceNumber: number;
  minSentenceBound: number;
  maxSentenceBound: number | null;
  promptPlanSentenceRange: { start: number; end: number } | null;
  chunkEndSentence?: number | null;
}

/**
 * Calculate the visible window bounds and prefetch slots for the reel.
 */
export function useReelWindowBounds({
  activeSentenceNumber,
  minSentenceBound,
  maxSentenceBound,
  promptPlanSentenceRange,
  chunkEndSentence,
}: UseReelWindowBoundsArgs) {
  const reelWindowBounds = useMemo<ReelWindowBounds>(() => {
    const base = Math.max(1, Math.trunc(activeSentenceNumber));
    const rangeStart = promptPlanSentenceRange?.start ?? minSentenceBound;
    const rangeEnd = promptPlanSentenceRange?.end ?? maxSentenceBound ?? chunkEndSentence ?? base;
    const boundedStart = Math.max(minSentenceBound, rangeStart);
    const boundedEnd =
      rangeEnd === null
        ? null
        : Math.max(boundedStart, Math.min(rangeEnd, maxSentenceBound ?? rangeEnd));
    const halfWindow = Math.max(0, Math.floor(REEL_WINDOW_SIZE / 2));

    let windowStart = base - halfWindow;
    let windowEnd = base + halfWindow;

    if (boundedEnd !== null && windowEnd > boundedEnd) {
      const overshoot = windowEnd - boundedEnd;
      windowEnd = boundedEnd;
      windowStart -= overshoot;
    }
    if (windowStart < boundedStart) {
      const overshoot = boundedStart - windowStart;
      windowStart = boundedStart;
      windowEnd = boundedEnd !== null ? Math.min(boundedEnd, windowEnd + overshoot) : windowEnd + overshoot;
    }
    if (boundedEnd !== null) {
      windowEnd = Math.min(windowEnd, boundedEnd);
    }
    windowStart = Math.max(windowStart, boundedStart);

    if (boundedEnd !== null && windowStart > boundedEnd) {
      windowStart = boundedEnd;
      windowEnd = boundedEnd;
    }

    return {
      base,
      start: Math.max(1, Math.trunc(windowStart)),
      end: Math.max(1, Math.trunc(windowEnd)),
      boundedStart,
      boundedEnd,
    };
  }, [activeSentenceNumber, chunkEndSentence, maxSentenceBound, minSentenceBound, promptPlanSentenceRange]);

  const reelSentenceSlots = useMemo(() => {
    const { base, start, end } = reelWindowBounds;
    const slots: number[] = [];
    for (let candidate = start; candidate <= end; candidate += 1) {
      slots.push(candidate);
    }
    if (slots.length === 0) {
      slots.push(base);
    }
    return slots;
  }, [reelWindowBounds]);

  const reelPrefetchSlots = useMemo(() => {
    if (REEL_PREFETCH_BUFFER <= 0) {
      return [] as number[];
    }
    const { start, end, boundedStart, boundedEnd } = reelWindowBounds;
    const visible = new Set(reelSentenceSlots);
    const slots: number[] = [];

    for (let offset = 1; offset <= REEL_PREFETCH_BUFFER; offset += 1) {
      const forward = end + offset;
      const back = start - offset;
      if (forward >= boundedStart && (boundedEnd === null || forward <= boundedEnd) && !visible.has(forward)) {
        slots.push(forward);
      }
      if (back >= boundedStart && (boundedEnd === null || back <= boundedEnd) && !visible.has(back)) {
        slots.push(back);
      }
    }

    return slots;
  }, [reelSentenceSlots, reelWindowBounds]);

  const reelEagerSlots = useMemo(() => {
    if (REEL_EAGER_PRELOAD_BUFFER <= 0) {
      return [] as number[];
    }
    const { boundedStart, boundedEnd } = reelWindowBounds;
    const base = Math.max(1, Math.trunc(activeSentenceNumber));
    const upperBound = boundedEnd ?? Number.POSITIVE_INFINITY;
    const slots: number[] = [];
    for (let offset = 1; offset <= REEL_EAGER_PRELOAD_BUFFER; offset += 1) {
      const forward = base + offset;
      const back = base - offset;
      if (forward >= boundedStart && forward <= upperBound) {
        slots.push(forward);
      }
      if (back >= boundedStart && back <= upperBound) {
        slots.push(back);
      }
    }
    return slots;
  }, [activeSentenceNumber, reelWindowBounds]);

  const reelPreloadSlots = useMemo(() => {
    const merged = new Set<number>();
    reelSentenceSlots.forEach((value) => {
      if (typeof value === 'number' && Number.isFinite(value)) {
        merged.add(value);
      }
    });
    reelPrefetchSlots.forEach((value) => {
      if (typeof value === 'number' && Number.isFinite(value)) {
        merged.add(value);
      }
    });
    reelEagerSlots.forEach((value) => {
      if (typeof value === 'number' && Number.isFinite(value)) {
        merged.add(value);
      }
    });
    return Array.from(merged);
  }, [reelEagerSlots, reelPrefetchSlots, reelSentenceSlots]);

  return {
    reelWindowBounds,
    reelSentenceSlots,
    reelPrefetchSlots,
    reelEagerSlots,
    reelPreloadSlots,
  };
}

export default useReelWindowBounds;
