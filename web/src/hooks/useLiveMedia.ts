import { useEffect, useMemo, useState } from 'react';
import { fetchJobMedia, fetchLiveJobMedia } from '../api/client';
import {
  PipelineMediaFile,
  PipelineMediaResponse,
  ProgressEventPayload,
  ChunkSentenceMetadata,
} from '../api/dtos';
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

export interface LiveMediaChunk {
  chunkId: string | null;
  rangeFragment: string | null;
  startSentence: number | null;
  endSentence: number | null;
  files: LiveMediaItem[];
  sentences?: ChunkSentenceMetadata[];
  metadataPath?: string | null;
  metadataUrl?: string | null;
  sentenceCount?: number | null;
}

export interface UseLiveMediaOptions {
  enabled?: boolean;
}

export interface UseLiveMediaResult {
  media: LiveMediaState;
  chunks: LiveMediaChunk[];
  isComplete: boolean;
  isLoading: boolean;
  error: Error | null;
}

const TEXT_TYPES = new Set(['text', 'html', 'pdf', 'epub', 'written', 'doc', 'docx', 'rtf']);

export function createEmptyState(): LiveMediaState {
  return {
    text: [],
    audio: [],
    video: []
  };
}

type MediaIndex = Map<string, LiveMediaItem>;

function buildMediaSignature(
  category: MediaCategory,
  path?: string | null,
  relativePath?: string | null,
  url?: string | null,
  name?: string | null
): string {
  const base = path ?? relativePath ?? url ?? name ?? '';
  return `${category}|${base}`.toLowerCase();
}

function buildEntrySignature(entry: Record<string, unknown>, category: MediaCategory): string {
  const path = toStringOrNull(entry.path);
  const relativePath = toStringOrNull(entry.relative_path);
  const url = toStringOrNull(entry.url);
  const name = toStringOrNull(entry.name);
  return buildMediaSignature(category, path, relativePath, url, name);
}

