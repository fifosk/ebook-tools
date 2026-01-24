/**
 * Core API utilities: fetch wrapper, authentication, and URL building.
 */

import type { SessionStatusResponse } from '../dtos';
import { resolveStorageBaseUrl } from '../../utils/storageResolver';

// API base URL resolution
export const API_BASE_URL = resolveApiBaseUrl();
export const STORAGE_BASE_URL = resolveStorageBaseUrl(API_BASE_URL);

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

// Authentication state
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

// Fetch utilities
export type FetchOptions = {
  skipAuth?: boolean;
  suppressUnauthorized?: boolean;
};

function buildHeaders(initHeaders?: HeadersInit): Headers {
  const headers = new Headers(initHeaders ?? {});
  return headers;
}

export async function apiFetch(
  path: string,
  init: RequestInit = {},
  { skipAuth = false, suppressUnauthorized = false }: FetchOptions = {}
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

  if (!skipAuth && !suppressUnauthorized && (response.status === 401 || response.status === 403)) {
    unauthorizedHandler?.();
  }

  return response;
}

export async function handleResponse<T>(response: Response): Promise<T> {
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

// URL utilities
export function normaliseApiUrl(candidate: string): string {
  if (/^https?:\/\//i.test(candidate)) {
    return candidate;
  }
  return withBase(candidate);
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

export function maybeAppendAccessTokenToStorage(url: string): string {
  if (!shouldAppendAccessTokenToStorage(url)) {
    return url;
  }
  return appendAccessToken(url);
}

export function appendAccessTokenToStorageUrl(url: string): string {
  return maybeAppendAccessTokenToStorage(url);
}
