import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  buildEventStreamUrl,
  acquireAcquisitionCandidate,
  clearTvMetadataCache,
  clearYoutubeMetadataCache,
  createAcquisitionJob,
  DEFAULT_PIPELINE_FILES_LIMIT,
  discoverAcquisitionCandidates,
  checkImageNodeAvailability,
  fetchAcquisitionJobStatus,
  fetchAcquisitionProviders,
  fetchBookContentIndex,
  fetchLlmModels,
  fetchCachedLookup,
  fetchCachedLookupsBulk,
  fetchPipelineDefaults,
  fetchPipelineFiles,
  fetchPipelineIntakeStatus,
  fetchPipelineStatus,
  fetchJobTiming,
  fetchJobs,
  fetchLookupCacheSummary,
  MAX_PIPELINE_FILES_LIMIT,
  MIN_PIPELINE_FILES_LIMIT,
  prepareAcquisitionArtifact,
  refreshPipelineMetadata,
  restartJob,
  submitPipeline,
  uploadEpubFile,
  deletePipelineEbook
} from '../jobs';
import { setAuthToken } from '../base';
import type { PipelineRequestPayload } from '../../dtos';

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

  it('uses shared pipeline source and default routes with encoded content-index queries', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse({ ebooks: [], outputs: [], books_root: '', output_root: '' }))
      .mockResolvedValueOnce(jsonResponse({ config: {} }))
      .mockResolvedValueOnce(jsonResponse({
        acceptingJobs: true,
        isUnderPressure: false,
        queueDepth: 0,
        activeCount: 0,
        delayCount: 0
      }))
      .mockResolvedValueOnce(jsonResponse({ book: {}, chapters: [] }))
      .mockResolvedValueOnce(jsonResponse({ nodes: [], available: [], unavailable: [] }))
      .mockResolvedValueOnce(jsonResponse({ path: '/books/upload.epub', filename: 'upload.epub', type: 'file' }))
      .mockResolvedValueOnce(jsonResponse({ ok: true }))
      .mockResolvedValueOnce(jsonResponse({ models: ['model-a'] }))
      .mockResolvedValueOnce(jsonResponse({ cleared: 1 }))
      .mockResolvedValueOnce(jsonResponse({ cleared: 2 }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await fetchPipelineFiles();
    await fetchPipelineDefaults();
    await fetchPipelineIntakeStatus();
    await fetchBookContentIndex('/books/Dan Brown?part=2.epub');
    await checkImageNodeAvailability({ base_urls: ['http://127.0.0.1:7860'] });
    await uploadEpubFile(new File(['epub'], 'upload.epub'));
    await deletePipelineEbook('/books/delete.epub');
    await fetchLlmModels();
    await clearTvMetadataCache('show s01e01');
    await clearYoutubeMetadataCache('clip id');

    expect(fetchMock).toHaveBeenCalledTimes(10);
    const pipelineFilesUrl = new URL(String(fetchMock.mock.calls[0][0]));
    expect(pipelineFilesUrl.pathname).toBe('/api/pipelines/files');
    expect(pipelineFilesUrl.searchParams.get('limit')).toBe(String(DEFAULT_PIPELINE_FILES_LIMIT));
    expect(new URL(String(fetchMock.mock.calls[1][0])).pathname).toBe('/api/pipelines/defaults');
    expect(new URL(String(fetchMock.mock.calls[2][0])).pathname).toBe(
      '/api/pipelines/intake/status'
    );

    const contentIndexUrl = new URL(String(fetchMock.mock.calls[3][0]));
    expect(contentIndexUrl.pathname).toBe('/api/pipelines/files/content-index');
    expect(contentIndexUrl.searchParams.get('input_file')).toBe('/books/Dan Brown?part=2.epub');

    expect(new URL(String(fetchMock.mock.calls[4][0])).pathname).toBe(
      '/api/pipelines/image-nodes/availability'
    );
    expect(new URL(String(fetchMock.mock.calls[5][0])).pathname).toBe(
      '/api/pipelines/files/upload'
    );
    expect(new URL(String(fetchMock.mock.calls[6][0])).pathname).toBe('/api/pipelines/files');
    expect(new URL(String(fetchMock.mock.calls[7][0])).pathname).toBe('/api/pipelines/llm-models');
    expect(new URL(String(fetchMock.mock.calls[8][0])).pathname).toBe(
      '/api/subtitles/metadata/tv/cache/clear'
    );
    expect(new URL(String(fetchMock.mock.calls[9][0])).pathname).toBe(
      '/api/subtitles/metadata/youtube/cache/clear'
    );
  });

  it('bounds custom pipeline file limits before requesting the picker', async () => {
    const fetchMock = vi
      .fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockImplementation(() => Promise.resolve(jsonResponse({ ebooks: [], outputs: [] })));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await fetchPipelineFiles(9999);
    await fetchPipelineFiles(0);

    const highLimitUrl = new URL(String(fetchMock.mock.calls[0][0]));
    const lowLimitUrl = new URL(String(fetchMock.mock.calls[1][0]));
    expect(highLimitUrl.searchParams.get('limit')).toBe(String(MAX_PIPELINE_FILES_LIMIT));
    expect(lowLimitUrl.searchParams.get('limit')).toBe(String(MIN_PIPELINE_FILES_LIMIT));
  });

  it('uses shared pipeline job, timing, and lookup-cache routes', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse({ job_id: 'new-job' }))
      .mockResolvedValueOnce(jsonResponse({ jobs: [] }))
      .mockResolvedValueOnce(jsonResponse({ entries: [] }))
      .mockResolvedValueOnce(jsonResponse({ word: 'Merhaba', cached: true }))
      .mockResolvedValueOnce(jsonResponse({ entries: [] }))
      .mockResolvedValueOnce(jsonResponse({ cachedCount: 1 }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const payload: PipelineRequestPayload = {
      config: {},
      environment_overrides: {},
      pipeline_overrides: {},
      inputs: {
        input_file: '/books/source.epub',
        base_output_file: 'source',
        input_language: 'English',
        target_languages: ['Turkish'],
        sentences_per_output_file: 25,
        start_sentence: 1,
        end_sentence: null,
        stitch_full: true,
        generate_audio: true,
        audio_mode: 'sentence',
        written_mode: 'translation',
        selected_voice: '',
        output_html: true,
        output_pdf: false,
        add_images: false,
        include_transliteration: false,
        tempo: 1,
        book_metadata: {}
      }
    };

    await submitPipeline(payload);
    await fetchJobs();
    await fetchJobTiming('job/with?parts');
    await fetchCachedLookup('job/with?parts', 'günaydın?');
    await fetchCachedLookupsBulk('job/with?parts', ['günaydın']);
    await fetchLookupCacheSummary('job/with?parts');

    expect(fetchMock).toHaveBeenCalledTimes(6);
    expect(new URL(String(fetchMock.mock.calls[0][0])).pathname).toBe('/api/pipelines');
    expect(new URL(String(fetchMock.mock.calls[1][0])).pathname).toBe('/api/pipelines/jobs');
    expect(new URL(String(fetchMock.mock.calls[2][0])).pathname).toBe(
      '/api/jobs/job%2Fwith%3Fparts/timing'
    );
    expect(new URL(String(fetchMock.mock.calls[3][0])).pathname).toBe(
      '/api/pipelines/jobs/job%2Fwith%3Fparts/lookup-cache/g%C3%BCnayd%C4%B1n%3F'
    );
    expect(new URL(String(fetchMock.mock.calls[4][0])).pathname).toBe(
      '/api/pipelines/jobs/job%2Fwith%3Fparts/lookup-cache/bulk'
    );
    expect(new URL(String(fetchMock.mock.calls[5][0])).pathname).toBe(
      '/api/pipelines/jobs/job%2Fwith%3Fparts/lookup-cache/summary'
    );
  });
});
