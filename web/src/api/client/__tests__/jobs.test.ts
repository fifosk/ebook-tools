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

function acquisitionProvider(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'local_epub',
    label: 'Local EPUBs',
    media_kinds: ['book'],
    capabilities: ['import_local'],
    status: 'available',
    configured: true,
    available: true,
    rights: ['user_provided'],
    discovery_media_kinds: ['book'],
    default_eligible_media_kinds: ['book'],
    policy_notes: [],
    next_actions: [],
    ...overrides
  };
}

function acquisitionProviderListResponse(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    providers: [acquisitionProvider()],
    policy_notes: [],
    paths: {},
    default_provider_ids: { book: ['local_epub'] },
    ...overrides
  };
}

function acquisitionCandidate(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    candidate_id: 'local-book',
    provider: 'local_epub',
    media_kind: 'book',
    title: 'Local Book',
    rights: 'user_provided',
    capabilities: ['import_local'],
    candidate_token: 'candidate-token',
    contributors: [],
    subtitles: [],
    metadata: {},
    requires_confirmation: false,
    policy_notes: [],
    ...overrides
  };
}

function acquisitionDiscoveryResponse(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    candidates: [acquisitionCandidate()],
    policy_notes: [],
    providers_queried: ['local_epub'],
    ...overrides
  };
}

function acquisitionArtifactResponse(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    provider: 'internet_archive',
    media_kind: 'book',
    status: 'ready',
    artifact_id: 'artifact-token',
    artifact_path: '/artifacts/demo.epub',
    local_path: '/books/demo.epub',
    filename: 'demo.epub',
    size_bytes: 42,
    modified_at: '2026-07-02T12:00:00Z',
    next_actions: [],
    metadata: {},
    ...overrides
  };
}

function acquisitionPreparedArtifactResponse(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    provider: 'local_epub',
    media_kind: 'book',
    source_kind: 'local_epub',
    local_path: '/books/demo.epub',
    input_file: '/books/demo.epub',
    video_path: null,
    subtitle_path: null,
    subtitles: [],
    next_actions: [],
    metadata: {},
    ...overrides
  };
}

