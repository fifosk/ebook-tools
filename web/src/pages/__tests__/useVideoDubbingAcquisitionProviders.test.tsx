import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchAcquisitionProviders } from '../../api/client';
import type { AcquisitionProvider } from '../../api/dtos';
import { useVideoDubbingAcquisitionProviders } from '../video-dubbing/useVideoDubbingAcquisitionProviders';

vi.mock('../../api/client', () => ({
  fetchAcquisitionProviders: vi.fn()
}));

const mockFetchAcquisitionProviders = vi.mocked(fetchAcquisitionProviders);

function provider(overrides: Partial<AcquisitionProvider>): AcquisitionProvider {
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

describe('useVideoDubbingAcquisitionProviders', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchAcquisitionProviders.mockResolvedValue({
      providers: [],
      policy_notes: [],
      paths: {}
    });
  });

  it('loads backend providers and exposes stable video discovery options', async () => {
    mockFetchAcquisitionProviders.mockResolvedValueOnce({
      providers: [
        provider({ id: 'youtube_search', label: 'YouTube backend', capabilities: ['search'] }),
        provider({ id: 'manual_downloads', label: 'Manual backend', media_kinds: ['book', 'video'], capabilities: ['import_local'] }),
        provider({ id: 'book_only', label: 'Book only', media_kinds: ['book'], capabilities: ['search'] })
      ],
      policy_notes: [],
      paths: {},
      default_provider_ids: { video: ['youtube_search'] }
    });

    const { result } = renderHook(() => useVideoDubbingAcquisitionProviders('manual_downloads'));

    await waitFor(() => expect(result.current.videoDiscoveryProviderOptions).toHaveLength(2));
    expect(result.current.acquisitionProviderError).toBeNull();
    expect(result.current.videoDiscoveryProviderOptions).toEqual([
      { id: 'manual_downloads', label: 'Manual downloads', available: true },
      { id: 'youtube_search', label: 'YouTube search', available: true }
    ]);
    expect(result.current.preferredVideoDiscoveryProvider).toBe('youtube_search');
    expect(result.current.isSelectedVideoDiscoveryProviderAvailable).toBe(true);
  });

  it('reports selected-provider unavailability through the derived provider state', async () => {
    mockFetchAcquisitionProviders.mockResolvedValueOnce({
      providers: [
        provider({
          id: 'youtube_search',
          label: 'YouTube search',
          capabilities: ['search'],
          status: 'not_configured',
          configured: false,
          available: false
        })
      ],
      policy_notes: [],
      paths: {}
    });

    const { result } = renderHook(() => useVideoDubbingAcquisitionProviders('youtube_search'));

    await waitFor(() => expect(result.current.videoDiscoveryProviderOptions).toHaveLength(1));
    expect(result.current.isSelectedVideoDiscoveryProviderAvailable).toBe(false);
    expect(result.current.selectedVideoDiscoveryProviderUnavailableMessage).toContain(
      'Configure the YouTube Data API key'
    );
  });

  it('prefers backend default source group when multiple defaults are available', async () => {
    mockFetchAcquisitionProviders.mockResolvedValueOnce({
      providers: [
        provider({ id: 'nas_video', label: 'NAS backend', capabilities: ['import_local'] }),
        provider({ id: 'newznab_torznab', label: 'Indexer backend', capabilities: ['search'] })
      ],
      policy_notes: [],
      paths: {},
      default_provider_ids: { video: ['nas_video', 'newznab_torznab'] }
    });

    const { result } = renderHook(() => useVideoDubbingAcquisitionProviders('backend_defaults'));

    await waitFor(() => expect(result.current.videoDiscoveryProviderOptions[0].id).toBe('backend_defaults'));
    expect(result.current.preferredVideoDiscoveryProvider).toBe('backend_defaults');
    expect(result.current.isSelectedVideoDiscoveryProviderAvailable).toBe(true);
  });

  it('keeps fallback options visible when provider loading fails', async () => {
    mockFetchAcquisitionProviders.mockRejectedValueOnce(new Error('registry unavailable'));

    const { result } = renderHook(() => useVideoDubbingAcquisitionProviders('nas_video'));

    await waitFor(() => expect(result.current.acquisitionProviderError).toBe('registry unavailable'));
    expect(result.current.videoDiscoveryProviderOptions.map((option) => option.id)).toEqual([
      'nas_video',
      'manual_downloads',
      'youtube_search',
      'newznab_torznab'
    ]);
    expect(result.current.isSelectedVideoDiscoveryProviderAvailable).toBe(true);
  });
});
