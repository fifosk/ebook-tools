import type { ChunkSentenceMetadata, LibraryItem, MediaSearchResult } from '../../api/dtos';
import { appendAccessToken, buildStorageUrl, resolveLibraryMediaUrl } from '../../api/client';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import { coerceExportPath, resolve as resolveStoragePath } from '../../utils/storageResolver';
import type { MediaCategory } from './constants';
import { MEDIA_CATEGORIES } from './constants';

export function deriveBaseIdFromReference(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const normalised = value.replace(/^[\\/]+/, '').split(/[\\/]/).pop();
  if (!normalised) {
    return null;
  }
  const withoutQuery = normalised.replace(/[?#].*$/, '');
  const dotIndex = withoutQuery.lastIndexOf('.');
  const base = dotIndex > 0 ? withoutQuery.slice(0, dotIndex) : withoutQuery;
  const trimmed = base.trim();
  return trimmed ? trimmed.toLowerCase() : null;
}

export function resolveChunkBaseId(chunk: LiveMediaChunk): string | null {
  const textFile = chunk.files.find(
    (file) => file.type === 'text' && typeof file.url === 'string' && file.url.length > 0,
  );
  if (textFile?.url) {
    return deriveBaseIdFromReference(textFile.url) ?? textFile.url ?? null;
  }
  if (chunk.chunkId) {
    return chunk.chunkId;
  }
  if (chunk.rangeFragment) {
    return chunk.rangeFragment;
  }
  if (chunk.metadataPath) {
    return chunk.metadataPath;
  }
  if (chunk.metadataUrl) {
    return chunk.metadataUrl;
  }
  return null;
}

export function resolveBaseIdFromResult(result: MediaSearchResult, preferred: MediaCategory | null): string | null {
  if (result.base_id) {
    return result.base_id;
  }

  const categories: MediaCategory[] = [];
  if (preferred) {
    categories.push(preferred);
  }
  MEDIA_CATEGORIES.forEach((category) => {
    if (!categories.includes(category)) {
      categories.push(category);
    }
  });

  for (const category of categories) {
    const entries = result.media?.[category];
    if (!entries || entries.length === 0) {
      continue;
    }
    const primary = entries[0];
    const baseId =
      deriveBaseIdFromReference(primary.relative_path ?? null) ??
      deriveBaseIdFromReference(primary.name ?? null) ??
      deriveBaseIdFromReference(primary.url ?? null) ??
      deriveBaseIdFromReference(primary.path ?? null);
    if (baseId) {
      return baseId;
    }
  }

  return null;
}

export function normaliseBookSentenceCount(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    const safe = Math.max(Math.trunc(value), 0);
    return safe > 0 ? safe : null;
  }

  if (Array.isArray(value)) {
    return value.length;
  }

  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    const sentences = record.sentences;
    if (Array.isArray(sentences)) {
      return sentences.length;
    }
    const total =
      record.total_sentences ??
      record.sentence_count ??
      record.book_sentence_count ??
      record.total ??
      record.count;
    if (typeof total === 'number' && Number.isFinite(total)) {
      const safe = Math.max(Math.trunc(total), 0);
      return safe > 0 ? safe : null;
    }
  }

  return null;
}

export function normaliseLookupToken(value: string | null | undefined): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const derived = deriveBaseIdFromReference(trimmed);
  if (derived) {
    return derived;
  }
  return trimmed.toLowerCase();
}

export function normaliseAudioSignature(value: string | null | undefined): string {
  if (!value) {
    return '';
  }
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '');
}

export function isCombinedAudioCandidate(...values: (string | null | undefined)[]): boolean {
  return values.some((value) => normaliseAudioSignature(value).includes('origtrans'));
}

export function isOriginalAudioCandidate(...values: (string | null | undefined)[]): boolean {
  return values.some((value) => {
    const signature = normaliseAudioSignature(value);
    return signature.includes('orig') && !signature.includes('origtrans');
  });
}

