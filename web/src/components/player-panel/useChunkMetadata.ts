import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import type { ChunkSentenceMetadata } from '../../api/dtos';
import { chunkCacheKey } from './utils';
import {
  CHUNK_METADATA_PREFETCH_RADIUS,
  CHUNK_SENTENCE_APPEND_BATCH,
  CHUNK_SENTENCE_BOOTSTRAP_COUNT,
  SINGLE_SENTENCE_PREFETCH_AHEAD,
  isSingleSentenceChunk,
  partitionChunkSentences,
  requestChunkMetadata,
  shouldPrefetchChunk,
} from './helpers';

type UseChunkMetadataArgs = {
  jobId: string | null;
  origin: 'job' | 'library';
  playerMode?: 'online' | 'export';
  chunks: LiveMediaChunk[];
  activeTextChunk: LiveMediaChunk | null;
  activeTextChunkIndex: number;
};

type UseChunkMetadataResult = {
  hasInteractiveChunks: boolean;
  resolvedActiveTextChunk: LiveMediaChunk | null;
};

export function useChunkMetadata({
  jobId,
  origin,
  playerMode = 'online',
  chunks,
  activeTextChunk,
  activeTextChunkIndex,
}: UseChunkMetadataArgs): UseChunkMetadataResult {
  const isExportMode = playerMode === 'export';
  const [chunkMetadataStore, setChunkMetadataStore] = useState<Record<string, ChunkSentenceMetadata[]>>({});
  const chunkMetadataStoreRef = useRef(chunkMetadataStore);
  const chunkMetadataLoadingRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    chunkMetadataStoreRef.current = chunkMetadataStore;
  }, [chunkMetadataStore]);

  const pushChunkMetadata = useCallback(
    (cacheKey: string, payload: ChunkSentenceMetadata[] | null | undefined, append: boolean) => {
      const normalized = Array.isArray(payload) ? payload : [];
      setChunkMetadataStore((current) => {
        const existing = current[cacheKey];
        if (!append && existing !== undefined) {
          return current;
        }
        if (append && normalized.length === 0) {
          return current;
        }
        const base = append && Array.isArray(existing) ? existing : [];
        const nextSentences = append ? base.concat(normalized) : normalized;
        if (append && Array.isArray(existing) && nextSentences.length === existing.length) {
          return current;
        }
        if (!append && existing === nextSentences) {
          return current;
        }
        return {
          ...current,
          [cacheKey]: nextSentences,
        };
      });
    },
    [],
  );

  const scheduleChunkMetadataAppend = useCallback(
    (cacheKey: string, remainder: ChunkSentenceMetadata[]) => {
      if (!Array.isArray(remainder) || remainder.length === 0) {
        return;
      }
      let offset = 0;
      const batchSize = CHUNK_SENTENCE_APPEND_BATCH;
      const flush = () => {
        const slice = remainder.slice(offset, offset + batchSize);
        offset += slice.length;
        if (slice.length > 0) {
          pushChunkMetadata(cacheKey, slice, true);
        }
        if (offset < remainder.length) {
          if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
            window.requestAnimationFrame(flush);
          } else {
            setTimeout(flush, 16);
          }
        }
      };
      flush();
    },
    [pushChunkMetadata],
  );

  const queueChunkMetadataFetch = useCallback(
    (chunk: LiveMediaChunk | null | undefined) => {
      if (!jobId || !chunk) {
        return;
      }
      if (Array.isArray(chunk.sentences) && chunk.sentences.length > 0) {
        return;
      }
      if (isExportMode && !chunk.metadataPath && !chunk.metadataUrl) {
        return;
      }
      const cacheKey = chunkCacheKey(chunk);
      if (!cacheKey) {
        return;
      }
      if (chunkMetadataStoreRef.current[cacheKey] !== undefined) {
        return;
      }
      if (chunkMetadataLoadingRef.current.has(cacheKey)) {
        return;
      }
      chunkMetadataLoadingRef.current.add(cacheKey);
      requestChunkMetadata(jobId, chunk, origin, playerMode)
        .then((sentences) => {
          if (sentences === null) {
            return;
          }
          const { immediate, remainder } = partitionChunkSentences(
            sentences,
            CHUNK_SENTENCE_BOOTSTRAP_COUNT,
          );
          pushChunkMetadata(cacheKey, immediate, false);
          if (remainder.length > 0) {
            scheduleChunkMetadataAppend(cacheKey, remainder);
          }
        })
        .catch((error) => {
          console.warn('Unable to load interactive chunk metadata', error);
        })
        .finally(() => {
          chunkMetadataLoadingRef.current.delete(cacheKey);
        });
    },
    [isExportMode, jobId, origin, playerMode, pushChunkMetadata, scheduleChunkMetadataAppend],
  );

  useEffect(() => {
    if (!jobId) {
      return;
    }
    const targets = new Set<LiveMediaChunk>();

    if (activeTextChunk) {
      targets.add(activeTextChunk);
    }

    if (activeTextChunkIndex >= 0) {
      for (let offset = -CHUNK_METADATA_PREFETCH_RADIUS; offset <= CHUNK_METADATA_PREFETCH_RADIUS; offset += 1) {
        const neighbourIndex = activeTextChunkIndex + offset;
        if (neighbourIndex < 0 || neighbourIndex >= chunks.length) {
          continue;
        }
        const neighbour = chunks[neighbourIndex];
        if (neighbour && (neighbour === activeTextChunk || shouldPrefetchChunk(neighbour))) {
          targets.add(neighbour);
        }
      }

      if (isSingleSentenceChunk(activeTextChunk)) {
        let aheadPrefetched = 0;
        for (
          let lookaheadIndex = activeTextChunkIndex + 1;
          lookaheadIndex < chunks.length && aheadPrefetched < SINGLE_SENTENCE_PREFETCH_AHEAD;
          lookaheadIndex += 1
        ) {
          const lookaheadChunk = chunks[lookaheadIndex];
          if (!lookaheadChunk) {
            continue;
          }
          if (shouldPrefetchChunk(lookaheadChunk)) {
            targets.add(lookaheadChunk);
          }
          aheadPrefetched += 1;
        }
      }
    }

    targets.forEach((chunk) => {
      queueChunkMetadataFetch(chunk);
    });
  }, [jobId, chunks, activeTextChunk, activeTextChunkIndex, queueChunkMetadataFetch]);

  const hasInteractiveChunks = useMemo(() => {
    return chunks.some((chunk) => {
      if (Array.isArray(chunk.sentences) && chunk.sentences.length > 0) {
        return true;
      }
      if (typeof chunk.sentenceCount === 'number' && chunk.sentenceCount > 0) {
        return true;
      }
      const cacheKey = chunkCacheKey(chunk);
      if (!cacheKey) {
        return false;
      }
      const cached = chunkMetadataStore[cacheKey];
      return cached !== undefined;
    });
  }, [chunks, chunkMetadataStore]);

  const resolvedActiveTextChunk = useMemo(() => {
    if (!activeTextChunk) {
      return null;
    }
    if (Array.isArray(activeTextChunk.sentences) && activeTextChunk.sentences.length > 0) {
      return activeTextChunk;
    }
    const cacheKey = chunkCacheKey(activeTextChunk);
    if (!cacheKey) {
      return activeTextChunk;
    }
    const cached = chunkMetadataStore[cacheKey];
    if (cached !== undefined) {
      return {
        ...activeTextChunk,
        sentences: cached,
        sentenceCount: cached.length,
      };
    }
    return activeTextChunk;
  }, [activeTextChunk, chunkMetadataStore]);

  return {
    hasInteractiveChunks,
    resolvedActiveTextChunk,
  };
}
