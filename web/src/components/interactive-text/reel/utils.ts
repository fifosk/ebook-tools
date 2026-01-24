import type { ExportPlayerManifest } from '../../../types/exportPlayer';

/**
 * Get the export manifest from window.__EXPORT_DATA__ if available.
 */
export function getExportManifest(): ExportPlayerManifest | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const candidate = (window as Window & { __EXPORT_DATA__?: unknown }).__EXPORT_DATA__;
  if (!candidate || typeof candidate !== 'object') {
    return null;
  }
  return candidate as ExportPlayerManifest;
}

/**
 * Parse batch start sentence number from a batch image path.
 * @example "media/images/batches/batch_00001.png" => 1
 */
export function parseBatchStartFromBatchImagePath(path: string | null): number | null {
  const candidate = (path ?? '').trim();
  if (!candidate) {
    return null;
  }
  const normalised = candidate.replace(/\\+/g, '/');
  const base = normalised.split('?')[0].split('#')[0];
  const match = base.match(/batch_(\d+)\.png$/i);
  if (!match) {
    return null;
  }
  const parsed = Number(match[1]);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return Math.max(1, Math.trunc(parsed));
}

/**
 * Infer batch size from a list of batch start sentence numbers.
 * Returns the most common difference between consecutive starts.
 */
export function inferBatchSizeFromStarts(starts: number[]): number | null {
  if (starts.length < 2) {
    return null;
  }
  const counts = new Map<number, number>();
  let bestSize: number | null = null;
  let bestCount = 0;
  for (let index = 1; index < starts.length; index += 1) {
    const diff = starts[index] - starts[index - 1];
    if (!Number.isFinite(diff) || diff <= 0) {
      continue;
    }
    const nextCount = (counts.get(diff) ?? 0) + 1;
    counts.set(diff, nextCount);
    if (nextCount > bestCount || (nextCount === bestCount && (bestSize === null || diff < bestSize))) {
      bestSize = diff;
      bestCount = nextCount;
    }
  }
  return bestSize;
}

/**
 * Check if a path looks like a batch image path.
 */
export function isBatchImagePath(value: string | null): boolean {
  if (!value) {
    return false;
  }
  return parseBatchStartFromBatchImagePath(value) !== null || value.includes('/images/batches/batch_');
}

/**
 * Normalize a number to a valid sentence number (at least 1, integer).
 */
export function normalizeSentenceNumber(value: unknown): number | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return null;
  }
  return Math.max(1, Math.trunc(value));
}

/**
 * Parse a numeric value from various possible formats.
 */
export function parseNumericValue(raw: unknown): number | null {
  if (typeof raw === 'number' && Number.isFinite(raw)) {
    return raw;
  }
  if (typeof raw === 'string') {
    const parsed = Number(raw);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return null;
}
