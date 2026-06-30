import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchReadingBeds } from '../admin';

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
}

describe('admin API client', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('uses the shared playback-state route for reading bed catalogs', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse({ items: [] }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await fetchReadingBeds();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(new URL(String(fetchMock.mock.calls[0][0])).pathname).toBe('/api/reading-beds');
  });
});
