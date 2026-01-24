/**
 * Hook for prefetching chunk metadata and audio data with retry logic.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { AudioTrackMetadata, ChunkSentenceMetadata } from '../../api/dtos';
import { appendAccessTokenToStorageUrl, buildStorageUrl } from '../../api/client';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import type { PlayerMode } from '../../types/player';

const PREFETCH_RADIUS = 2;
const METADATA_PREFETCH_RETRY_MS = 6000;
const AUDIO_PREFETCH_RETRY_MS = 12000;
const PREFETCH_TIMEOUT_MS = 4000;
const AUDIO_PREFETCH_RANGE = 'bytes=0-2047';

function resolveChunkKey(chunk: LiveMediaChunk | null): string | null {
  if (!chunk) {
    return null;
  }
  return (
    chunk.chunkId ??
    chunk.rangeFragment ??
    chunk.metadataPath ??
    chunk.metadataUrl ??
    (chunk.startSentence !== null || chunk.endSentence !== null
      ? `${chunk.startSentence ?? 'na'}-${chunk.endSentence ?? 'na'}`
      : null)
  );
}

function resolveStorageUrl(value: string | null, jobId: string | null): string | null {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (/^[a-z]+:\/\//i.test(trimmed) || trimmed.startsWith('data:') || trimmed.startsWith('blob:')) {
    return appendAccessTokenToStorageUrl(trimmed);
  }
  return buildStorageUrl(trimmed, jobId ?? null);
}

function resolveChunkMetadataUrl(chunk: LiveMediaChunk, jobId: string | null): string | null {
  if (chunk.metadataUrl) {
    return resolveStorageUrl(chunk.metadataUrl, jobId);
  }
  if (chunk.metadataPath) {
    return resolveStorageUrl(chunk.metadataPath, jobId);
  }
  return null;
}

function resolveChunkAudioUrl(
  chunk: LiveMediaChunk,
  jobId: string | null,
  originalAudioEnabled: boolean,
  translationAudioEnabled: boolean,
): string | null {
  const tracks = chunk.audioTracks ?? null;
  const translationUrl =
    tracks?.translation?.url ??
    tracks?.translation?.path ??
    tracks?.trans?.url ??
    tracks?.trans?.path ??
    null;
  const originalUrl =
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.orig?.url ??
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.orig?.path ??
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.original?.url ??
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.original?.path ??
    null;
  const combinedUrl =
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.orig_trans?.url ??
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.orig_trans?.path ??
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.combined?.url ??
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.combined?.path ??
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.mix?.url ??
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.mix?.path ??
    null;

  const candidate =
    (translationAudioEnabled ? translationUrl : null) ??
    (originalAudioEnabled ? originalUrl : null) ??
    (translationAudioEnabled ? combinedUrl : null) ??
    (originalAudioEnabled ? combinedUrl : null) ??
    translationUrl ??
    originalUrl ??
    combinedUrl;

  return resolveStorageUrl(candidate, jobId);
}

export function resolveActiveSentenceNumber(chunk: LiveMediaChunk | null, activeSentenceIndex: number): number {
  if (chunk?.sentences && chunk.sentences.length > 0) {
    const entry = chunk.sentences[Math.max(0, Math.min(activeSentenceIndex, chunk.sentences.length - 1))];
    const rawSentenceNumber = entry?.sentence_number ?? null;
    if (typeof rawSentenceNumber === 'number' && Number.isFinite(rawSentenceNumber)) {
      return Math.max(1, Math.trunc(rawSentenceNumber));
    }
  }
  const start = chunk?.startSentence ?? null;
  if (typeof start === 'number' && Number.isFinite(start)) {
    return Math.max(1, Math.trunc(start) + Math.max(0, Math.trunc(activeSentenceIndex)));
  }
  return Math.max(1, Math.trunc(activeSentenceIndex) + 1);
}

function findChunkForSentence(chunks: LiveMediaChunk[], sentenceNumber: number): LiveMediaChunk | null {
  for (const chunk of chunks) {
    const start = typeof chunk.startSentence === 'number' ? Math.trunc(chunk.startSentence) : null;
    const end = typeof chunk.endSentence === 'number' ? Math.trunc(chunk.endSentence) : null;
    if (start !== null && end !== null && sentenceNumber >= start && sentenceNumber <= end) {
      return chunk;
    }
    const sentenceCount = typeof chunk.sentenceCount === 'number' ? Math.trunc(chunk.sentenceCount) : null;
    if (start !== null && sentenceCount !== null) {
      const inferredEnd = start + Math.max(sentenceCount - 1, 0);
      if (sentenceNumber >= start && sentenceNumber <= inferredEnd) {
        return chunk;
      }
    }
    if (chunk.sentences && chunk.sentences.length > 0) {
      if (chunk.sentences.some((entry) => Math.trunc(entry?.sentence_number ?? -1) === sentenceNumber)) {
        return chunk;
      }
    }
  }
  return null;
}

export interface UseChunkPrefetchOptions {
  jobId: string | null;
  playerMode: PlayerMode;
  chunk: LiveMediaChunk | null;
  chunks: LiveMediaChunk[] | null;
  activeSentenceIndex: number;
  originalAudioEnabled: boolean;
  translationAudioEnabled: boolean;
}

export interface ChunkPrefetchState {
  /** Hydrates a chunk with prefetched sentence data if available */
  hydrateChunk: (target: LiveMediaChunk) => LiveMediaChunk;
  /** The active chunk with hydrated sentence data */
  resolvedChunk: LiveMediaChunk | null;
  /** All chunks with hydrated sentence data */
  resolvedChunks: LiveMediaChunk[] | null;
}

