/**
 * Library management API endpoints.
 */

import type {
  AccessPolicyUpdatePayload,
  LibraryIsbnLookupResponse,
  LibraryItem,
  LibraryMediaRemovalResponse,
  LibraryMetadataEnrichRequest,
  LibraryMetadataEnrichResponse,
  LibraryMetadataUpdatePayload,
  LibraryMoveResponse,
  LibraryReindexResponse,
  LibrarySearchResponse,
  LibraryViewMode,
  PipelineMediaResponse
} from '../dtos';
import { apiFetch, handleResponse, withBase, appendAccessToken } from './base';

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

export async function enrichLibraryMetadata(
  jobId: string,
  payload: LibraryMetadataEnrichRequest = {}
): Promise<LibraryMetadataEnrichResponse> {
  const response = await apiFetch(`/api/library/items/${encodeURIComponent(jobId)}/enrich`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force: Boolean(payload.force) })
  });
  return handleResponse<LibraryMetadataEnrichResponse>(response);
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
