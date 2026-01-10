import {
  LoginRequestPayload,
  ManagedUser,
  PasswordChangeRequestPayload,
  ImageNodeAvailabilityRequestPayload,
  ImageNodeAvailabilityResponse,
  PipelineDefaultsResponse,
  BookContentIndexResponse,
  PipelineFileBrowserResponse,
  PipelineFileEntry,
  PipelineJobActionResponse,
  PipelineJobListResponse,
  PipelineRequestPayload,
  PipelineStatusResponse,
  PipelineSubmissionResponse,
  JobTimingResponse,
  SessionStatusResponse,
  PipelineMediaResponse,
  PipelineMediaFile,
  VideoGenerationRequestPayload,
  VideoGenerationResponse,
  MediaSearchResult,
  MediaSearchResponse,
  ExportRequestPayload,
  ExportResponse,
  AccessPolicyUpdatePayload,
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
  LibraryViewMode,
  SubtitleJobResultPayload,
  LlmModelListResponse,
  SubtitleSourceEntry,
  SubtitleSourceListResponse,
  SubtitleDeleteResponse,
  SubtitleTvMetadataLookupRequest,
  SubtitleTvMetadataPreviewLookupRequest,
  SubtitleTvMetadataPreviewResponse,
  SubtitleTvMetadataResponse,
  YoutubeVideoMetadataLookupRequest,
  YoutubeVideoMetadataPreviewLookupRequest,
  YoutubeVideoMetadataPreviewResponse,
  YoutubeVideoMetadataResponse,
  BookOpenLibraryMetadataLookupRequest,
  BookOpenLibraryMetadataPreviewLookupRequest,
  BookOpenLibraryMetadataPreviewResponse,
  BookOpenLibraryMetadataResponse,
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
  YoutubeDubResponse,
  AssistantLookupRequest,
  AssistantLookupResponse,
  ReadingBedDeleteResponse,
  ReadingBedEntry,
  ReadingBedListResponse,
  ReadingBedUpdateRequestPayload,
  PlaybackBookmarkCreatePayload,
  PlaybackBookmarkDeleteResponse,
  PlaybackBookmarkEntry,
  PlaybackBookmarkListResponse,
  SentenceImageInfoBatchResponse,
  SentenceImageInfoResponse,
  SentenceImageRegenerateRequestPayload,
  SentenceImageRegenerateResponse
} from './dtos';
import { resolve as resolveStoragePath, resolveStorageBaseUrl } from '../utils/storageResolver';
import type { ExportPlayerManifest } from '../types/exportPlayer';

export const API_BASE_URL = resolveApiBaseUrl();
const STORAGE_BASE_URL = resolveStorageBaseUrl(API_BASE_URL);

