import { useEffect, useMemo, useState } from 'react';
import { appendAccessToken, fetchLibraryMedia, resolveLibraryMediaUrl } from '../api/client';
import type { PipelineMediaResponse } from '../api/dtos';
import {
  LiveMediaChunk,
  LiveMediaState,
  createEmptyState,
  normaliseFetchedMedia,
} from './useLiveMedia';

export interface UseLibraryMediaResult {
  media: LiveMediaState;
  chunks: LiveMediaChunk[];
  isComplete: boolean;
  isLoading: boolean;
  error: Error | null;
}

export function useLibraryMedia(jobId: string | null | undefined): UseLibraryMediaResult {
  const [media, setMedia] = useState<LiveMediaState>(() => createEmptyState());
  const [chunks, setChunks] = useState<LiveMediaChunk[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!jobId) {
      setMedia(createEmptyState());
      setChunks([]);
      setIsComplete(false);
      setIsLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setError(null);

    fetchLibraryMedia(jobId)
      .then((response: PipelineMediaResponse) => {
        if (cancelled) {
          return;
        }
        const { media: nextMedia, chunks: nextChunks, complete } = normaliseFetchedMedia(
          response,
          jobId,
        );
        setMedia(applyAccessTokens(nextMedia));
        setChunks(tokeniseChunks(nextChunks, jobId));
        setIsComplete(complete);
      })
      .catch((loadError: unknown) => {
        if (cancelled) {
          return;
        }
        setError(loadError instanceof Error ? loadError : new Error(String(loadError)));
        setMedia(createEmptyState());
        setChunks([]);
        setIsComplete(false);
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [jobId]);

  return useMemo(
    () => ({
      media,
      chunks,
      isComplete,
      isLoading,
      error,
    }),
    [chunks, error, isComplete, isLoading, media],
  );
}

function applyAccessTokens(state: LiveMediaState): LiveMediaState {
  const withTokens: LiveMediaState = {
    text: state.text.map((item) => ({ ...item, url: tokeniseUrl(item.url) })),
    audio: state.audio.map((item) => ({ ...item, url: tokeniseUrl(item.url) })),
    video: state.video.map((item) => ({ ...item, url: tokeniseUrl(item.url) })),
  };
  return withTokens;
}

function tokeniseChunks(
  chunks: LiveMediaChunk[],
  jobId: string | null | undefined,
): LiveMediaChunk[] {
  const normalisedJobId =
    typeof jobId === 'string' && jobId.trim().length > 0 ? jobId.trim() : null;

  return chunks.map((chunk) => {
    let metadataUrl = chunk.metadataUrl ?? null;
    if (!metadataUrl && normalisedJobId && chunk.metadataPath) {
      metadataUrl = resolveLibraryMediaUrl(normalisedJobId, chunk.metadataPath);
    }
    const tokenisedMetadataUrl = tokeniseUrl(metadataUrl);
    const sourceTracks = chunk.audioTracks ?? null;
    let tokenisedTracks: Record<string, string> | undefined;
    if (sourceTracks && typeof sourceTracks === 'object') {
      const entries: Record<string, string> = {};
      Object.entries(sourceTracks).forEach(([key, rawValue]) => {
        if (typeof rawValue !== 'string') {
          return;
        }
        const trimmed = rawValue.trim();
        if (!trimmed) {
          return;
        }
        let resolved = trimmed;
        if (normalisedJobId && !trimmed.includes('://')) {
          if (trimmed.startsWith('/api/library/')) {
            resolved = trimmed;
          } else {
            const relative = trimmed.replace(/^\/+/, '');
            const libraryResolved = resolveLibraryMediaUrl(normalisedJobId, relative);
            if (libraryResolved) {
              resolved = libraryResolved;
            }
          }
        }
        const tokenised = tokeniseUrl(resolved);
        if (tokenised) {
          entries[key] = tokenised;
        }
      });
      if (Object.keys(entries).length > 0) {
        tokenisedTracks = entries;
      }
    }

    return {
      ...chunk,
      metadataUrl: tokenisedMetadataUrl,
      files: chunk.files.map((file) => ({ ...file, url: tokeniseUrl(file.url) })),
      audioTracks: tokenisedTracks ?? chunk.audioTracks,
    };
  });
}

function tokeniseUrl(url: string | null | undefined): string | null {
  if (!url) {
    return null;
  }
  if (url.includes('access_token=')) {
    return url;
  }
  return appendAccessToken(url);
}
