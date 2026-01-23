/**
 * Subtitle-related helper functions for YouTube Player
 * Pure functions for subtitle URL resolution, data URL creation, and path normalization
 */

/**
 * Normalize an inline subtitle key by converting backslashes to forward slashes,
 * removing leading slashes, and decoding URI components
 * @example normalizeInlineSubtitleKey("./subtitles\\file.vtt") // "subtitles/file.vtt"
 */
export function normalizeInlineSubtitleKey(value: string): string {
  const trimmed = value.trim().replace(/\\+/g, '/');
  const pathOnly = trimmed.split(/[?#]/)[0] ?? trimmed;
  let normalized = pathOnly.replace(/^\.?\//, '');
  try {
    normalized = decodeURIComponent(normalized);
  } catch {
    // Keep normalized as-is when decoding fails
  }
  return normalized;
}

/**
 * Resolve inline subtitle payload from a map of subtitles
 * Tries both the normalized key and the key without leading slashes
 */
export function resolveInlineSubtitlePayload(
  value: string,
  inlineSubtitles: Record<string, string> | null
): string | null {
  if (!inlineSubtitles) {
    return null;
  }
  const normalized = normalizeInlineSubtitleKey(value);
  return inlineSubtitles[normalized] ?? inlineSubtitles[normalized.replace(/^\/+/, '')] ?? null;
}

/**
 * Build a data URL for subtitle content with the appropriate MIME type
 * @example buildSubtitleDataUrl("WEBVTT\n\n1\n00:00:01.000", "vtt") // "data:text/vtt;charset=utf-8,..."
 */
export function buildSubtitleDataUrl(payload: string, format?: string | null): string {
  const normalizedFormat = (format ?? '').toLowerCase();
  const mime = normalizedFormat === 'vtt' ? 'text/vtt' : 'text/plain';
  return `data:${mime};charset=utf-8,${encodeURIComponent(payload)}`;
}

/**
 * Extract file extension/suffix from a URL or path
 * Handles query parameters and hash fragments
 * @example extractFileSuffix("/path/to/file.vtt?token=abc#t=10") // "vtt"
 */
export function extractFileSuffix(value: string | null | undefined): string {
  if (!value) {
    return '';
  }
  const cleaned = value.split(/[?#]/)[0] ?? '';
  const leaf = cleaned.split('/').pop() ?? cleaned;
  const parts = leaf.split('.');
  if (parts.length <= 1) {
    return '';
  }
  return parts.pop()?.toLowerCase() ?? '';
}
