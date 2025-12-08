import type { ChunkSentenceMetadata, MediaSearchResult } from '../../api/dtos';
import type { LiveMediaChunk, LiveMediaItem, LiveMediaState } from '../../hooks/useLiveMedia';
import type { MediaCategory } from './constants';
import { MEDIA_CATEGORIES } from './constants';

export function isAudioFileType(value: unknown): boolean {
  if (typeof value !== 'string') {
    return false;
  }
  const signature = value.trim().toLowerCase();
  if (!signature) {
    return false;
  }
  return signature === 'audio' || signature.startsWith('audio_');
}

export function toAudioFiles(media: LiveMediaState['audio']) {
  return media
    .filter((item) => typeof item.url === 'string' && item.url.length > 0)
    .map((item, index) => ({
      id: item.url ?? `${item.type}-${index}`,
      url: item.url ?? '',
      name: typeof item.name === 'string' ? item.name : undefined,
    }));
}

function stripQuery(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return '';
  }
  return trimmed.replace(/[?#].*$/, '');
}

export function buildMediaFileId(item: LiveMediaItem, index: number): string {
  const relativePath = typeof item.relative_path === 'string' ? item.relative_path.trim() : '';
  if (relativePath) {
    return relativePath;
  }
  const path = typeof item.path === 'string' ? item.path.trim() : '';
  if (path) {
    return path;
  }
  const url = typeof item.url === 'string' ? stripQuery(item.url) : '';
  if (url) {
    return url;
  }
  const name = typeof item.name === 'string' ? item.name.trim() : '';
  if (name) {
    return name;
  }
  const chunkId = typeof item.chunk_id === 'string' ? item.chunk_id.trim() : '';
  if (chunkId) {
    return `${item.type}:${chunkId}`;
  }
  const rangeFragment = typeof item.range_fragment === 'string' ? item.range_fragment.trim() : '';
  if (rangeFragment) {
    return `${item.type}:${rangeFragment}`;
  }
  return `${item.type}-${index}`;
}

export function toVideoFiles(media: LiveMediaState['video']) {
  return media
    .filter((item) => typeof item.url === 'string' && item.url.length > 0)
    .map((item, index) => ({
      id: buildMediaFileId(item, index),
      url: item.url ?? '',
      name: typeof item.name === 'string' ? item.name : undefined,
    }));
}

export function deriveBaseIdFromReference(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  let trimmed = value.replace(/^[\\/]+/, '').split(/[\\/]/).pop();
  if (!trimmed) {
    return null;
  }
  const withoutQuery = trimmed.replace(/[?#].*$/, '');
  let decoded = withoutQuery;
  try {
    decoded = decodeURIComponent(withoutQuery);
  } catch (error) {
    void error;
  }
  const dotIndex = withoutQuery.lastIndexOf('.');
  const base = dotIndex > 0 ? decoded.slice(0, dotIndex) : decoded;
  const cleaned = base.trim();
  if (!cleaned) {
    return null;
  }
  try {
    return cleaned.normalize('NFC').toLowerCase();
  } catch (error) {
    void error;
  }
  return cleaned.toLowerCase();
}

export function resolveBaseIdFromResult(
  result: MediaSearchResult,
  preferred: MediaCategory | null,
): string | null {
  if (result.base_id) {
    return result.base_id;
  }
  if (result.range_fragment) {
    return deriveBaseIdFromReference(result.range_fragment);
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

export function formatSentenceRange(
  start: number | null | undefined,
  end: number | null | undefined,
): string {
  if (typeof start === 'number' && typeof end === 'number') {
    return start === end ? `${start}` : `${start}–${end}`;
  }
  if (typeof start === 'number') {
    return `${start}`;
  }
  if (typeof end === 'number') {
    return `${end}`;
  }
  return '—';
}

export function formatChunkLabel(chunk: LiveMediaChunk, index: number): string {
  const rangeFragment = typeof chunk.rangeFragment === 'string' ? chunk.rangeFragment.trim() : '';
  if (rangeFragment) {
    return rangeFragment;
  }
  const chunkId = typeof chunk.chunkId === 'string' ? chunk.chunkId.trim() : '';
  if (chunkId) {
    return chunkId;
  }
  const sentenceRange = formatSentenceRange(chunk.startSentence ?? null, chunk.endSentence ?? null);
  if (sentenceRange && sentenceRange !== '—') {
    return `Chunk ${index + 1} · ${sentenceRange}`;
  }
  return `Chunk ${index + 1}`;
}

export function buildInteractiveAudioCatalog(
  chunks: LiveMediaChunk[],
  audioMedia: LiveMediaItem[],
): {
  playlist: LiveMediaItem[];
  nameMap: Map<string, string>;
  chunkIndexMap: Map<string, number>;
} {
  const playlist: LiveMediaItem[] = [];
  const nameMap = new Map<string, string>();
  const chunkIndexMap = new Map<string, number>();
  const seen = new Set<string>();

  const register = (
    item: LiveMediaItem | null | undefined,
    chunkIndex: number | null,
    fallbackLabel?: string,
  ) => {
    if (!item || !item.url) {
      return;
    }
    const url = item.url;
    if (seen.has(url)) {
      return;
    }
    seen.add(url);
    const trimmedName = typeof item.name === 'string' ? item.name.trim() : '';
    const trimmedFallback = typeof fallbackLabel === 'string' ? fallbackLabel.trim() : '';
    const label = trimmedName || trimmedFallback || `Audio ${playlist.length + 1}`;
    const enriched = trimmedName ? item : { ...item, name: label };
    playlist.push(enriched);
    nameMap.set(url, label);
    if (typeof chunkIndex === 'number' && chunkIndex >= 0) {
      chunkIndexMap.set(url, chunkIndex);
    }
  };

  chunks.forEach((chunk, index) => {
    const chunkLabel = formatChunkLabel(chunk, index);
    chunk.files.forEach((file) => {
      if (!isAudioFileType(file.type)) {
        return;
      }
      register(file, index, chunkLabel);
    });
  });

  audioMedia.forEach((item) => {
    if (!item.url) {
      return;
    }
    const existingIndex = chunkIndexMap.get(item.url);
    register(item, typeof existingIndex === 'number' ? existingIndex : null, item.name);
  });

  return { playlist, nameMap, chunkIndexMap };
}

export function chunkCacheKey(chunk: LiveMediaChunk): string | null {
  if (chunk.chunkId) {
    return `id:${chunk.chunkId}`;
  }
  if (chunk.rangeFragment) {
    return `range:${chunk.rangeFragment}`;
  }
  if (chunk.metadataPath) {
    return `path:${chunk.metadataPath}`;
  }
  if (chunk.metadataUrl) {
    return `url:${chunk.metadataUrl}`;
  }
  const audioUrl = chunk.files.find((file) => isAudioFileType(file.type) && file.url)?.url;
  if (audioUrl) {
    return `audio:${audioUrl}`;
  }
  return null;
}

export type InlineAudioOption = { url: string; label: string };

export function deriveInlineAudioOptions(
  resolvedChunk: LiveMediaChunk | null,
  fallbackChunk: LiveMediaChunk | null,
  chunkIndex: number,
  nameMap: Map<string, string>,
  playlist: LiveMediaItem[],
): InlineAudioOption[] {
  const seen = new Set<string>();
  const options: InlineAudioOption[] = [];
  const register = (url: string | null | undefined, label: string | null | undefined) => {
    if (!url || seen.has(url)) {
      return;
    }
    const trimmedLabel = typeof label === 'string' ? label.trim() : '';
    options.push({
      url,
      label: trimmedLabel || `Audio ${options.length + 1}`,
    });
    seen.add(url);
  };
  const chunkForOptions = resolvedChunk ?? fallbackChunk;
  if (chunkForOptions && chunkIndex >= 0) {
    chunkForOptions.files.forEach((file) => {
      if (!isAudioFileType(file.type) || !file.url) {
        return;
      }
      const label =
        nameMap.get(file.url) ??
        (typeof file.name === 'string' ? file.name.trim() : '') ??
        formatChunkLabel(chunkForOptions, chunkIndex);
      register(file.url, label);
    });
  }
  playlist.forEach((item, index) => {
    register(item.url, item.name ?? `Audio ${index + 1}`);
  });
  return options;
}

export function fallbackTextFromSentences(chunk: LiveMediaChunk | null | undefined): string {
  if (!chunk || !Array.isArray(chunk.sentences)) {
    return '';
  }
  const blocks = chunk.sentences
    .map((sentence) => {
      if (!sentence) {
        return '';
      }
      const lines: string[] = [];
      if (sentence.original?.text) {
        lines.push(sentence.original.text);
      }
      if (sentence.translation?.text) {
        lines.push(sentence.translation.text);
      }
      if (sentence.transliteration?.text) {
        lines.push(sentence.transliteration.text);
      }
      return lines.filter(Boolean).join('\n');
    })
    .filter((block) => block.trim().length > 0);
  return blocks.join('\n\n');
}

export async function requestChunkMetadata(
  jobId: string,
  chunk: LiveMediaChunk,
  resolvePath: (jobId: string, path: string) => string,
): Promise<ChunkSentenceMetadata[] | null> {
  let targetUrl: string | null = chunk.metadataUrl ?? null;

  if (!targetUrl) {
    const metadataPath = chunk.metadataPath ?? null;
    if (metadataPath) {
      try {
        targetUrl = resolvePath(jobId, metadataPath);
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
    const response = await fetch(targetUrl, { credentials: 'include' });
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
