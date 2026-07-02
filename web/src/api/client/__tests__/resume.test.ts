import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  clearResumePosition,
  fetchResumePosition,
  fetchResumePositions,
  saveResumePosition,
} from '../resume';

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
}

describe('resume API client', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('normalizes visible row ids before fetching resume positions', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>().mockResolvedValue(
      jsonResponse({ entries: [] })
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await fetchResumePositions([' job-b ', 'job-a', '', 'job-b', 'job/a?']);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const url = new URL(String(fetchMock.mock.calls[0][0]));
    expect(url.pathname).toBe('/api/resume');
    expect(url.searchParams.getAll('job_id')).toEqual(['job-a', 'job-b', 'job/a?']);
  });

  it('returns an empty result without fetching when a visible row set has no valid ids', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>();
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const result = await fetchResumePositions(['  ', '']);

    expect(result).toEqual({ entries: [] });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('keeps the unfiltered resume list available when no visible row set is supplied', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>().mockResolvedValue(
      jsonResponse({ entries: [] })
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await fetchResumePositions();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/resume');
    expect(String(fetchMock.mock.calls[0][0])).not.toContain('job_id=');
  });

  it('validates resume position response payloads', async () => {
    const entry = {
      job_id: 'job/with?parts',
      kind: 'sentence',
      updated_at: 1_800_000_000,
      sentence: 42,
      media_type: 'text',
      playback_track: 'translation',
    };
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse({ entries: [entry] }))
      .mockResolvedValueOnce(jsonResponse({ job_id: 'job/with?parts', entry }))
      .mockResolvedValueOnce(jsonResponse({ job_id: 'job/with?parts', entry }))
      .mockResolvedValueOnce(jsonResponse({ deleted: true }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(fetchResumePositions(['job/with?parts'])).resolves.toEqual({ entries: [entry] });
    await expect(fetchResumePosition('job/with?parts')).resolves.toEqual({
      job_id: 'job/with?parts',
      entry,
    });
    await expect(
      saveResumePosition('job/with?parts', { kind: 'sentence', sentence: 42 })
    ).resolves.toEqual({ job_id: 'job/with?parts', entry });
    await expect(clearResumePosition('job/with?parts')).resolves.toEqual({ deleted: true });

    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/resume?job_id=job%2Fwith%3Fparts');
    expect(String(fetchMock.mock.calls[1][0])).toContain('/api/resume/job%2Fwith%3Fparts');
  });

  it('rejects malformed resume position response payloads', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>();
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    fetchMock.mockResolvedValueOnce(jsonResponse({}));
    await expect(fetchResumePositions(['job-1'])).rejects.toThrow(
      'Invalid resume position list response: missing entries.'
    );

    fetchMock.mockResolvedValueOnce(jsonResponse({ job_id: 'job-1' }));
    await expect(fetchResumePosition('job-1')).rejects.toThrow(
      'Invalid resume position response: missing entry.'
    );

    fetchMock.mockResolvedValueOnce(jsonResponse({
      job_id: 'job-1',
      entry: { job_id: 'job-1', kind: 'sentence' },
    }));
    await expect(saveResumePosition('job-1', { kind: 'sentence', sentence: 42 })).rejects.toThrow(
      'Invalid resume position response: missing updated_at.'
    );

    fetchMock.mockResolvedValueOnce(jsonResponse({}));
    await expect(clearResumePosition('job-1')).rejects.toThrow(
      'Invalid resume position delete response: missing deleted.'
    );
  });
});
