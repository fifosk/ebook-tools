/**
 * Subtitle and YouTube-related API endpoints.
 */

import type {
  AssistantLookupRequest,
  AssistantLookupResponse,
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

// Subtitle sources
export async function fetchSubtitleSources(directory?: string): Promise<SubtitleSourceEntry[]> {
  const query = directory ? `?directory=${encodeURIComponent(directory)}` : '';
  const response = await apiFetch(`/api/subtitles/sources${query}`);
  const payload = await handleResponse<SubtitleSourceListResponse>(response);
  return payload.sources;
}

export async function deleteSubtitleSource(
  subtitlePath: string,
  baseDir?: string | null
): Promise<SubtitleDeleteResponse> {
  const response = await apiFetch('/api/subtitles/delete-source', {
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
  const response = await apiFetch(`/api/subtitles/jobs/${encodeURIComponent(jobId)}/metadata/tv`);
  return handleResponse<SubtitleTvMetadataResponse>(response);
}

export async function lookupSubtitleTvMetadata(
  jobId: string,
  payload: SubtitleTvMetadataLookupRequest = {}
): Promise<SubtitleTvMetadataResponse> {
  const response = await apiFetch(`/api/subtitles/jobs/${encodeURIComponent(jobId)}/metadata/tv/lookup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force: Boolean(payload.force) })
  });
  return handleResponse<SubtitleTvMetadataResponse>(response);
}

export async function lookupSubtitleTvMetadataPreview(
  payload: SubtitleTvMetadataPreviewLookupRequest
): Promise<SubtitleTvMetadataPreviewResponse> {
  const response = await apiFetch('/api/subtitles/metadata/tv/lookup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_name: payload.source_name, force: Boolean(payload.force) })
  });
  return handleResponse<SubtitleTvMetadataPreviewResponse>(response);
}

// YouTube metadata
export async function fetchYoutubeVideoMetadata(jobId: string): Promise<YoutubeVideoMetadataResponse> {
  const response = await apiFetch(`/api/subtitles/jobs/${encodeURIComponent(jobId)}/metadata/youtube`);
  return handleResponse<YoutubeVideoMetadataResponse>(response);
}

export async function lookupYoutubeVideoMetadata(
  jobId: string,
  payload: YoutubeVideoMetadataLookupRequest = {}
): Promise<YoutubeVideoMetadataResponse> {
  const response = await apiFetch(`/api/subtitles/jobs/${encodeURIComponent(jobId)}/metadata/youtube/lookup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force: Boolean(payload.force) })
  });
  return handleResponse<YoutubeVideoMetadataResponse>(response);
}

export async function lookupYoutubeVideoMetadataPreview(
  payload: YoutubeVideoMetadataPreviewLookupRequest
): Promise<YoutubeVideoMetadataPreviewResponse> {
  const response = await apiFetch('/api/subtitles/metadata/youtube/lookup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_name: payload.source_name, force: Boolean(payload.force) })
  });
  return handleResponse<YoutubeVideoMetadataPreviewResponse>(response);
}

// YouTube subtitles and video
export async function fetchYoutubeSubtitleTracks(url: string): Promise<YoutubeSubtitleListResponse> {
  const query = `?url=${encodeURIComponent(url)}`;
  const response = await apiFetch(`/api/subtitles/youtube/subtitles${query}`);
  return handleResponse<YoutubeSubtitleListResponse>(response);
}

export async function downloadYoutubeSubtitle(
  payload: YoutubeSubtitleDownloadRequest
): Promise<YoutubeSubtitleDownloadResponse> {
  const response = await apiFetch('/api/subtitles/youtube/download', {
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
  const response = await apiFetch('/api/subtitles/youtube/video', {
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
  const response = await apiFetch(`/api/subtitles/youtube/library${query}`);
  return handleResponse<YoutubeNasLibraryResponse>(response);
}

export async function fetchInlineSubtitleStreams(
  videoPath: string
): Promise<YoutubeInlineSubtitleListResponse> {
  const query = `?video_path=${encodeURIComponent(videoPath)}`;
  const response = await apiFetch(`/api/subtitles/youtube/subtitle-streams${query}`);
  return handleResponse<YoutubeInlineSubtitleListResponse>(response);
}

export async function extractInlineSubtitles(
  videoPath: string,
  languages?: string[]
): Promise<YoutubeSubtitleExtractionResponse> {
  const payload: Record<string, unknown> = { video_path: videoPath };
  if (languages && languages.length > 0) {
    payload.languages = languages;
  }
  const response = await apiFetch('/api/subtitles/youtube/extract-subtitles', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<YoutubeSubtitleExtractionResponse>(response);
}

export async function deleteNasSubtitle(
  videoPath: string,
  subtitlePath: string
): Promise<YoutubeSubtitleDeleteResponse> {
  const response = await apiFetch('/api/subtitles/youtube/delete-subtitle', {
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
  const response = await apiFetch('/api/subtitles/youtube/delete-video', {
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
  const response = await apiFetch('/api/subtitles/youtube/dub', {
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
  const response = await apiFetch('/api/subtitles/jobs', {
    method: 'POST',
    body: formData
  });
  return handleResponse<PipelineSubmissionResponse>(response);
}

export async function fetchSubtitleResult(jobId: string): Promise<SubtitleJobResultPayload> {
  const encoded = encodeURIComponent(jobId);
  const response = await apiFetch(`/api/subtitles/jobs/${encoded}/result`);
  return handleResponse<SubtitleJobResultPayload>(response);
}

// LLM models (subtitle-related)
export { fetchLlmModels as fetchSubtitleModels } from './jobs';

// Assistant
export async function assistantLookup(payload: AssistantLookupRequest): Promise<AssistantLookupResponse> {
  const response = await apiFetch('/api/assistant/lookup', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<AssistantLookupResponse>(response);
}
