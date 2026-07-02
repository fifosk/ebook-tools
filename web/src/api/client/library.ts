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
  LibraryMetadataRefreshRequest,
  LibraryMetadataRefreshResponse,
  LibraryMetadataUpdatePayload,
  LibraryMoveResponse,
  LibraryReindexResponse,
  LibrarySearchResponse,
  LibraryViewMode,
  PipelineMediaResponse
} from '../dtos';
import { apiFetch, handleResponse, withBase, appendAccessToken } from './base';
import {
  replaceRuntimePathParameter,
  WEB_LIBRARY_ACTIONS_RUNTIME_CONTRACT,
  WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT,
} from './runtimeContract';

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
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_LIBRARY_ACTIONS_RUNTIME_CONTRACT.movePathTemplate,
      'job_id',
      jobId
    ),
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: statusOverride ? JSON.stringify({ statusOverride }) : undefined
    }
  );
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
  const path = queryString
    ? `${WEB_LIBRARY_ACTIONS_RUNTIME_CONTRACT.itemsPath}?${queryString}`
    : WEB_LIBRARY_ACTIONS_RUNTIME_CONTRACT.itemsPath;
  const response = await apiFetch(path);
  const payload = await handleResponse<unknown>(response);
  assertLibrarySearchResponse(payload);
  return payload;
}

function assertLibrarySearchResponse(payload: unknown): asserts payload is LibrarySearchResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid library search response.');
  }
  assertNumberField(payload, 'total', 'library search');
  assertNumberField(payload, 'page', 'library search');
  assertNumberField(payload, 'limit', 'library search');
  assertLibraryViewMode(payload.view);
  if (!Array.isArray(payload.items)) {
    throw new Error('Invalid library search response: missing items.');
  }
  payload.items.forEach(assertLibraryItem);
  if (
    payload.groups !== undefined &&
    payload.groups !== null &&
    !Array.isArray(payload.groups)
  ) {
    throw new Error('Invalid library search response: invalid groups.');
  }
}

function assertLibraryItem(payload: unknown): void {
  if (!isRecord(payload)) {
    throw new Error('Invalid library search response: missing item entry.');
  }
  assertStringField(payload, 'jobId', 'library item');
  assertStringField(payload, 'author', 'library item');
  assertStringField(payload, 'bookTitle', 'library item');
  assertLibraryItemType(payload.itemType);
  assertStringField(payload, 'language', 'library item');
  assertLibraryStatus(payload.status);
  assertBooleanField(payload, 'mediaCompleted', 'library item');
  assertStringField(payload, 'createdAt', 'library item');
  assertStringField(payload, 'updatedAt', 'library item');
  assertStringField(payload, 'libraryPath', 'library item');
  if (!isRecord(payload.metadata)) {
    throw new Error('Invalid library item response: missing metadata.');
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function assertStringField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (typeof record[key] !== 'string') {
    throw new Error(`Invalid ${responseKind} response: missing ${key}.`);
  }
}

function assertNumberField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (typeof record[key] !== 'number' || !Number.isFinite(record[key])) {
    throw new Error(`Invalid ${responseKind} response: missing ${key}.`);
  }
}

function assertBooleanField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (typeof record[key] !== 'boolean') {
    throw new Error(`Invalid ${responseKind} response: missing ${key}.`);
  }
}

function assertLibraryViewMode(value: unknown): void {
  if (
    value !== 'flat' &&
    value !== 'by_author' &&
    value !== 'by_genre' &&
    value !== 'by_language'
  ) {
    throw new Error('Invalid library search response: missing view.');
  }
}

function assertLibraryItemType(value: unknown): void {
  if (value !== 'book' && value !== 'video' && value !== 'narrated_subtitle') {
    throw new Error('Invalid library item response: missing itemType.');
  }
}

function assertLibraryStatus(value: unknown): void {
  if (value !== 'finished' && value !== 'paused') {
    throw new Error('Invalid library item response: missing status.');
  }
}

