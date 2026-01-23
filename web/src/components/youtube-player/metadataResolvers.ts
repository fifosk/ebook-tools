/**
 * Metadata resolver functions for YouTube video metadata
 * Extracts and formats metadata from various sources (job results, library items, TV metadata)
 */

import { appendAccessToken, resolveLibraryMediaUrl } from '../../api/client';
import { extractMetadataFirstString, extractMetadataText } from '../player-panel/helpers';
import { coerceRecord, readNestedValue, readStringValue } from './utils';
import type { LibraryItem } from '../../api/dtos';

/** Maximum length for summary text before truncation */
const SUMMARY_LENGTH_LIMIT = 320;

/**
 * Extract source and translation languages from job result
 * Checks multiple possible field names for compatibility
 */
export function extractLanguagesFromResult(result: unknown): {
  original: string | null;
  translation: string | null;
} {
  const record = coerceRecord(result);
  if (!record) {
    return { original: null, translation: null };
  }

  // Try youtube_dub payload first
  const dubPayload = coerceRecord(record['youtube_dub']);
  const dubOriginal =
    readStringValue(dubPayload, 'source_language') ??
    readStringValue(dubPayload, 'translation_source_language') ??
    readStringValue(dubPayload, 'source');
  const dubTranslation =
    readStringValue(dubPayload, 'language') ??
    readStringValue(dubPayload, 'target_language') ??
    readStringValue(dubPayload, 'translation_language');

  // Fallback to book_metadata
  const bookMetadata = coerceRecord(record['book_metadata']);
  const metadataOriginal =
    extractMetadataText(bookMetadata, [
      'input_language',
      'original_language',
      'source_language',
      'translation_source_language',
      'language',
      'lang',
    ]) ?? null;
  const metadataTranslation =
    extractMetadataFirstString(bookMetadata, [
      'target_language',
      'translation_language',
      'target_languages',
    ]) ?? null;

  return {
    original: dubOriginal ?? metadataOriginal,
    translation: dubTranslation ?? metadataTranslation,
  };
}

/**
 * Resolve a library asset URL, handling relative paths and API paths
 * @param jobId - Job ID for resolving relative paths
 * @param value - URL or path to resolve
 */
export function resolveLibraryAssetUrl(jobId: string, value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  // Already absolute URL
  if (/^[a-z]+:\/\//i.test(trimmed)) {
    return trimmed;
  }

  // API path needs auth token
  if (trimmed.startsWith('/api/')) {
    return appendAccessToken(trimmed);
  }

  // Absolute path on server
  if (trimmed.startsWith('/')) {
    return trimmed;
  }

  // Relative path - resolve via library URL
  return resolveLibraryMediaUrl(jobId, trimmed);
}

/**
 * Extract TV media metadata from a library item
 * Searches multiple possible locations in the item metadata
 */
export function extractTvMediaMetadataFromLibrary(
  item: LibraryItem | null | undefined
): Record<string, unknown> | null {
  const payload = item?.metadata ?? null;
  if (!payload || typeof payload !== 'object') {
    return null;
  }

  const candidate =
    readNestedValue(payload, ['result', 'youtube_dub', 'media_metadata']) ??
    readNestedValue(payload, ['result', 'subtitle', 'metadata', 'media_metadata']) ??
    readNestedValue(payload, ['request', 'media_metadata']) ??
    readNestedValue(payload, ['media_metadata']) ??
    null;

  return coerceRecord(candidate);
}

/**
 * Extract TV media metadata from a job result payload
 * Similar to extractTvMediaMetadataFromLibrary but for raw payloads
 */
export function extractTvMediaMetadataFromPayload(
  payload: Record<string, unknown> | null
): Record<string, unknown> | null {
  if (!payload) {
    return null;
  }

  const candidate =
    readNestedValue(payload, ['result', 'youtube_dub', 'media_metadata']) ??
    readNestedValue(payload, ['result', 'subtitle', 'metadata', 'media_metadata']) ??
    readNestedValue(payload, ['request', 'media_metadata']) ??
    readNestedValue(payload, ['media_metadata']) ??
    null;

  return coerceRecord(candidate);
}

/**
 * Resolve a TV show or episode image URL
 * @param jobId - Job ID for URL resolution
 * @param tvMetadata - TV metadata object
 * @param path - 'show' or 'episode'
 * @param resolver - Function to resolve the final URL
 */
