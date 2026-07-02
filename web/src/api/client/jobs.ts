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
  const payload = await handleResponse<unknown>(response);
  assertPipelineJobListResponse(payload);
  return payload.jobs;
}

function assertPipelineJobListResponse(payload: unknown): asserts payload is PipelineJobListResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid pipeline job list response.');
  }
  if (!Array.isArray(payload.jobs)) {
    throw new Error('Invalid pipeline job list response: missing jobs.');
  }
  payload.jobs.forEach(assertPipelineJobListEntry);
}

function assertPipelineJobListEntry(payload: unknown): void {
  if (!isRecord(payload)) {
    throw new Error('Invalid pipeline job list response: missing job entry.');
  }
  assertPipelineJobStringField(payload, 'job_id');
  assertPipelineJobStringField(payload, 'job_type');
  assertPipelineJobStatus(payload.status);
  assertPipelineJobStringField(payload, 'created_at');
}

function assertPipelineJobStringField(record: Record<string, unknown>, key: string): void {
  if (typeof record[key] !== 'string') {
    throw new Error(`Invalid pipeline job list response: missing ${key}.`);
  }
}

function assertPipelineJobStatus(value: unknown): void {
  if (
    value !== 'pending' &&
    value !== 'running' &&
    value !== 'pausing' &&
    value !== 'paused' &&
    value !== 'completed' &&
    value !== 'failed' &&
    value !== 'cancelled'
  ) {
    throw new Error('Invalid pipeline job list response: missing status.');
  }
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
  const payload = await handleResponse<unknown>(response);
  assertJobTimingResponse(payload);
  return payload;
}

function assertJobTimingResponse(payload: unknown): asserts payload is JobTimingResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid job timing response.');
  }
  assertTimingStringField(payload, 'job_id', 'job timing');
  if (!isRecord(payload.tracks)) {
    throw new Error('Invalid job timing response: missing tracks.');
  }
  Object.values(payload.tracks).forEach(assertJobTimingTrackPayload);
  if (!isRecord(payload.audio)) {
    throw new Error('Invalid job timing response: missing audio.');
  }
  Object.values(payload.audio).forEach(assertJobTimingAudioBinding);
  if (payload.highlighting_policy !== null && typeof payload.highlighting_policy !== 'string') {
    throw new Error('Invalid job timing response: invalid highlighting_policy.');
  }
  assertTimingBooleanField(payload, 'has_estimated_segments', 'job timing');
}

function assertJobTimingTrackPayload(payload: unknown): void {
  if (!isRecord(payload)) {
    throw new Error('Invalid job timing response: missing track entry.');
  }
  assertTimingTrackName(payload.track, 'job timing track');
  if (!Array.isArray(payload.segments)) {
    throw new Error('Invalid job timing response: missing segments.');
  }
  if (
    payload.playback_rate !== undefined &&
    payload.playback_rate !== null &&
    typeof payload.playback_rate !== 'number'
  ) {
    throw new Error('Invalid job timing response: invalid playback_rate.');
  }
}

function assertJobTimingAudioBinding(payload: unknown): void {
  if (!isRecord(payload)) {
    throw new Error('Invalid job timing response: missing audio binding.');
  }
  assertTimingTrackName(payload.track, 'job timing audio');
  assertTimingBooleanField(payload, 'available', 'job timing audio');
}

function assertTimingTrackName(value: unknown, responseKind: string): void {
  if (value !== 'mix' && value !== 'translation' && value !== 'original') {
    throw new Error(`Invalid ${responseKind} response: missing track.`);
  }
}

function assertTimingStringField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (typeof record[key] !== 'string') {
    throw new Error(`Invalid ${responseKind} response: missing ${key}.`);
  }
}

function assertTimingBooleanField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (typeof record[key] !== 'boolean') {
    throw new Error(`Invalid ${responseKind} response: missing ${key}.`);
  }
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
  const payload = await handleResponse<unknown>(response);
  assertPipelineFileBrowserResponse(payload);
  return payload;
}

