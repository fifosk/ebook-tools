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

const AUDIO_EXTENSIONS = new Set(['.mp3', '.wav', '.aac', '.m4a', '.flac']);
const VIDEO_EXTENSIONS = new Set(['.mp4', '.mov', '.mkv', '.webm']);
const TEXT_EXTENSIONS = new Set(['.html', '.htm', '.pdf', '.epub', '.txt', '.doc', '.docx', '.rtf']);

function inferCategoryFromPath(value: string | null | undefined): MediaCategory | null {
  const candidate = toStringOrNull(value)?.toLowerCase();
  if (!candidate) {
    return null;
  }

  const extensionMatch = candidate.match(/\.([a-z0-9]+)(?:\?|#|$)/i);
  if (!extensionMatch) {
    return null;
  }

  const extension = `.${extensionMatch[1].toLowerCase()}`;
  if (AUDIO_EXTENSIONS.has(extension)) {
    return 'audio';
  }
  if (VIDEO_EXTENSIONS.has(extension)) {
    return 'video';
  }
  if (TEXT_EXTENSIONS.has(extension)) {
    return 'text';
  }

  return null;
}

function resolveCategory(
  entry: Record<string, unknown>,
  hint: MediaCategory | null,
): MediaCategory | null {
  const explicit = normaliseCategory(entry.type);
  if (explicit) {
    return explicit;
  }

  if (hint) {
    return hint;
  }

  const pathCandidate =
    toStringOrNull(entry.relative_path) ??
    toStringOrNull(entry.path) ??
    toStringOrNull(entry.url);

  return inferCategoryFromPath(pathCandidate);
}

function buildLiveMediaItem(
  entry: Record<string, unknown>,
  jobId: string | null | undefined,
  hint: MediaCategory | null = null,
): LiveMediaItem | null {
  const category = resolveCategory(entry, hint);
  if (!category) {
    return null;
  }

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
      const item = buildLiveMediaItem(record, jobId, category);
      if (item) {
        result[item.type].push(item);
      }
    });
  });

  return result;
}

function inferCategoryHintFromKey(key: string): MediaCategory | null {
  const normalised = key.toLowerCase();
  const direct = normaliseCategory(normalised);
  if (direct) {
    return direct;
  }

  if (normalised.endsWith('_files')) {
    return normaliseCategory(normalised.slice(0, -6));
  }

  if (normalised.endsWith('_media')) {
    return normaliseCategory(normalised.slice(0, -6));
  }

  return null;
}

function collectSnapshotEntries(snapshot: unknown): Array<{
  entry: Record<string, unknown>;
  hint: MediaCategory | null;
}> {
  const results: Array<{ entry: Record<string, unknown>; hint: MediaCategory | null }> = [];

  function visit(
    candidate: unknown,
    context: Record<string, unknown>,
    hint: MediaCategory | null,
    depth: number,
  ): void {
    if (!candidate || depth > 6) {
      return;
    }

    if (Array.isArray(candidate)) {
      candidate.forEach((value) => {
        visit(value, context, hint, depth + 1);
      });
      return;
    }

    if (typeof candidate !== 'object') {
      return;
    }

    const record = candidate as Record<string, unknown>;
    const nextContext: Record<string, unknown> = { ...context };

    const chunkId = record.chunk_id;
    if (chunkId !== undefined) {
      nextContext.chunk_id = chunkId;
    }

    const rangeFragment = record.range_fragment;
    if (rangeFragment !== undefined) {
      nextContext.range_fragment = rangeFragment;
    }

    const startSentence = record.start_sentence;
    if (startSentence !== undefined) {
      nextContext.start_sentence = startSentence;
    }

    const endSentence = record.end_sentence;
    if (endSentence !== undefined) {
      nextContext.end_sentence = endSentence;
    }

    const looksLikeFile =
      toStringOrNull(record.path) !== null ||
      toStringOrNull(record.relative_path) !== null ||
      toStringOrNull(record.url) !== null;

    const entryHint = resolveCategory(record, hint);
    if (looksLikeFile) {
      const payload: Record<string, unknown> = { ...nextContext, ...record };
      if (!payload.type && entryHint) {
        payload.type = entryHint;
      }
      results.push({ entry: payload, hint: entryHint });
    }

    Object.entries(record).forEach(([key, value]) => {
      if (value === null || value === undefined) {
        return;
      }
      if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
        return;
      }
      const keyHint = inferCategoryHintFromKey(key) ?? entryHint ?? hint;
      visit(value, nextContext, keyHint, depth + 1);
    });
  }

  visit(snapshot, {}, null, 0);
  return results;
}

