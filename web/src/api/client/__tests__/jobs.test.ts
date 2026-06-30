import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  buildEventStreamUrl,
  acquireAcquisitionCandidate,
  createAcquisitionJob,
  discoverAcquisitionCandidates,
  fetchAcquisitionJobStatus,
  fetchAcquisitionProviders,
  fetchPipelineStatus,
  prepareAcquisitionArtifact,
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

  it('uses shared acquisition routes and encodes artifact and task ids', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse({}))
      .mockResolvedValueOnce(jsonResponse({}))
      .mockResolvedValueOnce(jsonResponse({}))
      .mockResolvedValueOnce(jsonResponse({}))
      .mockResolvedValueOnce(jsonResponse({}))
      .mockResolvedValueOnce(jsonResponse({}));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await fetchAcquisitionProviders();
    await discoverAcquisitionCandidates({
      mediaKind: 'book',
      query: 'origin',
      provider: 'default_sources',
      language: 'tr',
      sourceIds: [' nas ', ''],
      limit: 7
    });
    await acquireAcquisitionCandidate({ candidate_token: 'candidate-token', confirmed: true });
    await prepareAcquisitionArtifact('artifact/with?parts');
    await createAcquisitionJob({
      provider: 'download_station',
      source_uri: 'token://source',
      confirmed: true
    });
    await fetchAcquisitionJobStatus('task/with?parts', 'download_station');

    expect(fetchMock).toHaveBeenCalledTimes(6);
    expect(new URL(String(fetchMock.mock.calls[0][0])).pathname).toBe('/api/acquisition/providers');

    const discoveryUrl = new URL(String(fetchMock.mock.calls[1][0]));
    expect(discoveryUrl.pathname).toBe('/api/acquisition/discover');
    expect(discoveryUrl.searchParams.get('media_kind')).toBe('book');
    expect(discoveryUrl.searchParams.get('q')).toBe('origin');
    expect(discoveryUrl.searchParams.get('provider')).toBe('default_sources');
    expect(discoveryUrl.searchParams.get('language')).toBe('tr');
    expect(discoveryUrl.searchParams.get('limit')).toBe('7');
    expect(discoveryUrl.searchParams.getAll('source_id')).toEqual(['nas']);

    expect(new URL(String(fetchMock.mock.calls[2][0])).pathname).toBe('/api/acquisition/acquire');
    expect(new URL(String(fetchMock.mock.calls[3][0])).pathname).toBe(
      '/api/acquisition/artifacts/artifact%2Fwith%3Fparts/prepare'
    );
    expect(new URL(String(fetchMock.mock.calls[4][0])).pathname).toBe('/api/acquisition/jobs');

    const statusUrl = new URL(String(fetchMock.mock.calls[5][0]));
    expect(statusUrl.pathname).toBe('/api/acquisition/jobs/task%2Fwith%3Fparts');
    expect(statusUrl.searchParams.get('provider')).toBe('download_station');
  });
});
