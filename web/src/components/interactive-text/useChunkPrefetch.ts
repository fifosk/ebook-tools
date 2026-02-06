/**
 * Hook for prefetching chunk metadata and audio data with retry logic.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ChunkSentenceMetadata } from '../../api/dtos';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import type { PlayerMode } from '../../types/player';
import {
  resolveChunkKey,
  resolveChunkMetadataUrl,
  resolveChunkAudioUrl,
  buildSentenceChunkIndex,
  findChunkBySentence,
} from '../../lib/media';

const PREFETCH_RADIUS = 2;
const PREFETCH_TIMEOUT_MS = 4000;
const AUDIO_PREFETCH_RANGE = 'bytes=0-2047';

/** Exponential backoff: 2s, 4s, 8s, 16s cap */
const BACKOFF_BASE_MS = 2000;
const BACKOFF_MAX_MS = 16000;
/** After this many consecutive failures for a single chunk, skip prefetch */
const CIRCUIT_BREAKER_THRESHOLD = 3;
/** After this many consecutive systemic failures, pause all prefetch temporarily */
const SYSTEMIC_FAILURE_THRESHOLD = 5;
/** How long to pause all prefetch after systemic failure detection */
const SYSTEMIC_PAUSE_MS = 30000;

export interface RetryState {
  lastAttempt: number;
  failures: number;
}

export function getBackoffMs(failures: number): number {
  return Math.min(BACKOFF_BASE_MS * Math.pow(2, failures), BACKOFF_MAX_MS);
}