function normaliseGeneratedSnapshot(
  snapshot: unknown,
  jobId: string | null | undefined,
): LiveMediaState {
  if (!snapshot || typeof snapshot !== 'object') {
    return createEmptyState();
  }

  const collected = collectSnapshotEntries(snapshot);
  if (collected.length === 0) {
    return createEmptyState();
  }

  const result = createEmptyState();

  collected.forEach(({ entry, hint }) => {
    const item = buildLiveMediaItem(entry, jobId, hint);
    if (item) {
      result[item.type].push(item);
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

function hasMediaEntries(state: LiveMediaState): boolean {
  return state.text.length > 0 || state.audio.length > 0 || state.video.length > 0;
}

function findGeneratedFiles(
  candidate: unknown,
  depth: number,
): unknown {
  if (!candidate || depth > 4) {
    return null;
  }

  if (Array.isArray(candidate)) {
    for (const value of candidate) {
      const nested = findGeneratedFiles(value, depth + 1);
      if (nested) {
        return nested;
      }
    }
    return null;
  }

  if (typeof candidate !== 'object') {
    return null;
  }

  const record = candidate as Record<string, unknown>;
  if (record.generated_files) {
    return record.generated_files;
  }

  for (const value of Object.values(record)) {
    const nested = findGeneratedFiles(value, depth + 1);
    if (nested) {
      return nested;
    }
  }

  return null;
}

function normaliseMetadata(metadata: unknown): Record<string, unknown> | null {
  if (!metadata) {
    return null;
  }

  if (typeof metadata === 'string') {
    try {
      const parsed = JSON.parse(metadata);
      if (parsed && typeof parsed === 'object') {
        return parsed as Record<string, unknown>;
      }
      return null;
    } catch (error) {
      console.warn('Unable to parse progress event metadata JSON', error);
      return null;
    }
  }

  if (typeof metadata === 'object') {
    return metadata as Record<string, unknown>;
  }

  return null;
}

function extractGeneratedFiles(metadata: Record<string, unknown> | null): unknown {
  if (!metadata) {
    return null;
  }
  return findGeneratedFiles(metadata, 0);
}

function includesDeferredWrite(value: string | null | undefined): boolean {
  const normalised = toStringOrNull(value)?.toLowerCase();
  if (!normalised) {
    return false;
  }
  if (normalised.includes('deferred_write') || normalised.includes('deferred write')) {
    return true;
  }
  return normalised.includes('deferred') && normalised.includes('write');
}

function findStage(candidate: unknown, depth: number): string | null {
  if (!candidate || depth > 4) {
    return null;
  }

  if (Array.isArray(candidate)) {
    for (const value of candidate) {
      const nested = findStage(value, depth + 1);
      if (nested) {
        return nested;
      }
    }
    return null;
  }

  if (typeof candidate !== 'object') {
    return null;
  }

  const record = candidate as Record<string, unknown>;
  const directStage = toStringOrNull(record.stage);
  if (directStage) {
    return directStage;
  }

  for (const value of Object.values(record)) {
    const nested = findStage(value, depth + 1);
    if (nested) {
      return nested;
    }
  }

  return null;
}

function containsDeferredWrite(candidate: unknown, depth: number): boolean {
  if (!candidate || depth > 4) {
    return false;
  }

  if (typeof candidate === 'string') {
    return includesDeferredWrite(candidate);
  }

  if (Array.isArray(candidate)) {
    return candidate.some((value) => containsDeferredWrite(value, depth + 1));
  }

  if (typeof candidate === 'object') {
    const record = candidate as Record<string, unknown>;
    for (const [key, value] of Object.entries(record)) {
      if (includesDeferredWrite(key) || containsDeferredWrite(value, depth + 1)) {
        return true;
      }
    }
  }

  return false;
}

function shouldRefreshForEvent(
  event: ProgressEventPayload,
  metadata: Record<string, unknown> | null,
): boolean {
  const eventType = toStringOrNull(event.event_type)?.toLowerCase();
  if (eventType) {
    if (eventType.includes('file_chunk')) {
      return true;
    }
    if (eventType.includes('deferred') && eventType.includes('write')) {
      return true;
    }
  }

  if (!metadata) {
    return false;
  }

  const stage = findStage(metadata, 0);
  if (includesDeferredWrite(stage)) {
    return true;
  }

  if (containsDeferredWrite(metadata, 0)) {
    return true;
  }

  return false;
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

    let cancelled = false;
    let pendingRefresh: Promise<void> | null = null;

    const refreshFromServer = () => {
      if (pendingRefresh) {
        return pendingRefresh;
      }

      pendingRefresh = fetchLiveJobMedia(jobId)
        .then((response: PipelineMediaResponse) => {
          if (cancelled) {
            return;
          }
          setMedia((current) => mergeMediaBuckets(current, normaliseFetchedMedia(response, jobId)));
        })
        .catch((refreshError: unknown) => {
          if (!cancelled) {
            console.warn('Failed to refresh live media after event', refreshError);
          }
        })
        .finally(() => {
          pendingRefresh = null;
        });

      return pendingRefresh;
    };

    const unsubscribe = subscribeToJobEvents(jobId, {
      onEvent: (event) => {
        const metadataRecord = normaliseMetadata(event.metadata);
        const snapshot = extractGeneratedFiles(metadataRecord);
        if (!snapshot) {
          if (shouldRefreshForEvent(event, metadataRecord)) {
            void refreshFromServer();
          }
          return;
        }

        const nextMedia = normaliseGeneratedSnapshot(snapshot, jobId);
        if (hasMediaEntries(nextMedia)) {
          setMedia((current) => mergeMediaBuckets(current, nextMedia));
          if (shouldRefreshForEvent(event, metadataRecord)) {
            void refreshFromServer();
          }
        } else {
          void refreshFromServer();
        }
      }
    });
    return () => {
      cancelled = true;
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    };
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