function assertPipelineFileBrowserResponse(
  payload: unknown
): asserts payload is PipelineFileBrowserResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid pipeline file browser response.');
  }
  assertPipelineFileEntries(payload.ebooks, 'ebooks');
  assertPipelineFileEntries(payload.outputs, 'outputs');
  assertPipelineFileStringField(payload, 'books_root', 'file browser');
  assertPipelineFileStringField(payload, 'output_root', 'file browser');
}

function assertPipelineFileEntries(value: unknown, key: string): void {
  if (!Array.isArray(value)) {
    throw new Error(`Invalid pipeline file browser response: missing ${key}.`);
  }
  for (const entry of value) {
    assertPipelineFileEntry(entry);
  }
}

function assertPipelineFileEntry(payload: unknown): asserts payload is PipelineFileEntry {
  if (!isRecord(payload)) {
    throw new Error('Invalid pipeline file entry response.');
  }
  assertPipelineFileStringField(payload, 'name', 'file entry');
  assertPipelineFileStringField(payload, 'path', 'file entry');
  assertPipelineFileStringField(payload, 'type', 'file entry');
  assertPipelineFileOptionalNumber(payload.size_bytes, 'size_bytes');
  assertPipelineFileOptionalString(payload.modified_at, 'modified_at');
}

function assertPipelineFileStringField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (typeof record[key] !== 'string') {
    throw new Error(`Invalid pipeline ${responseKind} response: missing ${key}.`);
  }
}

function assertPipelineFileOptionalString(value: unknown, key: string): void {
  if (value !== undefined && value !== null && typeof value !== 'string') {
    throw new Error(`Invalid pipeline file entry response: invalid ${key}.`);
  }
}

function assertPipelineFileOptionalNumber(value: unknown, key: string): void {
  if (value !== undefined && value !== null && typeof value !== 'number') {
    throw new Error(`Invalid pipeline file entry response: invalid ${key}.`);
  }
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
  const payload = await handleResponse<unknown>(response);
  assertAcquisitionDiscoveryResponse(payload);
  return payload;
}

function assertAcquisitionDiscoveryResponse(
  payload: unknown
): asserts payload is AcquisitionDiscoveryResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid acquisition discovery response.');
  }
  if (!Array.isArray(payload.candidates)) {
    throw new Error('Invalid acquisition discovery response: missing candidates.');
  }
  assertDiscoveryStringArray(payload.policy_notes, 'policy_notes');
  assertDiscoveryStringArray(payload.providers_queried, 'providers_queried');
  for (const candidate of payload.candidates) {
    if (!isRecord(candidate)) {
      throw new Error('Invalid acquisition discovery response: missing candidate entry.');
    }
    assertDiscoveryStringField(candidate, 'candidate_id');
    assertDiscoveryStringField(candidate, 'provider');
    assertDiscoveryStringField(candidate, 'media_kind');
    assertDiscoveryStringField(candidate, 'title');
    assertDiscoveryStringField(candidate, 'rights');
    assertDiscoveryStringField(candidate, 'candidate_token');
    assertDiscoveryStringArray(candidate.capabilities, 'capabilities');
    assertDiscoveryStringArray(candidate.contributors, 'contributors');
    assertDiscoverySubtitleHints(candidate.subtitles);
    if (!isRecord(candidate.metadata)) {
      throw new Error('Invalid acquisition discovery response: missing metadata.');
    }
    if (typeof candidate.requires_confirmation !== 'boolean') {
      throw new Error('Invalid acquisition discovery response: missing requires_confirmation.');
    }
    assertDiscoveryStringArray(candidate.policy_notes, 'policy_notes');
    assertOptionalString(candidate.subtitle, 'subtitle');
    assertOptionalString(candidate.language, 'language');
    assertOptionalString(candidate.published_at, 'published_at');
    assertOptionalString(candidate.source_url, 'source_url');
    assertOptionalString(candidate.thumbnail_url, 'thumbnail_url');
    assertOptionalString(candidate.cover_url, 'cover_url');
    assertOptionalString(candidate.local_path, 'local_path');
    assertOptionalString(candidate.modified_at, 'modified_at');
    assertOptionalNumber(candidate.year, 'year');
    assertOptionalNumber(candidate.size_bytes, 'size_bytes');
    assertOptionalNumber(candidate.duration_seconds, 'duration_seconds');
  }
}

