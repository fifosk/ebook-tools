import { useEffect, useMemo, useState } from 'react';
import { fetchLibraryMedia } from '../api/client';
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
        setMedia(nextMedia);
        setChunks(nextChunks);
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
