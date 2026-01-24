import { useCallback } from 'react';
import {
  appendAccessToken,
  buildStorageUrl,
  resolveLibraryMediaUrl,
} from '../../../api/client';
import { coerceExportPath } from '../../../utils/storageResolver';

interface UseImageUrlResolverArgs {
  jobId: string | null;
  isExportMode: boolean;
  isLibraryMediaOrigin: boolean;
  imageRefreshToken: number;
  reelImageRetryTokens: Record<string, number>;
}

/**
 * Hook providing a function to resolve sentence image URLs.
 */
export function useImageUrlResolver({
  jobId,
  isExportMode,
  isLibraryMediaOrigin,
  imageRefreshToken,
  reelImageRetryTokens,
}: UseImageUrlResolverArgs) {
  const resolveSentenceImageUrl = useCallback(
    (path: string | null, sentenceNumber?: number | null): string | null => {
      const candidate = (path ?? '').trim();
      if (!candidate) {
        return null;
      }
      if (candidate.startsWith('data:') || candidate.startsWith('blob:')) {
        return candidate;
      }

      const retryToken =
        sentenceNumber && Number.isFinite(sentenceNumber)
          ? reelImageRetryTokens[String(sentenceNumber)] ?? 0
          : 0;
      const refreshToken = imageRefreshToken + retryToken;

      const addRefreshToken = (url: string) => {
        if (refreshToken <= 0) {
          return url;
        }
        try {
          const resolved = new URL(url, typeof window !== 'undefined' ? window.location.origin : undefined);
          resolved.searchParams.set('v', String(refreshToken));
          return resolved.toString();
        } catch {
          const token = `v=${encodeURIComponent(String(refreshToken))}`;
          const hashIndex = url.indexOf('#');
          const base = hashIndex >= 0 ? url.slice(0, hashIndex) : url;
          const hash = hashIndex >= 0 ? url.slice(hashIndex) : '';
          const decorated = base.includes('?') ? `${base}&${token}` : `${base}?${token}`;
          return `${decorated}${hash}`;
        }
      };

      if (isExportMode) {
        const resolved = coerceExportPath(candidate, jobId);
        return resolved ? addRefreshToken(resolved) : null;
      }

      if (candidate.includes('://')) {
        return addRefreshToken(candidate);
      }

      if (candidate.startsWith('/api/') || candidate.startsWith('/storage/') || candidate.startsWith('/pipelines/')) {
        return addRefreshToken(appendAccessToken(candidate));
      }

      if (!jobId) {
        return null;
      }

      const normalisedCandidate = candidate.replace(/\\+/g, '/');
      const [pathPart, hashPart] = normalisedCandidate.split('#', 2);
      const [pathOnly, queryPart] = pathPart.split('?', 2);

      const coerceRelative = (value: string): string => {
        const trimmed = value.replace(/^\/+/, '');
        if (!trimmed) {
          return '';
        }

        const marker = `/${jobId}/`;
        const markerIndex = trimmed.indexOf(marker);
        if (markerIndex >= 0) {
          return trimmed.slice(markerIndex + marker.length);
        }

        const segments = trimmed.split('/');
        const mediaIndex = segments.lastIndexOf('media');
        if (mediaIndex >= 0) {
          return segments.slice(mediaIndex).join('/');
        }

        const metadataIndex = segments.lastIndexOf('metadata');
        if (metadataIndex >= 0) {
          return segments.slice(metadataIndex).join('/');
        }

        return trimmed;
      };

      const relativePath = coerceRelative(pathOnly);
      if (!relativePath) {
        return null;
      }

      try {
        const baseUrl = isLibraryMediaOrigin
          ? resolveLibraryMediaUrl(jobId, relativePath)
          : buildStorageUrl(relativePath, jobId);
        if (!baseUrl) {
          return null;
        }
        const withQuery = queryPart ? `${baseUrl}${baseUrl.includes('?') ? '&' : '?'}${queryPart}` : baseUrl;
        const withHash = hashPart ? `${withQuery}#${hashPart}` : withQuery;
        return addRefreshToken(withHash);
      } catch {
        return null;
      }
    },
    [imageRefreshToken, isExportMode, isLibraryMediaOrigin, jobId, reelImageRetryTokens],
  );

  return { resolveSentenceImageUrl };
}

export default useImageUrlResolver;