function assertDiscoveryStringField(record: Record<string, unknown>, key: string): void {
  if (typeof record[key] !== 'string') {
    throw new Error(`Invalid acquisition discovery response: missing ${key}.`);
  }
}

function assertDiscoveryStringArray(value: unknown, key: string): void {
  if (!Array.isArray(value) || value.some((entry) => typeof entry !== 'string')) {
    throw new Error(`Invalid acquisition discovery response: missing ${key}.`);
  }
}

function assertDiscoverySubtitleHints(value: unknown): void {
  if (!Array.isArray(value)) {
    throw new Error('Invalid acquisition discovery response: missing subtitles.');
  }
  for (const subtitle of value) {
    if (!isRecord(subtitle)) {
      throw new Error('Invalid acquisition discovery response: missing subtitle entry.');
    }
    assertDiscoveryStringField(subtitle, 'path');
    assertDiscoveryStringField(subtitle, 'filename');
    assertOptionalString(subtitle.language, 'language');
    assertOptionalString(subtitle.format, 'format');
  }
}

function assertOptionalString(value: unknown, key: string): void {
  if (value !== undefined && value !== null && typeof value !== 'string') {
    throw new Error(`Invalid acquisition discovery response: invalid ${key}.`);
  }
}

function assertOptionalNumber(value: unknown, key: string): void {
  if (value !== undefined && value !== null && typeof value !== 'number') {
    throw new Error(`Invalid acquisition discovery response: invalid ${key}.`);
  }
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
  const responsePayload = await handleResponse<unknown>(response);
  assertAcquisitionArtifactResponse(responsePayload);
  return responsePayload;
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
  const payload = await handleResponse<unknown>(response);
  assertAcquisitionPreparedArtifactResponse(payload);
  return payload;
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
  const responsePayload = await handleResponse<unknown>(response);
  assertAcquisitionJobStatusResponse(responsePayload);
  return responsePayload;
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
  const payload = await handleResponse<unknown>(response);
  assertAcquisitionJobStatusResponse(payload);
  return payload;
}

function assertAcquisitionArtifactResponse(
  payload: unknown
): asserts payload is AcquisitionArtifactResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid acquisition artifact response.');
  }
  assertHandoffStringField(payload, 'provider', 'artifact');
  assertHandoffStringField(payload, 'media_kind', 'artifact');
  assertHandoffStringField(payload, 'status', 'artifact');
  assertHandoffStringField(payload, 'artifact_id', 'artifact');
  assertHandoffStringField(payload, 'artifact_path', 'artifact');
  assertHandoffStringField(payload, 'local_path', 'artifact');
  assertHandoffStringField(payload, 'filename', 'artifact');
  assertHandoffNumberField(payload, 'size_bytes', 'artifact');
  assertHandoffStringField(payload, 'modified_at', 'artifact');
  assertHandoffStringArray(payload.next_actions, 'next_actions', 'artifact');
  assertHandoffMetadata(payload.metadata, 'artifact');
}

function assertAcquisitionPreparedArtifactResponse(
  payload: unknown
): asserts payload is AcquisitionPreparedArtifactResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid acquisition prepared artifact response.');
  }
  assertHandoffStringField(payload, 'provider', 'prepared artifact');
  assertHandoffStringField(payload, 'media_kind', 'prepared artifact');
  assertHandoffStringField(payload, 'source_kind', 'prepared artifact');
  assertHandoffStringField(payload, 'local_path', 'prepared artifact');
  assertHandoffOptionalString(payload.input_file, 'input_file', 'prepared artifact');
  assertHandoffOptionalString(payload.video_path, 'video_path', 'prepared artifact');
  assertHandoffOptionalString(payload.subtitle_path, 'subtitle_path', 'prepared artifact');
  assertHandoffSubtitleHints(payload.subtitles, 'prepared artifact');
  assertHandoffStringArray(payload.next_actions, 'next_actions', 'prepared artifact');
  assertHandoffMetadata(payload.metadata, 'prepared artifact');
}

