/**
 * Media, images, video, and audio API endpoints.
 */

import type {
  ExportRequestPayload,
  ExportResponse,
  MediaSearchResponse,
  PipelineMediaFile,
  PipelineMediaResponse,
  PlaybackBookmarkCreatePayload,
  PlaybackBookmarkDeleteResponse,
  PlaybackBookmarkEntry,
  PlaybackBookmarkListResponse,
  SentenceImageInfoBatchResponse,
  SentenceImageInfoResponse,
  SentenceImageRegenerateRequestPayload,
  SentenceImageRegenerateResponse,
  VideoGenerationRequestPayload,
  VideoGenerationResponse,
  VoiceInventoryResponse
} from '../dtos';
import type { ExportPlayerManifest } from '../../types/exportPlayer';
import { apiFetch, handleResponse, maybeAppendAccessTokenToStorage, withBase } from './base';
import { resolve as resolveStoragePath } from '../../utils/storageResolver';
import { API_BASE_URL, STORAGE_BASE_URL, appendAccessToken } from './base';

// Media endpoints
export async function fetchJobMedia(jobId: string): Promise<PipelineMediaResponse> {
  const response = await apiFetch(`/api/pipelines/jobs/${jobId}/media`);
  return handleResponse<PipelineMediaResponse>(response);
}

export async function fetchLiveJobMedia(jobId: string): Promise<PipelineMediaResponse> {
  const response = await apiFetch(`/api/pipelines/jobs/${jobId}/media/live`);
  return handleResponse<PipelineMediaResponse>(response);
}

// Sentence images
export async function fetchSentenceImageInfo(
  jobId: string,
  sentenceNumber: number
): Promise<SentenceImageInfoResponse> {
  const encodedJobId = encodeURIComponent(jobId);
  const response = await apiFetch(
    `/api/pipelines/jobs/${encodedJobId}/media/images/sentences/${encodeURIComponent(String(sentenceNumber))}`
  );
  return handleResponse<SentenceImageInfoResponse>(response);
}

export async function fetchSentenceImageInfoBatch(
  jobId: string,
  sentenceNumbers: number[]
): Promise<SentenceImageInfoResponse[]> {
  const requested = (sentenceNumbers ?? []).filter((value) => Number.isFinite(value));
  if (!requested.length) {
    return [];
  }
  const encodedJobId = encodeURIComponent(jobId);
  const params = new URLSearchParams();
  params.set('sentence_numbers', requested.join(','));
  const response = await apiFetch(
    `/api/pipelines/jobs/${encodedJobId}/media/images/sentences/batch?${params.toString()}`
  );
  const payload = await handleResponse<SentenceImageInfoBatchResponse>(response);
  return Array.isArray(payload.items) ? payload.items : [];
}

export async function regenerateSentenceImage(
  jobId: string,
  sentenceNumber: number,
  payload: SentenceImageRegenerateRequestPayload
): Promise<SentenceImageRegenerateResponse> {
  const encodedJobId = encodeURIComponent(jobId);
  const response = await apiFetch(
    `/api/pipelines/jobs/${encodedJobId}/media/images/sentences/${encodeURIComponent(String(sentenceNumber))}/regenerate`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    }
  );
  return handleResponse<SentenceImageRegenerateResponse>(response);
}

// Video generation
export async function generateVideo(
  jobId: string,
  parameters: Record<string, unknown>
): Promise<VideoGenerationResponse> {
  const payload: VideoGenerationRequestPayload = {
    job_id: jobId,
    parameters
  };
  const response = await apiFetch('/api/video/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<VideoGenerationResponse>(response);
}

export async function fetchVideoStatus(jobId: string): Promise<VideoGenerationResponse | null> {
  const response = await apiFetch(`/api/video/status/${encodeURIComponent(jobId)}`);
  if (response.status === 404) {
    return null;
  }
  return handleResponse<VideoGenerationResponse>(response);
}

// Audio/Voice endpoints
export async function fetchVoiceInventory(): Promise<VoiceInventoryResponse> {
  const response = await apiFetch('/api/audio/voices');
  return handleResponse<VoiceInventoryResponse>(response);
}

export interface VoicePreviewRequest {
  text: string;
  language: string;
  voice?: string | null;
  speed?: number | null;
}

export async function synthesizeVoicePreview(payload: VoicePreviewRequest): Promise<Blob> {
  const body: Record<string, unknown> = {
    text: payload.text,
    language: payload.language
  };
  if (payload.voice) {
    body.voice = payload.voice;
  }
  if (typeof payload.speed === 'number') {
    body.speed = payload.speed;
  }

  const response = await apiFetch('/api/audio', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'audio/mpeg'
    },
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || 'Unable to generate voice preview');
  }

  return await response.blob();
}

