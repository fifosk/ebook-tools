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
import {
  replaceRuntimePathParameter,
  WEB_PLAYBACK_STATE_RUNTIME_CONTRACT,
  WEB_READING_BED_ADMIN_RUNTIME_CONTRACT
} from './runtimeContract';

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
  const response = await apiFetch(WEB_PLAYBACK_STATE_RUNTIME_CONTRACT.readingBedsPath, { signal });
  const payload = await handleResponse<unknown>(response);
  assertReadingBedListResponse(payload);
  return payload;
}

export async function uploadReadingBed(file: File, label?: string): Promise<ReadingBedEntry> {
  const form = new FormData();
  form.append('file', file);
  if (label && label.trim()) {
    form.append('label', label.trim());
  }
  const response = await apiFetch(WEB_READING_BED_ADMIN_RUNTIME_CONTRACT.collectionPath, {
    method: 'POST',
    body: form
  });
  const payload = await handleResponse<unknown>(response);
  assertReadingBedEntry(payload, 'reading bed upload');
  return payload;
}

export async function updateReadingBed(bedId: string, payload: ReadingBedUpdateRequestPayload): Promise<ReadingBedEntry> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_READING_BED_ADMIN_RUNTIME_CONTRACT.itemPathTemplate,
      'bed_id',
      bedId
    ),
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    }
  );
  const responsePayload = await handleResponse<unknown>(response);
  assertReadingBedEntry(responsePayload, 'reading bed update');
  return responsePayload;
}

export async function deleteReadingBed(bedId: string): Promise<ReadingBedDeleteResponse> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_READING_BED_ADMIN_RUNTIME_CONTRACT.itemPathTemplate,
      'bed_id',
      bedId
    ),
    {
      method: 'DELETE'
    }
  );
  const payload = await handleResponse<unknown>(response);
  assertReadingBedDeleteResponse(payload);
  return payload;
}

function assertReadingBedListResponse(payload: unknown): asserts payload is ReadingBedListResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid reading bed list response.');
  }
  assertNullableStringField(payload, 'default_id', 'reading bed list');
  if (!Array.isArray(payload.beds)) {
    throw new Error('Invalid reading bed list response: missing beds.');
  }
  payload.beds.forEach((bed) => {
    assertReadingBedEntry(bed, 'reading bed list');
  });
}

function assertReadingBedEntry(
  payload: unknown,
  responseKind: string
): asserts payload is ReadingBedEntry {
  if (!isRecord(payload)) {
    throw new Error(`Invalid ${responseKind} response: missing bed entry.`);
  }
  assertStringField(payload, 'id', responseKind);
  assertStringField(payload, 'label', responseKind);
  assertStringField(payload, 'url', responseKind);
  if (payload.kind !== 'bundled' && payload.kind !== 'uploaded') {
    throw new Error(`Invalid ${responseKind} response: missing kind.`);
  }
  assertBooleanField(payload, 'is_default', responseKind);
  if (
    payload.content_type !== undefined &&
    payload.content_type !== null &&
    typeof payload.content_type !== 'string'
  ) {
    throw new Error(`Invalid ${responseKind} response: invalid content_type.`);
  }
}

function assertReadingBedDeleteResponse(
  payload: unknown
): asserts payload is ReadingBedDeleteResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid reading bed delete response.');
  }
  assertBooleanField(payload, 'deleted', 'reading bed delete');
  assertNullableStringField(payload, 'default_id', 'reading bed delete');
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

function assertNullableStringField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (record[key] !== null && typeof record[key] !== 'string') {
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