function acquisitionJobStatusResponse(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    provider: 'download_station',
    task_id: 'task-id',
    status: 'completed',
    progress: 1,
    message: null,
    external_task_id: null,
    raw_status: 'finished',
    started_at: null,
    updated_at: '2026-07-02T12:00:00Z',
    completed_files: [],
    next_actions: [],
    metadata: {},
    ...overrides
  };
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
      .mockResolvedValueOnce(jsonResponse(acquisitionProviderListResponse()))
      .mockResolvedValueOnce(jsonResponse(acquisitionDiscoveryResponse()))
      .mockResolvedValueOnce(jsonResponse(acquisitionDiscoveryResponse({
        candidates: [acquisitionCandidate({ provider: 'nas_video', media_kind: 'video' })],
        providers_queried: ['nas_video']
      })))
      .mockResolvedValueOnce(jsonResponse(acquisitionArtifactResponse()))
      .mockResolvedValueOnce(jsonResponse(acquisitionPreparedArtifactResponse()))
      .mockResolvedValueOnce(jsonResponse(acquisitionJobStatusResponse()))
      .mockResolvedValueOnce(jsonResponse(acquisitionJobStatusResponse()));
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
    await discoverAcquisitionCandidates({
      mediaKind: 'video',
      query: 'origin',
      provider: ' BACKEND_DEFAULTS ',
      limit: 3
    });
    await acquireAcquisitionCandidate({ candidate_token: 'candidate-token', confirmed: true });
    await prepareAcquisitionArtifact('artifact/with?parts');
    await createAcquisitionJob({
      provider: 'download_station',
      source_uri: 'token://source',
      confirmed: true
    });
    await fetchAcquisitionJobStatus('task/with?parts', 'download_station');

    expect(fetchMock).toHaveBeenCalledTimes(7);
    expect(new URL(String(fetchMock.mock.calls[0][0])).pathname).toBe('/api/acquisition/providers');

    const discoveryUrl = new URL(String(fetchMock.mock.calls[1][0]));
    expect(discoveryUrl.pathname).toBe('/api/acquisition/discover');
    expect(discoveryUrl.searchParams.get('media_kind')).toBe('book');
    expect(discoveryUrl.searchParams.get('q')).toBe('origin');
    expect(discoveryUrl.searchParams.get('provider')).toBe('default_sources');
    expect(discoveryUrl.searchParams.get('language')).toBe('tr');
    expect(discoveryUrl.searchParams.get('limit')).toBe('7');
    expect(discoveryUrl.searchParams.getAll('source_id')).toEqual(['nas']);

    const defaultDiscoveryUrl = new URL(String(fetchMock.mock.calls[2][0]));
    expect(defaultDiscoveryUrl.pathname).toBe('/api/acquisition/discover');
    expect(defaultDiscoveryUrl.searchParams.get('media_kind')).toBe('video');
    expect(defaultDiscoveryUrl.searchParams.get('q')).toBe('origin');
    expect(defaultDiscoveryUrl.searchParams.get('provider')).toBeNull();
    expect(defaultDiscoveryUrl.searchParams.get('limit')).toBe('3');

    expect(new URL(String(fetchMock.mock.calls[3][0])).pathname).toBe('/api/acquisition/acquire');
    expect(new URL(String(fetchMock.mock.calls[4][0])).pathname).toBe(
      '/api/acquisition/artifacts/artifact%2Fwith%3Fparts/prepare'
    );
    expect(new URL(String(fetchMock.mock.calls[5][0])).pathname).toBe('/api/acquisition/jobs');

    const statusUrl = new URL(String(fetchMock.mock.calls[6][0]));
    expect(statusUrl.pathname).toBe('/api/acquisition/jobs/task%2Fwith%3Fparts');
    expect(statusUrl.searchParams.get('provider')).toBe('download_station');
  });

  it('rejects malformed acquisition provider registry payloads', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse(acquisitionProviderListResponse({ default_provider_ids: undefined })))
      .mockResolvedValueOnce(jsonResponse(acquisitionProviderListResponse({ default_provider_ids: { book: 'local_epub' } })))
      .mockResolvedValueOnce(jsonResponse(acquisitionProviderListResponse({ paths: { books: 42 } })))
      .mockResolvedValueOnce(jsonResponse(acquisitionProviderListResponse({
        providers: [
          acquisitionProvider({ default_eligible_media_kinds: undefined })
        ]
      })))
      .mockResolvedValueOnce(jsonResponse(acquisitionProviderListResponse({
        providers: [
          acquisitionProvider({ configured: 'true' })
        ]
      })))
      .mockResolvedValueOnce(jsonResponse(acquisitionProviderListResponse({
        providers: [
          acquisitionProvider({ policy_notes: [42] })
        ]
      })));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(fetchAcquisitionProviders()).rejects.toThrow(
      'Invalid acquisition provider response: missing default_provider_ids.'
    );
    await expect(fetchAcquisitionProviders()).rejects.toThrow(
      'Invalid acquisition provider response: invalid default_provider_ids.'
    );
    await expect(fetchAcquisitionProviders()).rejects.toThrow(
      'Invalid acquisition provider response: invalid paths.'
    );
    await expect(fetchAcquisitionProviders()).rejects.toThrow(
      'Invalid acquisition provider response: missing default_eligible_media_kinds.'
    );
    await expect(fetchAcquisitionProviders()).rejects.toThrow(
      'Invalid acquisition provider response: missing configured.'
    );
    await expect(fetchAcquisitionProviders()).rejects.toThrow(
      'Invalid acquisition provider response: missing policy_notes.'
    );
  });

  it('rejects malformed acquisition discovery payloads', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse(acquisitionDiscoveryResponse({ candidates: undefined })))
      .mockResolvedValueOnce(jsonResponse(acquisitionDiscoveryResponse({ providers_queried: [42] })))
      .mockResolvedValueOnce(jsonResponse(acquisitionDiscoveryResponse({
        candidates: [
          acquisitionCandidate({ candidate_token: undefined })
        ]
      })))
      .mockResolvedValueOnce(jsonResponse(acquisitionDiscoveryResponse({
        candidates: [
          acquisitionCandidate({ metadata: null })
        ]
      })))
      .mockResolvedValueOnce(jsonResponse(acquisitionDiscoveryResponse({
        candidates: [
          acquisitionCandidate({ subtitles: [{ path: '/subs.srt' }] })
        ]
      })));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(discoverAcquisitionCandidates({ mediaKind: 'book' })).rejects.toThrow(
      'Invalid acquisition discovery response: missing candidates.'
    );
    await expect(discoverAcquisitionCandidates({ mediaKind: 'book' })).rejects.toThrow(
      'Invalid acquisition discovery response: missing providers_queried.'
    );
    await expect(discoverAcquisitionCandidates({ mediaKind: 'book' })).rejects.toThrow(
      'Invalid acquisition discovery response: missing candidate_token.'
    );
    await expect(discoverAcquisitionCandidates({ mediaKind: 'book' })).rejects.toThrow(
      'Invalid acquisition discovery response: missing metadata.'
    );
    await expect(discoverAcquisitionCandidates({ mediaKind: 'book' })).rejects.toThrow(
      'Invalid acquisition discovery response: missing filename.'
    );
  });

  it('rejects malformed acquisition handoff payloads', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse(acquisitionArtifactResponse({ artifact_id: undefined })))
      .mockResolvedValueOnce(jsonResponse(acquisitionArtifactResponse({ metadata: null })))
      .mockResolvedValueOnce(jsonResponse(acquisitionPreparedArtifactResponse({
        subtitles: [{ path: '/subs.srt' }]
      })))
      .mockResolvedValueOnce(jsonResponse(acquisitionPreparedArtifactResponse({ next_actions: [42] })))
      .mockResolvedValueOnce(jsonResponse(acquisitionJobStatusResponse({ completed_files: undefined })))
      .mockResolvedValueOnce(jsonResponse(acquisitionJobStatusResponse({ progress: '1' })));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(
      acquireAcquisitionCandidate({ candidate_token: 'candidate-token', confirmed: true })
    ).rejects.toThrow('Invalid acquisition artifact response: missing artifact_id.');
    await expect(
      acquireAcquisitionCandidate({ candidate_token: 'candidate-token', confirmed: true })
    ).rejects.toThrow('Invalid acquisition artifact response: missing metadata.');
    await expect(prepareAcquisitionArtifact('artifact-token')).rejects.toThrow(
      'Invalid acquisition prepared artifact response: missing filename.'
    );
    await expect(prepareAcquisitionArtifact('artifact-token')).rejects.toThrow(
      'Invalid acquisition prepared artifact response: missing next_actions.'
    );
    await expect(createAcquisitionJob({ provider: 'download_station', confirmed: true })).rejects.toThrow(
      'Invalid acquisition job response: missing completed_files.'
    );
    await expect(fetchAcquisitionJobStatus('task-id')).rejects.toThrow(
      'Invalid acquisition job response: invalid progress.'
    );
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
