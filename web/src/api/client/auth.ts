/**
 * Authentication API endpoints.
 */

import type {
  LoginRequestPayload,
  OAuthLoginRequestPayload,
  PasswordChangeRequestPayload,
  SessionStatusResponse
} from '../dtos';
import { apiFetch, handleResponse } from './base';

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

export async function loginWithOAuth(payload: OAuthLoginRequestPayload): Promise<SessionStatusResponse> {
  const response = await apiFetch(
    '/api/auth/oauth',
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
