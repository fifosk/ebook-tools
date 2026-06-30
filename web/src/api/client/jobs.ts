/**
 * Pipeline and Job management API endpoints.
 */

import type {
  AccessPolicyUpdatePayload,
  AcquisitionAcquireRequest,
  AcquisitionArtifactResponse,
  AcquisitionDiscoveryResponse,
  AcquisitionJobCreateRequest,
  AcquisitionJobStatusResponse,
  AcquisitionPreparedArtifactResponse,
  AcquisitionProviderListResponse,
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
  LookupCacheBulkResponse,
  LookupCacheEntryResponse,
  LookupCacheSummaryResponse,
  PipelineDefaultsResponse,
  PipelineFileBrowserResponse,
  PipelineFileEntry,
  PipelineIntakeStatusResponse,
  PipelineJobActionResponse,
  PipelineJobListResponse,
  PipelineRequestPayload,
  PipelineStatusResponse,
  PipelineSubmissionResponse
} from '../dtos';
import { apiFetch, handleResponse, getAuthToken, withBase } from './base';
import {
  replaceRuntimePathParameter,
  replaceRuntimePathParameters,
  WEB_CREATE_RUNTIME_CONTRACT,
  WEB_LINGUIST_RUNTIME_CONTRACT,
  WEB_PIPELINE_JOBS_RUNTIME_CONTRACT,
  WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT
} from './runtimeContract';

export const DEFAULT_PIPELINE_FILES_LIMIT = 200;

export async function submitPipeline(
  payload: PipelineRequestPayload
): Promise<PipelineSubmissionResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.pipelineJobsPath, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<PipelineSubmissionResponse>(response);
}

export async function fetchPipelineStatus(jobId: string): Promise<PipelineStatusResponse> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.statusPathTemplate,
      'job_id',
      jobId
    )
  );
  return handleResponse<PipelineStatusResponse>(response);
}

export async function fetchJobs(): Promise<PipelineStatusResponse[]> {
  const response = await apiFetch(WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.listPath);
  const payload = await handleResponse<PipelineJobListResponse>(response);
  return payload.jobs;
}

async function postJobAction(jobId: string, action: string): Promise<PipelineJobActionResponse> {
  const actionPath =
    action === 'restart'
      ? replaceRuntimePathParameter(
          WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.restartPathTemplate,
          'job_id',
          jobId
        )
      : action === 'delete'
        ? replaceRuntimePathParameter(
            WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.deletePathTemplate,
            'job_id',
            jobId
          )
        : `${WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.listPath}/${encodeURIComponent(jobId)}/${action}`;
  const response = await apiFetch(actionPath, {
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
  const response = await apiFetch(`/api/pipelines/${encodeURIComponent(jobId)}/metadata/refresh`, {
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
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.jobTimingPathTemplate,
      'job_id',
      jobId
    ),
    {
      signal,
      cache: 'no-store'
    },
    { suppressUnauthorized: true }
  );
  if (response.status === 404 || response.status === 403) {
    return null;
  }
  return handleResponse<JobTimingResponse>(response);
}

// Pipeline files and configuration
export async function fetchPipelineFiles(
  limit: number = DEFAULT_PIPELINE_FILES_LIMIT
): Promise<PipelineFileBrowserResponse> {
  const boundedLimit = Math.max(1, Math.min(500, Math.floor(limit)));
  const params = new URLSearchParams({ limit: String(boundedLimit) });
  const response = await apiFetch(
    `${WEB_CREATE_RUNTIME_CONTRACT.pipelineFilesPath}?${params.toString()}`
  );
  return handleResponse<PipelineFileBrowserResponse>(response);
}

export async function fetchAcquisitionProviders(): Promise<AcquisitionProviderListResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.acquisitionProvidersPath);
  return handleResponse<AcquisitionProviderListResponse>(response);
}

export async function discoverAcquisitionCandidates({
  mediaKind,
  query = '',
  provider,
  language,
  sourceIds = [],
  limit = 20
}: {
  mediaKind: 'book' | 'video';
  query?: string;
  provider?: string | null;
  language?: string | null;
  sourceIds?: string[];
  limit?: number;
}): Promise<AcquisitionDiscoveryResponse> {
  const params = new URLSearchParams({
    media_kind: mediaKind,
    q: query,
    limit: String(limit)
  });
  if (provider) {
    params.set('provider', provider);
  }
  if (language) {
    params.set('language', language);
  }
  for (const sourceId of sourceIds) {
    const normalizedSourceId = sourceId.trim();
    if (normalizedSourceId) {
      params.append('source_id', normalizedSourceId);
    }
  }
  const response = await apiFetch(
    `${WEB_CREATE_RUNTIME_CONTRACT.acquisitionDiscoverPath}?${params.toString()}`
  );
  return handleResponse<AcquisitionDiscoveryResponse>(response);
}

export async function acquireAcquisitionCandidate(
  payload: AcquisitionAcquireRequest
): Promise<AcquisitionArtifactResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.acquisitionAcquirePath, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<AcquisitionArtifactResponse>(response);
}

export async function prepareAcquisitionArtifact(
  artifactId: string
): Promise<AcquisitionPreparedArtifactResponse> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_CREATE_RUNTIME_CONTRACT.acquisitionArtifactPreparePathTemplate,
      'artifact_id',
      artifactId
    ),
    { method: 'POST' }
  );
  return handleResponse<AcquisitionPreparedArtifactResponse>(response);
}