// Bookmarks
export async function fetchPlaybackBookmarks(jobId: string): Promise<PlaybackBookmarkListResponse> {
  const response = await apiFetch(`/api/bookmarks/${encodeURIComponent(jobId)}`);
  return handleResponse<PlaybackBookmarkListResponse>(response);
}

export async function createPlaybackBookmark(
  jobId: string,
  payload: PlaybackBookmarkCreatePayload
): Promise<PlaybackBookmarkEntry> {
  const response = await apiFetch(`/api/bookmarks/${encodeURIComponent(jobId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return handleResponse<PlaybackBookmarkEntry>(response);
}

export async function deletePlaybackBookmark(
  jobId: string,
  bookmarkId: string
): Promise<PlaybackBookmarkDeleteResponse> {
  const response = await apiFetch(`/api/bookmarks/${encodeURIComponent(jobId)}/${encodeURIComponent(bookmarkId)}`, {
    method: 'DELETE'
  });
  return handleResponse<PlaybackBookmarkDeleteResponse>(response);
}

// Export
export async function createExport(payload: ExportRequestPayload): Promise<ExportResponse> {
  const response = await apiFetch('/api/exports', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<ExportResponse>(response);
}

// Export manifest utilities
function getExportManifest(): ExportPlayerManifest | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const candidate = (window as Window & { __EXPORT_DATA__?: unknown }).__EXPORT_DATA__;
  if (!candidate || typeof candidate !== 'object') {
    return null;
  }
  return candidate as ExportPlayerManifest;
}

function resolveExportJobLabel(manifest: ExportPlayerManifest): string | null {
  const metadata = manifest.media_metadata ?? manifest.book_metadata ?? null;
  if (metadata && typeof metadata === 'object') {
    const record = metadata as Record<string, unknown>;
    const keys = ['book_title', 'title', 'book_name', 'name'];
    for (const key of keys) {
      const raw = record[key];
      if (typeof raw === 'string' && raw.trim()) {
        return raw.trim();
      }
    }
  }
  const sourceLabel = manifest.source?.label;
  if (typeof sourceLabel === 'string' && sourceLabel.trim()) {
    return sourceLabel.trim();
  }
  const sourceId = manifest.source?.id;
  if (typeof sourceId === 'string' && sourceId.trim()) {
    return sourceId.trim();
  }
  return null;
}

// Search utilities
function normaliseSearchText(value: string): string {
  return value.toLowerCase();
}

function countOccurrences(text: string, needle: string): number {
  if (!needle) {
    return 0;
  }
  let count = 0;
  let index = 0;
  while (true) {
    const match = text.indexOf(needle, index);
    if (match < 0) {
      return count;
    }
    count += 1;
    index = match + needle.length;
  }
}

function buildSnippet(text: string, matchIndex: number, matchLength: number): {
  snippet: string;
  matchStart: number;
  matchEnd: number;
  textLength: number;
} {
  const maxRadius = 80;
  const start = Math.max(0, matchIndex - maxRadius);
  const end = Math.min(text.length, matchIndex + matchLength + maxRadius);
  let snippet = text.slice(start, end);
  if (start > 0) {
    snippet = `...${snippet}`;
  }
  if (end < text.length) {
    snippet = `${snippet}...`;
  }
  const matchStart = matchIndex - start + (start > 0 ? 3 : 0);
  return {
    snippet,
    matchStart,
    matchEnd: matchStart + matchLength,
    textLength: text.length,
  };
}

function normaliseMediaCategory(value: string | null | undefined): 'text' | 'audio' | 'video' | null {
  if (!value) {
    return null;
  }
  const normalised = value.trim().toLowerCase();
  if (!normalised) {
    return null;
  }
  if (normalised === 'video') {
    return 'video';
  }
  if (normalised.startsWith('audio')) {
    return 'audio';
  }
  return 'text';
}

function groupChunkMedia(files: PipelineMediaFile[]): Record<string, PipelineMediaFile[]> {
  const grouped: Record<string, PipelineMediaFile[]> = {};
  files.forEach((file) => {
    const category = normaliseMediaCategory(file.type ?? null);
    if (!category) {
      return;
    }
    const bucket = grouped[category] ?? [];
    bucket.push(file);
    grouped[category] = bucket;
  });
  return grouped;
}

function searchExportMedia(
  manifest: ExportPlayerManifest,
  query: string,
  limit: number,
  requestedJobId: string | null | undefined,
): MediaSearchResponse {
  const trimmed = query.trim();
  if (!trimmed) {
    return { query: '', limit, count: 0, results: [] };
  }
  const manifestJobId =
    typeof manifest.source?.id === 'string' && manifest.source.id.trim() ? manifest.source.id.trim() : null;
  if (requestedJobId && manifestJobId && requestedJobId !== manifestJobId) {
    return { query: trimmed, limit, count: 0, results: [] };
  }
  const resolvedJobId = (requestedJobId ?? manifestJobId ?? 'export').trim();
  const jobLabel = resolveExportJobLabel(manifest);
  const chunks = Array.isArray(manifest.chunks) ? manifest.chunks : [];
  const chunkTotal = chunks.length;
  const needle = normaliseSearchText(trimmed);

  const results: MediaSearchResponse['results'] = [];

  for (let chunkIndex = 0; chunkIndex < chunks.length; chunkIndex += 1) {
    if (results.length >= limit) {
      break;
    }
    const chunk = chunks[chunkIndex];
    const sentences = Array.isArray(chunk.sentences) ? chunk.sentences : [];
    if (sentences.length === 0) {
      continue;
    }
    const media = groupChunkMedia(chunk.files ?? []);
    if (!media.text || media.text.length === 0) {
      media.text = [
        {
          name: 'Text',
          url: null,
          source: 'completed',
          type: 'text',
          relative_path: chunk.metadata_path ?? null,
          path: chunk.metadata_path ?? null,
        },
      ];
    }
    const chunkId = typeof chunk.chunk_id === 'string' && chunk.chunk_id.trim() ? chunk.chunk_id.trim() : null;
    const rangeFragment =
      typeof chunk.range_fragment === 'string' && chunk.range_fragment.trim() ? chunk.range_fragment.trim() : null;
    const baseId =
      chunkId ??
      rangeFragment ??
      (typeof chunk.metadata_path === 'string' && chunk.metadata_path.trim()
        ? chunk.metadata_path.trim()
        : null) ??
      (typeof chunk.metadata_url === 'string' && chunk.metadata_url.trim() ? chunk.metadata_url.trim() : null);
    const startSentence =
      typeof chunk.start_sentence === 'number' && Number.isFinite(chunk.start_sentence)
        ? Math.trunc(chunk.start_sentence)
        : null;
    const endSentence =
      typeof chunk.end_sentence === 'number' && Number.isFinite(chunk.end_sentence)
        ? Math.trunc(chunk.end_sentence)
        : null;

    for (let sentenceIndex = 0; sentenceIndex < sentences.length; sentenceIndex += 1) {
      if (results.length >= limit) {
        break;
      }
      const sentence = sentences[sentenceIndex];
      if (!sentence) {
        continue;
      }
      const parts = [
        typeof sentence.original?.text === 'string' ? sentence.original.text : null,
        typeof sentence.translation?.text === 'string' ? sentence.translation.text : null,
        typeof sentence.transliteration?.text === 'string' ? sentence.transliteration.text : null,
      ].filter((value): value is string => Boolean(value && value.trim()));
      if (parts.length === 0) {
        continue;
      }
      const combined = parts.join(' ');
      const haystack = normaliseSearchText(combined);
      const matchIndex = haystack.indexOf(needle);
      if (matchIndex < 0) {
        continue;
      }

      const sentenceNumber =
        typeof sentence.sentence_number === 'number' && Number.isFinite(sentence.sentence_number)
          ? Math.trunc(sentence.sentence_number)
          : startSentence !== null
            ? startSentence + sentenceIndex
            : null;
      const offsetRatio =
        sentenceNumber !== null && startSentence !== null && endSentence !== null && endSentence > startSentence
          ? Math.min(Math.max((sentenceNumber - startSentence) / (endSentence - startSentence), 0), 1)
          : null;

      const occurrenceCount = countOccurrences(haystack, needle);
      const { snippet, matchStart, matchEnd, textLength } = buildSnippet(combined, matchIndex, needle.length);

      results.push({
        job_id: resolvedJobId,
        job_label: jobLabel,
        base_id: baseId,
        chunk_id: chunkId,
        chunk_index: chunkIndex,
        chunk_total: chunkTotal,
        range_fragment: rangeFragment,
        start_sentence: startSentence,
        end_sentence: endSentence,
        snippet,
        occurrence_count: Math.max(1, occurrenceCount),
        match_start: matchStart,
        match_end: matchEnd,
        text_length: textLength,
        offset_ratio: offsetRatio,
        approximate_time_seconds: null,
        media,
        source: 'pipeline',
      });
    }
  }

  return {
    query: trimmed,
    limit,
    count: results.length,
    results,
  };
}

export async function searchMedia(jobId: string | null | undefined, query: string, limit?: number): Promise<MediaSearchResponse> {
  const trimmed = query.trim();
  const resolvedLimit =
    typeof limit === 'number' && Number.isFinite(limit) && limit > 0 ? Math.floor(limit) : 20;
  if (!trimmed || !jobId) {
    return Promise.resolve({
      query: '',
      limit: resolvedLimit,
      count: 0,
      results: [],
    });
  }
  const exportManifest = getExportManifest();
  if (exportManifest) {
    return searchExportMedia(exportManifest, trimmed, resolvedLimit, jobId);
  }
  const params = new URLSearchParams();
  params.set('query', trimmed);
  params.set('limit', String(resolvedLimit));
  params.set('job_id', jobId);
  const response = await apiFetch(`/api/pipelines/search?${params.toString()}`);
  return handleResponse<MediaSearchResponse>(response);
}

// Storage URL utilities
export function buildStorageUrl(path: string, jobId?: string | null): string {
  const trimmedPath = (path ?? '').trim();
  if (!trimmedPath) {
    const resolved = resolveStoragePath(null, null, STORAGE_BASE_URL, API_BASE_URL);
    return maybeAppendAccessTokenToStorage(resolved);
  }

  const normalisedPath = trimmedPath.replace(/^\/+/, '');
  if (!normalisedPath) {
    const resolved = resolveStoragePath(null, null, STORAGE_BASE_URL, API_BASE_URL);
    return maybeAppendAccessTokenToStorage(resolved);
  }

  const normalisedJobId = (jobId ?? '').trim().replace(/^\/+/, '').replace(/\/+$/, '');
  const segments = normalisedPath.split('/').filter((segment) => segment.length > 0);

  if (normalisedJobId) {
    const jobIndex = segments.findIndex((segment) => segment === normalisedJobId);
    if (jobIndex >= 0) {
      const fileSegment = segments.slice(jobIndex + 1).join('/');
      const resolved = resolveStoragePath(
        normalisedJobId,
        fileSegment,
        STORAGE_BASE_URL,
        API_BASE_URL
      );
      return maybeAppendAccessTokenToStorage(resolved);
    }

    if (
      segments.length >= 2 &&
      segments[0].toLowerCase() === 'jobs' &&
      segments[1] === normalisedJobId
    ) {
      const fileSegment = segments.slice(2).join('/');
      const resolved = resolveStoragePath(
        normalisedJobId,
        fileSegment,
        STORAGE_BASE_URL,
        API_BASE_URL
      );
      return maybeAppendAccessTokenToStorage(resolved);
    }

    const firstSegment = segments[0]?.toLowerCase() ?? '';
    const requiresJobPrefix = firstSegment !== 'covers' && firstSegment !== 'storage' && firstSegment !== 'jobs';
    if (requiresJobPrefix) {
      const resolved = resolveStoragePath(
        normalisedJobId,
        normalisedPath,
        STORAGE_BASE_URL,
        API_BASE_URL
      );
      return maybeAppendAccessTokenToStorage(resolved);
    }
  }

  const [jobSegment, ...rest] = segments;
  const fileSegment = rest.length > 0 ? rest.join('/') : '';

  const resolved = resolveStoragePath(
    jobSegment || null,
    fileSegment,
    STORAGE_BASE_URL,
    API_BASE_URL
  );
  return maybeAppendAccessTokenToStorage(resolved);
}

export function resolveSubtitleDownloadUrl(
  jobId: string,
  relativePath: string | null | undefined
): string | null {
  if (!relativePath) {
    return null;
  }
  const trimmed = relativePath.trim().replace(/^\/+/, '');
  if (!trimmed) {
    return null;
  }
  const composedPath = `${jobId}/${trimmed}`;
  return buildStorageUrl(composedPath, jobId);
}
