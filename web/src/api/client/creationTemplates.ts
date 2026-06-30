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
  const payload = await handleResponse<CreationTemplateListResponse>(response);
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
  return handleResponse<CreationTemplateEntry>(response);
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
  return handleResponse<CreationTemplateEntry>(response);
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
  return handleResponse<CreationTemplateDeleteResponse>(response);
}
