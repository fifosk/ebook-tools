import type { TimelineSentenceRuntime } from './types';

export type InlineSentenceSkipResult = {
  targetIndex: number;
  startTime: number;
};

export function resolveInlineSentenceSkip(
  sentences: TimelineSentenceRuntime[] | null | undefined,
  currentIndex: number,
  totalSentences: number,
  direction: 1 | -1,
): InlineSentenceSkipResult | null {
  if (!sentences || sentences.length === 0 || totalSentences <= 0) {
    return null;
  }

  const targetIndex = currentIndex + direction;
  if (targetIndex < 0 || targetIndex >= sentences.length) {
    return null;
  }

  const target = sentences[targetIndex];
  if (!target || !Number.isFinite(target.startTime)) {
    return null;
  }

  return {
    targetIndex,
    startTime: target.startTime,
  };
}
