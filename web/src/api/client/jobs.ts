/**
 * Pipeline and Job management API endpoints.
 */

import type {
  AccessPolicyUpdatePayload,
  BookContentIndexResponse,
  BookOpenLibraryMetadataLookupRequest,
  BookOpenLibraryMetadataPreviewLookupRequest,
  BookOpenLibraryMetadataPreviewResponse,
  BookOpenLibraryMetadataResponse,
  ImageNodeAvailabilityRequestPayload,
  ImageNodeAvailabilityResponse,
  JobMetadataEnrichRequest,
  JobMetadataEnrichResponse,
  JobTimingResponse,
  LlmModelListResponse,
  PipelineDefaultsResponse,
  PipelineFileBrowserResponse,
  PipelineFileEntry,
  PipelineJobActionResponse,
  PipelineJobListResponse,
  PipelineRequestPayload,
  PipelineStatusResponse,
  PipelineSubmissionResponse
} from '../dtos';
import { apiFetch, handleResponse, getAuthToken, withBase } from './base';

export async function submitPipeline(
  payload: PipelineRequestPayload
): Promise<PipelineSubmissionResponse> {
  const response = await apiFetch('/api/pipelines', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<PipelineSubmissionResponse>(response);
}

export async function fetchPipelineStatus(jobId: string): Promise<PipelineStatusResponse> {
  const response = await apiFetch(`/api/pipelines/${jobId}`);
  return handleResponse<PipelineStatusResponse>(response);
}

export async function fetchJobs(): Promise<PipelineStatusResponse[]> {
  const response = await apiFetch('/api/pipelines/jobs');
  const payload = await handleResponse<PipelineJobListResponse>(response);
  return payload.jobs;
}

async function postJobAction(jobId: string, action: string): Promise<PipelineJobActionResponse> {
  const response = await apiFetch(`/api/pipelines/jobs/${jobId}/${action}`, {
    method: 'POST'
  });
  return handleResponse<PipelineJobActionResponse>(response);
}

export async function pauseJob(jobId: string): Promise<PipelineJobActionResponse> {
  return postJobAction(jobId, 'pause');
}

export async function resumeJob(jobId: string): Promise<PipelineJobActionResponse> {
  return postJobAction(jobId, 'resume');
}

export async function cancelJob(jobId: string): Promise<PipelineJobActionResponse> {
  return postJobAction(jobId, 'cancel');
}

export async function deleteJob(jobId: string): Promise<PipelineJobActionResponse> {
  return postJobAction(jobId, 'delete');
}

export async function restartJob(jobId: string): Promise<PipelineJobActionResponse> {
  return postJobAction(jobId, 'restart');
}

export async function refreshPipelineMetadata(jobId: string): Promise<PipelineStatusResponse> {
  const response = await apiFetch(`/api/pipelines/${jobId}/metadata/refresh`, {
    method: 'POST'
  });
  return handleResponse<PipelineStatusResponse>(response);
}

export async function enrichPipelineMetadata(
  jobId: string,
  payload: JobMetadataEnrichRequest = {}
): Promise<JobMetadataEnrichResponse> {
  const response = await apiFetch(`/api/pipelines/${encodeURIComponent(jobId)}/metadata/enrich`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force: Boolean(payload.force) })
  });
  return handleResponse<JobMetadataEnrichResponse>(response);
}

