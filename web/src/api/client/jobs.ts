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

export const DEFAULT_PIPELINE_FILES_LIMIT = WEB_CREATE_RUNTIME_CONTRACT.pipelineFilesDefaultLimit;
export const MIN_PIPELINE_FILES_LIMIT = WEB_CREATE_RUNTIME_CONTRACT.pipelineFilesMinLimit;
export const MAX_PIPELINE_FILES_LIMIT = WEB_CREATE_RUNTIME_CONTRACT.pipelineFilesMaxLimit;

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
  const actionPathTemplates: Record<string, string> = {
    pause: WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.pausePathTemplate,
    resume: WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.resumePathTemplate,
    cancel: WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.cancelPathTemplate,
    delete: WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.deletePathTemplate,
    restart: WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.restartPathTemplate
  };
  const template = actionPathTemplates[action];
  if (!template) {
    throw new Error(`Unsupported job action: ${action}`);
  }
  const actionPath = replaceRuntimePathParameter(template, 'job_id', jobId);
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
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.metadataRefreshPathTemplate,
      'job_id',
      jobId
    ),
    {
      method: 'POST'
    }
  );
  return handleResponse<PipelineStatusResponse>(response);
}

export async function enrichPipelineMetadata(
  jobId: string,
  payload: JobMetadataEnrichRequest = {}
): Promise<JobMetadataEnrichResponse> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.metadataEnrichPathTemplate,
      'job_id',
      jobId
    ),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force: Boolean(payload.force) })
    }
  );
  return handleResponse<JobMetadataEnrichResponse>(response);
}

export async function updateJobAccess(
  jobId: string,
  payload: AccessPolicyUpdatePayload
): Promise<PipelineStatusResponse> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.accessPathTemplate,
      'job_id',
      jobId
    ),
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    }
  );
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
  const boundedLimit = Math.max(
    MIN_PIPELINE_FILES_LIMIT,
    Math.min(MAX_PIPELINE_FILES_LIMIT, Math.floor(limit))
  );
  const params = new URLSearchParams({ limit: String(boundedLimit) });
  const response = await apiFetch(
    `${WEB_CREATE_RUNTIME_CONTRACT.pipelineFilesPath}?${params.toString()}`
  );
  return handleResponse<PipelineFileBrowserResponse>(response);
}

export async function fetchAcquisitionProviders(): Promise<AcquisitionProviderListResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.acquisitionProvidersPath);
  const payload = await handleResponse<unknown>(response);
  assertAcquisitionProviderListResponse(payload);
  return payload;
}

function assertAcquisitionProviderListResponse(
  payload: unknown
): asserts payload is AcquisitionProviderListResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid acquisition provider response.');
  }
  if (!Array.isArray(payload.providers)) {
    throw new Error('Invalid acquisition provider response: missing providers.');
  }
  if (!Array.isArray(payload.policy_notes)) {
    throw new Error('Invalid acquisition provider response: missing policy_notes.');
  }
  if (!isRecord(payload.paths)) {
    throw new Error('Invalid acquisition provider response: missing paths.');
  }
  if (!isRecord(payload.default_provider_ids)) {
    throw new Error('Invalid acquisition provider response: missing default_provider_ids.');
  }
  assertStringMap(payload.paths, 'paths');
  assertStringArrayMap(payload.default_provider_ids, 'default_provider_ids');
  for (const provider of payload.providers) {
    if (!isRecord(provider)) {
      throw new Error('Invalid acquisition provider response: missing provider entry.');
    }
    assertStringField(provider, 'id');
    assertStringField(provider, 'label');
    assertStringField(provider, 'status');
    assertBooleanField(provider, 'configured');
    assertBooleanField(provider, 'available');
    assertStringArray(provider.media_kinds, 'media_kinds');
    assertStringArray(provider.capabilities, 'capabilities');
    assertStringArray(provider.rights, 'rights');
    if (!Array.isArray(provider.discovery_media_kinds)) {
      throw new Error('Invalid acquisition provider response: missing discovery_media_kinds.');
    }
    if (!Array.isArray(provider.default_eligible_media_kinds)) {
      throw new Error('Invalid acquisition provider response: missing default_eligible_media_kinds.');
    }
    assertStringArray(provider.discovery_media_kinds, 'discovery_media_kinds');
    assertStringArray(provider.default_eligible_media_kinds, 'default_eligible_media_kinds');
    if (
      provider.source_path !== undefined &&
      provider.source_path !== null &&
      typeof provider.source_path !== 'string'
    ) {
      throw new Error('Invalid acquisition provider response: invalid source_path.');
    }
    if (
      provider.source_label !== undefined &&
      provider.source_label !== null &&
      typeof provider.source_label !== 'string'
    ) {
      throw new Error('Invalid acquisition provider response: invalid source_label.');
    }
    assertStringArray(provider.policy_notes, 'policy_notes');
    assertStringArray(provider.next_actions, 'next_actions');
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function assertStringField(record: Record<string, unknown>, key: string): void {
  if (typeof record[key] !== 'string') {
    throw new Error(`Invalid acquisition provider response: missing ${key}.`);
  }
}

function assertBooleanField(record: Record<string, unknown>, key: string): void {
  if (typeof record[key] !== 'boolean') {
    throw new Error(`Invalid acquisition provider response: missing ${key}.`);
  }
}

function assertStringArray(value: unknown, key: string): void {
  if (!Array.isArray(value) || value.some((entry) => typeof entry !== 'string')) {
    throw new Error(`Invalid acquisition provider response: missing ${key}.`);
  }
}

function assertStringMap(value: Record<string, unknown>, key: string): void {
  if (Object.values(value).some((entry) => typeof entry !== 'string')) {
    throw new Error(`Invalid acquisition provider response: invalid ${key}.`);
  }
}

function assertStringArrayMap(value: Record<string, unknown>, key: string): void {
  if (
    Object.values(value).some(
      (entry) => !Array.isArray(entry) || entry.some((item) => typeof item !== 'string')
    )
  ) {
    throw new Error(`Invalid acquisition provider response: invalid ${key}.`);
  }
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
  const normalizedProvider = provider?.trim();
  if (normalizedProvider && normalizedProvider.toLowerCase() !== 'backend_defaults') {
    params.set('provider', normalizedProvider);
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

  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.pipelineCoverUploadPath, {
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
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.bookMetadataPathTemplate,
      'job_id',
      jobId
    )
  );
  return handleResponse<BookOpenLibraryMetadataResponse>(response);
}

export async function lookupBookOpenLibraryMetadata(
  jobId: string,
  payload: BookOpenLibraryMetadataLookupRequest = {}
): Promise<BookOpenLibraryMetadataResponse> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.bookMetadataLookupPathTemplate,
      'job_id',
      jobId
    ),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force: Boolean(payload.force) })
    }
  );
  return handleResponse<BookOpenLibraryMetadataResponse>(response);
}

export async function lookupBookOpenLibraryMetadataPreview(
  payload: BookOpenLibraryMetadataPreviewLookupRequest
): Promise<BookOpenLibraryMetadataPreviewResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.bookMetadataPreviewPath, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: payload.query, force: Boolean(payload.force) })
  });
  return handleResponse<BookOpenLibraryMetadataPreviewResponse>(response);
}

export async function clearMediaMetadataCache(
  query: string
): Promise<{ cleared: number }> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.bookMetadataCacheClearPath, {
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
  return withBase(
    replaceRuntimePathParameter(
      WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.coverPathTemplate,
      'job_id',
      trimmed
    )
  );
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
