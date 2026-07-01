import type {
  AudioTrackMetadata,
  ChunkSentenceMetadata,
  PipelineMediaFile,
  ProgressEventPayload,
  TrackTimingPayload
} from '../api/dtos';

export type MediaCategory = 'text' | 'audio' | 'video';

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
  audioTracks?: Record<string, AudioTrackMetadata> | null;
  timingTracks?: TrackTimingPayload[] | null;
  /** Timing version - always "2" (backend pre-scales timing to match audio duration) */
  timingVersion?: string;
  /** Timing validation info from backend scaling */
  timingValidation?: Record<string, unknown> | null;
}

export type MediaIndex = Map<string, LiveMediaItem>;

const TEXT_TYPES = new Set(['text', 'html', 'pdf', 'epub', 'written', 'doc', 'docx', 'rtf', 'subtitle', 'ass', 'srt', 'vtt']);

export function createEmptyState(): LiveMediaState {
  return {
    text: [],
    audio: [],
    video: []
  };
}

export function toStringOrNull(value: unknown): string | null {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }
  return null;
}

export function toNumberOrNull(value: unknown): number | null {
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

export function normaliseCategory(type: unknown): MediaCategory | null {
  const stringValue = toStringOrNull(type)?.toLowerCase();
  if (!stringValue) {
    return null;
  }
  if (stringValue === 'audio' || stringValue.startsWith('audio_')) {
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

export function buildMediaSignature(
  category: MediaCategory,
  path?: string | null,
  relativePath?: string | null,
  url?: string | null,
  name?: string | null
): string {
  const base = path ?? relativePath ?? url ?? name ?? '';
  return `${category}|${base}`.toLowerCase();
}

export function buildEntrySignature(entry: Record<string, unknown>, category: MediaCategory): string {
  const path = toStringOrNull(entry.path);
  const relativePath = toStringOrNull(entry.relative_path);
  const url = toStringOrNull(entry.url);
  const name = toStringOrNull(entry.name);
  return buildMediaSignature(category, path, relativePath, url, name);
}

export function buildItemSignature(item: LiveMediaItem): string {
  return buildMediaSignature(item.type, item.path ?? null, item.relative_path ?? null, item.url ?? null, item.name ?? null);
}

export function deriveRelativePath(jobId: string | null | undefined, rawPath: string | null): string | null {
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

export function deriveLiveMediaName(entry: Record<string, unknown>, resolvedUrl: string | null): string {
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
      // Ignore URL parsing errors and fall back to range fragment or default.
    }
  }

  if (rangeFragment) {
    return rangeFragment;
  }

  return 'media';
}

export function hasAudioTracks(
  tracks: Record<string, AudioTrackMetadata> | null | undefined
): tracks is Record<string, AudioTrackMetadata> {
  return Boolean(tracks && Object.keys(tracks).length > 0);
}

export function extractAudioTracks(source: unknown): Record<string, AudioTrackMetadata> | null {
  if (!source || typeof source !== 'object') {
    return null;
  }
  const entries: Record<string, AudioTrackMetadata> = {};
  const register = (key: string | null, value: unknown) => {
    if (!key) {
      return;
    }
    const trimmedKey = key.trim();
    if (!trimmedKey) {
      return;
    }
    if (typeof value === 'string') {
      const trimmedValue = value.trim();
      if (!trimmedValue) {
        return;
      }
      entries[trimmedKey] = { path: trimmedValue };
      return;
    }
    if (typeof value !== 'object' || value === null) {
      return;
    }
    const record = value as Record<string, unknown>;
    const path = typeof record.path === 'string' ? record.path.trim() : null;
    const url = typeof record.url === 'string' ? record.url.trim() : null;
    const duration =
      typeof record.duration === 'number' && Number.isFinite(record.duration)
        ? record.duration
        : null;
    const sampleRate =
      typeof record.sampleRate === 'number' && Number.isFinite(record.sampleRate)
        ? Math.trunc(record.sampleRate)
        : null;
    const payload: AudioTrackMetadata = {};
    if (path) {
      payload.path = path;
    }
    if (url) {
      payload.url = url;
    }
    if (duration !== null) {
      payload.duration = duration;
    }
    if (sampleRate !== null) {
      payload.sampleRate = sampleRate;
    }
    if (Object.keys(payload).length === 0) {
      return;
    }
    entries[trimmedKey] = payload;
  };

  if (Array.isArray(source)) {
    source.forEach((entry) => {
      if (!entry || typeof entry !== 'object') {
        return;
      }
      const record = entry as Record<string, unknown>;
      const key =
        typeof record.key === 'string'
          ? record.key
          : typeof record.kind === 'string'
            ? record.kind
            : null;
      register(key, record.url);
    });
  } else {
    Object.entries(source as Record<string, unknown>).forEach(([key, value]) => {
      register(key, value);
    });
  }

  return Object.keys(entries).length > 0 ? entries : null;
}

export function mergeMediaBuckets(base: LiveMediaState, incoming: LiveMediaState): LiveMediaState {
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

export function extractGeneratedFiles(metadata: ProgressEventPayload['metadata']): unknown {
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

export function mergeChunkCollections(
  base: LiveMediaChunk[],
  incoming: LiveMediaChunk[]
): LiveMediaChunk[] {
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
    let mergedAudioTracks: Record<string, AudioTrackMetadata> | null | undefined;
    if (update.audioTracks === null) {
      mergedAudioTracks = null;
    } else if (hasAudioTracks(update.audioTracks)) {
      const baseTracks = hasAudioTracks(current.audioTracks) ? current.audioTracks : undefined;
      const combined: Record<string, AudioTrackMetadata> = { ...(baseTracks ?? {}) };
      Object.entries(update.audioTracks).forEach(([key, value]) => {
        combined[key] = {
          ...(combined[key] ?? {}),
          ...value
        };
      });
      mergedAudioTracks = combined;
    } else if (hasAudioTracks(current.audioTracks)) {
      mergedAudioTracks = current.audioTracks;
    } else if (update.audioTracks === null || current.audioTracks === null) {
      mergedAudioTracks = null;
    }
    let mergedTimingTracks: TrackTimingPayload[] | null | undefined = undefined;
    if (Array.isArray(update.timingTracks) && update.timingTracks.length > 0) {
      mergedTimingTracks = update.timingTracks;
    } else if (Array.isArray(current.timingTracks) && current.timingTracks.length > 0) {
      mergedTimingTracks = current.timingTracks;
    } else if (update.timingTracks === null || current.timingTracks === null) {
      mergedTimingTracks = null;
    }

    return {
      ...current,
      ...update,
      files: mergedFiles,
      sentences: mergedSentences,
      sentenceCount,
      audioTracks: mergedAudioTracks ?? null,
      timingTracks: mergedTimingTracks ?? null
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
        timingTracks:
          Array.isArray(chunk.timingTracks) && chunk.timingTracks.length > 0
            ? chunk.timingTracks
            : chunk.timingTracks ?? null
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

export function hasChunkSentences(chunks: LiveMediaChunk[]): boolean {
  return chunks.some(
    (chunk) =>
      (Array.isArray(chunk.sentences) && chunk.sentences.length > 0) ||
      (typeof chunk.sentenceCount === 'number' && chunk.sentenceCount > 0)
  );
}