export function shouldRetry(state: RetryState | undefined, now: number): boolean {
  if (!state) return true;
  if (state.failures >= CIRCUIT_BREAKER_THRESHOLD) return false;
  const backoff = getBackoffMs(state.failures);
  return now - state.lastAttempt >= backoff;
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

export interface UseChunkPrefetchOptions {
  jobId: string | null;
  playerMode: PlayerMode;
  chunk: LiveMediaChunk | null;
  chunks: LiveMediaChunk[] | null;
  activeSentenceIndex: number;
  originalAudioEnabled: boolean;
  translationAudioEnabled: boolean;
  /** When true, prefetch skews forward (3 ahead, 1 behind) instead of symmetric ±2 */
  isPlaying?: boolean;
}

export interface ChunkPrefetchState {
  /** Hydrates a chunk with prefetched sentence data if available */
  hydrateChunk: (target: LiveMediaChunk) => LiveMediaChunk;
  /** The active chunk with hydrated sentence data */
  resolvedChunk: LiveMediaChunk | null;
  /** All chunks with hydrated sentence data */
  resolvedChunks: LiveMediaChunk[] | null;
  /** True when prefetch has detected systemic connectivity issues */
  isPrefetchDegraded: boolean;
}

export function useChunkPrefetch({
  jobId,
  playerMode,
  chunk,
  chunks,
  activeSentenceIndex,
  originalAudioEnabled,
  translationAudioEnabled,
  isPlaying = false,
}: UseChunkPrefetchOptions): ChunkPrefetchState {
  const [prefetchedSentences, setPrefetchedSentences] = useState<Record<string, ChunkSentenceMetadata[]>>({});
  const prefetchedSentencesRef = useRef(prefetchedSentences);
  const metadataRetryRef = useRef<Map<string, RetryState>>(new Map());
  const metadataInFlightRef = useRef<Set<string>>(new Set());
  const audioRetryRef = useRef<Map<string, RetryState>>(new Map());
  const audioInFlightRef = useRef<Set<string>>(new Set());
  const prefetchedAudioRef = useRef<Set<string>>(new Set());
  const lastPrefetchSentenceRef = useRef<number | null>(null);
  const prevSentenceNumberRef = useRef<number | null>(null);
  const directionRef = useRef<'forward' | 'backward' | 'none'>('none');
  const consecutiveFailuresRef = useRef(0);
  const systemicPauseUntilRef = useRef(0);
  const [isPrefetchDegraded, setIsPrefetchDegraded] = useState(false);

  useEffect(() => {
    prefetchedSentencesRef.current = prefetchedSentences;
  }, [prefetchedSentences]);

  // Reset state on job or mode change
  useEffect(() => {
    setPrefetchedSentences({});
    prefetchedSentencesRef.current = {};
    metadataRetryRef.current.clear();
    metadataInFlightRef.current.clear();
    audioRetryRef.current.clear();
    audioInFlightRef.current.clear();
    prefetchedAudioRef.current.clear();
    lastPrefetchSentenceRef.current = null;
    prevSentenceNumberRef.current = null;
    directionRef.current = 'none';
    consecutiveFailuresRef.current = 0;
    systemicPauseUntilRef.current = 0;
    setIsPrefetchDegraded(false);
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

  // Pre-built sentence-to-chunk index for O(1) lookups (replaces linear scan)
  const sentenceIndex = useMemo(
    () => buildSentenceChunkIndex(Array.isArray(resolvedChunks) ? resolvedChunks : (Array.isArray(chunks) ? chunks : [])),
    [resolvedChunks, chunks],
  );

  const recordSuccess = useCallback(() => {
    consecutiveFailuresRef.current = 0;
    if (isPrefetchDegraded) {
      setIsPrefetchDegraded(false);
    }
  }, [isPrefetchDegraded]);

  const recordFailure = useCallback((retryMap: Map<string, RetryState>, key: string, now: number) => {
    const prev = retryMap.get(key);
    retryMap.set(key, { lastAttempt: now, failures: (prev?.failures ?? 0) + 1 });
    consecutiveFailuresRef.current += 1;
    if (consecutiveFailuresRef.current >= SYSTEMIC_FAILURE_THRESHOLD) {
      systemicPauseUntilRef.current = now + SYSTEMIC_PAUSE_MS;
      if (!isPrefetchDegraded) {
        setIsPrefetchDegraded(true);
      }
    }
  }, [isPrefetchDegraded]);

  const prefetchChunkMetadata = useCallback(
    async (target: LiveMediaChunk) => {
      if (playerMode !== 'online') {
        return;
      }
      const now = Date.now();
      if (now < systemicPauseUntilRef.current) {
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
      const retryState = metadataRetryRef.current.get(key);
      if (!shouldRetry(retryState, now)) {
        return;
      }
      const metadataUrl = resolveChunkMetadataUrl(target, jobId);
      if (!metadataUrl) {
        return;
      }
      metadataRetryRef.current.set(key, {
        lastAttempt: now,
        failures: retryState?.failures ?? 0,
      });
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
          recordFailure(metadataRetryRef.current, key, Date.now());
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
        recordSuccess();
        setPrefetchedSentences((current) => {
          if (current[key]) {
            return current;
          }
          return { ...current, [key]: sentences };
        });
      } catch {
        recordFailure(metadataRetryRef.current, key, Date.now());
        return;
      } finally {
        window.clearTimeout(timeout);
        metadataInFlightRef.current.delete(key);
      }
    },
    [jobId, playerMode, recordFailure, recordSuccess],
  );

  const prefetchChunkAudio = useCallback(
    async (target: LiveMediaChunk) => {
      if (playerMode !== 'online') {
        return;
      }
      const now = Date.now();
      if (now < systemicPauseUntilRef.current) {
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
      const retryState = audioRetryRef.current.get(audioUrl);
      if (!shouldRetry(retryState, now)) {
        return;
      }
      audioRetryRef.current.set(audioUrl, {
        lastAttempt: now,
        failures: retryState?.failures ?? 0,
      });
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
          recordSuccess();
        } else {
          recordFailure(audioRetryRef.current, audioUrl, Date.now());
        }
      } catch {
        recordFailure(audioRetryRef.current, audioUrl, Date.now());
        return;
      } finally {
        window.clearTimeout(timeout);
        audioInFlightRef.current.delete(audioUrl);
      }
    },
    [jobId, originalAudioEnabled, playerMode, translationAudioEnabled, recordFailure, recordSuccess],
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
    // Track direction from sentence number changes
    if (prevSentenceNumberRef.current !== null) {
      if (activeSentenceNumber > prevSentenceNumberRef.current) {
        directionRef.current = 'forward';
      } else if (activeSentenceNumber < prevSentenceNumberRef.current) {
        directionRef.current = 'backward';
      }
    }
    prevSentenceNumberRef.current = activeSentenceNumber;
    // Asymmetric prefetch: skew forward during active playback
    const skewForward = isPlaying && directionRef.current === 'forward';
    const backwardRadius = skewForward ? 1 : PREFETCH_RADIUS;
    const forwardRadius = skewForward ? PREFETCH_RADIUS + 1 : PREFETCH_RADIUS;
    const targetMap = new Map<string, LiveMediaChunk>();
    for (let offset = -backwardRadius; offset <= forwardRadius; offset += 1) {
      const candidate = activeSentenceNumber + offset;
      if (candidate <= 0) {
        continue;
      }
      const match = findChunkBySentence(sentenceIndex, chunkList, candidate);
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
        for (let offset = -backwardRadius; offset <= forwardRadius; offset += 1) {
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
    isPlaying,
    playerMode,
    prefetchChunkAudio,
    prefetchChunkMetadata,
    resolvedChunk,
    resolvedChunks,
    sentenceIndex,
  ]);

  return {
    hydrateChunk,
    resolvedChunk,
    resolvedChunks,
    isPrefetchDegraded,
  };
}

// Re-export for use in InteractiveTextViewer
export { resolveChunkKey } from '../../lib/media';
