/**
 * Admin and user management API endpoints.
 */

import type {
  ManagedUser,
  ReadingBedDeleteResponse,
  ReadingBedEntry,
  ReadingBedListResponse,
  ReadingBedUpdateRequestPayload,
  UserAccountResponse,
  UserCreateRequestPayload,
  UserListResponse,
  UserPasswordResetRequestPayload,
  UserUpdateRequestPayload
} from '../dtos';
import { apiFetch, handleResponse } from './base';

// User management
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

// Reading beds (admin endpoints)
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