export async function removeLibraryMedia(jobId: string): Promise<LibraryMediaRemovalResponse> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_LIBRARY_ACTIONS_RUNTIME_CONTRACT.removeMediaPathTemplate,
      'job_id',
      jobId
    ),
    {
      method: 'POST'
    }
  );
  return handleResponse<LibraryMediaRemovalResponse>(response);
}

export async function removeLibraryEntry(jobId: string): Promise<void> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_LIBRARY_ACTIONS_RUNTIME_CONTRACT.removePathTemplate,
      'job_id',
      jobId
    ),
    {
      method: 'DELETE'
    }
  );
  await handleResponse<unknown>(response);
}

export async function reindexLibrary(): Promise<LibraryReindexResponse> {
  const response = await apiFetch(WEB_LIBRARY_ACTIONS_RUNTIME_CONTRACT.reindexPath, {
    method: 'POST'
  });
  return handleResponse<LibraryReindexResponse>(response);
}

export async function refreshLibraryMetadata(
  jobId: string,
  payload: LibraryMetadataRefreshRequest = {}
): Promise<LibraryItem> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_LIBRARY_ACTIONS_RUNTIME_CONTRACT.metadataRefreshPathTemplate,
      'job_id',
      jobId
    ),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enrichFromExternal: Boolean(payload.enrichFromExternal) })
    }
  );
  const result = await handleResponse<LibraryMetadataRefreshResponse>(response);
  return result.item;
}

export async function enrichLibraryMetadata(
  jobId: string,
  payload: LibraryMetadataEnrichRequest = {}
): Promise<LibraryMetadataEnrichResponse> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_LIBRARY_ACTIONS_RUNTIME_CONTRACT.metadataEnrichPathTemplate,
      'job_id',
      jobId
    ),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force: Boolean(payload.force) })
    }
  );
  return handleResponse<LibraryMetadataEnrichResponse>(response);
}

export async function updateLibraryMetadata(
  jobId: string,
  payload: LibraryMetadataUpdatePayload
): Promise<LibraryItem> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_LIBRARY_ACTIONS_RUNTIME_CONTRACT.itemMetadataPathTemplate,
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
  return handleResponse<LibraryItem>(response);
}

export async function updateLibraryAccess(
  jobId: string,
  payload: AccessPolicyUpdatePayload
): Promise<LibraryItem> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_LIBRARY_ACTIONS_RUNTIME_CONTRACT.accessPathTemplate,
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
  return handleResponse<LibraryItem>(response);
}

export async function uploadLibrarySource(jobId: string, file: File): Promise<LibraryItem> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_LIBRARY_ACTIONS_RUNTIME_CONTRACT.sourceUploadPathTemplate,
      'job_id',
      jobId
    ),
    {
      method: 'POST',
      body: formData
    }
  );
  return handleResponse<LibraryItem>(response);
}

export async function applyLibraryIsbn(jobId: string, isbn: string): Promise<LibraryItem> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_LIBRARY_ACTIONS_RUNTIME_CONTRACT.isbnApplyPathTemplate,
      'job_id',
      jobId
    ),
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ isbn })
    }
  );
  return handleResponse<LibraryItem>(response);
}

export async function lookupLibraryIsbnMetadata(isbn: string): Promise<LibraryIsbnLookupResponse> {
  const response = await apiFetch(
    `${WEB_LIBRARY_ACTIONS_RUNTIME_CONTRACT.isbnLookupPath}?isbn=${encodeURIComponent(isbn)}`
  );
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
  const path = WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.libraryMediaFilePathTemplate
    .replace('{job_id}', encodedJobId)
    .replace('{file_path}', encodedPath);
  const url = withBase(path);
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
  const path = replaceRuntimePathParameter(
    WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.libraryMediaPathTemplate,
    'job_id',
    jobId
  );
  const url = suffix
    ? `${path}?${suffix}`
    : path;
  const response = await apiFetch(url);
  return handleResponse<PipelineMediaResponse>(response);
}
