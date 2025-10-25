import {
  LoginRequestPayload,
  ManagedUser,
  PasswordChangeRequestPayload,
  PipelineDefaultsResponse,
  PipelineFileBrowserResponse,
  PipelineFileEntry,
  PipelineJobActionResponse,
  PipelineJobListResponse,
  PipelineRequestPayload,
  PipelineStatusResponse,
  PipelineSubmissionResponse,
  LiveMediaResponse,
  SessionStatusResponse,
  UserAccountResponse,
  UserCreateRequestPayload,
  UserListResponse,
  UserPasswordResetRequestPayload,
  UserUpdateRequestPayload
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
  const explicit = (import.meta.env.VITE_STORAGE_BASE_URL ?? '').trim();
  if (explicit) {
    return explicit.replace(/\/$/, '');
  }

  const inferred = (import.meta.env.VITE_API_BASE_URL ?? '').trim();
  if (inferred) {
    return `${inferred.replace(/\/$/, '')}/pipelines/storage`;
  }

  if (API_BASE_URL) {
    return `${API_BASE_URL.replace(/\/$/, '')}/pipelines/storage`;
  }

  return '/pipelines/storage';
}

function withBase(path: string): string {
  if (!path.startsWith('/')) {
    return `${API_BASE_URL}/${path}`;
  }
  return `${API_BASE_URL}${path}`;
}

let authToken: string | null = null;
let unauthorizedHandler: (() => void) | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

export function setUnauthorizedHandler(handler: (() => void) | null): () => void {
  unauthorizedHandler = handler;
  return () => {
    if (unauthorizedHandler === handler) {
      unauthorizedHandler = null;
    }
  };
}

type FetchOptions = {
  skipAuth?: boolean;
};

function buildHeaders(initHeaders?: HeadersInit): Headers {
  const headers = new Headers(initHeaders ?? {});
  return headers;
}

async function apiFetch(
  path: string,
  init: RequestInit = {},
  { skipAuth = false }: FetchOptions = {}
): Promise<Response> {
  const headers = buildHeaders(init.headers);
  if (!skipAuth && authToken) {
    headers.set('Authorization', `Bearer ${authToken}`);
  }

  const response = await fetch(withBase(path), { ...init, headers });

  if (!skipAuth && (response.status === 401 || response.status === 403)) {
    unauthorizedHandler?.();
  }

  return response;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentLength = response.headers.get('content-length');
  if (contentLength === '0') {
    return undefined as T;
  }

  const contentType = response.headers.get('content-type') ?? '';
  if (!contentType.includes('application/json')) {
    const text = await response.text();
    if (!text) {
      return undefined as T;
    }
    try {
      return JSON.parse(text) as T;
    } catch (error) {
      console.warn('Unexpected non-JSON response', error);
      return undefined as T;
    }
  }

  return (await response.json()) as T;
}

export async function login(payload: LoginRequestPayload): Promise<SessionStatusResponse> {
  const response = await apiFetch(
    '/auth/login',
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    },
    { skipAuth: true }
  );
  return handleResponse<SessionStatusResponse>(response);
}

export async function logout(): Promise<void> {
  const response = await apiFetch('/auth/logout', {
    method: 'POST'
  });
  await handleResponse<unknown>(response);
}

export async function fetchSessionStatus(): Promise<SessionStatusResponse> {
  const response = await apiFetch('/auth/session');
  return handleResponse<SessionStatusResponse>(response);
}

export async function changePassword(payload: PasswordChangeRequestPayload): Promise<void> {
  const response = await apiFetch('/auth/password', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  await handleResponse<unknown>(response);
}

export async function submitPipeline(
  payload: PipelineRequestPayload
): Promise<PipelineSubmissionResponse> {
  const response = await apiFetch('/pipelines', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<PipelineSubmissionResponse>(response);
}

export async function fetchPipelineStatus(jobId: string): Promise<PipelineStatusResponse> {
  const response = await apiFetch(`/pipelines/${jobId}`);
  return handleResponse<PipelineStatusResponse>(response);
}

export async function fetchLiveMedia(jobId: string): Promise<LiveMediaResponse> {
  const response = await apiFetch(`/pipelines/jobs/${jobId}/media/live`);
  return handleResponse<LiveMediaResponse>(response);
}

export async function fetchJobs(): Promise<PipelineStatusResponse[]> {
  const response = await apiFetch('/pipelines/jobs');
  const payload = await handleResponse<PipelineJobListResponse>(response);
  return payload.jobs;
}

export async function listUsers(): Promise<ManagedUser[]> {
  const response = await apiFetch('/admin/users');
  const payload = await handleResponse<UserListResponse>(response);
  return payload.users;
}

export async function createUser(payload: UserCreateRequestPayload): Promise<ManagedUser> {
  const response = await apiFetch('/admin/users', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  const body = await handleResponse<UserAccountResponse>(response);
  return body.user;
}

export async function updateUserProfile(
  username: string,
  payload: UserUpdateRequestPayload
): Promise<ManagedUser> {
  const response = await apiFetch(`/admin/users/${encodeURIComponent(username)}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  const body = await handleResponse<UserAccountResponse>(response);
  return body.user;
}

export async function deleteUserAccount(username: string): Promise<void> {
  const response = await apiFetch(`/admin/users/${encodeURIComponent(username)}`, {
    method: 'DELETE'
  });
  await handleResponse<unknown>(response);
}

export async function suspendUserAccount(username: string): Promise<ManagedUser> {
  const response = await apiFetch(`/admin/users/${encodeURIComponent(username)}/suspend`, {
    method: 'POST'
  });
  const body = await handleResponse<UserAccountResponse>(response);
  return body.user;
}

export async function activateUserAccount(username: string): Promise<ManagedUser> {
  const response = await apiFetch(`/admin/users/${encodeURIComponent(username)}/activate`, {
    method: 'POST'
  });
  const body = await handleResponse<UserAccountResponse>(response);
  return body.user;
}

export async function resetUserPassword(
  username: string,
  payload: UserPasswordResetRequestPayload
): Promise<void> {
  const response = await apiFetch(`/admin/users/${encodeURIComponent(username)}/password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  await handleResponse<unknown>(response);
}

async function postJobAction(jobId: string, action: string): Promise<PipelineJobActionResponse> {
  const response = await apiFetch(`/pipelines/jobs/${jobId}/${action}`, {
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
  const response = await apiFetch(`/pipelines/${jobId}/metadata/refresh`, {
    method: 'POST'
  });
  return handleResponse<PipelineStatusResponse>(response);
}

export function buildEventStreamUrl(jobId: string): string {
  const baseUrl = withBase(`/pipelines/${jobId}/events`);
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
  const response = await apiFetch('/pipelines/files');
  return handleResponse<PipelineFileBrowserResponse>(response);
}

export async function fetchPipelineDefaults(): Promise<PipelineDefaultsResponse> {
  const response = await apiFetch('/pipelines/defaults');
  return handleResponse<PipelineDefaultsResponse>(response);
}

export async function uploadEpubFile(file: File): Promise<PipelineFileEntry> {
  const formData = new FormData();
  formData.append('file', file, file.name);

  const response = await apiFetch('/pipelines/files/upload', {
    method: 'POST',
    body: formData
  });

  return handleResponse<PipelineFileEntry>(response);
}
