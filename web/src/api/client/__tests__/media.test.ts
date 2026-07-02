import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  createPlaybackBookmark,
  createExport,
  deletePlaybackBookmark,
  fetchJobMedia,
  fetchLiveJobMedia,
  fetchPlaybackBookmarks,
  fetchSentenceImageInfo,
  fetchSentenceImageInfoBatch,
  fetchVoiceInventory,
  regenerateSentenceImage,
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
    const voiceInventory = {
      macos: [
        {
          name: 'Alex',
          lang: 'en_US',
          quality: 'Enhanced',
          gender: 'Male',
        },
      ],
      gtts: [{ code: 'en', name: 'English' }],
      piper: [{ name: 'en_US-lessac-medium', lang: 'en_US', quality: 'medium' }],
    };
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse(voiceInventory));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(fetchVoiceInventory()).resolves.toEqual(voiceInventory);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(new URL(String(fetchMock.mock.calls[0][0])).pathname).toBe('/api/audio/voices');
  });

  it('rejects malformed voice inventory response payloads', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>();
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    fetchMock.mockResolvedValueOnce(jsonResponse({ macos: [], gtts: [] }));
    await expect(fetchVoiceInventory()).rejects.toThrow(
      'Invalid voice inventory response: missing piper.'
    );

    fetchMock.mockResolvedValueOnce(jsonResponse({
      macos: [{ name: 'Alex', quality: 'Enhanced' }],
      gtts: [],
      piper: [],
    }));
    await expect(fetchVoiceInventory()).rejects.toThrow(
      'Invalid voice inventory macos response: missing lang.'
    );

    fetchMock.mockResolvedValueOnce(jsonResponse({
      macos: [],
      gtts: [{ code: 'en' }],
      piper: [],
    }));
    await expect(fetchVoiceInventory()).rejects.toThrow(
      'Invalid voice inventory gtts response: missing name.'
    );

    fetchMock.mockResolvedValueOnce(jsonResponse({
      macos: [],
      gtts: [],
      piper: [{ name: 'en_US-lessac-medium', lang: 'en_US' }],
    }));
    await expect(fetchVoiceInventory()).rejects.toThrow(
      'Invalid voice inventory piper response: missing quality.'
    );
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

  it('uses shared sentence image route templates and batch query key', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse({
        job_id: 'job/with?parts',
        sentence_number: 42,
        relative_path: 'media/images/1-50/sentence_00042.png',
      }))
      .mockResolvedValueOnce(jsonResponse({
        job_id: 'job/with?parts',
        items: [],
        missing: [],
      }))
      .mockResolvedValueOnce(jsonResponse({
        job_id: 'job/with?parts',
        sentence_number: 42,
        relative_path: 'media/images/1-50/sentence_00042.png',
        prompt: 'A clear scene',
        negative_prompt: '',
        width: 512,
        height: 512,
        steps: 20,
        cfg_scale: 7,
      }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await fetchSentenceImageInfo('job/with?parts', 42);
    await fetchSentenceImageInfoBatch('job/with?parts', [40, 41, 42]);
    await regenerateSentenceImage('job/with?parts', 42, { prompt: 'A clear scene' });

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(String(fetchMock.mock.calls[0][0])).toContain(
      '/api/pipelines/jobs/job%2Fwith%3Fparts/media/images/sentences/42'
    );
    const batchUrl = new URL(String(fetchMock.mock.calls[1][0]));
    expect(batchUrl.pathname).toBe('/api/pipelines/jobs/job%2Fwith%3Fparts/media/images/sentences/batch');
    expect(batchUrl.searchParams.get('sentence_numbers')).toBe('40,41,42');
    expect(String(fetchMock.mock.calls[2][0])).toContain(
      '/api/pipelines/jobs/job%2Fwith%3Fparts/media/images/sentences/42/regenerate'
    );
  });

  it('validates playback bookmark response payloads', async () => {
    const bookmark = {
      id: 'bookmark-1',
      job_id: 'job/with?parts',
      kind: 'sentence',
      created_at: 1_800_000_000,
      label: 'Chapter turn',
      sentence: 42,
    };
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse({ job_id: 'job/with?parts', bookmarks: [bookmark] }))
      .mockResolvedValueOnce(jsonResponse(bookmark))
      .mockResolvedValueOnce(jsonResponse({ deleted: true, bookmark_id: 'bookmark-1' }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(fetchPlaybackBookmarks('job/with?parts')).resolves.toEqual({
      job_id: 'job/with?parts',
      bookmarks: [bookmark],
    });
    await expect(
      createPlaybackBookmark('job/with?parts', { label: 'Chapter turn', sentence: 42 })
    ).resolves.toEqual(bookmark);
    await expect(deletePlaybackBookmark('job/with?parts', 'bookmark-1')).resolves.toEqual({
      deleted: true,
      bookmark_id: 'bookmark-1',
    });

    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/bookmarks/job%2Fwith%3Fparts');
    expect(String(fetchMock.mock.calls[2][0])).toContain(
      '/api/bookmarks/job%2Fwith%3Fparts/bookmark-1'
    );
  });

  it('rejects malformed playback bookmark response payloads', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>();
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    fetchMock.mockResolvedValueOnce(jsonResponse({ job_id: 'job-1' }));
    await expect(fetchPlaybackBookmarks('job-1')).rejects.toThrow(
      'Invalid playback bookmark list response: missing bookmarks.'
    );

    fetchMock.mockResolvedValueOnce(jsonResponse({
      id: 'bookmark-1',
      job_id: 'job-1',
      kind: 'sentence',
      label: 'Missing timestamp',
    }));
    await expect(
      createPlaybackBookmark('job-1', { label: 'Missing timestamp' })
    ).rejects.toThrow('Invalid bookmark create response: missing created_at.');

    fetchMock.mockResolvedValueOnce(jsonResponse({ deleted: true }));
    await expect(deletePlaybackBookmark('job-1', 'bookmark-1')).rejects.toThrow(
      'Invalid playback bookmark delete response: missing bookmark_id.'
    );
  });
});
