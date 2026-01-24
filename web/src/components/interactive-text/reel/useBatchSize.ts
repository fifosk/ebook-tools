import { useMemo, useCallback } from 'react';
import type { LiveMediaChunk } from '../../../hooks/useLiveMedia';
import type { ImagePromptPlanSummary } from './types';
import { parseBatchStartFromBatchImagePath, inferBatchSizeFromStarts, parseNumericValue } from './utils';

interface UseBatchSizeArgs {
  chunk: LiveMediaChunk | null;
  activeSentenceIndex: number;
  promptPlanBatchSize: number | null;
  minSentenceBound: number;
  promptPlanSentenceRange: { start: number; end: number } | null;
}

/**
 * Hook to calculate batch size and resolve batch start for sentences.
 */
export function useBatchSize({
  chunk,
  activeSentenceIndex,
  promptPlanBatchSize,
  minSentenceBound,
  promptPlanSentenceRange,
}: UseBatchSizeArgs) {
  // Extract batch start candidates from chunk files
  const batchStartCandidatesFromFiles = useMemo(() => {
    const files = chunk?.files ?? [];
    if (!files.length) {
      return [] as number[];
    }
    const starts = new Set<number>();
    files.forEach((file) => {
      const candidates = [
        typeof file.relative_path === 'string' ? file.relative_path : null,
        typeof file.path === 'string' ? file.path : null,
        typeof file.url === 'string' ? file.url : null,
      ];
      for (const candidate of candidates) {
        if (!candidate) {
          continue;
        }
        const inferred = parseBatchStartFromBatchImagePath(candidate);
        if (inferred !== null) {
          starts.add(inferred);
          break;
        }
      }
    });
    return Array.from(starts).sort((a, b) => a - b);
  }, [chunk?.files]);

  const batchSizeFromFiles = useMemo(
    () => inferBatchSizeFromStarts(batchStartCandidatesFromFiles),
    [batchStartCandidatesFromFiles]
  );

  // Calculate active image batch size
  const activeImageBatchSize = useMemo(() => {
    const entries = chunk?.sentences ?? null;
    const entry =
      entries && entries.length > 0
        ? entries[Math.max(0, Math.min(activeSentenceIndex, entries.length - 1))]
        : null;
    const imagePayload = entry?.image ?? null;

    // Try explicit batch_size
    const raw = imagePayload?.batch_size ?? (imagePayload as Record<string, unknown>)?.batchSize ?? null;
    const parsed = parseNumericValue(raw);
    if (parsed !== null && Number.isFinite(parsed)) {
      return Math.max(1, Math.trunc(parsed));
    }

    // Try batch start/end range
    const rawStart = imagePayload?.batch_start_sentence ?? (imagePayload as Record<string, unknown>)?.batchStartSentence ?? null;
    const rawEnd = imagePayload?.batch_end_sentence ?? (imagePayload as Record<string, unknown>)?.batchEndSentence ?? null;
    const startParsed = parseNumericValue(rawStart);
    const endParsed = parseNumericValue(rawEnd);
    if (startParsed !== null && endParsed !== null && endParsed >= startParsed) {
      return Math.max(1, Math.trunc(endParsed) - Math.trunc(startParsed) + 1);
    }

    // Try prompt plan batch size
    if (typeof promptPlanBatchSize === 'number' && Number.isFinite(promptPlanBatchSize)) {
      return Math.max(1, Math.trunc(promptPlanBatchSize));
    }

    // Try batch size inferred from files
    if (typeof batchSizeFromFiles === 'number' && Number.isFinite(batchSizeFromFiles)) {
      return Math.max(1, Math.trunc(batchSizeFromFiles));
    }

    // Check if path indicates batch images
    const explicitPath =
      (typeof imagePayload?.path === 'string' && imagePayload.path.trim()) ||
      (typeof entry?.image_path === 'string' && entry.image_path.trim()) ||
      (typeof entry?.imagePath === 'string' && entry.imagePath.trim()) ||
      null;
    if (explicitPath && explicitPath.includes('/images/batches/batch_')) {
      return 10;
    }

    return 1;
  }, [activeSentenceIndex, batchSizeFromFiles, chunk?.sentences, promptPlanBatchSize]);

  // Resolve which batch a sentence belongs to
  const resolveBatchStartForSentence = useCallback(
    (sentenceNumber: number) => {
      const size = Math.max(1, Math.trunc(activeImageBatchSize));
      if (size <= 1) {
        return Math.max(1, Math.trunc(sentenceNumber));
      }
      const anchor = promptPlanSentenceRange?.start ?? minSentenceBound;
      const base = Math.max(1, Math.trunc(anchor));
      const current = Math.max(1, Math.trunc(sentenceNumber));
      const offset = Math.max(0, current - base);
      return base + Math.floor(offset / size) * size;
    },
    [activeImageBatchSize, minSentenceBound, promptPlanSentenceRange],
  );

  return {
    activeImageBatchSize,
    batchSizeFromFiles,
    batchStartCandidatesFromFiles,
    resolveBatchStartForSentence,
  };
}

/**
 * Extract prompt plan batch size from summary.
 */
export function extractPromptPlanBatchSize(summary: ImagePromptPlanSummary | null): number | null {
  if (!summary) {
    return null;
  }
  const quality = summary.quality;
  if (!quality || typeof quality !== 'object') {
    return null;
  }
  const raw = quality.prompt_batch_size ?? quality.promptBatchSize ?? null;
  const parsed = parseNumericValue(raw);
  if (parsed === null) {
    return null;
  }
  return Math.max(1, Math.trunc(parsed));
}

/**
 * Extract prompt plan sentence range from summary.
 */
export function extractPromptPlanSentenceRange(
  summary: ImagePromptPlanSummary | null
): { start: number; end: number } | null {
  if (!summary || typeof summary !== 'object') {
    return null;
  }
  const rawStart = summary.start_sentence ?? summary.startSentence ?? null;
  const rawEnd = summary.end_sentence ?? summary.endSentence ?? null;
  const startParsed = parseNumericValue(rawStart);
  const endParsed = parseNumericValue(rawEnd);
  if (startParsed === null || endParsed === null) {
    return null;
  }
  const start = Math.max(1, Math.trunc(startParsed));
  const end = Math.max(start, Math.trunc(endParsed));
  return { start, end };
}

export default useBatchSize;
