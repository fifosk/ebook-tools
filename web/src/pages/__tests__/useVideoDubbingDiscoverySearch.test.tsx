import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { discoverAcquisitionCandidates } from '../../api/client';
import type { AcquisitionCandidate, AcquisitionProvider } from '../../api/dtos';
import { DEFAULT_VIDEO_DISCOVERY_PROVIDER } from '../video-dubbing/videoDubbingDiscovery';
import { useVideoDubbingDiscoverySearch } from '../video-dubbing/useVideoDubbingDiscoverySearch';

vi.mock('../../api/client', () => ({
  discoverAcquisitionCandidates: vi.fn()
}));

const mockDiscoverAcquisitionCandidates = vi.mocked(discoverAcquisitionCandidates);

function candidate(overrides: Partial<AcquisitionCandidate> = {}): AcquisitionCandidate {
  return {
    candidate_id: 'candidate-1',
    provider: 'nas_video',
    media_kind: 'video',
    title: 'Local episode',
    rights: 'user_provided',
    capabilities: ['import_local'],
    candidate_token: '',
    contributors: [],
    local_path: '/Volumes/Data/Download/DStation/episode.mkv',
    subtitles: [],
    metadata: {},
    requires_confirmation: false,
    policy_notes: [],
    ...overrides
  };
}

function provider(overrides: Partial<AcquisitionProvider> = {}): AcquisitionProvider {
  return {
    id: 'nas_video',
    label: 'NAS videos',
    media_kinds: ['video'],
    capabilities: ['import_local'],
    status: 'available',
    configured: true,
    available: true,
    rights: ['user_provided'],
    policy_notes: [],
    next_actions: [],
    ...overrides
  };
}

function renderDiscoveryHook({
  acquisitionProviders = []
}: {
  acquisitionProviders?: AcquisitionProvider[];
} = {}) {
  const onClearSelectedDiscoveryTemplate = vi.fn();
  const result = renderHook(() =>
    useVideoDubbingDiscoverySearch({
      onClearSelectedDiscoveryTemplate,
      acquisitionProviders
    })
  );

  return {
    ...result,
    onClearSelectedDiscoveryTemplate
  };
}

