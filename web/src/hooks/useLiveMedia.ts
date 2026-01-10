import { useCallback, useEffect, useMemo, useState } from 'react';
import type { RefObject } from 'react';
import { appendAccessTokenToStorageUrl, fetchJobMedia, fetchLiveJobMedia } from '../api/client';
import {
  AudioTrackMetadata,
  PipelineMediaFile,
  PipelineMediaResponse,
  ProgressEventPayload,
  ChunkSentenceMetadata,
  TrackTimingPayload,
  WordTiming,
  PauseTiming,
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
  audioTracks?: Record<string, AudioTrackMetadata> | null;
  timingTracks?: TrackTimingPayload[] | null;
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

const TEXT_TYPES = new Set(['text', 'html', 'pdf', 'epub', 'written', 'doc', 'docx', 'rtf', 'subtitle', 'ass', 'srt', 'vtt']);

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

function extractAudioTracks(source: unknown): Record<string, AudioTrackMetadata> | null {
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

function hasAudioTracks(
  tracks: Record<string, AudioTrackMetadata> | null | undefined,
): tracks is Record<string, AudioTrackMetadata> {
  return Boolean(tracks && Object.keys(tracks).length > 0);
}

const VALID_TRACK_TYPES: Set<TrackTimingPayload['trackType']> = new Set([
  'translated',
  'original_translated',
  'original',
]);

function normaliseTrackType(value: unknown): TrackTimingPayload['trackType'] | null {
  const raw = toStringOrNull(value)?.toLowerCase();
  if (!raw) {
    return null;
  }
  if (VALID_TRACK_TYPES.has(raw as TrackTimingPayload['trackType'])) {
    return raw as TrackTimingPayload['trackType'];
  }
  if (raw === 'original-translated' || raw === 'originaltranslated') {
    return 'original_translated';
  }
  if (raw === 'original' || raw === 'orig') {
    return 'original';
  }
  if (raw === 'translation' || raw === 'translated') {
    return 'translated';
  }
  return null;
}

function normaliseWordLanguage(value: unknown): WordTiming['lang'] | null {
  const raw = toStringOrNull(value)?.toLowerCase();
  if (!raw) {
    return null;
  }
  if (raw === 'orig' || raw === 'original') {
    return 'orig';
  }
  if (raw === 'xlit' || raw === 'translit' || raw === 'transliteration') {
    return 'xlit';
  }
  if (raw === 'trans' || raw === 'translation') {
    return 'trans';
  }
  return null;
}

function normaliseWordTimings(source: unknown): WordTiming[] {
  if (!Array.isArray(source)) {
    return [];
  }
  const result: WordTiming[] = [];
  source.forEach((entry) => {
    if (!entry || typeof entry !== 'object') {
      return;
    }
    const record = entry as Record<string, unknown>;
    const id = toStringOrNull(record.id);
    const sentenceId = toNumberOrNull(record.sentence_id ?? record.sentenceId);
    const tokenIdx = toNumberOrNull(record.token_idx ?? record.tokenIdx);
    const lang = normaliseWordLanguage(record.lang);
    const t0 = toNumberOrNull(record.t0);
    const t1 = toNumberOrNull(record.t1);
    if (!id || sentenceId === null || tokenIdx === null || !lang || t0 === null || t1 === null) {
      return;
    }
    result.push({
      id,
      sentenceId,
      tokenIdx,
      lang,
      text: toStringOrNull(record.text) ?? '',
      t0,
      t1,
    });
  });

  result.sort((left, right) => {
    const timeDelta = left.t0 - right.t0;
    if (timeDelta !== 0) {
      return timeDelta;
    }
    const endDelta = left.t1 - right.t1;
    if (endDelta !== 0) {
      return endDelta;
    }
    if (left.sentenceId !== right.sentenceId) {
      return left.sentenceId - right.sentenceId;
    }
    if (left.tokenIdx !== right.tokenIdx) {
      return left.tokenIdx - right.tokenIdx;
    }
    return left.id.localeCompare(right.id);
  });

  return result;
}

function normalisePauseTimings(source: unknown): PauseTiming[] {
  if (!Array.isArray(source)) {
    return [];
  }
  const result: PauseTiming[] = [];
  source.forEach((entry) => {
    if (!entry || typeof entry !== 'object') {
      return;
    }
    const record = entry as Record<string, unknown>;
    const t0 = toNumberOrNull(record.t0);
    const t1 = toNumberOrNull(record.t1);
    if (t0 === null || t1 === null) {
      return;
    }
    const reasonRaw = toStringOrNull(record.reason);
    const reason =
      reasonRaw === 'silence' || reasonRaw === 'tempo' || reasonRaw === 'gap' ? reasonRaw : undefined;
    result.push({
      t0,
      t1,
      reason,
    });
  });
  result.sort((left, right) => {
    const delta = left.t0 - right.t0;
    if (delta !== 0) {
      return delta;
    }
    return left.t1 - right.t1;
  });
  return result;
}

function normaliseTrackTimingCollection(source: unknown): TrackTimingPayload[] | null {
  if (!source) {
    return null;
  }
  const entries = Array.isArray(source) ? source : [source];
  const payloads: TrackTimingPayload[] = [];
  entries.forEach((entry) => {
    const converted = convertTrackTimingEntry(entry);
    if (converted && converted.length > 0) {
      payloads.push(...converted);
    }
  });
  return payloads.length > 0 ? payloads : null;
}

function convertTrackTimingEntry(entry: unknown): TrackTimingPayload[] | null {
  if (!entry || typeof entry !== 'object') {
    return null;
  }
  const record = entry as Record<string, unknown>;
  const trackType = normaliseTrackType(record.track_type ?? record.trackType);
  if (trackType) {
    const chunkId = toStringOrNull(record.chunk_id ?? record.chunkId) ?? '';
    const words = normaliseWordTimings(record.words);
    const pauses = normalisePauseTimings(record.pauses);
    const trackOffset = toNumberOrNull(record.track_offset ?? record.trackOffset) ?? 0;
    const tempoFactorRaw = toNumberOrNull(record.tempo_factor ?? record.tempoFactor);
    const tempoFactor = tempoFactorRaw && tempoFactorRaw > 0 ? tempoFactorRaw : 1;
    const version = toStringOrNull(record.version) ?? '1';
    return [
      {
        trackType,
        chunkId,
        words,
        pauses,
        trackOffset,
        tempoFactor,
        version,
      },
    ];
  }
  return convertLegacyTimingTracks(record);
}

function convertLegacyTimingTracks(record: Record<string, unknown>): TrackTimingPayload[] | null {
  const mixEntries = Array.isArray(record.mix) ? (record.mix as unknown[]) : null;
  const translationEntries = Array.isArray(record.translation)
    ? (record.translation as unknown[])
    : null;
  const originalEntries = Array.isArray(record.original)
    ? (record.original as unknown[])
    : null;
  if (!mixEntries && !translationEntries && !originalEntries) {
    return null;
  }
  const chunkId = toStringOrNull(record.chunk_id ?? record.chunkId) ?? '';
  const trackOffset = toNumberOrNull(record.track_offset ?? record.trackOffset) ?? 0;
  const tempoFactorRaw = toNumberOrNull(record.tempo_factor ?? record.tempoFactor);
  const tempoFactor = tempoFactorRaw && tempoFactorRaw > 0 ? tempoFactorRaw : 1;
  const version = toStringOrNull(record.version) ?? '1';
  const payloads: TrackTimingPayload[] = [];
  if (Array.isArray(translationEntries) && translationEntries.length > 0) {
    const words = buildWordTimingsFromLegacyTokens(
      translationEntries,
      chunkId,
      'trans',
      false,
      true,
    );
    if (words.length > 0) {
      payloads.push({
        trackType: 'translated',
        chunkId,
        words,
        pauses: [],
        trackOffset,
        tempoFactor,
        version,
      });
    }
  }
  if (Array.isArray(mixEntries) && mixEntries.length > 0) {
    const words = buildWordTimingsFromLegacyTokens(
      mixEntries,
      chunkId,
      'orig',
      true,
      false,
    );
    if (words.length > 0) {
      payloads.push({
        trackType: 'original_translated',
        chunkId,
        words,
        pauses: [],
        trackOffset,
        tempoFactor,
        version,
      });
    }
  }
  if (Array.isArray(originalEntries) && originalEntries.length > 0) {
    const words = buildWordTimingsFromLegacyTokens(
      originalEntries,
      chunkId,
      'orig',
      false,
      false,
    );
    if (words.length > 0) {
      payloads.push({
        trackType: 'original',
        chunkId,
        words,
        pauses: [],
        trackOffset,
        tempoFactor,
        version,
      });
    }
  }
  return payloads.length > 0 ? payloads : null;
}

function buildWordTimingsFromLegacyTokens(
  tokens: unknown[],
  chunkId: string,
  defaultLang: WordTiming['lang'],
  laneAware: boolean,
  applyGateOffset: boolean,
): WordTiming[] {
  const timings: WordTiming[] = [];
  tokens.forEach((token) => {
    if (!token || typeof token !== 'object') {
      return;
    }
    const record = token as Record<string, unknown>;
    const sentenceId = toNumberOrNull(record.sentenceIdx ?? record.sentence_id ?? record.sentenceId);
    const tokenIdx = toNumberOrNull(record.wordIdx ?? record.token_idx ?? record.tokenIdx);
    let start = toNumberOrNull(record.start ?? record.t0);
    let end = toNumberOrNull(record.end ?? record.t1 ?? start);
    if (sentenceId === null || tokenIdx === null || start === null || end === null) {
      return;
    }
    if (applyGateOffset) {
      const gate = toNumberOrNull(record.start_gate ?? record.startGate);
      if (gate !== null && start >= gate - 1e-3) {
        start -= gate;
        end -= gate;
      }
    }
    if (start < 0) {
      end -= start;
      start = 0;
    }
    if (end < start) {
      end = start;
    }
    let lang: WordTiming['lang'] | null = defaultLang;
    if (laneAware) {
      lang = normaliseWordLanguage(record.lane) ?? defaultLang;
    }
    if (!lang) {
      lang = 'trans';
    }
    const id = createLegacyWordTimingId(chunkId, lang, sentenceId, tokenIdx);
    timings.push({
      id,
      sentenceId,
      tokenIdx,
      lang,
      text: toStringOrNull(record.text) ?? '',
      t0: start,
      t1: end,
    });
  });
  return timings;
}

function createLegacyWordTimingId(
  chunkId: string,
  lang: WordTiming['lang'],
  sentenceId: number,
  tokenIdx: number,
): string {
  const prefix = chunkId || 'chunk';
  return `${prefix}:${lang}:${sentenceId}:${tokenIdx}`;
}

function attachChunkIdToTimingSource(source: unknown, chunkId: string | null): unknown {
  if (!chunkId || !source || typeof source !== 'object' || Array.isArray(source)) {
    return source;
  }
  const record = source as Record<string, unknown>;
  if ('chunk_id' in record || 'chunkId' in record) {
    return source;
  }
  return { chunk_id: chunkId, ...record };
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
      const chunkId = toStringOrNull(payload.chunk_id ?? payload.chunkId);
      const filesRaw = payload.files;
      if (!Array.isArray(filesRaw)) {
        return;
      }
      const chunkFiles: LiveMediaItem[] = [];
      const chunkRangeFragment = toStringOrNull(payload.range_fragment ?? payload.rangeFragment);
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
          const enriched: LiveMediaItem = {
            ...built,
            chunk_id: built.chunk_id ?? chunkId ?? null,
            range_fragment: built.range_fragment ?? chunkRangeFragment ?? null,
          };
          item = registerMediaItem(state, index, enriched);
        } else {
          if (item.chunk_id == null) {
            item.chunk_id = chunkId ?? null;
          }
          if (item.range_fragment == null) {
            item.range_fragment = chunkRangeFragment ?? null;
          }
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
      const audioTracks =
        extractAudioTracks(
          (payload.audio_tracks as Record<string, unknown> | undefined) ??
            (payload.audioTracks as Record<string, unknown> | undefined),
        ) ?? null;
      const rawTimingSource =
        (payload.timing_tracks as unknown) ?? (payload.timingTracks as unknown);
      const timingTracks = normaliseTrackTimingCollection(
        attachChunkIdToTimingSource(rawTimingSource, chunkId),
      );
      const sentenceCount =
        typeof rawSentenceCount === 'number' && Number.isFinite(rawSentenceCount)
          ? rawSentenceCount
          : sentences.length > 0
            ? sentences.length
            : null;
      chunkRecords.push({
        chunkId,
        rangeFragment: toStringOrNull(payload.range_fragment),
        startSentence: toNumberOrNull(payload.start_sentence),
        endSentence: toNumberOrNull(payload.end_sentence),
        files: chunkFiles,
        sentences: sentences.length > 0 ? sentences : undefined,
        metadataPath,
        metadataUrl,
        sentenceCount,
        audioTracks,
        timingTracks: timingTracks ?? null,
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

function tokeniseStorageUrl(url: string | null): string | null {
  if (!url) {
    return null;
  }
  if (url.startsWith('data:') || url.startsWith('blob:')) {
    return url;
  }
  return appendAccessTokenToStorageUrl(url);
}

function resolveFileUrl(
  jobId: string | null | undefined,
  entry: Record<string, unknown>,
): string | null {
  const explicitUrl = toStringOrNull(entry.url);
  if (explicitUrl) {
    if (!explicitUrl.includes('://') && !explicitUrl.startsWith('/') && !explicitUrl.startsWith('data:') && !explicitUrl.startsWith('blob:')) {
      try {
        return tokeniseStorageUrl(resolveStoragePath(jobId ?? null, explicitUrl));
      } catch (error) {
        console.warn('Unable to resolve storage URL for generated media', error);
      }
    }
    return tokeniseStorageUrl(explicitUrl);
  }

  const relativePath =
    toStringOrNull(entry.relative_path) ??
    deriveRelativePath(jobId, toStringOrNull(entry.path));

  if (relativePath) {
    try {
      return tokeniseStorageUrl(resolveStoragePath(jobId ?? null, relativePath));
    } catch (error) {
      console.warn('Unable to resolve storage URL for generated media', error);
    }
  }

  const fallbackPath = toStringOrNull(entry.path);
  if (fallbackPath && fallbackPath.includes('://')) {
    return tokeniseStorageUrl(fallbackPath);
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
  const relativePath = toStringOrNull(entry.relative_path ?? (entry as { relativePath?: unknown }).relativePath);
  const pathValue = toStringOrNull(entry.path);

  return {
    name,
    url,
    path: pathValue ?? undefined,
    relative_path: relativePath ?? undefined,
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
    let mergedAudioTracks: Record<string, AudioTrackMetadata> | null | undefined;
    if (update.audioTracks === null) {
      mergedAudioTracks = null;
    } else if (hasAudioTracks(update.audioTracks)) {
      const baseTracks = hasAudioTracks(current.audioTracks) ? current.audioTracks : undefined;
      const combined: Record<string, AudioTrackMetadata> = { ...(baseTracks ?? {}) };
      Object.entries(update.audioTracks).forEach(([key, value]) => {
        combined[key] = {
          ...(combined[key] ?? {}),
          ...value,
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
      timingTracks: mergedTimingTracks ?? null,
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
            : chunk.timingTracks ?? null,
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
        if (event.event_type === 'complete') {
          setIsComplete(true);
          fetchJobMedia(jobId)
            .then((fallbackResponse: PipelineMediaResponse) => {
              const { media: nextMedia, chunks: nextChunks, complete } = normaliseFetchedMedia(fallbackResponse, jobId);
              setMedia(nextMedia);
              setChunks(nextChunks);
              if (complete) {
                setIsComplete(true);
              }
            })
            .catch(() => {
              // Ignore failures; last known snapshot will remain in place.
            });
          return;
        }

        const metadataRecord = event.metadata as Record<string, unknown>;
        const stage = typeof metadataRecord.stage === 'string' ? metadataRecord.stage : null;
        if (event.event_type === 'progress' && stage === 'complete') {
          setIsComplete(true);
          fetchJobMedia(jobId)
            .then((fallbackResponse: PipelineMediaResponse) => {
              const { media: nextMedia, chunks: nextChunks, complete } = normaliseFetchedMedia(fallbackResponse, jobId);
              setMedia(nextMedia);
              setChunks(nextChunks);
              if (complete) {
                setIsComplete(true);
              }
            })
            .catch(() => {
              // Ignore failures; last known snapshot will remain in place.
            });
          return;
        }

        const snapshot = extractGeneratedFiles(event.metadata);
        if (!snapshot) {
          return;
        }

        const { media: nextMedia, chunks: incomingChunks, complete } = normaliseGeneratedSnapshot(snapshot, jobId);

        if (event.event_type === 'progress' && metadataRecord.media_reset === true) {
          setMedia(nextMedia);
          setChunks(incomingChunks);
          setIsComplete(complete);
          return;
        }

        if (event.event_type !== 'file_chunk_generated') {
          return;
        }

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

export interface MediaClock {
  mediaTime: () => number;
  playbackRate: () => number;
  effectiveTime: (track: Pick<TrackTimingPayload, 'trackOffset' | 'tempoFactor'>) => number;
}

function sanitiseRate(value: number | null | undefined): number {
  if (typeof value !== 'number' || Number.isNaN(value) || !Number.isFinite(value) || value <= 0) {
    return 1;
  }
  return value;
}

export function useMediaClock(audioRef: RefObject<HTMLAudioElement | null>): MediaClock {
  const mediaTime = useCallback(() => {
    const element = audioRef.current;
    if (!element) {
      return 0;
    }
    const raw = element.currentTime;
    if (typeof raw !== 'number' || Number.isNaN(raw) || !Number.isFinite(raw)) {
      return 0;
    }
    return raw;
  }, [audioRef]);

  const effectiveTime = useCallback(
    (track: Pick<TrackTimingPayload, 'trackOffset' | 'tempoFactor'>) => {
      const offset =
        typeof track.trackOffset === 'number' && Number.isFinite(track.trackOffset)
          ? track.trackOffset
          : 0;
      const tempoFactor =
        typeof track.tempoFactor === 'number' && Number.isFinite(track.tempoFactor) && track.tempoFactor > 0
          ? track.tempoFactor
          : 1;
      const adjusted = (mediaTime() - offset) / tempoFactor;
      if (!Number.isFinite(adjusted) || Number.isNaN(adjusted)) {
        return 0;
      }
      return adjusted < 0 ? 0 : adjusted;
    },
    [mediaTime]
  );

  const playbackRate = useCallback(() => {
    const element = audioRef.current;
    return sanitiseRate(element?.playbackRate ?? 1);
  }, [audioRef]);

  return useMemo(
    () => ({
      mediaTime,
      playbackRate,
      effectiveTime
    }),
    [mediaTime, playbackRate, effectiveTime]
  );
}
