import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { discoverAcquisitionCandidates, fetchAcquisitionProviders } from '../../api/client';
import type { AcquisitionCandidate, AcquisitionProvider } from '../../api/dtos';
import { DEFAULT_VIDEO_DISCOVERY_PROVIDER } from '../video-dubbing/videoDubbingDiscovery';
import { useVideoDubbingDiscoveryController } from '../video-dubbing/useVideoDubbingDiscoveryController';

vi.mock('../../api/client', () => ({
  discoverAcquisitionCandidates: vi.fn(),
  fetchAcquisitionProviders: vi.fn()
}));

const mockDiscoverAcquisitionCandidates = vi.mocked(discoverAcquisitionCandidates);
const mockFetchAcquisitionProviders = vi.mocked(fetchAcquisitionProviders);

function provider(overrides: Partial<AcquisitionProvider>): AcquisitionProvider {
  const mediaKinds = overrides.media_kinds ?? ['video'];
  const discoveryMediaKinds = overrides.discovery_media_kinds ?? mediaKinds;
  return {
    id: 'nas_video',
    label: 'NAS videos',
    media_kinds: mediaKinds,
    capabilities: ['import_local'],
    status: 'available',
    configured: true,
    available: true,
    rights: ['user_provided'],
    discovery_media_kinds: discoveryMediaKinds,
    default_eligible_media_kinds: overrides.default_eligible_media_kinds ?? discoveryMediaKinds,
    policy_notes: [],
    next_actions: [],
    ...overrides
  };
}

function candidate(overrides: Partial<AcquisitionCandidate>): AcquisitionCandidate {
  return {
    candidate_id: 'candidate-1',
    provider: 'nas_video',
    media_kind: 'video',
    title: 'Candidate',
    rights: 'user_provided',
    capabilities: ['import_local'],
    candidate_token: 'token',
    subtitle: null,
    contributors: [],
    language: null,
    year: null,
    published_at: null,
    source_url: null,
    thumbnail_url: null,
    cover_url: null,
    local_path: '/videos/demo.mkv',
    size_bytes: null,
    modified_at: null,
    duration_seconds: null,
    subtitles: [],
    metadata: {},
    requires_confirmation: false,
    policy_notes: [],
    ...overrides
  };
}

function renderController() {
  const onClearSelectedDiscoveryTemplate = vi.fn();
  const result = renderHook(() =>
    useVideoDubbingDiscoveryController({
      onClearSelectedDiscoveryTemplate
    })
  );

  return {
    ...result,
    onClearSelectedDiscoveryTemplate
  };
}

describe('useVideoDubbingDiscoveryController', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchAcquisitionProviders.mockResolvedValue({
      providers: [],
      policy_notes: [],
      paths: {},
      default_provider_ids: {}
    });
  });

  it('auto-selects the backend default video source group when it is available', async () => {
    mockFetchAcquisitionProviders.mockResolvedValueOnce({
      providers: [
        provider({ id: 'nas_video', default_eligible_media_kinds: ['video'] }),
        provider({
          id: 'newznab_torznab',
          label: 'Indexers',
          capabilities: ['search'],
          discovery_media_kinds: ['video'],
          default_eligible_media_kinds: ['video']
        })
      ],
      policy_notes: [],
      paths: {},
      default_provider_ids: { video: ['nas_video', 'newznab_torznab'] }
    });

    const { result, onClearSelectedDiscoveryTemplate } = renderController();

    await waitFor(() => {
      expect(result.current.videoDiscoveryProvider).toBe(DEFAULT_VIDEO_DISCOVERY_PROVIDER);
      expect(result.current.videoDiscoveryProviderOptions[0].id).toBe(DEFAULT_VIDEO_DISCOVERY_PROVIDER);
    }, { timeout: 3000 });
    expect(onClearSelectedDiscoveryTemplate).not.toHaveBeenCalled();
  });

  it('filters default discovery candidates through provider default eligibility', async () => {
    mockFetchAcquisitionProviders.mockResolvedValueOnce({
      providers: [
        provider({ id: 'nas_video', default_eligible_media_kinds: ['video'] }),
        provider({
          id: 'youtube_url',
          label: 'YouTube URL',
          capabilities: ['metadata'],
          discovery_media_kinds: ['video'],
          default_eligible_media_kinds: []
        }),
        provider({
          id: 'newznab_torznab',
          label: 'Indexers',
          capabilities: ['search'],
          discovery_media_kinds: ['video'],
          default_eligible_media_kinds: ['video']
        })
      ],
      policy_notes: [],
      paths: {},
      default_provider_ids: { video: ['nas_video', 'newznab_torznab'] }
    });
    mockDiscoverAcquisitionCandidates.mockResolvedValueOnce({
      candidates: [
        candidate({
          candidate_id: 'youtube-url',
          provider: 'youtube_url',
          source_url: 'https://youtube.test/watch?v=demo',
          local_path: null
        }),
        candidate({
          candidate_id: 'indexer',
          provider: 'newznab_torznab',
          local_path: null,
          requires_confirmation: true
        }),
        candidate({
          candidate_id: 'nas',
          provider: 'nas_video',
          local_path: '/videos/demo.mkv'
        })
      ],
      policy_notes: [],
      providers_queried: ['youtube_url', 'newznab_torznab', 'nas_video']
    });

    const { result } = renderController();
    await waitFor(() =>
      expect(result.current.videoDiscoveryProvider).toBe(DEFAULT_VIDEO_DISCOVERY_PROVIDER)
    );

    await act(async () => {
      await result.current.discoverVideos();
    });

    expect(mockDiscoverAcquisitionCandidates).toHaveBeenCalledWith({
      mediaKind: 'video',
      provider: null,
      query: '',
      limit: 25
    });
    expect(result.current.discoveredVideoCandidates.map((entry) => entry.candidate_id)).toEqual([
      'indexer',
      'nas'
    ]);
  });

  it('passes discovery policy notes through the page controller', async () => {
    mockFetchAcquisitionProviders.mockResolvedValueOnce({
      providers: [
        provider({ id: 'nas_video', default_eligible_media_kinds: ['video'] }),
        provider({
          id: 'youtube_search',
          label: 'YouTube search',
          capabilities: ['metadata'],
          discovery_media_kinds: ['video'],
          default_eligible_media_kinds: ['video']
        })
      ],
      policy_notes: [],
      paths: {},
      default_provider_ids: { video: ['nas_video', 'youtube_search'] }
    });
    mockDiscoverAcquisitionCandidates.mockResolvedValueOnce({
      candidates: [
        candidate({
          candidate_id: 'nas',
          provider: 'nas_video',
          local_path: '/videos/demo.mkv'
        })
      ],
      policy_notes: ['YouTube search failed; showing NAS results.'],
      providers_queried: ['nas_video', 'youtube_search']
    });

    const { result } = renderController();
    await waitFor(() =>
      expect(result.current.videoDiscoveryProvider).toBe(DEFAULT_VIDEO_DISCOVERY_PROVIDER)
    );

    await act(async () => {
      await result.current.discoverVideos();
    });

    await waitFor(() => {
      expect(result.current.discoveryPolicyNotes).toEqual([
        'YouTube search failed; showing NAS results.'
      ]);
    });
  });
});
