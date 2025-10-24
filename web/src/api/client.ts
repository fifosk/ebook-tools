import {
  PipelineDefaultsResponse,
  PipelineFileBrowserResponse,
  PipelineFileEntry,
  PipelineJobActionResponse,
  PipelineJobListResponse,
  PipelineRequestPayload,
  PipelineStatusResponse,
  PipelineSubmissionResponse
} from './dtos';

const API_BASE_URL = resolveApiBaseUrl();
const STORAGE_BASE_URL = resolveStorageBaseUrl();

function resolveApiBaseUrl(): string {
  const explicit = (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/$/, '');
  if (explicit) {
    return explicit;
  }

  if (typeof window !== 'undefined') {
    const url = new URL(window.location.href);
    if (url.port === '5173') {
      url.port = '8000';
      return url.origin.replace(/\/$/, '');
    }
    return url.origin.replace(/\/$/, '');
  }

  return '';
}

function resolveStorageBaseUrl(): string {
  const explicit = (import.meta.env.VITE_STORAGE_BASE_URL ?? '').trim().replace(/\/$/, '');
  if (explicit) {
    return explicit;
  }

  const inferred = (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/$/, '');
  if (inferred) {
    return inferred;
  }

  return API_BASE_URL;
}

function withBase(path: string): string {
  if (!path.startsWith('/')) {
    return `${API_BASE_URL}/${path}`;
  }
  return `${API_BASE_URL}${path}`;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function submitPipeline(
  payload: PipelineRequestPayload
): Promise<PipelineSubmissionResponse> {
  const response = await fetch(withBase('/pipelines'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<PipelineSubmissionResponse>(response);
}

export async function fetchPipelineStatus(jobId: string): Promise<PipelineStatusResponse> {
  const response = await fetch(withBase(`/pipelines/${jobId}`));
  return handleResponse<PipelineStatusResponse>(response);
}

export async function fetchJobs(): Promise<PipelineStatusResponse[]> {
  const response = await fetch(withBase('/pipelines/jobs'));
  const payload = await handleResponse<PipelineJobListResponse>(response);
  return payload.jobs;
}

async function postJobAction(jobId: string, action: string): Promise<PipelineJobActionResponse> {
  const response = await fetch(withBase(`/pipelines/jobs/${jobId}/${action}`), {
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

export async function refreshPipelineMetadata(jobId: string): Promise<PipelineStatusResponse> {
  const response = await fetch(withBase(`/pipelines/${jobId}/metadata/refresh`), {
    method: 'POST'
  });
  return handleResponse<PipelineStatusResponse>(response);
}

export function buildEventStreamUrl(jobId: string): string {
  return withBase(`/pipelines/${jobId}/events`);
}

export function buildStorageUrl(path: string): string {
  if (!STORAGE_BASE_URL) {
    throw new Error('VITE_STORAGE_BASE_URL is not configured.');
  }
  if (!path) {
    return STORAGE_BASE_URL;
  }
  if (!path.startsWith('/')) {
    return `${STORAGE_BASE_URL}/${path}`;
  }
  return `${STORAGE_BASE_URL}${path}`;
}

export async function fetchPipelineFiles(): Promise<PipelineFileBrowserResponse> {
  const response = await fetch(withBase('/pipelines/files'));
  return handleResponse<PipelineFileBrowserResponse>(response);
}

export async function fetchPipelineDefaults(): Promise<PipelineDefaultsResponse> {
  const response = await fetch(withBase('/pipelines/defaults'));
  return handleResponse<PipelineDefaultsResponse>(response);
}

export async function uploadEpubFile(file: File): Promise<PipelineFileEntry> {
  const formData = new FormData();
  formData.append('file', file, file.name);

  const response = await fetch(withBase('/pipelines/files/upload'), {
    method: 'POST',
    body: formData
  });

  return handleResponse<PipelineFileEntry>(response);
}
