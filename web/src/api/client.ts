import {
  PipelineRequestPayload,
  PipelineStatusResponse,
  PipelineSubmissionResponse
} from './dtos';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
const STORAGE_BASE_URL = (
  import.meta.env.VITE_STORAGE_BASE_URL ?? import.meta.env.VITE_API_BASE_URL ?? ''
).replace(/\/$/, '');

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