function assertAcquisitionJobStatusResponse(
  payload: unknown
): asserts payload is AcquisitionJobStatusResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid acquisition job response.');
  }
  assertHandoffStringField(payload, 'provider', 'job');
  assertHandoffStringField(payload, 'task_id', 'job');
  assertHandoffStringField(payload, 'status', 'job');
  assertHandoffOptionalNumber(payload.progress, 'progress', 'job');
  assertHandoffOptionalString(payload.message, 'message', 'job');
  assertHandoffOptionalString(payload.external_task_id, 'external_task_id', 'job');
  assertHandoffOptionalString(payload.raw_status, 'raw_status', 'job');
  assertHandoffOptionalString(payload.started_at, 'started_at', 'job');
  assertHandoffStringField(payload, 'updated_at', 'job');
  assertHandoffStringArray(payload.completed_files, 'completed_files', 'job');
  assertHandoffStringArray(payload.next_actions, 'next_actions', 'job');
  assertHandoffMetadata(payload.metadata, 'job');
}

function assertHandoffStringField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (typeof record[key] !== 'string') {
    throw new Error(`Invalid acquisition ${responseKind} response: missing ${key}.`);
  }
}

function assertHandoffNumberField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (typeof record[key] !== 'number') {
    throw new Error(`Invalid acquisition ${responseKind} response: missing ${key}.`);
  }
}

function assertHandoffStringArray(value: unknown, key: string, responseKind: string): void {
  if (!Array.isArray(value) || value.some((entry) => typeof entry !== 'string')) {
    throw new Error(`Invalid acquisition ${responseKind} response: missing ${key}.`);
  }
}

function assertHandoffSubtitleHints(value: unknown, responseKind: string): void {
  if (!Array.isArray(value)) {
    throw new Error(`Invalid acquisition ${responseKind} response: missing subtitles.`);
  }
  for (const subtitle of value) {
    if (!isRecord(subtitle)) {
      throw new Error(`Invalid acquisition ${responseKind} response: missing subtitle entry.`);
    }
    assertHandoffStringField(subtitle, 'path', responseKind);
    assertHandoffStringField(subtitle, 'filename', responseKind);
    assertHandoffOptionalString(subtitle.language, 'language', responseKind);
    assertHandoffOptionalString(subtitle.format, 'format', responseKind);
  }
}

function assertHandoffMetadata(value: unknown, responseKind: string): void {
  if (!isRecord(value)) {
    throw new Error(`Invalid acquisition ${responseKind} response: missing metadata.`);
  }
}

function assertHandoffOptionalString(value: unknown, key: string, responseKind: string): void {
  if (value !== undefined && value !== null && typeof value !== 'string') {
    throw new Error(`Invalid acquisition ${responseKind} response: invalid ${key}.`);
  }
}

function assertHandoffOptionalNumber(value: unknown, key: string, responseKind: string): void {
  if (value !== undefined && value !== null && typeof value !== 'number') {
    throw new Error(`Invalid acquisition ${responseKind} response: invalid ${key}.`);
  }
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
  const payload = await handleResponse<unknown>(response);
  assertPipelineIntakeStatusResponse(payload);
  return payload;
}

function assertPipelineIntakeStatusResponse(
  payload: unknown
): asserts payload is PipelineIntakeStatusResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid pipeline intake status response.');
  }
  assertReadinessBooleanField(payload, 'acceptingJobs', 'intake status');
  assertReadinessBooleanField(payload, 'isUnderPressure', 'intake status');
  assertReadinessNumberField(payload, 'queueDepth', 'intake status');
  assertReadinessNumberField(payload, 'activeCount', 'intake status');
  assertReadinessOptionalNumberField(payload.softLimit, 'softLimit', 'intake status');
  assertReadinessOptionalNumberField(payload.hardLimit, 'hardLimit', 'intake status');
  assertReadinessNumberField(payload, 'delayCount', 'intake status');
}

export async function fetchBookContentIndex(inputFile: string): Promise<BookContentIndexResponse> {
  const trimmed = inputFile.trim();
  const params = new URLSearchParams({ input_file: trimmed });
  const response = await apiFetch(
    `${WEB_CREATE_RUNTIME_CONTRACT.pipelineContentIndexPath}?${params.toString()}`
  );
  const payload = await handleResponse<unknown>(response);
  assertBookContentIndexResponse(payload);
  return payload;
}

