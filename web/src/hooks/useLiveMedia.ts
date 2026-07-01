import { useCallback, useEffect, useMemo, useState } from 'react';
import type { RefObject } from 'react';
import { appendAccessTokenToStorageUrl, fetchJobMedia, fetchLiveJobMedia } from '../api/client';
import {
  PipelineMediaDiagnostics,
  PipelineMediaResponse,
  ChunkSentenceMetadata,
  TrackTimingPayload,
} from '../api/dtos';
import { subscribeToJobEvents } from '../services/api';
import { resolve as resolveStoragePath } from '../utils/storageResolver';
import {
  buildEntrySignature,
  buildItemSignature,
  createEmptyState,
  deriveLiveMediaName,
  deriveRelativePath,
  extractAudioTracks,
  extractGeneratedFiles,
  hasAudioTracks,
  hasChunkSentences,
  mergeChunkCollections,
  mergeMediaBuckets,
  normaliseCategory,
  toNumberOrNull,
  toStringOrNull,
  type LiveMediaChunk,
  type LiveMediaItem,
  type LiveMediaState,
  type MediaCategory,
  type MediaIndex
} from './liveMediaState';
import {
  attachChunkIdToTimingSource,
  normaliseTrackTimingCollection
} from './liveMediaTiming';
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

function registerMediaItem(state: LiveMediaState, index: MediaIndex, item: LiveMediaItem): LiveMediaItem {
  const key = buildItemSignature(item);
  const existing = index.get(key);
  if (existing) {
    Object.assign(existing, { ...existing, ...item });
    return existing;
  }
  index.set(key, item);
  state[item.type].push(item);
  return item;
}

function groupFilesByType(filesSection: unknown): Record<string, unknown[]> {
  const grouped: Record<string, unknown[]> = {};
  if (!Array.isArray(filesSection)) {
    return grouped;
  }

  filesSection.forEach((entry) => {
    if (!entry || typeof entry !== 'object') {
      return;
    }
    const category = normaliseCategory((entry as Record<string, unknown>).type);
    if (!category) {
      return;
    }
    if (!grouped[category]) {
      grouped[category] = [];
    }
    grouped[category]!.push(entry);
  });

  return grouped;
}

