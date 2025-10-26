import { useEffect, useMemo, useState } from 'react';
import { fetchLiveJobMedia } from '../api/client';
import { PipelineMediaFile, PipelineMediaResponse, ProgressEventPayload } from '../api/dtos';
import { subscribeToJobEvents } from '../services/api';
import { resolve as resolveStoragePath } from '../utils/storageResolver';

type MediaCategory = 'text' | 'audio' | 'video';

export interface LiveMediaItem extends PipelineMediaFile {
  type: MediaCategory;
}

export interface LiveMediaState {
  text: LiveMediaItem[];
  audio: LiveMediaItem[];
  video: LiveMediaItem[];
}

export interface UseLiveMediaOptions {
  enabled?: boolean;
}

export interface UseLiveMediaResult {
  media: LiveMediaState;
  isLoading: boolean;
  error: Error | null;
}

const TEXT_TYPES = new Set(['text', 'html', 'pdf', 'epub', 'written', 'doc', 'docx', 'rtf']);

function createEmptyState(): LiveMediaState {
  return {
    text: [],
    audio: [],
    video: []
  };
}

function toStringOrNull(value: unknown): string | null {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }
  return null;
}

function toNumberOrNull(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function normaliseCategory(type: unknown): MediaCategory | null {
  const stringValue = toStringOrNull(type)?.toLowerCase();
  if (!stringValue) {
    return null;
  }
  if (stringValue === 'audio') {
    return 'audio';
  }
  if (stringValue === 'video') {
    return 'video';
  }
  if (TEXT_TYPES.has(stringValue) || stringValue.startsWith('html') || stringValue.startsWith('pdf')) {
    return 'text';
  }
  return null;
}

function deriveRelativePath(jobId: string | null | undefined, rawPath: string | null): string | null {
  if (!rawPath) {
    return null;
  }

  const normalised = rawPath.replace(/\\+/g, '/');
  if (normalised.includes('://')) {
    return null;
  }

  if (jobId) {
    const marker = `/${jobId}/`;
    const markerIndex = normalised.indexOf(marker);
    if (markerIndex >= 0) {
      return normalised.slice(markerIndex + marker.length);
    }
    const prefix = `${jobId}/`;
    if (normalised.startsWith(prefix)) {
      return normalised.slice(prefix.length);
    }
  }

  if (!normalised.startsWith('/')) {
    return normalised;
  }

  return null;
}

function resolveFileUrl(
  jobId: string | null | undefined,
  entry: Record<string, unknown>,
): string | null {
  const explicitUrl = toStringOrNull(entry.url);
  if (explicitUrl) {
    return explicitUrl;
  }

  const relativePath =
    toStringOrNull(entry.relative_path) ??
    deriveRelativePath(jobId, toStringOrNull(entry.path));

  if (relativePath) {
    try {
      return resolveStoragePath(jobId ?? null, relativePath);
    } catch (error) {
      console.warn('Unable to resolve storage URL for generated media', error);
    }
  }

  const fallbackPath = toStringOrNull(entry.path);
  if (fallbackPath && fallbackPath.includes('://')) {
    return fallbackPath;
  }

  return null;
}

function deriveName(entry: Record<string, unknown>, resolvedUrl: string | null): string {
  const explicit = toStringOrNull(entry.name);
  if (explicit) {
    return explicit;
  }

  const rangeFragment = toStringOrNull(entry.range_fragment);
  const relative = toStringOrNull(entry.relative_path);
  const pathValue = toStringOrNull(entry.path);

  const candidate = relative ?? pathValue;
  if (candidate) {
    const segments = candidate.replace(/\\+/g, '/').split('/').filter(Boolean);
    if (segments.length > 0) {
      return segments[segments.length - 1];
    }
  }

  if (resolvedUrl) {
    try {
      const url = new URL(resolvedUrl);
      const segments = url.pathname.split('/').filter(Boolean);
      if (segments.length > 0) {
        return segments[segments.length - 1];
      }
    } catch (error) {
      // Ignore URL parsing errors and fall back to range fragment or default
    }
  }

  if (rangeFragment) {
    return rangeFragment;
  }

  return 'media';
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

  const name = deriveName(entry, url);
  const size = toNumberOrNull(entry.size) ?? undefined;
  const updatedAt = toStringOrNull(entry.updated_at) ?? undefined;
  const sourceRaw = toStringOrNull(entry.source);
  const source: 'completed' | 'live' = sourceRaw === 'completed' ? 'completed' : 'live';

  return {
    name,
    url,
    size,
    updated_at: updatedAt,
    source,
    type: category
  };
}

function normaliseFetchedMedia(
  response: PipelineMediaResponse | null | undefined,
  jobId: string | null | undefined,
): LiveMediaState {
  if (!response || typeof response !== 'object') {
    return createEmptyState();
  }

  const media = response.media ?? {};
  const result = createEmptyState();

  Object.entries(media).forEach(([rawType, files]) => {
    const category = normaliseCategory(rawType);
    if (!category || !Array.isArray(files)) {
      return;
    }

    files.forEach((file) => {
      if (!file) {
        return;
      }

      const record = file as Record<string, unknown>;
      const item = buildLiveMediaItem(record, category, jobId);
      if (item) {
        result[category].push(item);
      }
    });
  });

  return result;
}

function normaliseGeneratedSnapshot(
  snapshot: unknown,
  jobId: string | null | undefined,
): LiveMediaState {
  if (!snapshot || typeof snapshot !== 'object') {
    return createEmptyState();
  }

  const files = (snapshot as Record<string, unknown>).files;
  if (!Array.isArray(files)) {
    return createEmptyState();
  }

  const result = createEmptyState();

  files.forEach((entry) => {
    if (!entry || typeof entry !== 'object') {
      return;
    }

    const category = normaliseCategory((entry as Record<string, unknown>).type);
    if (!category) {
      return;
    }

    const item = buildLiveMediaItem(entry as Record<string, unknown>, category, jobId);
    if (item) {
      result[category].push(item);
    }
  });

  return result;
}

function mergeMediaBuckets(base: LiveMediaState, incoming: LiveMediaState): LiveMediaState {
  const categories: MediaCategory[] = ['text', 'audio', 'video'];
  const merged: LiveMediaState = createEmptyState();

  categories.forEach((category) => {
    const seen = new Map<string, LiveMediaItem>();
    const register = (item: LiveMediaItem) => {
      const key = item.url ?? `${item.type}:${item.name}`;
      const existing = seen.get(key);
      if (existing) {
        seen.set(key, {
          ...existing,
          ...item,
          name: item.name || existing.name,
          url: item.url ?? existing.url,
          size: item.size ?? existing.size,
          updated_at: item.updated_at ?? existing.updated_at,
          source: item.source ?? existing.source
        });
      } else {
        seen.set(key, item);
      }
    };

    base[category].forEach(register);
    incoming[category].forEach(register);

    merged[category] = Array.from(seen.values());
  });

  return merged;
}

function extractGeneratedFiles(metadata: ProgressEventPayload['metadata']): unknown {
  if (!metadata || typeof metadata !== 'object') {
    return null;
  }
  return (metadata as Record<string, unknown>).generated_files;
}

export function useLiveMedia(
  jobId: string | null | undefined,
  options: UseLiveMediaOptions = {},
): UseLiveMediaResult {
  const { enabled = true } = options;
  const [media, setMedia] = useState<LiveMediaState>(() => createEmptyState());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!enabled || !jobId) {
      setMedia(createEmptyState());
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
          return;
        }
        setMedia(normaliseFetchedMedia(response, jobId));
      })
      .catch((fetchError: unknown) => {
        if (cancelled) {
          return;
        }
        const errorInstance =
          fetchError instanceof Error ? fetchError : new Error(String(fetchError));
        setError(errorInstance);
        setMedia(createEmptyState());
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
        if (event.event_type !== 'file_chunk_generated') {
          return;
        }

        const snapshot = extractGeneratedFiles(event.metadata);
        if (!snapshot) {
          return;
        }

        const nextMedia = normaliseGeneratedSnapshot(snapshot, jobId);
        setMedia((current) => mergeMediaBuckets(current, nextMedia));
      }
    });
  }, [enabled, jobId]);

  return useMemo(
    () => ({
      media,
      isLoading,
      error
    }),
    [media, isLoading, error]
  );
}
