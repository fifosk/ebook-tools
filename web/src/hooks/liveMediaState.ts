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

export function createEmptyState(): LiveMediaState {
  return {
    text: [],
    audio: [],
    video: []
  };
}

export function hasAudioTracks(
  tracks: Record<string, AudioTrackMetadata> | null | undefined
): tracks is Record<string, AudioTrackMetadata> {
  return Boolean(tracks && Object.keys(tracks).length > 0);
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
