import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchResumePositions } from '../resume';

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
});
