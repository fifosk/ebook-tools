/**
 * Hook for computing video player info badge data (title, cover, metadata).
 */

import { useMemo } from 'react';
import { appendAccessToken } from '../../api/client';
import type { LibraryItem } from '../../api/dtos';
import type { LiveMediaItem } from '../../hooks/useLiveMedia';
import {
  coerceRecord,
} from './utils';
import {
  resolveLibraryAssetUrl,
  extractTvMediaMetadataFromLibrary,
  extractYoutubeVideoMetadataFromTv,
  resolveTvImage,
  resolveYoutubeThumbnail,
  resolveYoutubeTitle,
  resolveYoutubeChannel,
  resolveYoutubeSummary,
  resolveTvSummary,
  formatTvEpisodeLabel,
} from './metadataResolvers';
import { createJobMediaResolver } from './mediaHelpers';

export interface InfoBadgeData {
  title: string | null;
  meta: string | null;
  coverUrl: string | null;
  coverAltText: string;
  coverSecondaryUrl: string | null;
  glyph: string;
  glyphLabel: string;
  summary: string | null;
}

export interface UseInfoBadgeOptions {
  jobId: string;
  activeVideoId: string | null;
  videoFiles: Array<{ id: string; name?: string }>;
  libraryItem?: LibraryItem | null;
  resolvedJobType: string | null;
  /** TV metadata from job API */
  jobTvMetadata: Record<string, unknown> | null;
  /** YouTube metadata from job API */
  jobYoutubeMetadata: Record<string, unknown> | null;
  /** TV metadata from export payload */
  exportTvMetadata: Record<string, unknown> | null;
  /** YouTube metadata from export payload */
  exportYoutubeMetadata: Record<string, unknown> | null;
}

export function useInfoBadge({
  jobId,
  activeVideoId,
  videoFiles,
  libraryItem = null,
  resolvedJobType,
  jobTvMetadata,
  jobYoutubeMetadata,
  exportTvMetadata,
  exportYoutubeMetadata,
}: UseInfoBadgeOptions): InfoBadgeData {
  return useMemo(() => {
    const isLibrary = Boolean(libraryItem);
    const resolver = isLibrary ? resolveLibraryAssetUrl : createJobMediaResolver(appendAccessToken);

    // Resolve TV metadata from various sources
    const tvMetadata = isLibrary
      ? extractTvMediaMetadataFromLibrary(libraryItem)
      : jobTvMetadata ?? exportTvMetadata;
    const kind = typeof tvMetadata?.['kind'] === 'string' ? (tvMetadata.kind as string).trim().toLowerCase() : '';
    const youtubeFromTv = extractYoutubeVideoMetadataFromTv(tvMetadata);
    const youtubeMetadata = isLibrary
      ? youtubeFromTv
      : jobYoutubeMetadata ?? exportYoutubeMetadata ?? youtubeFromTv;

    // Resolve cover images
    const episodeCoverUrl = resolveTvImage(jobId, tvMetadata, 'episode', resolver);
    const showCoverUrl = resolveTvImage(jobId, tvMetadata, 'show', resolver);
    const youtubeThumbnailUrl = resolveYoutubeThumbnail(jobId, youtubeMetadata, resolver);

    const coverFromLibrary =
      isLibrary && libraryItem?.coverPath ? resolver(jobId, libraryItem.coverPath) : null;
    const coverUrl =
      coverFromLibrary ??
      episodeCoverUrl ??
      showCoverUrl ??
      youtubeThumbnailUrl ??
      null;
    const coverSecondaryUrl =
      kind === 'tv_episode' && showCoverUrl && coverUrl && coverUrl !== showCoverUrl ? showCoverUrl : null;

    // Resolve title
    const titleFromLibrary =
      typeof libraryItem?.bookTitle === 'string' && libraryItem.bookTitle.trim() ? libraryItem.bookTitle.trim() : null;
    const title =
      titleFromLibrary ??
      resolveYoutubeTitle(youtubeMetadata) ??
      formatTvEpisodeLabel(tvMetadata) ??
      (() => {
        const active = activeVideoId ? videoFiles.find((file) => file.id === activeVideoId) ?? null : null;
        const fallback = active ?? videoFiles[0] ?? null;
        return fallback?.name ?? null;
      })() ??
      null;

    // Resolve glyph and label
    const jobTypeValue = (resolvedJobType ?? '').trim().toLowerCase();
    const hasYoutubeJobType = jobTypeValue.includes('youtube');
    const isYoutubeVideo = Boolean(youtubeMetadata) || hasYoutubeJobType;
    const isTvSeries = kind === 'tv_episode' || Boolean(tvMetadata?.['show'] || tvMetadata?.['episode']);
    const glyph = isTvSeries ? 'TV' : isYoutubeVideo ? 'YT' : !isLibrary ? 'DUB' : 'NAS';
    const glyphLabel = isTvSeries
      ? 'TV episode'
      : isYoutubeVideo
        ? 'YouTube video'
        : !isLibrary
          ? 'Dubbed video'
          : 'NAS video';

    // Resolve metadata line
    const metaParts: string[] = [];
    const authorFromLibrary =
      typeof libraryItem?.author === 'string' && libraryItem.author.trim() ? libraryItem.author.trim() : null;
    const genreFromLibrary =
      typeof libraryItem?.genre === 'string' && libraryItem.genre.trim() ? libraryItem.genre.trim() : null;
    if (authorFromLibrary) {
      metaParts.push(authorFromLibrary);
    } else {
      const channel = resolveYoutubeChannel(youtubeMetadata);
      if (channel) {
        metaParts.push(channel);
      } else {
        const show = coerceRecord(tvMetadata?.['show']);
        const showName = typeof show?.['name'] === 'string' && show.name.trim() ? show.name.trim() : null;
        if (showName) {
          metaParts.push(showName);
        }
      }
    }
    if (genreFromLibrary) {
      metaParts.push(genreFromLibrary);
    } else {
      if (kind === 'tv_episode') {
        metaParts.push('TV');
      } else if (youtubeMetadata) {
        metaParts.push('YouTube');
      }
    }
    const meta = metaParts.filter(Boolean).join(' · ') || null;
    const summary = resolveYoutubeSummary(youtubeMetadata) ?? resolveTvSummary(tvMetadata) ?? null;

    return {
      title,
      meta,
      coverUrl,
      coverAltText: title ? `Cover for ${title}` : 'Cover',
      coverSecondaryUrl,
      glyph,
      glyphLabel,
      summary,
    };
  }, [
    activeVideoId,
    exportTvMetadata,
    exportYoutubeMetadata,
    jobId,
    jobTvMetadata,
    jobYoutubeMetadata,
    libraryItem,
    resolvedJobType,
    videoFiles,
  ]);
}
