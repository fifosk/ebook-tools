import type {
  CreationTemplateDeleteResponse,
  CreationTemplateEntry,
  CreationTemplateListResponse,
  CreationTemplatePayload
} from '../dtos';
import { apiFetch, handleResponse } from './base';

const CREATION_TEMPLATES_PATH = '/api/creation/templates';

export async function fetchCreationTemplates(mode?: string): Promise<CreationTemplateEntry[]> {
  const query = mode?.trim() ? `?mode=${encodeURIComponent(mode.trim())}` : '';
  const response = await apiFetch(`${CREATION_TEMPLATES_PATH}${query}`);
  const payload = await handleResponse<CreationTemplateListResponse>(response);
  return payload.templates;
}

export async function fetchCreationTemplate(
  templateId: string
): Promise<CreationTemplateEntry> {
  const response = await apiFetch(
    `${CREATION_TEMPLATES_PATH}/${encodeURIComponent(templateId)}`
  );
  return handleResponse<CreationTemplateEntry>(response);
}

export async function saveCreationTemplate(
  payload: CreationTemplatePayload
): Promise<CreationTemplateEntry> {
  const response = await apiFetch(CREATION_TEMPLATES_PATH, {
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
    `${CREATION_TEMPLATES_PATH}/${encodeURIComponent(templateId)}`,
    {
      method: 'DELETE'
    }
  );
  return handleResponse<CreationTemplateDeleteResponse>(response);
}
