import { useCallback, useEffect, useMemo, useState } from 'react';
import { appendAccessToken, buildStorageUrl, resolveJobCoverUrl, resolveLibraryMediaUrl } from '../../api/client';
import { coerceExportPath } from '../../utils/storageResolver';
import { DEFAULT_COVER_URL } from './constants';

type UseCoverArtArgs = {
  jobId: string | null;
  origin: 'job' | 'library';
  bookMetadata?: Record<string, unknown> | null;
  mediaComplete: boolean;
  playerMode?: 'online' | 'export';
};

type UseCoverArtResult = {
  coverUrl: string;
  shouldShowCoverImage: boolean;
  onCoverError?: () => void;
};

export function useCoverArt({
  jobId,
  origin,
  bookMetadata = null,
  mediaComplete,
  playerMode = 'online',
}: UseCoverArtArgs): UseCoverArtResult {
  const [coverSourceIndex, setCoverSourceIndex] = useState(0);
  const normalisedJobId = jobId ?? '';
  const isExportMode = playerMode === 'export';

  const jobCoverAsset = useMemo(() => {
    const value = bookMetadata?.['job_cover_asset'];
    if (typeof value !== 'string') {
      return null;
    }
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }, [bookMetadata]);

  const legacyCoverFile = useMemo(() => {
    const value = bookMetadata?.['book_cover_file'];
    if (typeof value !== 'string') {
      return null;
    }
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }, [bookMetadata]);

  const apiCoverUrl = useMemo(() => {
    if (!normalisedJobId || origin === 'library' || isExportMode) {
      return null;
    }
    return resolveJobCoverUrl(normalisedJobId);
  }, [isExportMode, normalisedJobId, origin]);

  const coverCandidates = useMemo(() => {
    const candidates: string[] = [];
    const unique = new Set<string>();

    const convertCandidate = (value: string | null | undefined): string | null => {
      if (typeof value !== 'string') {
        return null;
      }
      const trimmed = value.trim();
      if (!trimmed) {
        return null;
      }
      if (isExportMode) {
        return coerceExportPath(trimmed, normalisedJobId);
      }

      if (origin === 'library' && trimmed.includes('/pipelines/')) {
        return null;
      }

      if (/^https?:\/\//i.test(trimmed)) {
        if (origin === 'library' && trimmed.includes('/pipelines/')) {
          return null;
        }
        return appendAccessToken(trimmed);
      }

      if (/^\/?assets\//i.test(trimmed)) {
        return trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
      }

      if (origin === 'library' && trimmed.startsWith('/') && !trimmed.startsWith('/api/library/')) {
        return null;
      }

      if (trimmed.startsWith('/api/pipelines/')) {
        return appendAccessToken(trimmed);
      }
      if (trimmed.startsWith('/api/jobs/')) {
        return appendAccessToken(trimmed);
      }
      if (origin === 'library') {
        if (trimmed.includes('/pipelines/')) {
          return null;
        }
        if (trimmed.startsWith('/api/library/')) {
          return appendAccessToken(trimmed);
        }
        if (trimmed.startsWith('/')) {
          return null;
        }
        const resolved = resolveLibraryMediaUrl(normalisedJobId, trimmed);
        return resolved ? appendAccessToken(resolved) : null;
      }

      if (trimmed.startsWith('/api/library/')) {
        return appendAccessToken(trimmed);
      }
      if (trimmed.startsWith('/pipelines/')) {
        return appendAccessToken(trimmed);
      }

      const stripped = trimmed.replace(/^\/+/, '');
      if (!stripped) {
        return null;
      }
      try {
        return buildStorageUrl(stripped, normalisedJobId);
      } catch (error) {
        console.warn('Unable to build storage URL for cover image', error);
        return `/${stripped}`;
      }
    };

    const push = (candidate: string | null | undefined) => {
      const resolved = convertCandidate(candidate);
      if (!resolved || unique.has(resolved)) {
        return;
      }
      unique.add(resolved);
      candidates.push(resolved);
    };

    if (apiCoverUrl) {
      push(apiCoverUrl);
    }

    const metadataCoverUrl = (() => {
      const value = bookMetadata?.['job_cover_asset_url'];
      return typeof value === 'string' ? value : null;
    })();

    if (metadataCoverUrl && !(origin === 'library' && /\/pipelines\//.test(metadataCoverUrl))) {
      push(metadataCoverUrl);
    }

    push(jobCoverAsset);
    if (legacyCoverFile && legacyCoverFile !== jobCoverAsset) {
      push(legacyCoverFile);
    }

    push(DEFAULT_COVER_URL);

    return candidates;
  }, [apiCoverUrl, bookMetadata, isExportMode, jobCoverAsset, legacyCoverFile, normalisedJobId, origin]);

  useEffect(() => {
    if (coverSourceIndex !== 0) {
      setCoverSourceIndex(0);
    }
  }, [coverCandidates, coverSourceIndex]);

  const coverUrl = coverCandidates[coverSourceIndex] ?? DEFAULT_COVER_URL;
  const handleCoverError = useCallback(() => {
    setCoverSourceIndex((currentIndex) => {
      const nextIndex = currentIndex + 1;
      if (nextIndex >= coverCandidates.length) {
        return currentIndex;
      }
      return nextIndex;
    });
  }, [coverCandidates]);
  const shouldHandleCoverError = coverSourceIndex < coverCandidates.length - 1;
  const shouldShowCoverImage = origin === 'library' || mediaComplete || isExportMode;
  const onCoverError = shouldShowCoverImage && shouldHandleCoverError ? handleCoverError : undefined;

  return {
    coverUrl,
    shouldShowCoverImage,
    onCoverError,
  };
}