describe('useVideoDubbingDiscoverySearch', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('starts on the backend default provider without discovered candidates', () => {
    const { result } = renderDiscoveryHook();

    expect(result.current.videoDiscoveryProvider).toBe(DEFAULT_VIDEO_DISCOVERY_PROVIDER);
    expect(result.current.discoveryQuery).toBe('');
    expect(result.current.discoveredVideoCandidates).toEqual([]);
  });

  it('reports provider unavailability before calling backend discovery', async () => {
    const { result } = renderDiscoveryHook();

    await act(async () => {
      await result.current.discoverVideos({
        isDiscoveryProviderAvailable: false,
        unavailableMessage: 'YouTube search needs an API key.'
      });
    });

    expect(result.current.discoveryError).toBe('YouTube search needs an API key.');
    expect(mockDiscoverAcquisitionCandidates).not.toHaveBeenCalled();
  });

  it('discovers video candidates for the selected provider and filters unrelated results', async () => {
    mockDiscoverAcquisitionCandidates.mockResolvedValueOnce({
      candidates: [
        candidate(),
        candidate({
          candidate_id: 'candidate-2',
          provider: 'youtube_search',
          source_url: 'https://youtube.test/watch?v=1',
          local_path: null
        })
      ],
      policy_notes: [],
      providers_queried: ['nas_video']
    });
    const { result } = renderDiscoveryHook();

    act(() => {
      result.current.setDiscoveryQuery('episode query');
    });
    await act(async () => {
      await result.current.discoverVideos({
        isDiscoveryProviderAvailable: true,
        unavailableMessage: null
      });
    });

    expect(mockDiscoverAcquisitionCandidates).toHaveBeenCalledWith({
      mediaKind: 'video',
      provider: null,
      query: 'episode query',
      limit: 25
    });
    expect(result.current.discoveryError).toBeNull();
    expect(result.current.discoveredVideoCandidates.map((entry) => entry.candidate_id)).toEqual([
      'candidate-1'
    ]);
  });

  it('exposes trimmed unique policy notes from partial discovery responses', async () => {
    mockDiscoverAcquisitionCandidates.mockResolvedValueOnce({
      candidates: [candidate()],
      policy_notes: [
        '  YouTube search failed; showing local results.  ',
        '',
        'YouTube search failed; showing local results.',
        'Indexer search timed out.'
      ],
      providers_queried: ['nas_video', 'youtube_search', 'newznab_torznab']
    });
    const { result } = renderDiscoveryHook();

    await act(async () => {
      await result.current.discoverVideos({
        isDiscoveryProviderAvailable: true,
        unavailableMessage: null
      });
    });

    expect(result.current.discoveryPolicyNotes).toEqual([
      'YouTube search failed; showing local results.',
      'Indexer search timed out.'
    ]);
  });

  it('omits provider when discovering backend default video sources', async () => {
    mockDiscoverAcquisitionCandidates.mockResolvedValueOnce({
      candidates: [
        candidate(),
        candidate({
          candidate_id: 'candidate-2',
          provider: 'newznab_torznab',
          local_path: null,
          requires_confirmation: true
        })
      ],
      policy_notes: [],
      providers_queried: ['nas_video', 'newznab_torznab']
    });
    const { result } = renderDiscoveryHook();

    act(() => {
      result.current.handleDiscoveryProviderChange(DEFAULT_VIDEO_DISCOVERY_PROVIDER);
    });
    await act(async () => {
      await result.current.discoverVideos({
        isDiscoveryProviderAvailable: true,
        unavailableMessage: null
      });
    });

    expect(mockDiscoverAcquisitionCandidates).toHaveBeenCalledWith({
      mediaKind: 'video',
      provider: null,
      query: '',
      limit: 25
    });
    expect(result.current.discoveredVideoCandidates.map((entry) => entry.candidate_id)).toEqual([
      'candidate-1',
      'candidate-2'
    ]);
  });

  it('filters backend default video results with provider default eligibility', async () => {
    mockDiscoverAcquisitionCandidates.mockResolvedValueOnce({
      candidates: [
        candidate({
          candidate_id: 'candidate-1',
          provider: 'youtube_url',
          source_url: 'https://youtube.test/watch?v=direct',
          local_path: null
        }),
        candidate({
          candidate_id: 'candidate-2',
          provider: 'newznab_torznab',
          local_path: null,
          requires_confirmation: true
        })
      ],
      policy_notes: [],
      providers_queried: ['youtube_url', 'newznab_torznab']
    });
    const { result } = renderDiscoveryHook({
      acquisitionProviders: [
        provider({
          id: 'youtube_url',
          capabilities: ['metadata'],
          discovery_media_kinds: ['video'],
          default_eligible_media_kinds: []
        }),
        provider({
          id: 'newznab_torznab',
          capabilities: ['search'],
          discovery_media_kinds: ['video'],
          default_eligible_media_kinds: ['video']
        })
      ]
    });

    act(() => {
      result.current.handleDiscoveryProviderChange(DEFAULT_VIDEO_DISCOVERY_PROVIDER);
    });
    await act(async () => {
      await result.current.discoverVideos({
        isDiscoveryProviderAvailable: true,
        unavailableMessage: null
      });
    });

    expect(result.current.discoveredVideoCandidates.map((entry) => entry.candidate_id)).toEqual([
      'candidate-2'
    ]);
  });

  it('resets discovery results and saved template state when provider changes', async () => {
    mockDiscoverAcquisitionCandidates.mockResolvedValueOnce({
      candidates: [candidate()],
      policy_notes: [],
      providers_queried: ['nas_video']
    });
    const { result, onClearSelectedDiscoveryTemplate } = renderDiscoveryHook();

    await act(async () => {
      await result.current.discoverVideos({
        isDiscoveryProviderAvailable: true,
        unavailableMessage: null
      });
    });
    act(() => {
      result.current.setDiscoveryError('stale error');
      result.current.handleDiscoveryProviderChange('youtube_search');
    });

    expect(result.current.videoDiscoveryProvider).toBe('youtube_search');
    expect(result.current.discoveryError).toBeNull();
    expect(result.current.discoveredVideoCandidates).toEqual([]);
    expect(onClearSelectedDiscoveryTemplate).toHaveBeenCalledTimes(1);
  });
});
