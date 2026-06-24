import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  deleteCreationTemplate,
  fetchCreationTemplate,
  fetchCreationTemplates,
  saveCreationTemplate
} from '../creationTemplates';
import type { CreationTemplateEntry } from '../../dtos';

const templateEntry: CreationTemplateEntry = {
  id: 'draft-template',
  name: 'Draft template',
  mode: 'narrate_ebook',
  created_at: 1,
  updated_at: 2,
  payload: {
    form_state: {
      input_file: '/nas/book.epub'
    }
  }
};

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' }
  });
}

describe('creation template API client', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('fetches template lists with an encoded mode filter', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>().mockResolvedValue(
      jsonResponse({ templates: [templateEntry] })
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const result = await fetchCreationTemplates(' narrate ebook ');

    expect(result).toEqual([templateEntry]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0][0])).toContain(
      '/api/creation/templates?mode=narrate%20ebook'
    );
  });

  it('fetches a single template by encoded id for Web handoff loads', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>().mockResolvedValue(
      jsonResponse(templateEntry)
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const result = await fetchCreationTemplate('draft/template?secret');

    expect(result).toEqual(templateEntry);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0][0])).toContain(
      '/api/creation/templates/draft%2Ftemplate%3Fsecret'
    );
  });

  it('saves and deletes templates through the shared template path', async () => {
    const fetchMock = vi
      .fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse(templateEntry))
      .mockResolvedValueOnce(jsonResponse({ deleted: true, template_id: 'draft-template' }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const saved = await saveCreationTemplate({
      id: 'draft-template',
      name: 'Draft template',
      mode: 'narrate_ebook',
      payload: templateEntry.payload
    });
    const deleted = await deleteCreationTemplate('draft-template');

    expect(saved).toEqual(templateEntry);
    expect(deleted).toEqual({ deleted: true, template_id: 'draft-template' });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/creation/templates');
    expect(fetchMock.mock.calls[0][1]?.method).toBe('POST');
    expect(String(fetchMock.mock.calls[1][0])).toContain(
      '/api/creation/templates/draft-template'
    );
    expect(fetchMock.mock.calls[1][1]?.method).toBe('DELETE');
  });
});