export async function updateJobAccess(
  jobId: string,
  payload: AccessPolicyUpdatePayload
): Promise<PipelineStatusResponse> {
  const response = await apiFetch(`/api/pipelines/${encodeURIComponent(jobId)}/access`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<PipelineStatusResponse>(response);
}

export async function fetchJobTiming(jobId: string, signal?: AbortSignal): Promise<JobTimingResponse | null> {
  const response = await apiFetch(`/api/jobs/${encodeURIComponent(jobId)}/timing`, {
    signal,
    cache: 'no-store'
  });
  if (response.status === 404) {
    return null;
  }
  return handleResponse<JobTimingResponse>(response);
}

// Pipeline files and configuration
export async function fetchPipelineFiles(): Promise<PipelineFileBrowserResponse> {
  const response = await apiFetch('/api/pipelines/files');
  return handleResponse<PipelineFileBrowserResponse>(response);
}

export async function fetchPipelineDefaults(): Promise<PipelineDefaultsResponse> {
  const response = await apiFetch('/api/pipelines/defaults');
  return handleResponse<PipelineDefaultsResponse>(response);
}

export async function fetchBookContentIndex(inputFile: string): Promise<BookContentIndexResponse> {
  const trimmed = inputFile.trim();
  const params = new URLSearchParams({ input_file: trimmed });
  const response = await apiFetch(`/api/pipelines/files/content-index?${params.toString()}`);
  return handleResponse<BookContentIndexResponse>(response);
}

export async function checkImageNodeAvailability(
  payload: ImageNodeAvailabilityRequestPayload
): Promise<ImageNodeAvailabilityResponse> {
  const response = await apiFetch('/api/pipelines/image-nodes/availability', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<ImageNodeAvailabilityResponse>(response);
}

export async function uploadEpubFile(file: File): Promise<PipelineFileEntry> {
  const formData = new FormData();
  formData.append('file', file, file.name);

  const response = await apiFetch('/api/pipelines/files/upload', {
    method: 'POST',
    body: formData
  });

  return handleResponse<PipelineFileEntry>(response);
}

export async function uploadCoverFile(file: File): Promise<PipelineFileEntry> {
  const formData = new FormData();
  formData.append('file', file, file.name);

  const response = await apiFetch('/api/pipelines/covers/upload', {
    method: 'POST',
    body: formData
  });

  return handleResponse<PipelineFileEntry>(response);
}

export async function deletePipelineEbook(path: string): Promise<void> {
  const response = await apiFetch('/api/pipelines/files', {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ path })
  });
  await handleResponse<unknown>(response);
}

// Book metadata
export async function fetchBookOpenLibraryMetadata(jobId: string): Promise<BookOpenLibraryMetadataResponse> {
  const response = await apiFetch(`/api/pipelines/${encodeURIComponent(jobId)}/metadata/book`);
  return handleResponse<BookOpenLibraryMetadataResponse>(response);
}

export async function lookupBookOpenLibraryMetadata(
  jobId: string,
  payload: BookOpenLibraryMetadataLookupRequest = {}
): Promise<BookOpenLibraryMetadataResponse> {
  const response = await apiFetch(`/api/pipelines/${encodeURIComponent(jobId)}/metadata/book/lookup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force: Boolean(payload.force) })
  });
  return handleResponse<BookOpenLibraryMetadataResponse>(response);
}

export async function lookupBookOpenLibraryMetadataPreview(
  payload: BookOpenLibraryMetadataPreviewLookupRequest
): Promise<BookOpenLibraryMetadataPreviewResponse> {
  const response = await apiFetch('/api/pipelines/metadata/book/lookup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: payload.query, force: Boolean(payload.force) })
  });
  return handleResponse<BookOpenLibraryMetadataPreviewResponse>(response);
}

// LLM models
export async function fetchLlmModels(): Promise<string[]> {
  const response = await apiFetch('/api/pipelines/llm-models', {}, { suppressUnauthorized: true });
  if (response.status === 401 || response.status === 403) {
    return [];
  }
  const payload = await handleResponse<LlmModelListResponse>(response);
  return payload.models ?? [];
}

// Event stream URL builder
export function buildEventStreamUrl(jobId: string): string {
  const baseUrl = withBase(`/api/pipelines/${jobId}/events`);
  const token = getAuthToken();
  try {
    const url = new URL(baseUrl, typeof window !== 'undefined' ? window.location.origin : undefined);
    if (token) {
      url.searchParams.set('access_token', token);
    }
    return url.toString();
  } catch (error) {
    if (token) {
      const separator = baseUrl.includes('?') ? '&' : '?';
      return `${baseUrl}${separator}access_token=${encodeURIComponent(token)}`;
    }
    return baseUrl;
  }
}

// Job cover URL
export function resolveJobCoverUrl(jobId: string): string | null {
  const trimmed = (jobId ?? '').trim();
  if (!trimmed) {
    return null;
  }
  const encoded = encodeURIComponent(trimmed);
  return withBase(`/api/pipelines/${encoded}/cover`);
}
