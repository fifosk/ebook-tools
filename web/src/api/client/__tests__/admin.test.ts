import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  deleteReadingBed,
  fetchReadingBeds,
  updateReadingBed,
  uploadReadingBed
} from '../admin';

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

  it('uses shared admin reading-bed routes for write actions', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse({ id: 'rain-room', label: 'Rain Room' }))
      .mockResolvedValueOnce(jsonResponse({ id: 'bed/with?parts', label: 'Updated' }))
      .mockResolvedValueOnce(jsonResponse({ deleted: true, id: 'bed/with?parts' }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await uploadReadingBed(new File(['audio'], 'rain.mp3'), ' Rain Room ');
    await updateReadingBed('bed/with?parts', { label: 'Updated' });
    await deleteReadingBed('bed/with?parts');

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(new URL(String(fetchMock.mock.calls[0][0])).pathname).toBe('/api/admin/reading-beds');
    expect(fetchMock.mock.calls[0][1]?.method).toBe('POST');
    expect(new URL(String(fetchMock.mock.calls[1][0])).pathname).toBe(
      '/api/admin/reading-beds/bed%2Fwith%3Fparts'
    );
    expect(fetchMock.mock.calls[1][1]?.method).toBe('PATCH');
    expect(new URL(String(fetchMock.mock.calls[2][0])).pathname).toBe(
      '/api/admin/reading-beds/bed%2Fwith%3Fparts'
    );
    expect(fetchMock.mock.calls[2][1]?.method).toBe('DELETE');
  });
});
