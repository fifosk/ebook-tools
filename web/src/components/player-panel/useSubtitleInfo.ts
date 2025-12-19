import { useEffect, useMemo, useState } from 'react';
import type { LibraryItem, SubtitleTvMetadataResponse } from '../../api/dtos';
import { fetchSubtitleTvMetadata } from '../../api/client';
import {
  coerceRecord,
  extractTvMediaMetadataFromLibrary,
  normaliseMetadataText,
  resolveJobAssetUrl,
  resolveLibraryAssetUrl,
  resolveTvMetadataImage,
} from './helpers';

type SubtitleInfo = {
  title: string | null;
  meta: string | null;
  coverUrl: string | null;
  coverSecondaryUrl: string | null;
  coverAltText: string | null;
};

type UseSubtitleInfoArgs = {
  jobId: string | null;
  jobType?: string | null;
  itemType?: 'book' | 'video' | 'narrated_subtitle' | null;
  origin?: 'job' | 'library';
  libraryItem?: LibraryItem | null;
};

export function useSubtitleInfo({
  jobId,
  jobType = null,
  itemType = null,
  origin = 'job',
  libraryItem = null,
}: UseSubtitleInfoArgs): { isSubtitleContext: boolean; subtitleInfo: SubtitleInfo } {
  const isSubtitleContext = useMemo(() => {
    if (itemType === 'narrated_subtitle') {
      return true;
    }
    const normalized = (jobType ?? '').trim().toLowerCase();
    return normalized === 'subtitle' || normalized.includes('subtitle');
  }, [itemType, jobType]);

  const libraryTvMediaMetadata = useMemo(() => {
    if (!isSubtitleContext || origin !== 'library') {
      return null;
    }
    return extractTvMediaMetadataFromLibrary(libraryItem);
  }, [isSubtitleContext, libraryItem, origin]);

  const [subtitleTvMetadata, setSubtitleTvMetadata] = useState<SubtitleTvMetadataResponse | null>(null);
  useEffect(() => {
    let cancelled = false;
    if (!isSubtitleContext) {
      setSubtitleTvMetadata(null);
      return () => {
        cancelled = true;
      };
    }
    if (origin === 'library' && libraryTvMediaMetadata) {
      return () => {
        cancelled = true;
      };
    }
    const jobIdValue = jobId ?? '';
    if (!jobIdValue) {
      setSubtitleTvMetadata(null);
      return () => {
        cancelled = true;
      };
    }
    void fetchSubtitleTvMetadata(jobIdValue)
      .then((payload) => {
        if (!cancelled) {
          setSubtitleTvMetadata(payload);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          console.warn('Unable to load subtitle TV metadata for player', error);
          setSubtitleTvMetadata(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [isSubtitleContext, jobId, libraryTvMediaMetadata, origin]);

  const subtitleMediaMetadata = useMemo<Record<string, unknown> | null>(() => {
    if (!isSubtitleContext) {
      return null;
    }
    if (libraryTvMediaMetadata) {
      return libraryTvMediaMetadata;
    }
    const candidate = subtitleTvMetadata?.media_metadata ?? null;
    return candidate && typeof candidate === 'object' ? (candidate as Record<string, unknown>) : null;
  }, [isSubtitleContext, libraryTvMediaMetadata, subtitleTvMetadata]);

  const subtitleInfo = useMemo<SubtitleInfo>(() => {
    if (!isSubtitleContext) {
      return {
        title: null,
        meta: null,
        coverUrl: null,
        coverSecondaryUrl: null,
        coverAltText: null,
      };
    }

    const jobIdValue = jobId ?? '';
    const resolver = origin === 'library' ? resolveLibraryAssetUrl : resolveJobAssetUrl;
    const episodeCoverUrl = resolveTvMetadataImage(jobIdValue, subtitleMediaMetadata, 'episode', resolver);
    const showCoverUrl = resolveTvMetadataImage(jobIdValue, subtitleMediaMetadata, 'show', resolver);
    const coverUrl = episodeCoverUrl ?? showCoverUrl ?? null;
    const coverSecondaryUrl =
      showCoverUrl && coverUrl && coverUrl !== showCoverUrl ? showCoverUrl : null;

    const show = coerceRecord(subtitleMediaMetadata?.['show']);
    const episode = coerceRecord(subtitleMediaMetadata?.['episode']);
    const showName = normaliseMetadataText(show?.['name']);
    const parsedSeries = subtitleTvMetadata?.parsed ? normaliseMetadataText(subtitleTvMetadata.parsed.series) : null;
    const sourceName = subtitleTvMetadata ? normaliseMetadataText(subtitleTvMetadata.source_name) : null;
    const title = showName ?? parsedSeries ?? sourceName ?? null;

    const seasonNumber = typeof episode?.['season'] === 'number' ? (episode['season'] as number) : null;
    const episodeNumber = typeof episode?.['number'] === 'number' ? (episode['number'] as number) : null;
    const code =
      seasonNumber && episodeNumber && seasonNumber > 0 && episodeNumber > 0
        ? `S${seasonNumber.toString().padStart(2, '0')}E${episodeNumber.toString().padStart(2, '0')}`
        : null;
    const episodeTitle = normaliseMetadataText(episode?.['name']);
    const airdate = normaliseMetadataText(episode?.['airdate']);
    const metaParts = [code, episodeTitle, airdate].filter((value): value is string => Boolean(value));
    const meta = metaParts.length > 0 ? metaParts.join(' · ') : null;

    const coverAltText = title ? `Cover for ${title}` : null;

    return { title, meta, coverUrl, coverSecondaryUrl, coverAltText };
  }, [isSubtitleContext, jobId, origin, subtitleMediaMetadata, subtitleTvMetadata]);

  return {
    isSubtitleContext,
    subtitleInfo,
  };
}
