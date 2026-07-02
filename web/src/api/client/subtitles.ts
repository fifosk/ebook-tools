/**
 * Subtitle and YouTube-related API endpoints.
 */

import type {
  AssistantLookupRequest,
  AssistantLookupResponse,
  LlmModelListResponse,
  PipelineSubmissionResponse,
  SubtitleDeleteResponse,
  SubtitleJobResultPayload,
  SubtitleSourceEntry,
  SubtitleSourceListResponse,
  SubtitleTvMetadataLookupRequest,
  SubtitleTvMetadataPreviewLookupRequest,
  SubtitleTvMetadataPreviewResponse,
  SubtitleTvMetadataResponse,
  YoutubeVideoMetadataLookupRequest,
  YoutubeVideoMetadataPreviewLookupRequest,
  YoutubeVideoMetadataPreviewResponse,
  YoutubeVideoMetadataResponse,
  YoutubeSubtitleDownloadRequest,
  YoutubeSubtitleDownloadResponse,
  YoutubeSubtitleListResponse,
  YoutubeVideoDownloadRequest,
  YoutubeVideoDownloadResponse,
  YoutubeNasLibraryResponse,
  YoutubeInlineSubtitleListResponse,
  YoutubeSubtitleExtractionResponse,
  YoutubeSubtitleDeleteResponse,
  YoutubeVideoDeleteRequest,
  YoutubeVideoDeleteResponse,
  YoutubeDubRequest,
  YoutubeDubResponse
} from '../dtos';
import { apiFetch, handleResponse } from './base';
import {
  replaceRuntimePathParameter,
  WEB_CREATE_RUNTIME_CONTRACT,
  WEB_LINGUIST_RUNTIME_CONTRACT,
  WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT,
} from './runtimeContract';

// Subtitle sources
export async function fetchSubtitleSources(directory?: string): Promise<SubtitleSourceEntry[]> {
  const query = directory ? `?directory=${encodeURIComponent(directory)}` : '';
  const response = await apiFetch(`${WEB_CREATE_RUNTIME_CONTRACT.subtitleSourcesPath}${query}`);
  const payload = await handleResponse<unknown>(response);
  assertSubtitleSourceListResponse(payload);
  return payload.sources;
}

function assertSubtitleSourceListResponse(
  payload: unknown
): asserts payload is SubtitleSourceListResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid subtitle source list response.');
  }
  if (!Array.isArray(payload.sources)) {
    throw new Error('Invalid subtitle source list response: missing sources.');
  }
  for (const source of payload.sources) {
    assertSubtitleSourceEntry(source, 'source list');
  }
}

export async function deleteSubtitleSource(
  subtitlePath: string,
  baseDir?: string | null
): Promise<SubtitleDeleteResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.subtitleDeleteSourcePath, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      subtitle_path: subtitlePath,
      base_dir: baseDir ?? null
    })
  });
  return handleResponse<SubtitleDeleteResponse>(response);
}

// TV metadata
export async function fetchSubtitleTvMetadata(jobId: string): Promise<SubtitleTvMetadataResponse> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.subtitleTvMetadataPathTemplate,
      'job_id',
      jobId
    )
  );
  return handleResponse<SubtitleTvMetadataResponse>(response);
}

export async function lookupSubtitleTvMetadata(
  jobId: string,
  payload: SubtitleTvMetadataLookupRequest = {}
): Promise<SubtitleTvMetadataResponse> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.subtitleTvMetadataLookupPathTemplate,
      'job_id',
      jobId
    ),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force: Boolean(payload.force) })
    }
  );
  return handleResponse<SubtitleTvMetadataResponse>(response);
}

export async function lookupSubtitleTvMetadataPreview(
  payload: SubtitleTvMetadataPreviewLookupRequest
): Promise<SubtitleTvMetadataPreviewResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.subtitleTvMetadataPreviewPath, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_name: payload.source_name, force: Boolean(payload.force) })
  });
  return handleResponse<SubtitleTvMetadataPreviewResponse>(response);
}

// YouTube metadata
export async function fetchYoutubeVideoMetadata(jobId: string): Promise<YoutubeVideoMetadataResponse> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.youtubeVideoMetadataPathTemplate,
      'job_id',
      jobId
    )
  );
  return handleResponse<YoutubeVideoMetadataResponse>(response);
}

export async function lookupYoutubeVideoMetadata(
  jobId: string,
  payload: YoutubeVideoMetadataLookupRequest = {}
): Promise<YoutubeVideoMetadataResponse> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.youtubeVideoMetadataLookupPathTemplate,
      'job_id',
      jobId
    ),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force: Boolean(payload.force) })
    }
  );
  return handleResponse<YoutubeVideoMetadataResponse>(response);
}

export async function lookupYoutubeVideoMetadataPreview(
  payload: YoutubeVideoMetadataPreviewLookupRequest
): Promise<YoutubeVideoMetadataPreviewResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.youtubeMetadataPreviewPath, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_name: payload.source_name, force: Boolean(payload.force) })
  });
  return handleResponse<YoutubeVideoMetadataPreviewResponse>(response);
}