export function resolveTvImage(
  jobId: string,
  tvMetadata: Record<string, unknown> | null,
  path: 'show' | 'episode',
  resolver: (jobId: string, value: unknown) => string | null
): string | null {
  const section = coerceRecord(tvMetadata?.[path]);
  if (!section) {
    return null;
  }

  const image = section['image'];
  if (!image) {
    return null;
  }

  // Direct string URL
  if (typeof image === 'string') {
    return resolver(jobId, image);
  }

  // Object with medium/original quality options
  const record = coerceRecord(image);
  if (!record) {
    return null;
  }

  return resolver(jobId, record['medium']) ?? resolver(jobId, record['original']);
}

/**
 * Extract YouTube video metadata from TV metadata object
 */
export function extractYoutubeVideoMetadataFromTv(
  tvMetadata: Record<string, unknown> | null
): Record<string, unknown> | null {
  return coerceRecord(tvMetadata?.['youtube']);
}

/**
 * Resolve YouTube video thumbnail URL
 */
export function resolveYoutubeThumbnail(
  jobId: string,
  youtubeMetadata: Record<string, unknown> | null,
  resolver: (jobId: string, value: unknown) => string | null
): string | null {
  if (!youtubeMetadata) {
    return null;
  }
  return resolver(jobId, youtubeMetadata['thumbnail']);
}

/**
 * Get YouTube video title from metadata
 */
export function resolveYoutubeTitle(youtubeMetadata: Record<string, unknown> | null): string | null {
  const title = youtubeMetadata?.['title'];
  return typeof title === 'string' && title.trim() ? title.trim() : null;
}

/**
 * Get YouTube channel name from metadata
 * Falls back to uploader if channel is not available
 */
export function resolveYoutubeChannel(
  youtubeMetadata: Record<string, unknown> | null
): string | null {
  const channel = youtubeMetadata?.['channel'];
  if (typeof channel === 'string' && channel.trim()) {
    return channel.trim();
  }

  const uploader = youtubeMetadata?.['uploader'];
  return typeof uploader === 'string' && uploader.trim() ? uploader.trim() : null;
}

/**
 * Normalize summary text: strip HTML, limit length, trim whitespace
 * @param value - Raw summary text
 * @returns Cleaned summary text or null
 */
export function normaliseSummary(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }

  let text = value.trim();
  if (!text) {
    return null;
  }

  // Strip HTML tags
  text = text.replace(/<[^>]+>/g, ' ');

  // Normalize whitespace
  text = text.replace(/\s+/g, ' ').trim();
  if (!text) {
    return null;
  }

  // Truncate if too long
  if (text.length > SUMMARY_LENGTH_LIMIT) {
    const cutoff = Math.max(SUMMARY_LENGTH_LIMIT - 3, 0);
    text = `${text.slice(0, cutoff).trim()}...`;
  }

  return text;
}

/**
 * Get YouTube video summary/description
 */
export function resolveYoutubeSummary(
  youtubeMetadata: Record<string, unknown> | null
): string | null {
  if (!youtubeMetadata) {
    return null;
  }
  return normaliseSummary(youtubeMetadata['summary'] ?? youtubeMetadata['description']);
}

/**
 * Get TV episode or show summary
 * Prefers episode summary, falls back to show summary
 */
export function resolveTvSummary(tvMetadata: Record<string, unknown> | null): string | null {
  if (!tvMetadata) {
    return null;
  }

  const episode = coerceRecord(tvMetadata['episode']);
  const episodeSummary = normaliseSummary(episode?.['summary']);
  if (episodeSummary) {
    return episodeSummary;
  }

  const show = coerceRecord(tvMetadata['show']);
  return normaliseSummary(show?.['summary']);
}

/**
 * Format TV episode label (e.g., "S01E05 - Episode Name" or "Episode Name")
 * Only returns value for TV episodes (not movies)
 */
export function formatTvEpisodeLabel(tvMetadata: Record<string, unknown> | null): string | null {
  const kind =
    typeof tvMetadata?.['kind'] === 'string'
      ? (tvMetadata?.['kind'] as string).trim().toLowerCase()
      : '';

  if (kind !== 'tv_episode') {
    return null;
  }

  const episode = coerceRecord(tvMetadata?.['episode']);
  const season = episode?.['season'];
  const number = episode?.['number'];
  const episodeName =
    typeof episode?.['name'] === 'string' && episode.name.trim() ? episode.name.trim() : null;

  const code =
    typeof season === 'number' && typeof number === 'number'
      ? `S${String(season).padStart(2, '0')}E${String(number).padStart(2, '0')}`
      : null;

  if (code && episodeName) {
    return `${code} - ${episodeName}`;
  }

  return episodeName ?? code;
}
