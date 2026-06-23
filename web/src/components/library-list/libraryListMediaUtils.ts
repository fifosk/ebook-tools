import type { LibraryItem } from '../../api/dtos';
import { appendAccessToken, resolveLibraryMediaUrl } from '../../api/client';
import { extractLibraryBookMetadata } from '../../utils/libraryMetadata';
import { SUBTITLE_AUTHOR, UNTITLED_SUBTITLE, resolveAuthor } from './libraryListUtils';

export type TvMediaMetadata = Record<string, unknown>;

export type SubtitleEpisodeParts = {
  code: string | null;
  title: string | null;
  airdate: string | null;
};

export type VideoSourceBadge = {
  icon: string;
  label: string;
  title: string;
};

function readNestedValue(source: unknown, path: string[]): unknown {
  let current: unknown = source;
  for (const key of path) {
    if (!current || typeof current !== 'object') {
      return null;
    }
    current = (current as Record<string, unknown>)[key];
  }
  return current;
}

function resolveLibraryAssetUrl(jobId: string, value: unknown): string | null {
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

export function resolveBookSummary(item: LibraryItem): string | null {
  const mediaMetadata = extractLibraryBookMetadata(item);
  if (!mediaMetadata) {
    return null;
  }
  const candidate = mediaMetadata['book_summary'] ?? mediaMetadata['summary'] ?? mediaMetadata['description'];
  if (typeof candidate !== 'string') {
    return null;
  }
  const trimmed = candidate.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function extractTvMediaMetadata(item: LibraryItem): TvMediaMetadata | null {
  const payload = item.metadata ?? null;
  if (!payload || typeof payload !== 'object') {
    return null;
  }
  const candidate =
    readNestedValue(payload, ['result', 'youtube_dub', 'media_metadata']) ??
    readNestedValue(payload, ['result', 'subtitle', 'metadata', 'media_metadata']) ??
    readNestedValue(payload, ['request', 'media_metadata']) ??
    readNestedValue(payload, ['media_metadata']) ??
    null;
  return candidate && typeof candidate === 'object' ? (candidate as TvMediaMetadata) : null;
}

export function resolveVideoSourcePill(item: LibraryItem): string | null {
  const payload = item.metadata ?? null;
  if (!payload || typeof payload !== 'object') {
    return null;
  }
  const raw =
    readNestedValue(payload, ['request', 'source_kind']) ??
    readNestedValue(payload, ['result', 'youtube_dub', 'source_kind']) ??
    readNestedValue(payload, ['source_kind']) ??
    null;
  if (typeof raw !== 'string') {
    return null;
  }
  const normalized = raw.trim().toLowerCase();
  if (!normalized) {
    return null;
  }
  if (normalized === 'youtube') {
    return 'YouTube';
  }
  if (normalized === 'nas_video') {
    return 'NAS';
  }
  return raw.trim();
}

export function videoSourceBadgeFromLabel(label: string): VideoSourceBadge {
  const normalized = label.trim().toLowerCase();
  if (normalized === 'youtube') {
    return { icon: '📺', label: 'YT', title: 'YouTube download' };
  }
  if (normalized === 'nas') {
    return { icon: '🗃', label: 'NAS', title: 'NAS video' };
  }
  return { icon: '📦', label, title: label };
}

export function resolveSubtitleShowName(item: LibraryItem, tvMetadata: TvMediaMetadata | null): string {
  const metadata = item.metadata ?? null;
  if (metadata && typeof metadata === 'object') {
    const seriesTitle = (metadata as Record<string, unknown>)['series_title'];
    if (typeof seriesTitle === 'string' && seriesTitle.trim()) {
      return seriesTitle.trim();
    }
  }
  const show = tvMetadata?.['show'];
  if (show && typeof show === 'object') {
    const name = (show as Record<string, unknown>)['name'];
    if (typeof name === 'string' && name.trim()) {
      return name.trim();
    }
  }
  const author = resolveAuthor(item);
  return author === SUBTITLE_AUTHOR ? UNTITLED_SUBTITLE : author;
}

export function resolveSubtitleEpisodeParts(
  item: LibraryItem,
  tvMetadata: TvMediaMetadata | null,
): SubtitleEpisodeParts {
  const metadata = item.metadata ?? null;
  const record = metadata && typeof metadata === 'object' ? (metadata as Record<string, unknown>) : null;
  const explicitCode = record && typeof record['episode_code'] === 'string' ? (record['episode_code'] as string).trim() : '';
  const explicitTitle = record && typeof record['episode_title'] === 'string' ? (record['episode_title'] as string).trim() : '';
  const explicitAirdate = record && typeof record['airdate'] === 'string' ? (record['airdate'] as string).trim() : '';

  const episode = tvMetadata?.['episode'];
  const episodeRecord = episode && typeof episode === 'object' ? (episode as Record<string, unknown>) : null;
  const season = episodeRecord?.['season'];
  const number = episodeRecord?.['number'];
  const computedCode =
    typeof season === 'number' && typeof number === 'number' && season > 0 && number > 0
      ? `S${season.toString().padStart(2, '0')}E${number.toString().padStart(2, '0')}`
      : null;
  const tvTitle = typeof episodeRecord?.['name'] === 'string' ? (episodeRecord['name'] as string).trim() : '';
  const tvAirdate = typeof episodeRecord?.['airdate'] === 'string' ? (episodeRecord['airdate'] as string).trim() : '';

  const code = explicitCode || computedCode || null;
  const title = explicitTitle || tvTitle || null;
  const airdate = explicitAirdate || tvAirdate || null;

  return { code, title, airdate };
}

export function resolveSubtitleSummary(tvMetadata: TvMediaMetadata | null): string | null {
  const episode = tvMetadata?.['episode'];
  if (episode && typeof episode === 'object') {
    const summary = (episode as Record<string, unknown>)['summary'];
    if (typeof summary === 'string' && summary.trim()) {
      return summary.trim();
    }
  }
  const show = tvMetadata?.['show'];
  if (show && typeof show === 'object') {
    const summary = (show as Record<string, unknown>)['summary'];
    if (typeof summary === 'string' && summary.trim()) {
      return summary.trim();
    }
  }
  return null;
}

export function resolveSubtitleGenres(item: LibraryItem, tvMetadata: TvMediaMetadata | null): string[] {
  const metadata = item.metadata ?? null;
  const record = metadata && typeof metadata === 'object' ? (metadata as Record<string, unknown>) : null;
  const fromMetadata = record?.['series_genres'];
  if (Array.isArray(fromMetadata)) {
    const filtered = fromMetadata.filter((entry) => typeof entry === 'string' && entry.trim()).map((entry) => entry.trim());
    if (filtered.length > 0) {
      return filtered.slice(0, 3);
    }
  }
  const show = tvMetadata?.['show'];
  if (show && typeof show === 'object') {
    const genres = (show as Record<string, unknown>)['genres'];
    if (Array.isArray(genres)) {
      const filtered = genres.filter((entry) => typeof entry === 'string' && entry.trim()).map((entry) => entry.trim());
      return filtered.slice(0, 3);
    }
  }
  return [];
}

export function resolveTvImage(
  jobId: string,
  tvMetadata: TvMediaMetadata | null,
  path: 'show' | 'episode',
): string | null {
  const section = tvMetadata?.[path];
  if (!section || typeof section !== 'object') {
    return null;
  }
  const image = (section as Record<string, unknown>)['image'];
  if (!image) {
    return null;
  }
  if (typeof image === 'string') {
    return resolveLibraryAssetUrl(jobId, image);
  }
  if (typeof image === 'object') {
    const record = image as Record<string, unknown>;
    return (
      resolveLibraryAssetUrl(jobId, record['medium']) ??
      resolveLibraryAssetUrl(jobId, record['original']) ??
      null
    );
  }
  return null;
}

export function extractYoutubeVideoMetadata(tvMetadata: TvMediaMetadata | null): TvMediaMetadata | null {
  const youtube = tvMetadata?.['youtube'];
  return youtube && typeof youtube === 'object' && !Array.isArray(youtube) ? (youtube as TvMediaMetadata) : null;
}

export function resolveYoutubeThumbnail(jobId: string, youtubeMetadata: TvMediaMetadata | null): string | null {
  if (!youtubeMetadata) {
    return null;
  }
  return resolveLibraryAssetUrl(jobId, youtubeMetadata['thumbnail']);
}

export function resolveYoutubeTitle(youtubeMetadata: TvMediaMetadata | null): string | null {
  if (!youtubeMetadata) {
    return null;
  }
  const title = youtubeMetadata['title'];
  return typeof title === 'string' && title.trim() ? title.trim() : null;
}

export function resolveYoutubeChannel(youtubeMetadata: TvMediaMetadata | null): string | null {
  if (!youtubeMetadata) {
    return null;
  }
  const channel = youtubeMetadata['channel'];
  if (typeof channel === 'string' && channel.trim()) {
    return channel.trim();
  }
  const uploader = youtubeMetadata['uploader'];
  return typeof uploader === 'string' && uploader.trim() ? uploader.trim() : null;
}

export function resolveYoutubeSummary(youtubeMetadata: TvMediaMetadata | null): string | null {
  if (!youtubeMetadata) {
    return null;
  }
  const summary = youtubeMetadata['summary'];
  if (typeof summary === 'string' && summary.trim()) {
    return summary.trim();
  }
  const description = youtubeMetadata['description'];
  return typeof description === 'string' && description.trim() ? description.trim() : null;
}
