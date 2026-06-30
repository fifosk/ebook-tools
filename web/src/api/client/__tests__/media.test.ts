import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchJobMedia, fetchLiveJobMedia, fetchVoiceInventory } from '../media';

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
});
