import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { discoverAcquisitionCandidates } from '../../api/client';
import type { AcquisitionCandidate } from '../../api/dtos';
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

function renderDiscoveryHook() {
  const onClearSelectedDiscoveryTemplate = vi.fn();
  const result = renderHook(() =>
    useVideoDubbingDiscoverySearch({
      onClearSelectedDiscoveryTemplate
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

  it('starts on the NAS video provider without discovered candidates', () => {
    const { result } = renderDiscoveryHook();

    expect(result.current.videoDiscoveryProvider).toBe('nas_video');
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
      provider: 'nas_video',
      query: 'episode query',
      limit: 25
    });
    expect(result.current.discoveryError).toBeNull();
    expect(result.current.discoveredVideoCandidates.map((entry) => entry.candidate_id)).toEqual([
      'candidate-1'
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