function buildStateFromSections(
  mediaSection: Record<string, unknown[] | undefined>,
  chunkSection: unknown,
  jobId: string | null | undefined,
): { media: LiveMediaState; chunks: LiveMediaChunk[]; index: MediaIndex } {
  const state = createEmptyState();
  const index: MediaIndex = new Map();

  Object.entries(mediaSection).forEach(([rawType, files]) => {
    const category = normaliseCategory(rawType);
    if (!category || !Array.isArray(files)) {
      return;
    }
    files.forEach((entry) => {
      if (!entry || typeof entry !== 'object') {
        return;
      }
      const item = buildLiveMediaItem(entry as Record<string, unknown>, category, jobId);
      if (item) {
        registerMediaItem(state, index, item);
      }
    });
  });

  const chunkRecords: LiveMediaChunk[] = [];
  if (Array.isArray(chunkSection)) {
    chunkSection.forEach((chunk) => {
      if (!chunk || typeof chunk !== 'object') {
        return;
      }
      const payload = chunk as Record<string, unknown>;
      const chunkId = toStringOrNull(payload.chunk_id ?? payload.chunkId);
      const filesRaw = payload.files;
      if (!Array.isArray(filesRaw)) {
        return;
      }
      const chunkFiles: LiveMediaItem[] = [];
      const chunkRangeFragment = toStringOrNull(payload.range_fragment ?? payload.rangeFragment);
      filesRaw.forEach((fileEntry) => {
        if (!fileEntry || typeof fileEntry !== 'object') {
          return;
        }
        const record = fileEntry as Record<string, unknown>;
        const category = normaliseCategory(record.type);
        if (!category) {
          return;
        }
        const key = buildEntrySignature(record, category);
        let item = index.get(key);
        if (!item) {
          const built = buildLiveMediaItem(record, category, jobId);
          if (!built) {
            return;
          }
          const enriched: LiveMediaItem = {
            ...built,
            chunk_id: built.chunk_id ?? chunkId ?? null,
            range_fragment: built.range_fragment ?? chunkRangeFragment ?? null,
          };
          item = registerMediaItem(state, index, enriched);
        } else {
          if (item.chunk_id == null) {
            item.chunk_id = chunkId ?? null;
          }
          if (item.range_fragment == null) {
            item.range_fragment = chunkRangeFragment ?? null;
          }
        }
        chunkFiles.push(item);
      });
      if (chunkFiles.length === 0) {
        return;
      }
      const metadataPath = toStringOrNull(
        (payload.metadata_path as string | undefined) ?? (payload.metadataPath as string | undefined),
      );
      const metadataUrl = toStringOrNull(
        (payload.metadata_url as string | undefined) ?? (payload.metadataUrl as string | undefined),
      );
      const rawSentenceCount = toNumberOrNull(
        (payload.sentence_count as number | string | undefined) ??
          (payload.sentenceCount as number | string | undefined),
      );
      const sentencesRaw = payload.sentences;
      const sentences = Array.isArray(sentencesRaw)
        ? (sentencesRaw as ChunkSentenceMetadata[])
        : [];
      const audioTracks =
        extractAudioTracks(
          payload.audioTracks as Record<string, unknown> | undefined,
        ) ?? null;
      const rawTimingSource = payload.timingTracks as unknown;
      const timingTracks = normaliseTrackTimingCollection(
        attachChunkIdToTimingSource(rawTimingSource, chunkId),
      );
      const sentenceCount =
        typeof rawSentenceCount === 'number' && Number.isFinite(rawSentenceCount)
          ? rawSentenceCount
          : sentences.length > 0
            ? sentences.length
            : null;
      // Extract timing version (v2 = pre-scaled timing from backend)
      const timingVersion = toStringOrNull(
        payload.timingVersion as string | undefined,
      );
      const timingValidationRaw = payload.timing_validation ?? payload.timingValidation;
      const timingValidation =
        timingValidationRaw && typeof timingValidationRaw === 'object' && !Array.isArray(timingValidationRaw)
          ? (timingValidationRaw as Record<string, unknown>)
          : null;
      chunkRecords.push({
        chunkId,
        rangeFragment: chunkRangeFragment,
        startSentence: toNumberOrNull(payload.startSentence ?? payload.start_sentence),
        endSentence: toNumberOrNull(payload.endSentence ?? payload.end_sentence),
        files: chunkFiles,
        sentences: sentences.length > 0 ? sentences : undefined,
        metadataPath,
        metadataUrl,
        sentenceCount,
        audioTracks,
        timingTracks: timingTracks ?? null,
        timingVersion: timingVersion ?? undefined,
        timingValidation,
      });
    });
  }

  chunkRecords.sort((a, b) => {
    const left = a.startSentence ?? Number.MAX_SAFE_INTEGER;
    const right = b.startSentence ?? Number.MAX_SAFE_INTEGER;
    if (left === right) {
      return (a.rangeFragment ?? '').localeCompare(b.rangeFragment ?? '');
    }
    return left - right;
  });

  return { media: state, chunks: chunkRecords, index };
}

function tokeniseStorageUrl(url: string | null): string | null {
  if (!url) {
    return null;
  }
  if (url.startsWith('data:') || url.startsWith('blob:')) {
    return url;
  }
  return appendAccessTokenToStorageUrl(url);
}

