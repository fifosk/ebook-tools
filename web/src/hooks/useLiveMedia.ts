import { useCallback, useEffect, useMemo, useState } from 'react';
import type { RefObject } from 'react';
import { fetchJobMedia, fetchLiveJobMedia } from '../api/client';
import {
  PipelineMediaDiagnostics,
  PipelineMediaResponse,
  TrackTimingPayload,
} from '../api/dtos';
import { subscribeToJobEvents } from '../services/api';
import {
  createEmptyState,
  extractGeneratedFiles,
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
export { createEmptyState } from './liveMediaState';
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

    return subscribeToJobEvents(jobId, {
      onEvent: (event) => {
        if (event.event_type === 'complete') {
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
          return;
        }

        const metadataRecord = event.metadata as Record<string, unknown>;
        const stage = typeof metadataRecord.stage === 'string' ? metadataRecord.stage : null;
        if (event.event_type === 'progress' && stage === 'complete') {
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
          return;
        }

        const snapshot = extractGeneratedFiles(event.metadata);
        if (!snapshot) {
          return;
        }

        const { media: nextMedia, chunks: incomingChunks, complete } = normaliseGeneratedSnapshot(snapshot, jobId);

        if (event.event_type === 'progress' && metadataRecord.media_reset === true) {
          setMedia(nextMedia);
          setChunks(incomingChunks);
          setDiagnostics(null);
          setIsComplete(complete);
          return;
        }

        if (event.event_type !== 'file_chunk_generated') {
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

export interface MediaClock {
  mediaTime: () => number;
  playbackRate: () => number;
  effectiveTime: (track: Pick<TrackTimingPayload, 'trackOffset' | 'tempoFactor'>) => number;
}

function sanitiseRate(value: number | null | undefined): number {
  if (typeof value !== 'number' || Number.isNaN(value) || !Number.isFinite(value) || value <= 0) {
    return 1;
  }
  return value;
}

export function useMediaClock(audioRef: RefObject<HTMLAudioElement | null>): MediaClock {
  const mediaTime = useCallback(() => {
    const element = audioRef.current;
    if (!element) {
      return 0;
    }
    const raw = element.currentTime;
    if (typeof raw !== 'number' || Number.isNaN(raw) || !Number.isFinite(raw)) {
      return 0;
    }
    return raw;
  }, [audioRef]);

  const effectiveTime = useCallback(
    (track: Pick<TrackTimingPayload, 'trackOffset' | 'tempoFactor'>) => {
      const offset =
        typeof track.trackOffset === 'number' && Number.isFinite(track.trackOffset)
          ? track.trackOffset
          : 0;
      const tempoFactor =
        typeof track.tempoFactor === 'number' && Number.isFinite(track.tempoFactor) && track.tempoFactor > 0
          ? track.tempoFactor
          : 1;
      const adjusted = (mediaTime() - offset) / tempoFactor;
      if (!Number.isFinite(adjusted) || Number.isNaN(adjusted)) {
        return 0;
      }
      return adjusted < 0 ? 0 : adjusted;
    },
    [mediaTime]
  );

  const playbackRate = useCallback(() => {
    const element = audioRef.current;
    return sanitiseRate(element?.playbackRate ?? 1);
  }, [audioRef]);

  return useMemo(
    () => ({
      mediaTime,
      playbackRate,
      effectiveTime
    }),
    [mediaTime, playbackRate, effectiveTime]
  );
}
