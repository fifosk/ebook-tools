import type { LibraryItem } from '../../api/dtos';
import { appendAccessToken } from '../../api/client/base';
import { resolveLibraryMediaUrl } from '../../api/client/library';

export type LibraryItemType = 'book' | 'video' | 'narrated_subtitle';
export type LibraryEditValues = {
  title: string;
  author: string;
  genre: string;
  language: string;
  isbn: string;
};

const UNKNOWN_AUTHOR = 'Unknown Author';
const UNKNOWN_CREATOR = 'Unknown Creator';
const UNKNOWN_GENRE = 'Unknown Genre';
const UNTITLED_BOOK = 'Untitled Book';
const UNTITLED_VIDEO = 'Untitled Video';
const UNTITLED_SUBTITLE = 'Untitled Subtitle';
const SUBTITLE_AUTHOR = 'Subtitles';

export function resolveItemType(item: LibraryItem | null | undefined): LibraryItemType {
  return (item?.itemType ?? 'book') as LibraryItemType;
}

export function readNestedValue(source: unknown, path: string[]): unknown {
  let current: unknown = source;
  for (const key of path) {
    if (!current || typeof current !== 'object') {
      return null;
    }
    current = (current as Record<string, unknown>)[key];
  }
  return current;
}

export function resolveLibraryAssetUrl(jobId: string, value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (/^[a-z]+:\/\//i.test(trimmed)) {
    return trimmed;
  }
  if (trimmed.startsWith('/api/')) {
    return appendAccessToken(trimmed);
  }
  if (trimmed.startsWith('/')) {
    return trimmed;
  }
  return resolveLibraryMediaUrl(jobId, trimmed);
}

export function extractTvMediaMetadata(item: LibraryItem | null | undefined): Record<string, unknown> | null {
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
  return candidate && typeof candidate === 'object' ? (candidate as Record<string, unknown>) : null;
}

export function extractYoutubeVideoMetadata(mediaMetadata: Record<string, unknown> | null): Record<string, unknown> | null {
  const youtube = mediaMetadata?.['youtube'];
  return youtube && typeof youtube === 'object' && !Array.isArray(youtube) ? (youtube as Record<string, unknown>) : null;
}

export function resolveTvImage(
  jobId: string,
  tvMetadata: Record<string, unknown> | null,
  path: 'show' | 'episode',
): { src: string; link: string } | null {
  const section = tvMetadata?.[path];
  if (!section || typeof section !== 'object') {
    return null;
  }
  const image = (section as Record<string, unknown>)['image'];
  if (!image) {
    return null;
  }
  if (typeof image === 'string') {
    const url = resolveLibraryAssetUrl(jobId, image);
    return url ? { src: url, link: url } : null;
  }
  if (typeof image === 'object') {
    const record = image as Record<string, unknown>;
    const src =
      resolveLibraryAssetUrl(jobId, record['medium']) ??
      resolveLibraryAssetUrl(jobId, record['original']) ??
      null;
    const link =
      resolveLibraryAssetUrl(jobId, record['original']) ??
      resolveLibraryAssetUrl(jobId, record['medium']) ??
      null;
    if (src && link) {
      return { src, link };
    }
    if (src) {
      return { src, link: src };
    }
  }
  return null;
}

export function resolveYoutubeThumbnail(
  jobId: string,
  youtubeMetadata: Record<string, unknown> | null,
): { src: string; link: string } | null {
  if (!youtubeMetadata) {
    return null;
  }
  const thumbnail = resolveLibraryAssetUrl(jobId, youtubeMetadata['thumbnail']);
  if (!thumbnail) {
    return null;
  }
  const link = resolveLibraryAssetUrl(jobId, youtubeMetadata['webpage_url']) ?? thumbnail;
  return { src: thumbnail, link };
}

export function formatCount(value: unknown): string | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return null;
  }
  try {
    return new Intl.NumberFormat().format(Math.trunc(value));
  } catch {
    return `${Math.trunc(value)}`;
  }
}

export function formatYoutubeUploadDate(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (/^\d{8}$/.test(trimmed)) {
    return `${trimmed.slice(0, 4)}-${trimmed.slice(4, 6)}-${trimmed.slice(6, 8)}`;
  }
  return trimmed;
}

function trimmedMetadataString(metadata: Record<string, unknown>, key: string): string | null {
  const value = metadata[key];
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function mergeIsbnMetadataIntoEditValues(
  previous: LibraryEditValues,
  metadata: Record<string, unknown>,
  fallbackIsbn: string,
): LibraryEditValues {
  return {
    ...previous,
    title: trimmedMetadataString(metadata, 'book_title') ?? previous.title,
    author: trimmedMetadataString(metadata, 'book_author') ?? previous.author,
    genre: trimmedMetadataString(metadata, 'book_genre') ?? previous.genre,
    language: trimmedMetadataString(metadata, 'book_language') ?? previous.language,
    isbn: previous.isbn || fallbackIsbn,
  };
}

export function resolveIsbnPreviewCoverCandidate(metadata: Record<string, unknown>): string | null {
  return trimmedMetadataString(metadata, 'book_cover_file') ?? trimmedMetadataString(metadata, 'cover_url');
}

export function resolveTitle(item: LibraryItem | null | undefined): string {
  const candidate = item?.bookTitle?.trim() ?? '';
  if (candidate) {
    return candidate;
  }
  switch (resolveItemType(item)) {
    case 'video':
      return UNTITLED_VIDEO;
    case 'narrated_subtitle':
      return UNTITLED_SUBTITLE;
    default:
      return UNTITLED_BOOK;
  }
}

export function resolveAuthor(item: LibraryItem | null | undefined): string {
  const candidate = item?.author?.trim() ?? '';
  if (candidate) {
    return candidate;
  }
  switch (resolveItemType(item)) {
    case 'video':
      return UNKNOWN_CREATOR;
    case 'narrated_subtitle':
      return SUBTITLE_AUTHOR;
    default:
      return UNKNOWN_AUTHOR;
  }
}

export function resolveGenre(item: LibraryItem | null | undefined): string {
  const candidate = item?.genre?.toString().trim() ?? '';
  if (candidate) {
    return candidate;
  }
  switch (resolveItemType(item)) {
    case 'video':
      return 'Video';
    case 'narrated_subtitle':
      return 'Subtitles';
    default:
      return UNKNOWN_GENRE;
  }
}
