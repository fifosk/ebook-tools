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
  SessionStatusResponse,
  PipelineMediaResponse,
  MediaSearchResponse,
  UserAccountResponse,
  UserCreateRequestPayload,
  UserListResponse,
  UserPasswordResetRequestPayload,
  UserUpdateRequestPayload,
  VoiceInventoryResponse,
  LibraryItem,
  LibraryIsbnLookupResponse,
  LibraryMediaRemovalResponse,
  LibraryMetadataUpdatePayload,
  LibraryMoveResponse,
  LibraryReindexResponse,
  LibrarySearchResponse,
  LibraryViewMode
} from './dtos';
import { resolve as resolveStoragePath, resolveStorageBaseUrl } from '../utils/storageResolver';

const API_BASE_URL = resolveApiBaseUrl();
const STORAGE_BASE_URL = resolveStorageBaseUrl(API_BASE_URL);

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

function withBase(path: string): string {
  if (!path.startsWith('/')) {
    return `${API_BASE_URL}/${path}`;
  }
  return `${API_BASE_URL}${path}`;
}

let authToken: string | null = null;
let authUserId: string | null = null;
let authUserRole: string | null = null;
let unauthorizedHandler: (() => void) | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

export function setAuthContext(user: SessionStatusResponse['user'] | null): void {
  authUserId = user?.username ?? null;
  authUserRole = user?.role ?? null;
}

export function getAuthContext(): {
  token: string | null;
  userId: string | null;
  userRole: string | null;
} {
  return {
    token: authToken,
    userId: authUserId,
    userRole: authUserRole
  };
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
  if (!skipAuth && authToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${authToken}`);
  }
  if (!skipAuth && authUserId && !headers.has('X-User-Id')) {
    headers.set('X-User-Id', authUserId);
  }
  if (!skipAuth && authUserRole && !headers.has('X-User-Role')) {
    headers.set('X-User-Role', authUserRole);
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

export async function fetchJobMedia(jobId: string): Promise<PipelineMediaResponse> {
  const response = await apiFetch(`/pipelines/jobs/${jobId}/media`);
  return handleResponse<PipelineMediaResponse>(response);
}

export async function fetchLiveJobMedia(jobId: string): Promise<PipelineMediaResponse> {
  const response = await apiFetch(`/pipelines/jobs/${jobId}/media/live`);
  return handleResponse<PipelineMediaResponse>(response);
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
  const params = new URLSearchParams();
  params.set('query', trimmed);
  params.set('limit', String(resolvedLimit));
  params.set('job_id', jobId);
  const response = await apiFetch(`/pipelines/search?${params.toString()}`);
  return handleResponse<MediaSearchResponse>(response);
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

export function resolveJobCoverUrl(jobId: string): string | null {
  const trimmed = (jobId ?? '').trim();
  if (!trimmed) {
    return null;
  }
  const encoded = encodeURIComponent(trimmed);
  return withBase(`/pipelines/${encoded}/cover`);
}

export function buildStorageUrl(path: string): string {
  const trimmed = (path ?? '').trim();
  if (!trimmed) {
    return resolveStoragePath(null, null, STORAGE_BASE_URL, API_BASE_URL);
  }

  const normalised = trimmed.replace(/^\/+/, '');
  if (!normalised) {
    return resolveStoragePath(null, null, STORAGE_BASE_URL, API_BASE_URL);
  }

  const [jobSegment, ...rest] = normalised.split('/');
  const fileSegment = rest.length > 0 ? rest.join('/') : '';

  return resolveStoragePath(jobSegment, fileSegment, STORAGE_BASE_URL, API_BASE_URL);
}

export async function fetchPipelineFiles(): Promise<PipelineFileBrowserResponse> {
  const response = await apiFetch('/pipelines/files');
  return handleResponse<PipelineFileBrowserResponse>(response);
}

export async function fetchPipelineDefaults(): Promise<PipelineDefaultsResponse> {
  const response = await apiFetch('/pipelines/defaults');
  return handleResponse<PipelineDefaultsResponse>(response);
}

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

export async function uploadEpubFile(file: File): Promise<PipelineFileEntry> {
  const formData = new FormData();
  formData.append('file', file, file.name);

  const response = await apiFetch('/pipelines/files/upload', {
    method: 'POST',
    body: formData
  });

  return handleResponse<PipelineFileEntry>(response);
}

export async function deletePipelineEbook(path: string): Promise<void> {
  const response = await apiFetch('/pipelines/files', {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ path })
  });
  await handleResponse<unknown>(response);
}

export interface LibrarySearchParams {
  query?: string;
  author?: string;
  book?: string;
  genre?: string;
  language?: string;
  status?: 'finished' | 'paused';
  view?: LibraryViewMode;
  page?: number;
  limit?: number;
  sort?: 'updated_at_desc' | 'updated_at_asc';
}

export async function moveJobToLibrary(
  jobId: string,
  statusOverride?: 'finished' | 'paused'
): Promise<LibraryItem> {
  const response = await apiFetch(`/api/library/move/${encodeURIComponent(jobId)}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: statusOverride ? JSON.stringify({ statusOverride }) : undefined
  });
  const payload = await handleResponse<LibraryMoveResponse>(response);
  return payload.item;
}

