import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  createExport,
  fetchJobMedia,
  fetchLiveJobMedia,
  fetchVoiceInventory,
  resolveExportDownloadUrl,
  searchMedia,
  synthesizeVoicePreview,
} from '../media';

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
}

describe('media API client', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('encodes job ids for media and live media routes', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse({ files: [], chunks: [] }))
      .mockResolvedValueOnce(jsonResponse({ files: [], chunks: [] }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await fetchJobMedia('job/with?parts');
    await fetchLiveJobMedia('job/with?parts');

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(String(fetchMock.mock.calls[0][0])).toContain(
      '/api/pipelines/jobs/job%2Fwith%3Fparts/media'
    );
    expect(String(fetchMock.mock.calls[1][0])).toContain(
      '/api/pipelines/jobs/job%2Fwith%3Fparts/media/live'
    );
  });

  it('uses the shared audio voices route for voice inventory', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse({ macos: [], gtts: [], piper: [] }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await fetchVoiceInventory();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(new URL(String(fetchMock.mock.calls[0][0])).pathname).toBe('/api/audio/voices');
  });

  it('uses shared audio synthesis and pipeline search routes', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(new Response(new Blob(['audio'], { type: 'audio/mpeg' })))
      .mockResolvedValueOnce(jsonResponse({ query: 'origin', limit: 3, count: 0, results: [] }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await synthesizeVoicePreview({
      text: 'Merhaba',
      language: 'tr',
      voice: 'tr-voice',
      speed: 1.1,
    });
    await searchMedia('job/with?parts', ' origin ', 3);

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(new URL(String(fetchMock.mock.calls[0][0])).pathname).toBe('/api/audio');

    const searchUrl = new URL(String(fetchMock.mock.calls[1][0]));
    expect(searchUrl.pathname).toBe('/api/pipelines/search');
    expect(searchUrl.searchParams.get('job_id')).toBe('job/with?parts');
    expect(searchUrl.searchParams.get('query')).toBe('origin');
    expect(searchUrl.searchParams.get('limit')).toBe('3');
  });

  it('uses shared offline export routes for create and download URLs', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse({
        export_id: 'export/with?parts',
        download_url: '/api/exports/server-returned/download',
        filename: 'book.zip',
        created_at: '2026-06-30T00:00:00Z',
      }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const result = await createExport({
      source_kind: 'library',
      source_id: 'job-1',
      player_type: 'interactive-text',
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(new URL(String(fetchMock.mock.calls[0][0]), 'https://example.test').pathname).toBe('/api/exports');
    const downloadUrl = new URL(resolveExportDownloadUrl(result), 'https://example.test');
    expect(downloadUrl.pathname).toBe('/api/exports/export%2Fwith%3Fparts/download');
  });
});