export async function createAcquisitionJob(
  payload: AcquisitionJobCreateRequest
): Promise<AcquisitionJobStatusResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.acquisitionJobsPath, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<AcquisitionJobStatusResponse>(response);
}

export async function fetchAcquisitionJobStatus(
  taskId: string,
  provider = 'download_station'
): Promise<AcquisitionJobStatusResponse> {
  const params = new URLSearchParams({ provider });
  const response = await apiFetch(
    `${replaceRuntimePathParameter(
      WEB_CREATE_RUNTIME_CONTRACT.acquisitionJobPathTemplate,
      'task_id',
      taskId
    )}?${params.toString()}`
  );
  return handleResponse<AcquisitionJobStatusResponse>(response);
}

export async function fetchPipelineDefaults(): Promise<PipelineDefaultsResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.pipelineDefaultsPath);
  return handleResponse<PipelineDefaultsResponse>(response);
}

export async function fetchPipelineIntakeStatus(): Promise<PipelineIntakeStatusResponse | null> {
  const response = await apiFetch(
    WEB_CREATE_RUNTIME_CONTRACT.pipelineIntakeStatusPath,
    {},
    { suppressUnauthorized: true }
  );
  if (response.status === 401 || response.status === 403) {
    return null;
  }
  return handleResponse<PipelineIntakeStatusResponse>(response);
}

export async function fetchBookContentIndex(inputFile: string): Promise<BookContentIndexResponse> {
  const trimmed = inputFile.trim();
  const params = new URLSearchParams({ input_file: trimmed });
  const response = await apiFetch(
    `${WEB_CREATE_RUNTIME_CONTRACT.pipelineContentIndexPath}?${params.toString()}`
  );
  return handleResponse<BookContentIndexResponse>(response);
}

export async function checkImageNodeAvailability(
  payload: ImageNodeAvailabilityRequestPayload
): Promise<ImageNodeAvailabilityResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.imageNodeAvailabilityPath, {
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

  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.pipelineUploadPath, {
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
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.pipelineFilesPath, {
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

export async function clearMediaMetadataCache(
  query: string
): Promise<{ cleared: number }> {
  const response = await apiFetch('/api/pipelines/metadata/book/cache/clear', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query })
  });
  return handleResponse<{ cleared: number }>(response);
}

export async function clearTvMetadataCache(
  query: string
): Promise<{ cleared: number }> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.subtitleTvMetadataCacheClearPath, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query })
  });
  return handleResponse<{ cleared: number }>(response);
}

export async function clearYoutubeMetadataCache(
  query: string
): Promise<{ cleared: number }> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.youtubeMetadataCacheClearPath, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query })
  });
  return handleResponse<{ cleared: number }>(response);
}

// LLM models
export async function fetchLlmModels(): Promise<string[]> {
  const response = await apiFetch(
    WEB_CREATE_RUNTIME_CONTRACT.pipelineLlmModelsPath,
    {},
    { suppressUnauthorized: true }
  );
  if (response.status === 401 || response.status === 403) {
    return [];
  }
  const payload = await handleResponse<LlmModelListResponse>(response);
  return payload.models ?? [];
}

// Event stream URL builder
export function buildEventStreamUrl(jobId: string): string {
  const baseUrl = withBase(
    replaceRuntimePathParameter(
      WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.eventStreamPathTemplate,
      'job_id',
      jobId
    )
  );
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

// Lookup cache API
export async function fetchCachedLookup(
  jobId: string,
  word: string
): Promise<LookupCacheEntryResponse | null> {
  try {
    const response = await apiFetch(
      replaceRuntimePathParameters(WEB_LINGUIST_RUNTIME_CONTRACT.lookupCacheWordPathTemplate, {
        job_id: jobId,
        word
      }),
      {},
      { suppressUnauthorized: true }
    );
    if (response.status === 404) {
      return null;
    }
    return handleResponse<LookupCacheEntryResponse>(response);
  } catch {
    return null;
  }
}

export async function fetchCachedLookupsBulk(
  jobId: string,
  words: string[]
): Promise<LookupCacheBulkResponse | null> {
  try {
    const response = await apiFetch(
      replaceRuntimePathParameter(
        WEB_LINGUIST_RUNTIME_CONTRACT.lookupCacheBulkPathTemplate,
        'job_id',
        jobId
      ),
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ words })
      },
      { suppressUnauthorized: true }
    );
    if (response.status === 404) {
      return null;
    }
    return handleResponse<LookupCacheBulkResponse>(response);
  } catch {
    return null;
  }
}

export async function fetchLookupCacheSummary(
  jobId: string
): Promise<LookupCacheSummaryResponse | null> {
  try {
    const response = await apiFetch(
      replaceRuntimePathParameter(
        WEB_LINGUIST_RUNTIME_CONTRACT.lookupCacheSummaryPathTemplate,
        'job_id',
        jobId
      ),
      {},
      { suppressUnauthorized: true }
    );
    if (response.status === 404) {
      return null;
    }
    return handleResponse<LookupCacheSummaryResponse>(response);
  } catch {
    return null;
  }
}
