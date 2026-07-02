import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  fetchLibraryMedia,
  refreshLibraryMetadata,
  reindexLibrary,
  removeLibraryMedia,
  searchLibrary,
  updateLibraryAccess
} from '../library';
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

const mediaDiagnostics = {
  mediaFileCount: 1,
  chunkCount: 1,
  chunkFileCount: 1,
  audioFileCount: 1,
  imageFileCount: 0,
  chunksWithAudio: 1,
  chunksWithTiming: 0,
  chunksWithImages: 0,
  chunksWithoutFiles: 0,
  chunksWithoutMetadata: 0,
  filesWithoutUrl: 0,
  filesWithoutSize: 0
};

const mediaFile = {
  name: 'sentence.mp3',
  url: '/api/library/media/library-job/file/sentence.mp3',
  size: 1200,
  source: 'completed'
};

const mediaPayload = {
  media: { audio: [mediaFile] },
  chunks: [
    {
      chunk_id: 'chunk_0001',
      files: [mediaFile],
      sentences: [],
      audioTracks: {}
    }
  ],
  complete: true,
  diagnostics: mediaDiagnostics
};

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
}

describe('library API client', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('uses shared Library action routes for media removal, refresh, access, and reindex', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse({ removed: true }))
      .mockResolvedValueOnce(jsonResponse({ item: { job_id: 'job/with?parts' } }))
      .mockResolvedValueOnce(jsonResponse({ job_id: 'job/with?parts' }))
      .mockResolvedValueOnce(jsonResponse({ indexed: 2 }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await removeLibraryMedia('job/with?parts');
    await refreshLibraryMetadata('job/with?parts', { enrichFromExternal: true });
    await updateLibraryAccess('job/with?parts', { visibility: 'private' });
    await reindexLibrary();

    expect(fetchMock).toHaveBeenCalledTimes(4);
    expect(new URL(String(fetchMock.mock.calls[0][0])).pathname).toBe(
      '/api/library/remove-media/job%2Fwith%3Fparts'
    );
    expect(fetchMock.mock.calls[0][1]?.method).toBe('POST');

    expect(new URL(String(fetchMock.mock.calls[1][0])).pathname).toBe(
      '/api/library/items/job%2Fwith%3Fparts/refresh'
    );
    expect(fetchMock.mock.calls[1][1]?.method).toBe('POST');

    expect(new URL(String(fetchMock.mock.calls[2][0])).pathname).toBe(
      '/api/library/items/job%2Fwith%3Fparts/access'
    );
    expect(fetchMock.mock.calls[2][1]?.method).toBe('PATCH');

    expect(new URL(String(fetchMock.mock.calls[3][0])).pathname).toBe('/api/library/reindex');
    expect(fetchMock.mock.calls[3][1]?.method).toBe('POST');
  });

  it('unwraps metadata refresh responses and sends the enrich flag deliberately', async () => {
    const fetchMock = vi
      .fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValue(jsonResponse({ item: refreshedItem }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const result = await refreshLibraryMetadata('library-job', { enrichFromExternal: true });

    expect(result).toEqual(refreshedItem);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(new URL(String(url)).pathname).toBe('/api/library/items/library-job/refresh');
    expect(init?.method).toBe('POST');
    expect(init?.body).toBe(JSON.stringify({ enrichFromExternal: true }));
  });

  it('defaults metadata refresh to source-only refresh', async () => {
    const fetchMock = vi
      .fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValue(jsonResponse({ item: refreshedItem }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await refreshLibraryMetadata('library-job');

    const [, init] = fetchMock.mock.calls[0];
    expect(init?.body).toBe(JSON.stringify({ enrichFromExternal: false }));
  });

  it('validates library search responses and sends query params deliberately', async () => {
    const payload = {
      total: 1,
      page: 2,
      limit: 10,
      view: 'flat',
      items: [refreshedItem],
      groups: null
    };
    const fetchMock = vi
      .fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValue(jsonResponse(payload));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(
      searchLibrary({ query: 'dan brown', page: 2, limit: 10 })
    ).resolves.toEqual(payload);

    const url = new URL(String(fetchMock.mock.calls[0][0]));
    expect(url.pathname).toBe('/api/library/items');
    expect(url.searchParams.get('q')).toBe('dan brown');
    expect(url.searchParams.get('page')).toBe('2');
    expect(url.searchParams.get('limit')).toBe('10');
  });

  it('rejects malformed library search responses before rendering library rows', async () => {
    const fetchMock = vi
      .fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(
        jsonResponse({
          total: 0,
          page: 1,
          limit: 25,
          view: 'flat'
        })
      )
      .mockResolvedValueOnce(
        jsonResponse({
          total: 1,
          page: 1,
          limit: 25,
          view: 'flat',
          items: [{ ...refreshedItem, jobId: undefined }]
        })
      )
      .mockResolvedValueOnce(
        jsonResponse({
          total: 1,
          page: 1,
          limit: 25,
          view: 'flat',
          items: [{ ...refreshedItem, status: 'queued' }]
        })
      )
      .mockResolvedValueOnce(
        jsonResponse({
          total: 1,
          page: 1,
          limit: 25,
          view: 'flat',
          items: [{ ...refreshedItem, metadata: undefined }]
        })
      );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(searchLibrary({})).rejects.toThrow(
      'Invalid library search response: missing items.'
    );
    await expect(searchLibrary({})).rejects.toThrow(
      'Invalid library item response: missing jobId.'
    );
    await expect(searchLibrary({})).rejects.toThrow(
      'Invalid library item response: missing status.'
    );
    await expect(searchLibrary({})).rejects.toThrow(
      'Invalid library item response: missing metadata.'
    );
  });

  it('validates library media responses with the shared playback media contract', async () => {
    const fetchMock = vi
      .fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse(mediaPayload))
      .mockResolvedValueOnce(jsonResponse({ media: {}, chunks: [], complete: true }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(fetchLibraryMedia('library/job', { summary: true })).resolves.toEqual(mediaPayload);

    const url = new URL(String(fetchMock.mock.calls[0][0]));
    expect(url.pathname).toBe('/api/library/media/library%2Fjob');
    expect(url.searchParams.get('summary')).toBe('1');

    await expect(fetchLibraryMedia('library/job')).rejects.toThrow(
      'Invalid pipeline media response: missing diagnostics.'
    );
  });
});