export async function searchLibrary(params: LibrarySearchParams): Promise<LibrarySearchResponse> {
  const search = new URLSearchParams();
  if (params.query) search.set('q', params.query);
  if (params.author) search.set('author', params.author);
  if (params.book) search.set('book', params.book);
  if (params.genre) search.set('genre', params.genre);
  if (params.language) search.set('language', params.language);
  if (params.status) search.set('status', params.status);
  if (params.view) search.set('view', params.view);
  if (typeof params.page === 'number') search.set('page', String(params.page));
  if (typeof params.limit === 'number') search.set('limit', String(params.limit));
  if (params.sort) search.set('sort', params.sort);

  const queryString = search.toString();
  const path = queryString ? `/api/library/items?${queryString}` : '/api/library/items';
  const response = await apiFetch(path);
  return handleResponse<LibrarySearchResponse>(response);
}

export async function removeLibraryMedia(jobId: string): Promise<LibraryMediaRemovalResponse> {
  const response = await apiFetch(`/api/library/remove-media/${encodeURIComponent(jobId)}`, {
    method: 'POST'
  });
  return handleResponse<LibraryMediaRemovalResponse>(response);
}

export async function removeLibraryEntry(jobId: string): Promise<void> {
  const response = await apiFetch(`/api/library/remove/${encodeURIComponent(jobId)}`, {
    method: 'DELETE'
  });
  await handleResponse<unknown>(response);
}

export async function reindexLibrary(): Promise<LibraryReindexResponse> {
  const response = await apiFetch('/api/library/reindex', {
    method: 'POST'
  });
  return handleResponse<LibraryReindexResponse>(response);
}

export async function refreshLibraryMetadata(jobId: string): Promise<LibraryItem> {
  const response = await apiFetch(`/api/library/items/${encodeURIComponent(jobId)}/refresh`, {
    method: 'POST'
  });
  return handleResponse<LibraryItem>(response);
}

export async function updateLibraryMetadata(
  jobId: string,
  payload: LibraryMetadataUpdatePayload
): Promise<LibraryItem> {
  const response = await apiFetch(`/api/library/items/${encodeURIComponent(jobId)}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<LibraryItem>(response);
}

export async function uploadLibrarySource(jobId: string, file: File): Promise<LibraryItem> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiFetch(`/api/library/items/${encodeURIComponent(jobId)}/upload-source`, {
    method: 'POST',
    body: formData
  });
  return handleResponse<LibraryItem>(response);
}

export async function applyLibraryIsbn(jobId: string, isbn: string): Promise<LibraryItem> {
  const response = await apiFetch(`/api/library/items/${encodeURIComponent(jobId)}/isbn`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ isbn })
  });
  return handleResponse<LibraryItem>(response);
}

export async function lookupLibraryIsbnMetadata(isbn: string): Promise<LibraryIsbnLookupResponse> {
  const response = await apiFetch(`/api/library/isbn/lookup?isbn=${encodeURIComponent(isbn)}`);
  return handleResponse<LibraryIsbnLookupResponse>(response);
}

export function appendAccessToken(url: string): string {
  const token = getAuthToken();
  if (!token) {
    return url;
  }

  const absolute = normaliseApiUrl(url);
  try {
    const resolved = new URL(absolute);
    resolved.searchParams.set('access_token', token);
    return resolved.toString();
  } catch (error) {
    const separator = absolute.includes('?') ? '&' : '?';
    return `${absolute}${separator}access_token=${encodeURIComponent(token)}`;
  }
}

export function resolveLibraryMediaUrl(jobId: string, relativePath: string): string | null {
  const trimmedJobId = (jobId ?? '').trim();
  const trimmedPath = (relativePath ?? '').trim();
  if (!trimmedJobId || !trimmedPath) {
    return null;
  }
  const encodedJobId = encodeURIComponent(trimmedJobId);
  const normalisedPath = trimmedPath.replace(/^\/+/, '');
  const encodedPath = normalisedPath
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/');
  const url = withBase(`/api/library/media/${encodedJobId}/file/${encodedPath}`);
  return appendAccessToken(url);
}

export async function fetchLibraryMedia(jobId: string): Promise<PipelineMediaResponse> {
  const response = await apiFetch(`/api/library/media/${encodeURIComponent(jobId)}`);
  return handleResponse<PipelineMediaResponse>(response);
}

function normaliseApiUrl(candidate: string): string {
  if (/^https?:\/\//i.test(candidate)) {
    return candidate;
  }
  return withBase(candidate);
}