// YouTube subtitles and video
export async function fetchYoutubeSubtitleTracks(url: string): Promise<YoutubeSubtitleListResponse> {
  const query = `?url=${encodeURIComponent(url)}`;
  const response = await apiFetch(`${WEB_CREATE_RUNTIME_CONTRACT.youtubeSubtitlesPath}${query}`);
  return handleResponse<YoutubeSubtitleListResponse>(response);
}

export async function downloadYoutubeSubtitle(
  payload: YoutubeSubtitleDownloadRequest
): Promise<YoutubeSubtitleDownloadResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.youtubeSubtitleDownloadPath, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<YoutubeSubtitleDownloadResponse>(response);
}

export async function downloadYoutubeVideo(
  payload: YoutubeVideoDownloadRequest
): Promise<YoutubeVideoDownloadResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.youtubeVideoDownloadPath, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<YoutubeVideoDownloadResponse>(response);
}

export async function fetchYoutubeLibrary(
  baseDir?: string
): Promise<YoutubeNasLibraryResponse> {
  const query = baseDir ? `?base_dir=${encodeURIComponent(baseDir)}` : '';
  const response = await apiFetch(`${WEB_CREATE_RUNTIME_CONTRACT.youtubeLibraryPath}${query}`);
  const payload = await handleResponse<unknown>(response);
  assertYoutubeNasLibraryResponse(payload);
  return payload;
}

export async function fetchInlineSubtitleStreams(
  videoPath: string
): Promise<YoutubeInlineSubtitleListResponse> {
  const query = `?video_path=${encodeURIComponent(videoPath)}`;
  const response = await apiFetch(`${WEB_CREATE_RUNTIME_CONTRACT.youtubeSubtitleStreamsPath}${query}`);
  const payload = await handleResponse<unknown>(response);
  assertYoutubeInlineSubtitleListResponse(payload);
  return payload;
}

export async function extractInlineSubtitles(
  videoPath: string,
  languages?: string[]
): Promise<YoutubeSubtitleExtractionResponse> {
  const payload: Record<string, unknown> = { video_path: videoPath };
  if (languages && languages.length > 0) {
    payload.languages = languages;
  }
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.youtubeExtractSubtitlesPath, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  const responsePayload = await handleResponse<unknown>(response);
  assertYoutubeSubtitleExtractionResponse(responsePayload);
  return responsePayload;
}

function assertYoutubeNasLibraryResponse(
  payload: unknown
): asserts payload is YoutubeNasLibraryResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid YouTube NAS library response.');
  }
  assertSourcePickerStringField(payload, 'base_dir', 'YouTube NAS library');
  if (!Array.isArray(payload.videos)) {
    throw new Error('Invalid YouTube NAS library response: missing videos.');
  }
  for (const video of payload.videos) {
    assertYoutubeNasVideo(video);
  }
}

function assertYoutubeInlineSubtitleListResponse(
  payload: unknown
): asserts payload is YoutubeInlineSubtitleListResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid YouTube subtitle stream list response.');
  }
  assertSourcePickerStringField(payload, 'video_path', 'YouTube subtitle stream list');
  if (!Array.isArray(payload.streams)) {
    throw new Error('Invalid YouTube subtitle stream list response: missing streams.');
  }
  for (const stream of payload.streams) {
    if (!isRecord(stream)) {
      throw new Error('Invalid YouTube subtitle stream list response: missing stream entry.');
    }
    assertSourcePickerNumberField(stream, 'index', 'YouTube subtitle stream list');
    assertSourcePickerNumberField(stream, 'position', 'YouTube subtitle stream list');
    assertSourcePickerBooleanField(stream, 'can_extract', 'YouTube subtitle stream list');
    assertSourcePickerOptionalString(stream.language, 'language', 'YouTube subtitle stream list');
    assertSourcePickerOptionalString(stream.codec, 'codec', 'YouTube subtitle stream list');
    assertSourcePickerOptionalString(stream.title, 'title', 'YouTube subtitle stream list');
  }
}

function assertYoutubeSubtitleExtractionResponse(
  payload: unknown
): asserts payload is YoutubeSubtitleExtractionResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid YouTube subtitle extraction response.');
  }
  assertSourcePickerStringField(payload, 'video_path', 'YouTube subtitle extraction');
  if (!Array.isArray(payload.extracted)) {
    throw new Error('Invalid YouTube subtitle extraction response: missing extracted.');
  }
  for (const subtitle of payload.extracted) {
    assertYoutubeNasSubtitle(subtitle, 'YouTube subtitle extraction');
  }
}

