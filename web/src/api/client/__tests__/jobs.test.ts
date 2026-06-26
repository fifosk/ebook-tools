import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  buildEventStreamUrl,
  fetchPipelineStatus,
  refreshPipelineMetadata,
  restartJob
} from '../jobs';
import { setAuthToken } from '../base';

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
}

describe('jobs API client', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    setAuthToken(null);
    vi.restoreAllMocks();
  });

  it('encodes job ids for pipeline status, actions, and metadata refresh routes', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse({ job_id: 'job/with?parts', status: 'completed' }))
      .mockResolvedValueOnce(jsonResponse({ job: { job_id: 'job/with?parts', status: 'pending' } }))
      .mockResolvedValueOnce(jsonResponse({ job_id: 'job/with?parts', status: 'completed' }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await fetchPipelineStatus('job/with?parts');
    await restartJob('job/with?parts');
    await refreshPipelineMetadata('job/with?parts');

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/pipelines/job%2Fwith%3Fparts');
    expect(String(fetchMock.mock.calls[1][0])).toContain(
      '/api/pipelines/jobs/job%2Fwith%3Fparts/restart'
    );
    expect(String(fetchMock.mock.calls[2][0])).toContain(
      '/api/pipelines/job%2Fwith%3Fparts/metadata/refresh'
    );
  });

  it('encodes job ids and access tokens for event streams independently', () => {
    setAuthToken('token/with?parts');

    const url = new URL(buildEventStreamUrl('job/with?parts'));

    expect(url.pathname).toBe('/api/pipelines/job%2Fwith%3Fparts/events');
    expect(url.searchParams.get('access_token')).toBe('token/with?parts');
  });
});
