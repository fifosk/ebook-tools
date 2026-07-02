import type {
  CreationTemplateDeleteResponse,
  CreationTemplateEntry,
  CreationTemplateListResponse,
  CreationTemplatePayload
} from '../dtos';
import { apiFetch, handleResponse } from './base';
import {
  replaceRuntimePathParameter,
  WEB_CREATE_RUNTIME_CONTRACT,
} from './runtimeContract';

export async function fetchCreationTemplates(mode?: string): Promise<CreationTemplateEntry[]> {
  const query = mode?.trim() ? `?mode=${encodeURIComponent(mode.trim())}` : '';
  const response = await apiFetch(`${WEB_CREATE_RUNTIME_CONTRACT.templateListPath}${query}`);
  const payload = await handleResponse<unknown>(response);
  assertCreationTemplateListResponse(payload);
  return payload.templates;
}

export async function fetchCreationTemplate(
  templateId: string
): Promise<CreationTemplateEntry> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_CREATE_RUNTIME_CONTRACT.templatePathTemplate,
      'template_id',
      templateId
    )
  );
  const payload = await handleResponse<unknown>(response);
  assertCreationTemplateEntry(payload);
  return payload;
}

export async function saveCreationTemplate(
  payload: CreationTemplatePayload
): Promise<CreationTemplateEntry> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.templateListPath, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  const responsePayload = await handleResponse<unknown>(response);
  assertCreationTemplateEntry(responsePayload);
  return responsePayload;
}

export async function deleteCreationTemplate(
  templateId: string
): Promise<CreationTemplateDeleteResponse> {
  const response = await apiFetch(
    replaceRuntimePathParameter(
      WEB_CREATE_RUNTIME_CONTRACT.templatePathTemplate,
      'template_id',
      templateId
    ),
    {
      method: 'DELETE'
    }
  );
  const payload = await handleResponse<unknown>(response);
  assertCreationTemplateDeleteResponse(payload);
  return payload;
}

function assertCreationTemplateListResponse(
  payload: unknown
): asserts payload is CreationTemplateListResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid creation template list response.');
  }
  if (!Array.isArray(payload.templates)) {
    throw new Error('Invalid creation template list response: missing templates.');
  }
  for (const template of payload.templates) {
    assertCreationTemplateEntry(template);
  }
}

function assertCreationTemplateEntry(payload: unknown): asserts payload is CreationTemplateEntry {
  if (!isRecord(payload)) {
    throw new Error('Invalid creation template response.');
  }
  assertTemplateStringField(payload, 'id');
  assertTemplateStringField(payload, 'name');
  assertTemplateMode(payload.mode);
  assertTemplateNumberField(payload, 'created_at');
  assertTemplateNumberField(payload, 'updated_at');
  if (!isRecord(payload.payload)) {
    throw new Error('Invalid creation template response: missing payload.');
  }
}

function assertCreationTemplateDeleteResponse(
  payload: unknown
): asserts payload is CreationTemplateDeleteResponse {
  if (!isRecord(payload)) {
    throw new Error('Invalid creation template delete response.');
  }
  if (typeof payload.deleted !== 'boolean') {
    throw new Error('Invalid creation template delete response: missing deleted.');
  }
  if (typeof payload.template_id !== 'string') {
    throw new Error('Invalid creation template delete response: missing template_id.');
  }
}

function assertTemplateStringField(record: Record<string, unknown>, key: string): void {
  if (typeof record[key] !== 'string') {
    throw new Error(`Invalid creation template response: missing ${key}.`);
  }
}

function assertTemplateNumberField(record: Record<string, unknown>, key: string): void {
  if (typeof record[key] !== 'number') {
    throw new Error(`Invalid creation template response: missing ${key}.`);
  }
}

function assertTemplateMode(value: unknown): void {
  const modes = new Set(['generated_book', 'narrate_ebook', 'subtitle_job', 'youtube_dub']);
  if (typeof value !== 'string' || !modes.has(value)) {
    throw new Error('Invalid creation template response: missing mode.');
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
