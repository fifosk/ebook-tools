/**
 * Pre-built sentence-to-chunk mapping for O(1) lookups.
 *
 * Replaces repeated linear scans in useChunkPrefetch and useSentenceNavigation
 * with a single mapping built once when chunks change.
 */

import type { LiveMediaChunk } from '../../hooks/useLiveMedia';

export interface SentenceChunkEntry {
  /** Index of the chunk in the chunks array */
  chunkIndex: number;
  /** Local index of this sentence within the chunk (null if resolved from range) */
  localIndex: number | null;
  /** Total sentences in this chunk (null if unknown) */
  total: number | null;
  /** Chunk key (chunkId, rangeFragment, etc.) */
  chunkKey: string | null;
}

export interface SentenceChunkIndex {
  /** O(1) lookup: sentence number -> chunk entry */
  readonly map: ReadonlyMap<number, SentenceChunkEntry>;
  /** Sorted ranges for fallback when exact map has no entry */
  readonly ranges: readonly SentenceRange[];
  /** Smallest known sentence number */
  readonly min: number | null;
  /** Largest known sentence number */
  readonly max: number | null;
}

export interface SentenceRange {
  start: number;
  end: number;
  chunkIndex: number;
  chunkKey: string | null;
}

/**
 * Derive a stable identity key from a chunk (same logic as resolveChunkKey
 * but inlined to avoid circular dependency).
 */
function chunkKey(chunk: LiveMediaChunk): string | null {
  return (
    chunk.chunkId ??
    chunk.rangeFragment ??
    chunk.metadataPath ??
    chunk.metadataUrl ??
    null
  );
}

/**
 * Build a sentence-to-chunk index from the chunks array.
 *
 * Two data sources per chunk:
 *  1. `chunk.sentences[]` — exact sentence numbers with local indices
 *  2. `chunk.startSentence` / `chunk.endSentence` — range bounds
 *
 * When sentences are available, they populate the exact map.
 * Ranges are always recorded for fallback.
 */
export function buildSentenceChunkIndex(chunks: readonly LiveMediaChunk[]): SentenceChunkIndex {
  const map = new Map<number, SentenceChunkEntry>();
  const ranges: SentenceRange[] = [];
  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;

  for (let chunkIndex = 0; chunkIndex < chunks.length; chunkIndex++) {
    const chunk = chunks[chunkIndex];
    const key = chunkKey(chunk);

    // Record range from startSentence/endSentence
    const start = typeof chunk.startSentence === 'number' && Number.isFinite(chunk.startSentence)
      ? Math.trunc(chunk.startSentence)
      : null;
    let end = typeof chunk.endSentence === 'number' && Number.isFinite(chunk.endSentence)
      ? Math.trunc(chunk.endSentence)
      : null;

    // Infer end from sentenceCount if missing
    if (start !== null && end === null) {
      const count = typeof chunk.sentenceCount === 'number' && Number.isFinite(chunk.sentenceCount)
        ? Math.trunc(chunk.sentenceCount)
        : null;
      if (count !== null && count > 0) {
        end = start + count - 1;
      }
    }

    if (start !== null && end !== null && end >= start) {
      ranges.push({ start, end, chunkIndex, chunkKey: key });
      if (start < min) min = start;
      if (end > max) max = end;
    }

    // Record exact entries from sentences array
    if (Array.isArray(chunk.sentences) && chunk.sentences.length > 0) {
      const total = chunk.sentences.length;
      for (let localIndex = 0; localIndex < chunk.sentences.length; localIndex++) {
        const sentence = chunk.sentences[localIndex];
        if (!sentence) continue;
        const num = typeof sentence.sentence_number === 'number' && Number.isFinite(sentence.sentence_number)
          ? Math.trunc(sentence.sentence_number)
          : null;
        if (num === null) continue;
        if (num < min) min = num;
        if (num > max) max = num;
        // Exact entry takes priority — don't overwrite with a later chunk
        if (!map.has(num)) {
          map.set(num, { chunkIndex, localIndex, total, chunkKey: key });
        }
      }
    }
  }

  // Sort ranges by start for binary search
  ranges.sort((a, b) => a.start - b.start);

  const safeMin = Number.isFinite(min) ? min : null;
  const safeMax = Number.isFinite(max) ? max : null;

  return { map, ranges, min: safeMin, max: safeMax };
}

/**
 * Look up which chunk contains a given sentence number.
 *
 * Tries exact map first (O(1)), then searches known ranges.
 * Range lookup deliberately tolerates overlaps from legacy or partial metadata
 * and picks the earliest source chunk that contains the target sentence.
 */
export function lookupSentence(
  index: SentenceChunkIndex,
  sentenceNumber: number,
): SentenceChunkEntry | null {
  if (!Number.isFinite(sentenceNumber)) return null;
  const target = Math.trunc(sentenceNumber);

  // Exact lookup
  const exact = index.map.get(target);
  if (exact) return exact;

  // Find the last range whose start is <= target, then scan the eligible prefix.
  // A plain interval binary search is only valid for non-overlapping ranges; a
  // broad earlier chunk like 1-100 followed by 20-30 can otherwise hide valid
  // matches when looking up sentence 35.
  const { ranges } = index;
  let lo = 0;
  let hi = ranges.length - 1;
  let lastEligible = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >>> 1;
    const range = ranges[mid];
    if (target < range.start) {
      hi = mid - 1;
    } else {
      lastEligible = mid;
      lo = mid + 1;
    }
  }

  let best: SentenceRange | null = null;
  for (let index = 0; index <= lastEligible; index++) {
    const range = ranges[index];
    if (target > range.end) continue;
    if (!best || range.chunkIndex < best.chunkIndex) {
      best = range;
    }
  }

  if (best) {
    return {
      chunkIndex: best.chunkIndex,
      localIndex: null,
      total: null,
      chunkKey: best.chunkKey,
    };
  }

  return null;
}

/**
 * Find the chunk object for a given sentence number.
 *
 * Convenience wrapper that returns the LiveMediaChunk from the chunks array.
 */
export function findChunkBySentence(
  index: SentenceChunkIndex,
  chunks: readonly LiveMediaChunk[],
  sentenceNumber: number,
): LiveMediaChunk | null {
  const entry = lookupSentence(index, sentenceNumber);
  if (!entry) return null;
  return chunks[entry.chunkIndex] ?? null;
}
