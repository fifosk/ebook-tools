import { useEffect, useMemo, useRef, useState } from 'react';
import { appendAccessToken, fetchLibraryMedia, resolveLibraryMediaUrl } from '../api/client';
import type { ChunkSentenceMetadata, PipelineMediaResponse } from '../api/dtos';
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
  const loadedChunksRef = useRef<Set<string>>(new Set());
  const loadingChunksRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!jobId) {
      setMedia(createEmptyState());
      setChunks([]);
      setIsComplete(false);
      setIsLoading(false);
      setError(null);
      loadedChunksRef.current.clear();
      loadingChunksRef.current.clear();
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setError(null);
    loadedChunksRef.current.clear();
    loadingChunksRef.current.clear();

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

  useEffect(() => {
    if (!jobId) {
      return;
    }

    const normalisedJobId =
      typeof jobId === 'string' && jobId.trim().length > 0 ? jobId.trim() : null;
    let cancelled = false;

    const ensureChunkLoaded = (chunk: LiveMediaChunk) => {
      const key = chunkKey(chunk);
      if (loadedChunksRef.current.has(key) || loadingChunksRef.current.has(key)) {
        return;
      }
      if (Array.isArray(chunk.sentences) && chunk.sentences.length > 0) {
        loadedChunksRef.current.add(key);
        return;
      }
      const hasMetadataReference =
        typeof chunk.metadataUrl === 'string' ||
        (normalisedJobId && typeof chunk.metadataPath === 'string');
      if (!hasMetadataReference) {
        return;
      }
      loadingChunksRef.current.add(key);
      fetchLibraryChunkMetadata(normalisedJobId, chunk)
        .then((sentences) => {
          if (cancelled || sentences === null) {
            return;
          }
          setChunks((current) =>
            current.map((existing) => {
              if (chunkKey(existing) !== key) {
                return existing;
              }
              const sentenceCount =
                sentences.length > 0
                  ? sentences.length
                  : typeof existing.sentenceCount === 'number'
                    ? existing.sentenceCount
                    : 0;
              return {
                ...existing,
                sentences: sentences.length > 0 ? sentences : [],
                sentenceCount,
              };
            }),
          );
          loadedChunksRef.current.add(key);
        })
        .catch((loadError) => {
          if (!cancelled) {
            console.warn('Unable to load library chunk metadata', loadError);
          }
          loadedChunksRef.current.add(key);
        })
        .finally(() => {
          loadingChunksRef.current.delete(key);
        });
    };

    chunks.forEach(ensureChunkLoaded);

    return () => {
      cancelled = true;
    };
  }, [chunks, jobId]);

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

    return {
      ...chunk,
      metadataUrl: tokenisedMetadataUrl,
      files: chunk.files.map((file) => ({ ...file, url: tokeniseUrl(file.url) })),
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

function chunkKey(chunk: LiveMediaChunk): string {
  return (
    chunk.chunkId ??
    chunk.rangeFragment ??
    `${chunk.startSentence ?? 'na'}-${chunk.endSentence ?? 'na'}`
  );
}

async function fetchLibraryChunkMetadata(
  jobId: string | null,
  chunk: LiveMediaChunk,
): Promise<ChunkSentenceMetadata[] | null> {
  let targetUrl = chunk.metadataUrl ?? null;

  if (!targetUrl) {
    const metadataPath = chunk.metadataPath ?? null;
    if (metadataPath && jobId) {
      const resolved = resolveLibraryMediaUrl(jobId, metadataPath);
      if (resolved) {
        targetUrl = resolved;
      }
    }
  }

  if (!targetUrl) {
    return null;
  }

  const authorisedUrl = appendAccessToken(targetUrl);

  try {
    const response = await fetch(authorisedUrl, {
      credentials: 'include',
    });
    if (!response.ok) {
      throw new Error(`Library chunk metadata request failed with status ${response.status}`);
    }
    const payload = await response.json();
    const sentences = payload?.sentences;
    if (Array.isArray(sentences)) {
      return sentences as ChunkSentenceMetadata[];
    }
    return [];
  } catch (error) {
    console.warn('Unable to load chunk metadata', authorisedUrl, error);
    return null;
  }
}