function resolveFileUrl(
  jobId: string | null | undefined,
  entry: Record<string, unknown>,
): string | null {
  const explicitUrl = toStringOrNull(entry.url);
  if (explicitUrl) {
    if (!explicitUrl.includes('://') && !explicitUrl.startsWith('/') && !explicitUrl.startsWith('data:') && !explicitUrl.startsWith('blob:')) {
      try {
        return tokeniseStorageUrl(resolveStoragePath(jobId ?? null, explicitUrl));
      } catch (error) {
        console.warn('Unable to resolve storage URL for generated media', error);
      }
    }
    return tokeniseStorageUrl(explicitUrl);
  }

  const relativePath =
    toStringOrNull(entry.relative_path) ??
    deriveRelativePath(jobId, toStringOrNull(entry.path));

  if (relativePath) {
    try {
      return tokeniseStorageUrl(resolveStoragePath(jobId ?? null, relativePath));
    } catch (error) {
      console.warn('Unable to resolve storage URL for generated media', error);
    }
  }

  const fallbackPath = toStringOrNull(entry.path);
  if (fallbackPath && fallbackPath.includes('://')) {
    return tokeniseStorageUrl(fallbackPath);
  }

  return null;
}

function buildLiveMediaItem(
  entry: Record<string, unknown>,
  category: MediaCategory,
  jobId: string | null | undefined,
): LiveMediaItem | null {
  const url = resolveFileUrl(jobId, entry);
  if (!url) {
    return null;
  }

  const name = deriveLiveMediaName(entry, url);
  const size = toNumberOrNull(entry.size) ?? undefined;
  const updatedAt = toStringOrNull(entry.updated_at) ?? undefined;
  const sourceRaw = toStringOrNull(entry.source);
  const source: 'completed' | 'live' = sourceRaw === 'completed' ? 'completed' : 'live';
  const chunkId = toStringOrNull(entry.chunk_id ?? entry.chunkId) ?? undefined;
  const rangeFragment = toStringOrNull(entry.range_fragment ?? entry.rangeFragment) ?? undefined;
  const startSentence = toNumberOrNull(entry.start_sentence ?? entry.startSentence) ?? undefined;
  const endSentence = toNumberOrNull(entry.end_sentence ?? entry.endSentence) ?? undefined;
  const relativePath = toStringOrNull(entry.relative_path ?? (entry as { relativePath?: unknown }).relativePath);
  const pathValue = toStringOrNull(entry.path);

  return {
    name,
    url,
    path: pathValue ?? undefined,
    relative_path: relativePath ?? undefined,
    size,
    updated_at: updatedAt,
    source,
    type: category,
    chunk_id: chunkId ?? null,
    range_fragment: rangeFragment ?? null,
    start_sentence: startSentence ?? null,
    end_sentence: endSentence ?? null
  };
}

export function normaliseFetchedMedia(
  response: PipelineMediaResponse | null | undefined,
  jobId: string | null | undefined,
): {
  media: LiveMediaState;
  chunks: LiveMediaChunk[];
  complete: boolean;
  diagnostics: PipelineMediaDiagnostics | null;
  index: MediaIndex;
} {
  if (!response || typeof response !== 'object') {
    return { media: createEmptyState(), chunks: [], complete: false, diagnostics: null, index: new Map() };
  }

  const { media, chunks, index } = buildStateFromSections(
    response.media ?? {},
    response.chunks ?? [],
    jobId,
  );
  return {
    media,
    chunks,
    complete: Boolean(response.complete),
    diagnostics: response.diagnostics ?? null,
    index,
  };
}

function normaliseGeneratedSnapshot(
  snapshot: unknown,
  jobId: string | null | undefined,
): {
  media: LiveMediaState;
  chunks: LiveMediaChunk[];
  complete: boolean;
  index: MediaIndex;
} {
  if (!snapshot || typeof snapshot !== 'object') {
    return { media: createEmptyState(), chunks: [], complete: false, index: new Map() };
  }

  const payload = snapshot as Record<string, unknown>;
  const filesSection = groupFilesByType(payload.files);
  const { media, chunks, index } = buildStateFromSections(filesSection, payload.chunks, jobId);
  return {
    media,
    chunks,
    complete: Boolean(payload.complete),
    index,
  };
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
