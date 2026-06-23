import { afterEach, describe, expect, it, vi } from 'vitest';
import { refreshLibraryMetadata } from '../library';
import type { LibraryItem } from '../../dtos';

const refreshedItem: LibraryItem = {
  jobId: 'library-job',
  author: 'Example Author',
  bookTitle: 'Refreshed Title',
  itemType: 'book',
  genre: 'Reference',
  language: 'English',
  status: 'finished',
  mediaCompleted: true,
  createdAt: '2026-06-24T00:00:00Z',
  updatedAt: '2026-06-24T00:00:00Z',
  libraryPath: '/library/library-job',
  metadata: {}
};

describe('library API client', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('unwraps metadata refresh responses and sends the enrich flag deliberately', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>().mockResolvedValue(
      new Response(JSON.stringify({ item: refreshedItem }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      })
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const result = await refreshLibraryMetadata('library-job', { enrichFromExternal: true });

    expect(result).toEqual(refreshedItem);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain('/api/library/items/library-job/refresh');
    expect(init?.method).toBe('POST');
    expect(init?.body).toBe(JSON.stringify({ enrichFromExternal: true }));
  });

  it('defaults metadata refresh to source-only refresh', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>().mockResolvedValue(
      new Response(JSON.stringify({ item: refreshedItem }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      })
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await refreshLibraryMetadata('library-job');

    const [, init] = fetchMock.mock.calls[0];
    expect(init?.body).toBe(JSON.stringify({ enrichFromExternal: false }));
  });
});