export function resolveApiBaseUrl(): string {
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

export function withBase(path: string): string {
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
    '/api/auth/login',
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
  const response = await apiFetch('/api/auth/logout', {
    method: 'POST'
  });
  await handleResponse<unknown>(response);
}

export async function fetchSessionStatus(): Promise<SessionStatusResponse> {
  const response = await apiFetch('/api/auth/session');
  return handleResponse<SessionStatusResponse>(response);
}

export async function fetchSubtitleSources(directory?: string): Promise<SubtitleSourceEntry[]> {
  const query = directory ? `?directory=${encodeURIComponent(directory)}` : '';
  const response = await apiFetch(`/api/subtitles/sources${query}`);
  const payload = await handleResponse<SubtitleSourceListResponse>(response);
  return payload.sources;
}

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

export async function fetchLlmModels(): Promise<string[]> {
  const response = await apiFetch('/api/pipelines/llm-models');
  const payload = await handleResponse<LlmModelListResponse>(response);
  return payload.models ?? [];
}

export async function fetchSubtitleModels(): Promise<string[]> {
  return fetchLlmModels();
}

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

export async function changePassword(payload: PasswordChangeRequestPayload): Promise<void> {
  const response = await apiFetch('/api/auth/password', {
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

export async function listUsers(): Promise<ManagedUser[]> {
  const response = await apiFetch('/api/admin/users');
  const payload = await handleResponse<UserListResponse>(response);
  return payload.users;
}

export async function createUser(payload: UserCreateRequestPayload): Promise<ManagedUser> {
  const response = await apiFetch('/api/admin/users', {
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
  const response = await apiFetch(`/api/admin/users/${encodeURIComponent(username)}`, {
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
  const response = await apiFetch(`/api/admin/users/${encodeURIComponent(username)}`, {
    method: 'DELETE'
  });
  await handleResponse<unknown>(response);
}

export async function suspendUserAccount(username: string): Promise<ManagedUser> {
  const response = await apiFetch(`/api/admin/users/${encodeURIComponent(username)}/suspend`, {
    method: 'POST'
  });
  const body = await handleResponse<UserAccountResponse>(response);
  return body.user;
}

export async function activateUserAccount(username: string): Promise<ManagedUser> {
  const response = await apiFetch(`/api/admin/users/${encodeURIComponent(username)}/activate`, {
    method: 'POST'
  });
  const body = await handleResponse<UserAccountResponse>(response);
  return body.user;
}

export async function resetUserPassword(
  username: string,
  payload: UserPasswordResetRequestPayload
): Promise<void> {
  const response = await apiFetch(`/api/admin/users/${encodeURIComponent(username)}/password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  await handleResponse<unknown>(response);
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

export async function fetchReadingBeds(signal?: AbortSignal): Promise<ReadingBedListResponse> {
  const response = await apiFetch('/api/reading-beds', { signal });
  return handleResponse<ReadingBedListResponse>(response);
}

export async function uploadReadingBed(file: File, label?: string): Promise<ReadingBedEntry> {
  const form = new FormData();
  form.append('file', file);
  if (label && label.trim()) {
    form.append('label', label.trim());
  }
  const response = await apiFetch('/api/admin/reading-beds', {
    method: 'POST',
    body: form
  });
  return handleResponse<ReadingBedEntry>(response);
}

export async function updateReadingBed(bedId: string, payload: ReadingBedUpdateRequestPayload): Promise<ReadingBedEntry> {
  const response = await apiFetch(`/api/admin/reading-beds/${encodeURIComponent(bedId)}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<ReadingBedEntry>(response);
}

export async function deleteReadingBed(bedId: string): Promise<ReadingBedDeleteResponse> {
  const response = await apiFetch(`/api/admin/reading-beds/${encodeURIComponent(bedId)}`, {
    method: 'DELETE'
  });
  return handleResponse<ReadingBedDeleteResponse>(response);
}

export async function fetchPlaybackBookmarks(jobId: string): Promise<PlaybackBookmarkListResponse> {
  const response = await apiFetch(`/api/bookmarks/${encodeURIComponent(jobId)}`);
  return handleResponse<PlaybackBookmarkListResponse>(response);
}

export async function createPlaybackBookmark(
  jobId: string,
  payload: PlaybackBookmarkCreatePayload
): Promise<PlaybackBookmarkEntry> {
  const response = await apiFetch(`/api/bookmarks/${encodeURIComponent(jobId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return handleResponse<PlaybackBookmarkEntry>(response);
}

export async function deletePlaybackBookmark(
  jobId: string,
  bookmarkId: string
): Promise<PlaybackBookmarkDeleteResponse> {
  const response = await apiFetch(`/api/bookmarks/${encodeURIComponent(jobId)}/${encodeURIComponent(bookmarkId)}`, {
    method: 'DELETE'
  });
  return handleResponse<PlaybackBookmarkDeleteResponse>(response);
}

export async function fetchJobMedia(jobId: string): Promise<PipelineMediaResponse> {
  const response = await apiFetch(`/api/pipelines/jobs/${jobId}/media`);
  return handleResponse<PipelineMediaResponse>(response);
}

export async function fetchLiveJobMedia(jobId: string): Promise<PipelineMediaResponse> {
  const response = await apiFetch(`/api/pipelines/jobs/${jobId}/media/live`);
  return handleResponse<PipelineMediaResponse>(response);
}

export async function fetchSentenceImageInfo(
  jobId: string,
  sentenceNumber: number
): Promise<SentenceImageInfoResponse> {
  const encodedJobId = encodeURIComponent(jobId);
  const response = await apiFetch(
    `/api/pipelines/jobs/${encodedJobId}/media/images/sentences/${encodeURIComponent(String(sentenceNumber))}`
  );
  return handleResponse<SentenceImageInfoResponse>(response);
}

export async function fetchSentenceImageInfoBatch(
  jobId: string,
  sentenceNumbers: number[]
): Promise<SentenceImageInfoResponse[]> {
  const requested = (sentenceNumbers ?? []).filter((value) => Number.isFinite(value));
  if (!requested.length) {
    return [];
  }
  const encodedJobId = encodeURIComponent(jobId);
  const params = new URLSearchParams();
  params.set('sentence_numbers', requested.join(','));
  const response = await apiFetch(
    `/api/pipelines/jobs/${encodedJobId}/media/images/sentences/batch?${params.toString()}`
  );
  const payload = await handleResponse<SentenceImageInfoBatchResponse>(response);
  return Array.isArray(payload.items) ? payload.items : [];
}

export async function regenerateSentenceImage(
  jobId: string,
  sentenceNumber: number,
  payload: SentenceImageRegenerateRequestPayload
): Promise<SentenceImageRegenerateResponse> {
  const encodedJobId = encodeURIComponent(jobId);
  const response = await apiFetch(
    `/api/pipelines/jobs/${encodedJobId}/media/images/sentences/${encodeURIComponent(String(sentenceNumber))}/regenerate`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    }
  );
  return handleResponse<SentenceImageRegenerateResponse>(response);
}

export async function generateVideo(
  jobId: string,
  parameters: Record<string, unknown>
): Promise<VideoGenerationResponse> {
  const payload: VideoGenerationRequestPayload = {
    job_id: jobId,
    parameters
  };
  const response = await apiFetch('/api/video/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<VideoGenerationResponse>(response);
}

export async function fetchVideoStatus(jobId: string): Promise<VideoGenerationResponse | null> {
  const response = await apiFetch(`/api/video/status/${encodeURIComponent(jobId)}`);
  if (response.status === 404) {
    return null;
  }
  return handleResponse<VideoGenerationResponse>(response);
}

export async function createExport(payload: ExportRequestPayload): Promise<ExportResponse> {
  const response = await apiFetch('/api/exports', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<ExportResponse>(response);
}

function getExportManifest(): ExportPlayerManifest | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const candidate = (window as Window & { __EXPORT_DATA__?: unknown }).__EXPORT_DATA__;
  if (!candidate || typeof candidate !== 'object') {
    return null;
  }
  return candidate as ExportPlayerManifest;
}

function resolveExportJobLabel(manifest: ExportPlayerManifest): string | null {
  const metadata = manifest.book_metadata ?? null;
  if (metadata && typeof metadata === 'object') {
    const record = metadata as Record<string, unknown>;
    const keys = ['book_title', 'title', 'book_name', 'name'];
    for (const key of keys) {
      const raw = record[key];
      if (typeof raw === 'string' && raw.trim()) {
        return raw.trim();
      }
    }
  }
  const sourceLabel = manifest.source?.label;
  if (typeof sourceLabel === 'string' && sourceLabel.trim()) {
    return sourceLabel.trim();
  }
  const sourceId = manifest.source?.id;
  if (typeof sourceId === 'string' && sourceId.trim()) {
    return sourceId.trim();
  }
  return null;
}

function normaliseSearchText(value: string): string {
  return value.toLowerCase();
}

function countOccurrences(text: string, needle: string): number {
  if (!needle) {
    return 0;
  }
  let count = 0;
  let index = 0;
  while (true) {
    const match = text.indexOf(needle, index);
    if (match < 0) {
      return count;
    }
    count += 1;
    index = match + needle.length;
  }
}

function buildSnippet(text: string, matchIndex: number, matchLength: number): {
  snippet: string;
  matchStart: number;
  matchEnd: number;
  textLength: number;
} {
  const maxRadius = 80;
  const start = Math.max(0, matchIndex - maxRadius);
  const end = Math.min(text.length, matchIndex + matchLength + maxRadius);
  let snippet = text.slice(start, end);
  if (start > 0) {
    snippet = `...${snippet}`;
  }
  if (end < text.length) {
    snippet = `${snippet}...`;
  }
  const matchStart = matchIndex - start + (start > 0 ? 3 : 0);
  return {
    snippet,
    matchStart,
    matchEnd: matchStart + matchLength,
    textLength: text.length,
  };
}

function normaliseMediaCategory(value: string | null | undefined): 'text' | 'audio' | 'video' | null {
  if (!value) {
    return null;
  }
  const normalised = value.trim().toLowerCase();
  if (!normalised) {
    return null;
  }
  if (normalised === 'video') {
    return 'video';
  }
  if (normalised.startsWith('audio')) {
    return 'audio';
  }
  return 'text';
}

function groupChunkMedia(files: PipelineMediaFile[]): Record<string, PipelineMediaFile[]> {
  const grouped: Record<string, PipelineMediaFile[]> = {};
  files.forEach((file) => {
    const category = normaliseMediaCategory(file.type ?? null);
    if (!category) {
      return;
    }
    const bucket = grouped[category] ?? [];
    bucket.push(file);
    grouped[category] = bucket;
  });
  return grouped;
}

function searchExportMedia(
  manifest: ExportPlayerManifest,
  query: string,
  limit: number,
  requestedJobId: string | null | undefined,
): MediaSearchResponse {
  const trimmed = query.trim();
  if (!trimmed) {
    return { query: '', limit, count: 0, results: [] };
  }
  const manifestJobId =
    typeof manifest.source?.id === 'string' && manifest.source.id.trim() ? manifest.source.id.trim() : null;
  if (requestedJobId && manifestJobId && requestedJobId !== manifestJobId) {
    return { query: trimmed, limit, count: 0, results: [] };
  }
  const resolvedJobId = (requestedJobId ?? manifestJobId ?? 'export').trim();
  const jobLabel = resolveExportJobLabel(manifest);
  const chunks = Array.isArray(manifest.chunks) ? manifest.chunks : [];
  const chunkTotal = chunks.length;
  const needle = normaliseSearchText(trimmed);

  const results: MediaSearchResult[] = [];

  for (let chunkIndex = 0; chunkIndex < chunks.length; chunkIndex += 1) {
    if (results.length >= limit) {
      break;
    }
    const chunk = chunks[chunkIndex];
    const sentences = Array.isArray(chunk.sentences) ? chunk.sentences : [];
    if (sentences.length === 0) {
      continue;
    }
    const media = groupChunkMedia(chunk.files ?? []);
    if (!media.text || media.text.length === 0) {
      media.text = [
        {
          name: 'Text',
          url: null,
          source: 'completed',
          type: 'text',
          relative_path: chunk.metadata_path ?? null,
          path: chunk.metadata_path ?? null,
        },
      ];
    }
    const chunkId = typeof chunk.chunk_id === 'string' && chunk.chunk_id.trim() ? chunk.chunk_id.trim() : null;
    const rangeFragment =
      typeof chunk.range_fragment === 'string' && chunk.range_fragment.trim() ? chunk.range_fragment.trim() : null;
    const baseId =
      chunkId ??
      rangeFragment ??
      (typeof chunk.metadata_path === 'string' && chunk.metadata_path.trim()
        ? chunk.metadata_path.trim()
        : null) ??
      (typeof chunk.metadata_url === 'string' && chunk.metadata_url.trim() ? chunk.metadata_url.trim() : null);
    const startSentence =
      typeof chunk.start_sentence === 'number' && Number.isFinite(chunk.start_sentence)
        ? Math.trunc(chunk.start_sentence)
        : null;
    const endSentence =
      typeof chunk.end_sentence === 'number' && Number.isFinite(chunk.end_sentence)
        ? Math.trunc(chunk.end_sentence)
        : null;

    for (let sentenceIndex = 0; sentenceIndex < sentences.length; sentenceIndex += 1) {
      if (results.length >= limit) {
        break;
      }
      const sentence = sentences[sentenceIndex];
      if (!sentence) {
        continue;
      }
      const parts = [
        typeof sentence.original?.text === 'string' ? sentence.original.text : null,
        typeof sentence.translation?.text === 'string' ? sentence.translation.text : null,
        typeof sentence.transliteration?.text === 'string' ? sentence.transliteration.text : null,
      ].filter((value): value is string => Boolean(value && value.trim()));
      if (parts.length === 0) {
        continue;
      }
      const combined = parts.join(' ');
      const haystack = normaliseSearchText(combined);
      const matchIndex = haystack.indexOf(needle);
      if (matchIndex < 0) {
        continue;
      }

      const sentenceNumber =
        typeof sentence.sentence_number === 'number' && Number.isFinite(sentence.sentence_number)
          ? Math.trunc(sentence.sentence_number)
          : startSentence !== null
            ? startSentence + sentenceIndex
            : null;
      const offsetRatio =
        sentenceNumber !== null && startSentence !== null && endSentence !== null && endSentence > startSentence
          ? Math.min(Math.max((sentenceNumber - startSentence) / (endSentence - startSentence), 0), 1)
          : null;

      const occurrenceCount = countOccurrences(haystack, needle);
      const { snippet, matchStart, matchEnd, textLength } = buildSnippet(combined, matchIndex, needle.length);

      results.push({
        job_id: resolvedJobId,
        job_label: jobLabel,
        base_id: baseId,
        chunk_id: chunkId,
        chunk_index: chunkIndex,
        chunk_total: chunkTotal,
        range_fragment: rangeFragment,
        start_sentence: startSentence,
        end_sentence: endSentence,
        snippet,
        occurrence_count: Math.max(1, occurrenceCount),
        match_start: matchStart,
        match_end: matchEnd,
        text_length: textLength,
        offset_ratio: offsetRatio,
        approximate_time_seconds: null,
        media,
        source: 'pipeline',
      });
    }
  }

  return {
    query: trimmed,
    limit,
    count: results.length,
    results,
  };
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
  const exportManifest = getExportManifest();
  if (exportManifest) {
    return searchExportMedia(exportManifest, trimmed, resolvedLimit, jobId);
  }
  const params = new URLSearchParams();
  params.set('query', trimmed);
  params.set('limit', String(resolvedLimit));
  params.set('job_id', jobId);
  const response = await apiFetch(`/api/pipelines/search?${params.toString()}`);
  return handleResponse<MediaSearchResponse>(response);
}

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

export function resolveJobCoverUrl(jobId: string): string | null {
  const trimmed = (jobId ?? '').trim();
  if (!trimmed) {
    return null;
  }
  const encoded = encodeURIComponent(trimmed);
  return withBase(`/api/pipelines/${encoded}/cover`);
}

function shouldAppendAccessTokenToStorage(url: string): boolean {
  const token = getAuthToken();
  if (!token) {
    return false;
  }
  const trimmed = url.trim();
  if (!trimmed) {
    return false;
  }
  if (trimmed.startsWith('data:') || trimmed.startsWith('blob:')) {
    return false;
  }
  if (!/^[a-z]+:\/\//i.test(trimmed)) {
    return true;
  }
  try {
    const target = new URL(trimmed);
    const origins = new Set<string>();

    const addOrigin = (value: string | null | undefined) => {
      if (!value) {
        return;
      }
      try {
        origins.add(
          new URL(value, typeof window !== 'undefined' ? window.location.origin : undefined).origin
        );
      } catch (error) {
        // Ignore invalid base URLs.
      }
    };

    addOrigin(API_BASE_URL);
    addOrigin(STORAGE_BASE_URL);
    if (typeof window !== 'undefined') {
      origins.add(window.location.origin);
    }
    return origins.has(target.origin);
  } catch (error) {
    return false;
  }
}

function maybeAppendAccessTokenToStorage(url: string): string {
  if (!shouldAppendAccessTokenToStorage(url)) {
    return url;
  }
  return appendAccessToken(url);
}

export function appendAccessTokenToStorageUrl(url: string): string {
  return maybeAppendAccessTokenToStorage(url);
}

export function buildStorageUrl(path: string, jobId?: string | null): string {
  const trimmedPath = (path ?? '').trim();
  if (!trimmedPath) {
    const resolved = resolveStoragePath(null, null, STORAGE_BASE_URL, API_BASE_URL);
    return maybeAppendAccessTokenToStorage(resolved);
  }

  const normalisedPath = trimmedPath.replace(/^\/+/, '');
  if (!normalisedPath) {
    const resolved = resolveStoragePath(null, null, STORAGE_BASE_URL, API_BASE_URL);
    return maybeAppendAccessTokenToStorage(resolved);
  }

  const normalisedJobId = (jobId ?? '').trim().replace(/^\/+/, '').replace(/\/+$/, '');
  const segments = normalisedPath.split('/').filter((segment) => segment.length > 0);

  if (normalisedJobId) {
    const jobIndex = segments.findIndex((segment) => segment === normalisedJobId);
    if (jobIndex >= 0) {
      const fileSegment = segments.slice(jobIndex + 1).join('/');
      const resolved = resolveStoragePath(
        normalisedJobId,
        fileSegment,
        STORAGE_BASE_URL,
        API_BASE_URL
      );
      return maybeAppendAccessTokenToStorage(resolved);
    }

    if (
      segments.length >= 2 &&
      segments[0].toLowerCase() === 'jobs' &&
      segments[1] === normalisedJobId
    ) {
      const fileSegment = segments.slice(2).join('/');
      const resolved = resolveStoragePath(
        normalisedJobId,
        fileSegment,
        STORAGE_BASE_URL,
        API_BASE_URL
      );
      return maybeAppendAccessTokenToStorage(resolved);
    }

    const firstSegment = segments[0]?.toLowerCase() ?? '';
    const requiresJobPrefix = firstSegment !== 'covers' && firstSegment !== 'storage' && firstSegment !== 'jobs';
    if (requiresJobPrefix) {
      const resolved = resolveStoragePath(
        normalisedJobId,
        normalisedPath,
        STORAGE_BASE_URL,
        API_BASE_URL
      );
      return maybeAppendAccessTokenToStorage(resolved);
    }
  }

  const [jobSegment, ...rest] = segments;
  const fileSegment = rest.length > 0 ? rest.join('/') : '';

  const resolved = resolveStoragePath(
    jobSegment || null,
    fileSegment,
    STORAGE_BASE_URL,
    API_BASE_URL
  );
  return maybeAppendAccessTokenToStorage(resolved);
}

export function resolveSubtitleDownloadUrl(
  jobId: string,
  relativePath: string | null | undefined
): string | null {
  if (!relativePath) {
    return null;
  }
  const trimmed = relativePath.trim().replace(/^\/+/, '');
  if (!trimmed) {
    return null;
  }
  const composedPath = `${jobId}/${trimmed}`;
  return buildStorageUrl(composedPath, jobId);
}

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

export async function updateLibraryAccess(
  jobId: string,
  payload: AccessPolicyUpdatePayload
): Promise<LibraryItem> {
  const response = await apiFetch(`/api/library/items/${encodeURIComponent(jobId)}/access`, {
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

export async function fetchLibraryMedia(
  jobId: string,
  options?: { summary?: boolean },
): Promise<PipelineMediaResponse> {
  const query = new URLSearchParams();
  if (options?.summary) {
    query.set('summary', '1');
  }
  const suffix = query.toString();
  const url = suffix
    ? `/api/library/media/${encodeURIComponent(jobId)}?${suffix}`
    : `/api/library/media/${encodeURIComponent(jobId)}`;
  const response = await apiFetch(url);
  return handleResponse<PipelineMediaResponse>(response);
}

function normaliseApiUrl(candidate: string): string {
  if (/^https?:\/\//i.test(candidate)) {
    return candidate;
  }
  return withBase(candidate);
}