function assertYoutubeNasVideo(payload: unknown): void {
  if (!isRecord(payload)) {
    throw new Error('Invalid YouTube NAS library response: missing video entry.');
  }
  assertSourcePickerStringField(payload, 'path', 'YouTube NAS library');
  assertSourcePickerStringField(payload, 'filename', 'YouTube NAS library');
  assertSourcePickerStringField(payload, 'folder', 'YouTube NAS library');
  assertSourcePickerNumberField(payload, 'size_bytes', 'YouTube NAS library');
  assertSourcePickerStringField(payload, 'modified_at', 'YouTube NAS library');
  assertSourcePickerOptionalString(payload.source, 'source', 'YouTube NAS library');
  assertSourcePickerStringArray(payload.linked_job_ids, 'linked_job_ids', 'YouTube NAS library');
  if (!Array.isArray(payload.subtitles)) {
    throw new Error('Invalid YouTube NAS library response: missing subtitles.');
  }
  for (const subtitle of payload.subtitles) {
    assertYoutubeNasSubtitle(subtitle, 'YouTube NAS library');
  }
}

function assertSubtitleSourceEntry(payload: unknown, responseKind: string): void {
  if (!isRecord(payload)) {
    throw new Error(`Invalid subtitle ${responseKind} response: missing source entry.`);
  }
  assertSourcePickerStringField(payload, 'name', `subtitle ${responseKind}`);
  assertSourcePickerStringField(payload, 'path', `subtitle ${responseKind}`);
  assertSourcePickerStringField(payload, 'format', `subtitle ${responseKind}`);
  assertSourcePickerOptionalString(payload.language, 'language', `subtitle ${responseKind}`);
  assertSourcePickerOptionalString(payload.modified_at, 'modified_at', `subtitle ${responseKind}`);
}

function assertYoutubeNasSubtitle(payload: unknown, responseKind: string): void {
  if (!isRecord(payload)) {
    throw new Error(`Invalid ${responseKind} response: missing subtitle entry.`);
  }
  assertSourcePickerStringField(payload, 'path', responseKind);
  assertSourcePickerStringField(payload, 'filename', responseKind);
  assertSourcePickerStringField(payload, 'format', responseKind);
  assertSourcePickerOptionalString(payload.language, 'language', responseKind);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function assertSourcePickerStringField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (typeof record[key] !== 'string') {
    throw new Error(`Invalid ${responseKind} response: missing ${key}.`);
  }
}

function assertSourcePickerNumberField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (typeof record[key] !== 'number') {
    throw new Error(`Invalid ${responseKind} response: missing ${key}.`);
  }
}

function assertSourcePickerBooleanField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (typeof record[key] !== 'boolean') {
    throw new Error(`Invalid ${responseKind} response: missing ${key}.`);
  }
}

function assertSourcePickerOptionalString(
  value: unknown,
  key: string,
  responseKind: string
): void {
  if (value !== undefined && value !== null && typeof value !== 'string') {
    throw new Error(`Invalid ${responseKind} response: invalid ${key}.`);
  }
}

function assertSourcePickerStringArray(value: unknown, key: string, responseKind: string): void {
  if (!Array.isArray(value) || value.some((entry) => typeof entry !== 'string')) {
    throw new Error(`Invalid ${responseKind} response: missing ${key}.`);
  }
}

export async function deleteNasSubtitle(
  videoPath: string,
  subtitlePath: string
): Promise<YoutubeSubtitleDeleteResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.youtubeSubtitleDeletePath, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      video_path: videoPath,
      subtitle_path: subtitlePath
    })
  });
  return handleResponse<YoutubeSubtitleDeleteResponse>(response);
}

export async function deleteYoutubeVideo(
  payload: YoutubeVideoDeleteRequest
): Promise<YoutubeVideoDeleteResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.youtubeVideoDeletePath, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<YoutubeVideoDeleteResponse>(response);
}

export async function generateYoutubeDub(
  payload: YoutubeDubRequest
): Promise<YoutubeDubResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.youtubeDubPath, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<YoutubeDubResponse>(response);
}

// Subtitle jobs
export async function submitSubtitleJob(formData: FormData): Promise<PipelineSubmissionResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.subtitleJobsPath, {
    method: 'POST',
    body: formData
  });
  return handleResponse<PipelineSubmissionResponse>(response);
}

export async function fetchSubtitleResult(jobId: string): Promise<SubtitleJobResultPayload> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.subtitleJobResultPathTemplate,
      'job_id',
      jobId
    )
  );
  return handleResponse<SubtitleJobResultPayload>(response);
}

// LLM models (subtitle-related)
export async function fetchSubtitleModels(): Promise<string[]> {
  const response = await apiFetch(
    WEB_CREATE_RUNTIME_CONTRACT.subtitleModelsPath,
    {},
    { suppressUnauthorized: true }
  );
  if (response.status === 401 || response.status === 403) {
    return [];
  }
  const payload = await handleResponse<unknown>(response);
  assertSubtitleModelListResponse(payload);
  return payload.models;
}

function assertSubtitleModelListResponse(
  payload: unknown
): asserts payload is LlmModelListResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid subtitle model list response.');
  }
  if (!Array.isArray(payload.models) || payload.models.some((entry) => typeof entry !== 'string')) {
    throw new Error('Invalid subtitle model list response: missing models.');
  }
}

// Assistant
export async function assistantLookup(payload: AssistantLookupRequest): Promise<AssistantLookupResponse> {
  const response = await apiFetch(WEB_LINGUIST_RUNTIME_CONTRACT.assistantLookupPath, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<AssistantLookupResponse>(response);
}