export function findChunkIndexForBaseId(baseId: string | null, chunks: LiveMediaChunk[]): number {
  const target = normaliseLookupToken(baseId);
  if (!target) {
    return -1;
  }

  const matches = (candidate: string | null | undefined): boolean => {
    const normalised = normaliseLookupToken(candidate);
    return normalised !== null && normalised === target;
  };

  for (let index = 0; index < chunks.length; index += 1) {
    const chunk = chunks[index];
    if (
      matches(chunk.chunkId) ||
      matches(chunk.rangeFragment) ||
      matches(chunk.metadataPath) ||
      matches(chunk.metadataUrl)
    ) {
      return index;
    }
    for (const file of chunk.files) {
      if (matches(file.relative_path) || matches(file.path) || matches(file.url) || matches(file.name)) {
        return index;
      }
    }
  }

  return -1;
}

export function normaliseMetadataText(value: unknown): string | null {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }

  if (typeof value === 'number' && Number.isFinite(value)) {
    return value.toString();
  }

  return null;
}

export function extractMetadataText(
  metadata: Record<string, unknown> | null | undefined,
  keys: string[],
): string | null {
  if (!metadata) {
    return null;
  }

  for (const key of keys) {
    const raw = metadata[key];
    const normalised = normaliseMetadataText(raw);
    if (normalised) {
      return normalised;
    }
  }

  return null;
}

export function extractMetadataFirstString(
  metadata: Record<string, unknown> | null | undefined,
  keys: string[],
): string | null {
  if (!metadata) {
    return null;
  }
  for (const key of keys) {
    const raw = metadata[key];
    if (Array.isArray(raw)) {
      for (const entry of raw) {
        const normalised = normaliseMetadataText(entry);
        if (normalised) {
          return normalised;
        }
      }
    }
    const normalised = normaliseMetadataText(raw);
    if (normalised) {
      return normalised;
    }
  }
  return null;
}

export function readNestedValue(source: unknown, path: string[]): unknown {
  let current: unknown = source;
  for (const key of path) {
    if (!current || typeof current !== 'object') {
      return null;
    }
    current = (current as Record<string, unknown>)[key];
  }
  return current;
}

export function coerceRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

export function extractTvMediaMetadataFromLibrary(item: LibraryItem | null | undefined): Record<string, unknown> | null {
  const payload = item?.metadata ?? null;
  if (!payload || typeof payload !== 'object') {
    return null;
  }
  const candidate =
    readNestedValue(payload, ['result', 'subtitle', 'metadata', 'media_metadata']) ??
    readNestedValue(payload, ['result', 'youtube_dub', 'media_metadata']) ??
    readNestedValue(payload, ['request', 'media_metadata']) ??
    readNestedValue(payload, ['media_metadata']) ??
    null;
  return coerceRecord(candidate);
}

export function resolveLibraryAssetUrl(jobId: string, value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (/^[a-z]+:\/\//i.test(trimmed)) {
    return trimmed;
  }
  if (trimmed.startsWith('/api/')) {
    return appendAccessToken(trimmed);
  }
  if (trimmed.startsWith('/')) {
    return trimmed;
  }
  return resolveLibraryMediaUrl(jobId, trimmed);
}

export function resolveJobAssetUrl(jobId: string, value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (/^[a-z]+:\/\//i.test(trimmed)) {
    return trimmed;
  }
  if (trimmed.startsWith('/api/')) {
    return appendAccessToken(trimmed);
  }
  if (trimmed.startsWith('/')) {
    return appendAccessToken(trimmed);
  }
  try {
    return buildStorageUrl(trimmed, jobId);
  } catch (error) {
    console.warn('Unable to resolve job asset url', error);
    return `/${trimmed.replace(/^\/+/, '')}`;
  }
}

export function resolveTvMetadataImage(
  jobId: string,
  tvMetadata: Record<string, unknown> | null,
  path: 'show' | 'episode',
  resolver: (jobId: string, value: unknown) => string | null,
): string | null {
  const section = coerceRecord(tvMetadata?.[path]);
  if (!section) {
    return null;
  }
  const image = section['image'];
  if (!image) {
    return null;
  }
  if (typeof image === 'string') {
    return resolver(jobId, image);
  }
  const record = coerceRecord(image);
  if (!record) {
    return null;
  }
  return resolver(jobId, record['medium']) ?? resolver(jobId, record['original']);
}

export const CHUNK_METADATA_PREFETCH_RADIUS = 2;
export const SINGLE_SENTENCE_PREFETCH_AHEAD = 3;
export const MAX_SENTENCE_PREFETCH_COUNT = 400;
export const CHUNK_SENTENCE_BOOTSTRAP_COUNT = 12;
export const CHUNK_SENTENCE_APPEND_BATCH = 75;

