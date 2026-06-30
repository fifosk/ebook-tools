/**
 * Authentication API endpoints.
 */

import type {
  LoginRequestPayload,
  OAuthLoginRequestPayload,
  PasswordChangeRequestPayload,
  RegistrationRequestPayload,
  RegistrationResponse,
  SessionStatusResponse
} from '../dtos';
import { apiFetch, handleResponse } from './base';
import { WEB_AUTH_RUNTIME_CONTRACT } from './runtimeContract';

export async function login(payload: LoginRequestPayload): Promise<SessionStatusResponse> {
  const response = await apiFetch(
    WEB_AUTH_RUNTIME_CONTRACT.loginPath,
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
    WEB_AUTH_RUNTIME_CONTRACT.oauthPath,
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
  const response = await apiFetch(WEB_AUTH_RUNTIME_CONTRACT.logoutPath, {
    method: 'POST'
  });
  await handleResponse<unknown>(response);
}

export async function fetchSessionStatus(): Promise<SessionStatusResponse> {
  const response = await apiFetch(WEB_AUTH_RUNTIME_CONTRACT.sessionPath);
  return handleResponse<SessionStatusResponse>(response);
}

export async function changePassword(payload: PasswordChangeRequestPayload): Promise<void> {
  const response = await apiFetch(WEB_AUTH_RUNTIME_CONTRACT.passwordPath, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  await handleResponse<unknown>(response);
}

export async function register(payload: RegistrationRequestPayload): Promise<RegistrationResponse> {
  const response = await apiFetch(
    WEB_AUTH_RUNTIME_CONTRACT.registerPath,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    },
    { skipAuth: true }
  );
  return handleResponse<RegistrationResponse>(response);
}