export function useChunkPrefetch({
  jobId,
  playerMode,
  chunk,
  chunks,
  activeSentenceIndex,
  originalAudioEnabled,
  translationAudioEnabled,
}: UseChunkPrefetchOptions): ChunkPrefetchState {
  const [prefetchedSentences, setPrefetchedSentences] = useState<Record<string, ChunkSentenceMetadata[]>>({});
  const prefetchedSentencesRef = useRef(prefetchedSentences);
  const metadataAttemptRef = useRef<Map<string, number>>(new Map());
  const metadataInFlightRef = useRef<Set<string>>(new Set());
  const audioAttemptRef = useRef<Map<string, number>>(new Map());
  const audioInFlightRef = useRef<Set<string>>(new Set());
  const prefetchedAudioRef = useRef<Set<string>>(new Set());
  const lastPrefetchSentenceRef = useRef<number | null>(null);

  useEffect(() => {
    prefetchedSentencesRef.current = prefetchedSentences;
  }, [prefetchedSentences]);

  // Reset state on job or mode change
  useEffect(() => {
    setPrefetchedSentences({});
    prefetchedSentencesRef.current = {};
    metadataAttemptRef.current.clear();
    metadataInFlightRef.current.clear();
    audioAttemptRef.current.clear();
    audioInFlightRef.current.clear();
    prefetchedAudioRef.current.clear();
    lastPrefetchSentenceRef.current = null;
  }, [jobId, playerMode]);

  const hydrateChunk = useCallback(
    (target: LiveMediaChunk): LiveMediaChunk => {
      if (target.sentences && target.sentences.length > 0) {
        return target;
      }
      const key = resolveChunkKey(target);
      if (!key) {
        return target;
      }
      const cached = prefetchedSentences[key];
      if (!cached || cached.length === 0) {
        return target;
      }
      return {
        ...target,
        sentences: cached,
        sentenceCount:
          typeof target.sentenceCount === 'number' && Number.isFinite(target.sentenceCount)
            ? target.sentenceCount
            : cached.length,
      };
    },
    [prefetchedSentences],
  );

  const resolvedChunk = useMemo(() => (chunk ? hydrateChunk(chunk) : null), [chunk, hydrateChunk]);

  const resolvedChunks = useMemo(() => {
    if (!Array.isArray(chunks)) {
      return null;
    }
    const hydrated = chunks.map((entry) => (entry ? hydrateChunk(entry) : null));
    return hydrated.filter((entry): entry is LiveMediaChunk => Boolean(entry));
  }, [chunks, hydrateChunk]);

  const prefetchChunkMetadata = useCallback(
    async (target: LiveMediaChunk) => {
      if (playerMode !== 'online') {
        return;
      }
      if (target.sentences && target.sentences.length > 0) {
        return;
      }
      const key = resolveChunkKey(target);
      if (!key || prefetchedSentencesRef.current[key]) {
        return;
      }
      if (metadataInFlightRef.current.has(key)) {
        return;
      }
      const lastAttempt = metadataAttemptRef.current.get(key);
      const now = Date.now();
      if (lastAttempt && now - lastAttempt < METADATA_PREFETCH_RETRY_MS) {
        return;
      }
      const metadataUrl = resolveChunkMetadataUrl(target, jobId);
      if (!metadataUrl) {
        return;
      }
      metadataAttemptRef.current.set(key, now);
      metadataInFlightRef.current.add(key);
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), PREFETCH_TIMEOUT_MS);
      try {
        const response = await fetch(metadataUrl, {
          method: 'GET',
          cache: 'no-store',
          signal: controller.signal,
        });
        if (!response.ok) {
          return;
        }
        const payload = (await response.json()) as unknown;
        const sentences = Array.isArray(payload)
          ? (payload as ChunkSentenceMetadata[])
          : Array.isArray((payload as { sentences?: ChunkSentenceMetadata[] })?.sentences)
            ? (payload as { sentences?: ChunkSentenceMetadata[] }).sentences ?? null
            : null;
        if (!sentences || sentences.length === 0) {
          return;
        }
        setPrefetchedSentences((current) => {
          if (current[key]) {
            return current;
          }
          return { ...current, [key]: sentences };
        });
      } catch {
        return;
      } finally {
        window.clearTimeout(timeout);
        metadataInFlightRef.current.delete(key);
      }
    },
    [jobId, playerMode],
  );

  const prefetchChunkAudio = useCallback(
    async (target: LiveMediaChunk) => {
      if (playerMode !== 'online') {
        return;
      }
      const audioUrl = resolveChunkAudioUrl(target, jobId, originalAudioEnabled, translationAudioEnabled);
      if (!audioUrl) {
        return;
      }
      if (prefetchedAudioRef.current.has(audioUrl)) {
        return;
      }
      if (audioInFlightRef.current.has(audioUrl)) {
        return;
      }
      const lastAttempt = audioAttemptRef.current.get(audioUrl);
      const now = Date.now();
      if (lastAttempt && now - lastAttempt < AUDIO_PREFETCH_RETRY_MS) {
        return;
      }
      audioAttemptRef.current.set(audioUrl, now);
      audioInFlightRef.current.add(audioUrl);
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), PREFETCH_TIMEOUT_MS);
      try {
        const response = await fetch(audioUrl, {
          method: 'GET',
          headers: {
            Range: AUDIO_PREFETCH_RANGE,
          },
          signal: controller.signal,
        });
        if (response.ok) {
          prefetchedAudioRef.current.add(audioUrl);
        }
      } catch {
        return;
      } finally {
        window.clearTimeout(timeout);
        audioInFlightRef.current.delete(audioUrl);
      }
    },
    [jobId, originalAudioEnabled, playerMode, translationAudioEnabled],
  );

  // Prefetch nearby chunks based on active sentence
  useEffect(() => {
    if (playerMode !== 'online') {
      return;
    }
    const activeChunk = resolvedChunk ?? chunk;
    const chunkList = Array.isArray(resolvedChunks) ? resolvedChunks : (Array.isArray(chunks) ? chunks : []);
    if (!activeChunk || chunkList.length === 0) {
      return;
    }
    const activeSentenceNumber = resolveActiveSentenceNumber(activeChunk, activeSentenceIndex);
    const hasActiveSentences = Boolean(activeChunk.sentences && activeChunk.sentences.length > 0);
    if (hasActiveSentences) {
      if (lastPrefetchSentenceRef.current === activeSentenceNumber) {
        return;
      }
      lastPrefetchSentenceRef.current = activeSentenceNumber;
    }
    const targetMap = new Map<string, LiveMediaChunk>();
    for (let offset = -PREFETCH_RADIUS; offset <= PREFETCH_RADIUS; offset += 1) {
      const candidate = activeSentenceNumber + offset;
      if (candidate <= 0) {
        continue;
      }
      const match = findChunkForSentence(chunkList, candidate);
      if (match) {
        const key = resolveChunkKey(match) ?? `sentence:${candidate}`;
        targetMap.set(key, match);
      }
    }
    if (targetMap.size === 0) {
      const activeKey = resolveChunkKey(activeChunk);
      const activeIndex = activeKey
        ? chunkList.findIndex((entry) => resolveChunkKey(entry) === activeKey)
        : -1;
      if (activeIndex >= 0) {
        for (let offset = -PREFETCH_RADIUS; offset <= PREFETCH_RADIUS; offset += 1) {
          const index = activeIndex + offset;
          if (index < 0 || index >= chunkList.length) {
            continue;
          }
          const entry = chunkList[index];
          const key = resolveChunkKey(entry) ?? `chunk:${index}`;
          targetMap.set(key, entry);
        }
      } else {
        const key = resolveChunkKey(activeChunk) ?? 'chunk:active';
        targetMap.set(key, activeChunk);
      }
    }
    targetMap.forEach((target) => {
      void prefetchChunkMetadata(target);
      void prefetchChunkAudio(target);
    });
  }, [
    activeSentenceIndex,
    chunk,
    chunks,
    playerMode,
    prefetchChunkAudio,
    prefetchChunkMetadata,
    resolvedChunk,
    resolvedChunks,
  ]);

  return {
    hydrateChunk,
    resolvedChunk,
    resolvedChunks,
  };
}

// Re-export for use in InteractiveTextViewer
export { resolveChunkKey };