export type SentenceLookupEntry = {
  chunkIndex: number;
  localIndex: number;
  total: number;
  baseId: string | null;
};

export type SentenceLookupRange = {
  start: number;
  end: number;
  chunkIndex: number;
  baseId: string | null;
};

export type SentenceLookup = {
  min: number | null;
  max: number | null;
  exact: Map<number, SentenceLookupEntry>;
  ranges: SentenceLookupRange[];
  suggestions: number[];
};

export function isSingleSentenceChunk(chunk: LiveMediaChunk | null | undefined): boolean {
  if (!chunk) {
    return false;
  }
  if (Array.isArray(chunk.sentences) && chunk.sentences.length > 0) {
    return chunk.sentences.length === 1;
  }
  if (typeof chunk.sentenceCount === 'number' && chunk.sentenceCount > 0) {
    return chunk.sentenceCount === 1;
  }
  return false;
}

export function getKnownSentenceCount(chunk: LiveMediaChunk | null | undefined): number | null {
  if (!chunk) {
    return null;
  }
  if (Array.isArray(chunk.sentences) && chunk.sentences.length > 0) {
    return chunk.sentences.length;
  }
  if (typeof chunk.sentenceCount === 'number' && chunk.sentenceCount > 0) {
    return chunk.sentenceCount;
  }
  return null;
}

export function shouldPrefetchChunk(chunk: LiveMediaChunk | null | undefined): boolean {
  const count = getKnownSentenceCount(chunk);
  if (count === null) {
    return true;
  }
  return count <= MAX_SENTENCE_PREFETCH_COUNT;
}

export function partitionChunkSentences(
  sentences: ChunkSentenceMetadata[] | null | undefined,
  bootstrapCount: number,
): { immediate: ChunkSentenceMetadata[]; remainder: ChunkSentenceMetadata[] } {
  if (!Array.isArray(sentences) || sentences.length === 0) {
    return { immediate: [], remainder: [] };
  }
  const take = Math.max(bootstrapCount, 0);
  if (take <= 0 || sentences.length <= take) {
    return { immediate: sentences, remainder: [] };
  }
  return {
    immediate: sentences.slice(0, take),
    remainder: sentences.slice(take),
  };
}

export async function requestChunkMetadata(
  jobId: string,
  chunk: LiveMediaChunk,
  origin: 'job' | 'library',
  playerMode: 'online' | 'export' = 'online',
): Promise<ChunkSentenceMetadata[] | null> {
  const isExportMode = playerMode === 'export';
  let targetUrl: string | null = chunk.metadataUrl ?? null;

  if (isExportMode) {
    const candidate = chunk.metadataPath ?? chunk.metadataUrl ?? null;
    if (candidate) {
      targetUrl = coerceExportPath(candidate, jobId) ?? candidate;
    } else {
      targetUrl = null;
    }
  } else if (!targetUrl) {
    const metadataPath = chunk.metadataPath ?? null;
    if (metadataPath) {
      try {
        if (origin === 'library') {
          if (metadataPath.startsWith('/api/library/') || metadataPath.includes('://')) {
            targetUrl = metadataPath;
          } else {
            targetUrl = resolveLibraryMediaUrl(jobId, metadataPath);
          }
        } else {
          targetUrl = resolveStoragePath(jobId, metadataPath);
        }
      } catch (error) {
        if (jobId) {
          const encodedJobId = encodeURIComponent(jobId);
          const sanitizedPath = metadataPath.replace(/^\/+/, '');
          targetUrl = `/pipelines/jobs/${encodedJobId}/${encodeURI(sanitizedPath)}`;
        } else {
          console.warn('Unable to resolve chunk metadata path', metadataPath, error);
        }
      }
    }
  }

  if (!targetUrl) {
    return null;
  }

  try {
    const url = origin === 'library' && !isExportMode ? appendAccessToken(targetUrl) : targetUrl;
    const response = await fetch(url, { credentials: 'include' });
    if (!response.ok) {
      throw new Error(`Chunk metadata request failed with status ${response.status}`);
    }
    const payload = await response.json();
    const sentences = payload?.sentences;
    if (Array.isArray(sentences)) {
      return sentences as ChunkSentenceMetadata[];
    }
    return [];
  } catch (error) {
    console.warn('Unable to load chunk metadata', targetUrl, error);
    return null;
  }
}