function buildItemSignature(item: LiveMediaItem): string {
  return buildMediaSignature(item.type, item.path ?? null, item.relative_path ?? null, item.url ?? null, item.name ?? null);
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
      const filesRaw = payload.files;
      if (!Array.isArray(filesRaw)) {
        return;
      }
      const chunkFiles: LiveMediaItem[] = [];
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
          item = registerMediaItem(state, index, built);
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
      const sentenceCount =
        typeof rawSentenceCount === 'number' && Number.isFinite(rawSentenceCount)
          ? rawSentenceCount
          : sentences.length > 0
            ? sentences.length
            : null;
      chunkRecords.push({
        chunkId: toStringOrNull(payload.chunk_id),
        rangeFragment: toStringOrNull(payload.range_fragment),
        startSentence: toNumberOrNull(payload.start_sentence),
        endSentence: toNumberOrNull(payload.end_sentence),
        files: chunkFiles,
        sentences: sentences.length > 0 ? sentences : undefined,
        metadataPath,
        metadataUrl,
        sentenceCount,
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
  const rangeFragment = toStringOrNull(entry.range_fragment ?? entry.rangeFragment);
  if (explicit) {
    return rangeFragment ? `${rangeFragment} • ${explicit}` : explicit;
  }

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
  const chunkId = toStringOrNull(entry.chunk_id ?? entry.chunkId) ?? undefined;
  const rangeFragment = toStringOrNull(entry.range_fragment ?? entry.rangeFragment) ?? undefined;
  const startSentence = toNumberOrNull(entry.start_sentence ?? entry.startSentence) ?? undefined;
  const endSentence = toNumberOrNull(entry.end_sentence ?? entry.endSentence) ?? undefined;

  return {
    name,
    url,
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
  index: MediaIndex;
} {
  if (!response || typeof response !== 'object') {
    return { media: createEmptyState(), chunks: [], complete: false, index: new Map() };
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

function chunkKey(chunk: LiveMediaChunk): string {
  return (
    chunk.chunkId ??
    chunk.rangeFragment ??
    `${chunk.startSentence ?? 'na'}-${chunk.endSentence ?? 'na'}`
  );
}

function mergeChunkCollections(base: LiveMediaChunk[], incoming: LiveMediaChunk[]): LiveMediaChunk[] {
  if (incoming.length === 0) {
    return base.slice();
  }

  const mergeChunk = (current: LiveMediaChunk, update: LiveMediaChunk): LiveMediaChunk => {
    const mergedFiles =
      update.files && update.files.length > 0
        ? update.files
        : current.files;
    const mergedSentences =
      update.sentences && update.sentences.length > 0
        ? update.sentences
        : current.sentences;

    const sentenceCount =
      update.sentences && update.sentences.length > 0
        ? update.sentences.length
        : typeof update.sentenceCount === 'number'
          ? update.sentenceCount
          : typeof current.sentenceCount === 'number'
            ? current.sentenceCount
            : mergedSentences && mergedSentences.length > 0
              ? mergedSentences.length
              : null;

    return {
      ...current,
      ...update,
      files: mergedFiles,
      sentences: mergedSentences,
      sentenceCount,
    };
  };

  const baseKeys = new Map<string, LiveMediaChunk>();
  base.forEach((chunk) => {
    baseKeys.set(chunkKey(chunk), chunk);
  });

  const incomingMap = new Map<string, LiveMediaChunk>();
  incoming.forEach((chunk) => {
    incomingMap.set(chunkKey(chunk), chunk);
  });

  const result: LiveMediaChunk[] = base.map((chunk) => {
    const key = chunkKey(chunk);
    const update = incomingMap.get(key);
    if (!update) {
      return chunk;
    }
    return mergeChunk(chunk, update);
  });

  incomingMap.forEach((chunk, key) => {
    if (!baseKeys.has(key)) {
      result.push({
        ...chunk,
        sentences: chunk.sentences && chunk.sentences.length > 0 ? chunk.sentences : undefined,
        sentenceCount:
          typeof chunk.sentenceCount === 'number'
            ? chunk.sentenceCount
            : chunk.sentences && chunk.sentences.length > 0
              ? chunk.sentences.length
              : null,
      });
    }
  });

  result.sort((a, b) => {
    const left = a.startSentence ?? Number.MAX_SAFE_INTEGER;
    const right = b.startSentence ?? Number.MAX_SAFE_INTEGER;
    if (left === right) {
      return (a.rangeFragment ?? '').localeCompare(b.rangeFragment ?? '');
    }
    return left - right;
  });

  return result;
}

function hasChunkSentences(chunks: LiveMediaChunk[]): boolean {
  return chunks.some(
    (chunk) =>
      (Array.isArray(chunk.sentences) && chunk.sentences.length > 0) ||
      (typeof chunk.sentenceCount === 'number' && chunk.sentenceCount > 0),
  );
}

export function useLiveMedia(
  jobId: string | null | undefined,
  options: UseLiveMediaOptions = {},
): UseLiveMediaResult {
  const { enabled = true } = options;
  const [media, setMedia] = useState<LiveMediaState>(() => createEmptyState());
  const [chunks, setChunks] = useState<LiveMediaChunk[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!enabled || !jobId) {
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

    fetchLiveJobMedia(jobId)
      .then((response: PipelineMediaResponse) => {
        if (cancelled) {
          return null;
        }
        const { media: initialMedia, chunks: initialChunks, complete } = normaliseFetchedMedia(response, jobId);
        setMedia(initialMedia);
        setChunks(initialChunks);
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
            } = normaliseFetchedMedia(fallbackResponse, jobId);
            if (fallbackMedia.text.length + fallbackMedia.audio.length + fallbackMedia.video.length === 0) {
              return;
            }
            setMedia(fallbackMedia);
            setChunks(fallbackChunks);
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
        if (event.event_type !== 'file_chunk_generated') {
          return;
        }

        const snapshot = extractGeneratedFiles(event.metadata);
        if (!snapshot) {
          return;
        }

        const { media: nextMedia, chunks: incomingChunks, complete } = normaliseGeneratedSnapshot(snapshot, jobId);
        setMedia((current) => mergeMediaBuckets(current, nextMedia));
        if (incomingChunks.length > 0) {
          setChunks((current) => mergeChunkCollections(current, incomingChunks));
        }
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
      isComplete,
      isLoading,
      error
    }),
    [media, chunks, isComplete, isLoading, error]
  );
}