function assertBookContentIndexResponse(payload: unknown): asserts payload is BookContentIndexResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid book content-index response.');
  }
  assertContentIndexStringField(payload, 'input_file', 'book content-index');
  if (!isRecord(payload.content_index)) {
    throw new Error('Invalid book content-index response: missing content_index.');
  }
  if (typeof payload.content_index.total_sentences !== 'number') {
    throw new Error('Invalid book content-index response: missing total_sentences.');
  }
  if (!Array.isArray(payload.content_index.chapters)) {
    throw new Error('Invalid book content-index response: missing chapters.');
  }
  payload.content_index.chapters.forEach((chapter) => {
    if (!isRecord(chapter)) {
      throw new Error('Invalid book content-index response: invalid chapter.');
    }
  });
}

function assertContentIndexStringField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (typeof record[key] !== 'string') {
    throw new Error(`Invalid ${responseKind} response: missing ${key}.`);
  }
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
  const responsePayload = await handleResponse<unknown>(response);
  assertImageNodeAvailabilityResponse(responsePayload);
  return responsePayload;
}

function assertImageNodeAvailabilityResponse(
  payload: unknown
): asserts payload is ImageNodeAvailabilityResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid image node availability response.');
  }
  if (!Array.isArray(payload.nodes)) {
    throw new Error('Invalid image node availability response: missing nodes.');
  }
  assertReadinessStringArray(payload.available, 'available', 'image node availability');
  assertReadinessStringArray(payload.unavailable, 'unavailable', 'image node availability');
  for (const node of payload.nodes) {
    if (!isRecord(node)) {
      throw new Error('Invalid image node availability response: missing node entry.');
    }
    assertReadinessStringField(node, 'base_url', 'image node availability');
    assertReadinessBooleanField(node, 'available', 'image node availability');
  }
}

function assertReadinessStringField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (typeof record[key] !== 'string') {
    throw new Error(`Invalid ${responseKind} response: missing ${key}.`);
  }
}

function assertReadinessBooleanField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (typeof record[key] !== 'boolean') {
    throw new Error(`Invalid ${responseKind} response: missing ${key}.`);
  }
}

function assertReadinessNumberField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (typeof record[key] !== 'number') {
    throw new Error(`Invalid ${responseKind} response: missing ${key}.`);
  }
}

function assertReadinessOptionalNumberField(
  value: unknown,
  key: string,
  responseKind: string
): void {
  if (value !== undefined && value !== null && typeof value !== 'number') {
    throw new Error(`Invalid ${responseKind} response: invalid ${key}.`);
  }
}

function assertReadinessStringArray(value: unknown, key: string, responseKind: string): void {
  if (!Array.isArray(value) || value.some((entry) => typeof entry !== 'string')) {
    throw new Error(`Invalid ${responseKind} response: missing ${key}.`);
  }
}

export async function uploadEpubFile(file: File): Promise<PipelineFileEntry> {
  const formData = new FormData();
  formData.append('file', file, file.name);

  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.pipelineUploadPath, {
    method: 'POST',
    body: formData
  });

  const payload = await handleResponse<unknown>(response);
  assertPipelineFileEntry(payload);
  return payload;
}

export async function uploadCoverFile(file: File): Promise<PipelineFileEntry> {
  const formData = new FormData();
  formData.append('file', file, file.name);

  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.pipelineCoverUploadPath, {
    method: 'POST',
    body: formData
  });

  const payload = await handleResponse<unknown>(response);
  assertPipelineFileEntry(payload);
  return payload;
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
  const payload = await handleResponse<unknown>(response);
  assertLlmModelListResponse(payload);
  return payload.models;
}

function assertLlmModelListResponse(payload: unknown): asserts payload is LlmModelListResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid LLM model list response.');
  }
  if (!Array.isArray(payload.models) || payload.models.some((entry) => typeof entry !== 'string')) {
    throw new Error('Invalid LLM model list response: missing models.');
  }
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
  let response: Response;
  try {
    response = await apiFetch(
      replaceRuntimePathParameters(WEB_LINGUIST_RUNTIME_CONTRACT.lookupCacheWordPathTemplate, {
        job_id: jobId,
        word
      }),
      {},
      { suppressUnauthorized: true }
    );
  } catch {
    return null;
  }
  if (response.status === 401 || response.status === 403 || response.status === 404) {
    return null;
  }
  const payload = await handleResponse<unknown>(response);
  assertLookupCacheEntryResponse(payload);
  return payload;
}

