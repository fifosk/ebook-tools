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
      .mockResolvedValueOnce(jsonResponse({
        default_id: 'lost-in-the-pages',
        beds: [
          {
            id: 'lost-in-the-pages',
            label: 'Lost in the Pages',
            url: '/assets/reading-beds/lost-in-the-pages.mp3',
            kind: 'bundled',
            content_type: 'audio/mpeg',
            is_default: true,
          },
        ],
      }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const catalog = await fetchReadingBeds();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(new URL(String(fetchMock.mock.calls[0][0])).pathname).toBe('/api/reading-beds');
    expect(catalog.beds[0].id).toBe('lost-in-the-pages');
  });

  it('uses shared admin reading-bed routes for write actions', async () => {
    const uploaded = {
      id: 'rain-room',
      label: 'Rain Room',
      url: '/api/reading-beds/rain-room/file',
      kind: 'uploaded',
      content_type: 'audio/mpeg',
      is_default: false,
    };
    const updated = {
      ...uploaded,
      id: 'bed/with?parts',
      label: 'Updated',
      is_default: true,
    };
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse(uploaded))
      .mockResolvedValueOnce(jsonResponse(updated))
      .mockResolvedValueOnce(jsonResponse({ deleted: true, default_id: 'lost-in-the-pages' }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(
      uploadReadingBed(new File(['audio'], 'rain.mp3'), ' Rain Room ')
    ).resolves.toEqual(uploaded);
    await expect(updateReadingBed('bed/with?parts', { label: 'Updated' })).resolves.toEqual(
      updated
    );
    await expect(deleteReadingBed('bed/with?parts')).resolves.toEqual({
      deleted: true,
      default_id: 'lost-in-the-pages',
    });

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

  it('rejects malformed reading-bed response payloads', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>();
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    fetchMock.mockResolvedValueOnce(jsonResponse({ default_id: 'bed-1' }));
    await expect(fetchReadingBeds()).rejects.toThrow(
      'Invalid reading bed list response: missing beds.'
    );

    fetchMock.mockResolvedValueOnce(jsonResponse({
      id: 'rain-room',
      label: 'Rain Room',
      url: '/api/reading-beds/rain-room/file',
      kind: 'uploaded',
    }));
    await expect(uploadReadingBed(new File(['audio'], 'rain.mp3'))).rejects.toThrow(
      'Invalid reading bed upload response: missing is_default.'
    );

    fetchMock.mockResolvedValueOnce(jsonResponse({
      id: 'rain-room',
      label: 'Rain Room',
      url: '/api/reading-beds/rain-room/file',
      kind: 'mystery',
      is_default: false,
    }));
    await expect(updateReadingBed('rain-room', { label: 'Rain Room' })).rejects.toThrow(
      'Invalid reading bed update response: missing kind.'
    );

    fetchMock.mockResolvedValueOnce(jsonResponse({ deleted: true }));
    await expect(deleteReadingBed('rain-room')).rejects.toThrow(
      'Invalid reading bed delete response: missing default_id.'
    );
  });
});
