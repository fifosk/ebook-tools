import { useEffect, useMemo, useState } from 'react';
import { appendAccessToken, fetchLibraryMedia, resolveLibraryMediaUrl } from '../api/client';
import type { AudioTrackMetadata, PipelineMediaResponse } from '../api/dtos';
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

    fetchLibraryMedia(jobId, { summary: true })
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

  const resolveLibraryUrl = (value: string | null | undefined): string | null => {
    if (!value) {
      return null;
    }
    if (value.includes('://') || value.startsWith('data:')) {
      return value;
    }
    if (value.startsWith('/api/library/')) {
      return value;
    }
    if (normalisedJobId) {
      const relative = value.replace(/^\/+/, '');
      const resolved = resolveLibraryMediaUrl(normalisedJobId, relative);
      if (resolved) {
        return resolved;
      }
    }
    return value;
  };

  return chunks.map((chunk) => {
    let metadataUrl = chunk.metadataUrl ?? null;
    if (!metadataUrl && normalisedJobId && chunk.metadataPath) {
      metadataUrl = resolveLibraryMediaUrl(normalisedJobId, chunk.metadataPath);
    }
    const tokenisedMetadataUrl = tokeniseUrl(metadataUrl);
    const sourceTracks = chunk.audioTracks ?? null;
    let tokenisedTracks: Record<string, AudioTrackMetadata> | undefined;
    if (sourceTracks && typeof sourceTracks === 'object') {
      const legacyTracks = sourceTracks as Record<string, AudioTrackMetadata | string>;
      const entries: Record<string, AudioTrackMetadata> = {};
      Object.entries(legacyTracks).forEach(([key, rawValue]) => {
        if (!key) {
          return;
        }
        let descriptor: AudioTrackMetadata;
        if (typeof rawValue === 'string') {
          const trimmed = rawValue.trim();
          if (!trimmed) {
            return;
          }
          descriptor = { path: trimmed };
        } else if (rawValue && typeof rawValue === 'object') {
          descriptor = { ...rawValue } as AudioTrackMetadata;
        } else {
          return;
        }
        const pathValue =
          typeof descriptor.path === 'string' && descriptor.path.trim()
            ? descriptor.path.trim()
            : undefined;
        const baseUrl =
          typeof descriptor.url === 'string' && descriptor.url.trim()
            ? descriptor.url.trim()
            : undefined;
        const resolvedUrl = tokeniseUrl(resolveLibraryUrl(baseUrl ?? pathValue));
        entries[key] = {
          path: pathValue,
          url: resolvedUrl,
          duration:
            typeof descriptor.duration === 'number' && Number.isFinite(descriptor.duration)
              ? descriptor.duration
              : undefined,
          sampleRate:
            typeof descriptor.sampleRate === 'number' && Number.isFinite(descriptor.sampleRate)
              ? Math.trunc(descriptor.sampleRate)
              : undefined,
        };
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