export async function fetchCachedLookupsBulk(
  jobId: string,
  words: string[]
): Promise<LookupCacheBulkResponse | null> {
  let response: Response;
  try {
    response = await apiFetch(
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
  } catch {
    return null;
  }
  if (response.status === 401 || response.status === 403 || response.status === 404) {
    return null;
  }
  const payload = await handleResponse<unknown>(response);
  assertLookupCacheBulkResponse(payload);
  return payload;
}

export async function fetchLookupCacheSummary(
  jobId: string
): Promise<LookupCacheSummaryResponse | null> {
  let response: Response;
  try {
    response = await apiFetch(
      replaceRuntimePathParameter(
        WEB_LINGUIST_RUNTIME_CONTRACT.lookupCacheSummaryPathTemplate,
        'job_id',
        jobId
      ),
      {},
      { suppressUnauthorized: true }
    );
  } catch {
    return null;
  }
  if (response.status === 401 || response.status === 403 || response.status === 404) {
    return null;
  }
  const payload = await handleResponse<unknown>(response);
  assertLookupCacheSummaryResponse(payload);
  return payload;
}

function assertLookupCacheEntryResponse(
  payload: unknown
): asserts payload is LookupCacheEntryResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid lookup cache entry response.');
  }
  assertReadinessStringField(payload, 'word', 'lookup cache entry');
  assertReadinessStringField(payload, 'word_normalized', 'lookup cache entry');
  assertReadinessBooleanField(payload, 'cached', 'lookup cache entry');
  if (!Array.isArray(payload.audio_references)) {
    throw new Error('Invalid lookup cache entry response: missing audio_references.');
  }
  payload.audio_references.forEach(assertLookupCacheAudioRef);
  if (
    payload.lookup_result !== undefined &&
    payload.lookup_result !== null &&
    !isRecord(payload.lookup_result)
  ) {
    throw new Error('Invalid lookup cache entry response: invalid lookup_result.');
  }
}

function assertLookupCacheAudioRef(payload: unknown): void {
  if (!isRecord(payload)) {
    throw new Error('Invalid lookup cache audio reference response.');
  }
  assertReadinessStringField(payload, 'chunk_id', 'lookup cache audio reference');
  assertReadinessNumberField(payload, 'sentence_idx', 'lookup cache audio reference');
  assertReadinessNumberField(payload, 'token_idx', 'lookup cache audio reference');
  assertReadinessStringField(payload, 'track', 'lookup cache audio reference');
  assertReadinessNumberField(payload, 't0', 'lookup cache audio reference');
  assertReadinessNumberField(payload, 't1', 'lookup cache audio reference');
}

function assertLookupCacheBulkResponse(
  payload: unknown
): asserts payload is LookupCacheBulkResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid lookup cache bulk response.');
  }
  if (!isRecord(payload.results)) {
    throw new Error('Invalid lookup cache bulk response: missing results.');
  }
  Object.values(payload.results).forEach((entry) => {
    if (entry !== null) {
      assertLookupCacheEntryResponse(entry);
    }
  });
  assertReadinessNumberField(payload, 'cache_hits', 'lookup cache bulk');
  assertReadinessNumberField(payload, 'cache_misses', 'lookup cache bulk');
}

function assertLookupCacheSummaryResponse(
  payload: unknown
): asserts payload is LookupCacheSummaryResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid lookup cache summary response.');
  }
  assertReadinessBooleanField(payload, 'available', 'lookup cache summary');
  assertReadinessNumberField(payload, 'word_count', 'lookup cache summary');
  assertReadinessStringField(payload, 'input_language', 'lookup cache summary');
  assertReadinessStringField(payload, 'definition_language', 'lookup cache summary');
  assertReadinessNumberField(payload, 'llm_calls', 'lookup cache summary');
  assertReadinessNumberField(payload, 'skipped_stopwords', 'lookup cache summary');
  assertReadinessNumberField(payload, 'build_time_seconds', 'lookup cache summary');
}
