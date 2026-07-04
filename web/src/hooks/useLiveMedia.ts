import { useEffect, useMemo, useState } from 'react';
import { fetchJobMedia, fetchLiveJobMedia } from '../api/client';
import {
  PipelineMediaDiagnostics,
  PipelineMediaResponse,
} from '../api/dtos';
import { subscribeToJobEvents } from '../services/api';
import {
  createEmptyState,
  hasChunkSentences,
  mergeChunkCollections,
  mergeMediaBuckets,
  type LiveMediaChunk,
  type LiveMediaState,
} from './liveMediaState';
import {
  normaliseFetchedMedia,
  normaliseGeneratedSnapshot,
} from './liveMediaNormalise';
import { resolveLiveMediaEventAction } from './liveMediaEvents';
export { createEmptyState } from './liveMediaState';
export { useMediaClock } from './liveMediaClock';
export type { MediaClock } from './liveMediaClock';
export type { LiveMediaChunk, LiveMediaItem, LiveMediaState } from './liveMediaState';

export interface UseLiveMediaOptions {
  enabled?: boolean;
}

export interface UseLiveMediaResult {
  media: LiveMediaState;
  chunks: LiveMediaChunk[];
  diagnostics: PipelineMediaDiagnostics | null;
  isComplete: boolean;
  isLoading: boolean;
  error: Error | null;
}

export function useLiveMedia(
  jobId: string | null | undefined,
  options: UseLiveMediaOptions = {},
): UseLiveMediaResult {
  const { enabled = true } = options;
  const [media, setMedia] = useState<LiveMediaState>(() => createEmptyState());
  const [chunks, setChunks] = useState<LiveMediaChunk[]>([]);
  const [diagnostics, setDiagnostics] = useState<PipelineMediaDiagnostics | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!enabled || !jobId) {
      setMedia(createEmptyState());
      setChunks([]);
      setDiagnostics(null);
      setIsComplete(false);
      setIsLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setError(null);

    fetchLiveJobMedia(jobId)
      .then((response: PipelineMediaResponse) => {
        if (cancelled) {
          return null;
        }
        const {
          media: initialMedia,
          chunks: initialChunks,
          complete,
          diagnostics: initialDiagnostics,
        } = normaliseFetchedMedia(response, jobId);
        setMedia(initialMedia);
        setChunks(initialChunks);
        setDiagnostics(initialDiagnostics);
        setIsComplete(complete);
        return { initialMedia, initialChunks, complete };
      })
      .then((payload) => {
        if (cancelled || !payload) {
          return;
        }
        if (hasChunkSentences(payload.initialChunks)) {
          return;
        }
        return fetchJobMedia(jobId)
          .then((fallbackResponse: PipelineMediaResponse) => {
            if (cancelled) {
              return;
            }
            const {
              media: fallbackMedia,
              chunks: fallbackChunks,
              complete: fallbackComplete,
              diagnostics: fallbackDiagnostics,
            } = normaliseFetchedMedia(fallbackResponse, jobId);
            if (fallbackMedia.text.length + fallbackMedia.audio.length + fallbackMedia.video.length === 0) {
              return;
            }
            setMedia(fallbackMedia);
            setChunks(fallbackChunks);
            setDiagnostics(fallbackDiagnostics);
            setIsComplete(fallbackComplete || payload.complete);
          })
          .catch(() => {
            // Ignore failures; live snapshot will remain in place.
          });
      })
      .catch((fetchError: unknown) => {
        if (cancelled) {
          return;
        }
        const errorInstance =
          fetchError instanceof Error ? fetchError : new Error(String(fetchError));
        setError(errorInstance);
        setMedia(createEmptyState());
        setChunks([]);
        setDiagnostics(null);
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
  }, [enabled, jobId]);

  useEffect(() => {
    if (!enabled || !jobId) {
      return;
    }

    const refreshCompletedMedia = () => {
      setIsComplete(true);
      fetchJobMedia(jobId)
        .then((fallbackResponse: PipelineMediaResponse) => {
          const {
            media: nextMedia,
            chunks: nextChunks,
            complete,
            diagnostics: nextDiagnostics,
          } = normaliseFetchedMedia(fallbackResponse, jobId);
          setMedia(nextMedia);
          setChunks(nextChunks);
          setDiagnostics(nextDiagnostics);
          if (complete) {
            setIsComplete(true);
          }
        })
        .catch(() => {
          // Ignore failures; last known snapshot will remain in place.
        });
    };

    return subscribeToJobEvents(jobId, {
      onEvent: (event) => {
        const action = resolveLiveMediaEventAction(event);
        if (action.kind === 'refresh') {
          refreshCompletedMedia();
          return;
        }
        if (action.kind === 'ignore') {
          return;
        }

        const { media: nextMedia, chunks: incomingChunks, complete } = normaliseGeneratedSnapshot(action.generatedFiles, jobId);

        if (action.kind === 'reset') {
          setMedia(nextMedia);
          setChunks(incomingChunks);
          setDiagnostics(null);
          setIsComplete(complete);
          return;
        }

        setMedia((current) => mergeMediaBuckets(current, nextMedia));
        if (incomingChunks.length > 0) {
          setChunks((current) => mergeChunkCollections(current, incomingChunks));
        }
        setDiagnostics(null);
        if (complete) {
          setIsComplete(true);
        }
      }
    });
  }, [enabled, jobId]);

  return useMemo(
    () => ({
      media,
      chunks,
      diagnostics,
      isComplete,
      isLoading,
      error
    }),
    [media, chunks, diagnostics, isComplete, isLoading, error]
  );
}
