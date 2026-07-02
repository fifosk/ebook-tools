/**
 * Resume position API endpoints.
 */

import type {
  ResumePositionDeleteResponse,
  ResumePositionEntry,
  ResumePositionListResponse,
  ResumePositionPayload,
  ResumePositionResponse,
} from '../dtos';
import { apiFetch, handleResponse } from './base';
import {
  replaceRuntimePathParameter,
  WEB_PLAYBACK_STATE_RUNTIME_CONTRACT,
} from './runtimeContract';

function normalizeResumeJobIds(jobIds: string[]): string[] {
  return Array.from(new Set(jobIds.map((jobId) => jobId.trim()).filter(Boolean))).sort();
}

export async function fetchResumePositions(jobIds?: string[]): Promise<ResumePositionListResponse> {
  if (jobIds && jobIds.length === 0) {
    return { entries: [] };
  }
  const normalizedJobIds = jobIds ? normalizeResumeJobIds(jobIds) : [];
  if (jobIds && normalizedJobIds.length === 0) {
    return { entries: [] };
  }
  const params = new URLSearchParams();
  normalizedJobIds.forEach((jobId) => {
    params.append(WEB_PLAYBACK_STATE_RUNTIME_CONTRACT.resumeFilterQuery, jobId);
  });
  const query = params.toString();
  const response = await apiFetch(
    `${WEB_PLAYBACK_STATE_RUNTIME_CONTRACT.resumeListPath}${query ? `?${query}` : ''}`
  );
  const payload = await handleResponse<unknown>(response);
  assertResumePositionListResponse(payload);
  return payload;
}

export async function fetchResumePosition(jobId: string): Promise<ResumePositionResponse> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_PLAYBACK_STATE_RUNTIME_CONTRACT.resumePathTemplate,
      'job_id',
      jobId
    )
  );
  const payload = await handleResponse<unknown>(response);
  assertResumePositionResponse(payload);
  return payload;
}

export async function saveResumePosition(
  jobId: string,
  payload: ResumePositionPayload,
): Promise<ResumePositionResponse> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_PLAYBACK_STATE_RUNTIME_CONTRACT.resumePathTemplate,
      'job_id',
      jobId
    ),
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  );
  const responsePayload = await handleResponse<unknown>(response);
  assertResumePositionResponse(responsePayload);
  return responsePayload;
}

export async function clearResumePosition(jobId: string): Promise<ResumePositionDeleteResponse> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_PLAYBACK_STATE_RUNTIME_CONTRACT.resumePathTemplate,
      'job_id',
      jobId
    ),
    {
      method: 'DELETE',
    }
  );
  const payload = await handleResponse<unknown>(response);
  assertResumePositionDeleteResponse(payload);
  return payload;
}

function assertResumePositionListResponse(
  payload: unknown
): asserts payload is ResumePositionListResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid resume position list response.');
  }
  if (!Array.isArray(payload.entries)) {
    throw new Error('Invalid resume position list response: missing entries.');
  }
  payload.entries.forEach(assertResumePositionEntry);
}

function assertResumePositionResponse(payload: unknown): asserts payload is ResumePositionResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid resume position response.');
  }
  assertResumeStringField(payload, 'job_id', 'resume position');
  if (payload.entry !== null) {
    assertResumePositionEntry(payload.entry);
  }
}

function assertResumePositionEntry(payload: unknown): asserts payload is ResumePositionEntry {
  if (!isRecord(payload)) {
    throw new Error('Invalid resume position response: missing entry.');
  }
  assertResumeStringField(payload, 'job_id', 'resume position');
  assertResumeKind(payload.kind);
  assertResumeNumberField(payload, 'updated_at', 'resume position');
}

function assertResumePositionDeleteResponse(
  payload: unknown
): asserts payload is ResumePositionDeleteResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid resume position delete response.');
  }
  assertResumeBooleanField(payload, 'deleted', 'resume position delete');
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function assertResumeStringField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (typeof record[key] !== 'string') {
    throw new Error(`Invalid ${responseKind} response: missing ${key}.`);
  }
}

function assertResumeNumberField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (typeof record[key] !== 'number' || !Number.isFinite(record[key])) {
    throw new Error(`Invalid ${responseKind} response: missing ${key}.`);
  }
}

function assertResumeBooleanField(
  record: Record<string, unknown>,
  key: string,
  responseKind: string
): void {
  if (typeof record[key] !== 'boolean') {
    throw new Error(`Invalid ${responseKind} response: missing ${key}.`);
  }
}

function assertResumeKind(value: unknown): void {
  if (value !== 'time' && value !== 'sentence') {
    throw new Error('Invalid resume position response: missing kind.');
  }
}
