import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  acquireAcquisitionCandidate,
  discoverAcquisitionCandidates,
  fetchAcquisitionProviders,
  prepareAcquisitionArtifact,
} from '../../api/client';
import type {
  AcquisitionCandidate,
  AcquisitionDiscoveryResponse,
} from '../../api/dtos';
import { useBookNarrationDiscovery } from '../book-narration/useBookNarrationDiscovery';

vi.mock('../../api/client', () => ({
  acquireAcquisitionCandidate: vi.fn(),
  discoverAcquisitionCandidates: vi.fn(),
  fetchAcquisitionProviders: vi.fn(),
  prepareAcquisitionArtifact: vi.fn(),
}));

const mockAcquireAcquisitionCandidate = vi.mocked(acquireAcquisitionCandidate);
const mockDiscoverAcquisitionCandidates = vi.mocked(discoverAcquisitionCandidates);
const mockFetchAcquisitionProviders = vi.mocked(fetchAcquisitionProviders);
const mockPrepareAcquisitionArtifact = vi.mocked(prepareAcquisitionArtifact);

function candidate(overrides: Partial<AcquisitionCandidate> = {}): AcquisitionCandidate {
  return {
    candidate_id: 'local_epub:demo',
    provider: 'local_epub',
    media_kind: 'book',
    title: 'Demo Book',
    rights: 'user_provided',
    capabilities: ['metadata', 'import_local'],
    candidate_token: 'token',
    contributors: [],
    local_path: '/books/demo.epub',
    subtitles: [],
    metadata: {},
    requires_confirmation: false,
    policy_notes: [],
    ...overrides,
  };
}

function discoveryResponse(
  candidates: AcquisitionCandidate[],
  providersQueried: string[] = [],
): AcquisitionDiscoveryResponse {
  return {
    candidates,
    providers_queried: providersQueried,
    policy_notes: [],
  };
}

describe('useBookNarrationDiscovery', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('returns provider-filtered discovery candidates from the hook', async () => {
    mockDiscoverAcquisitionCandidates.mockResolvedValue(discoveryResponse([
      candidate({ candidate_id: 'local', provider: 'local_epub' }),
      candidate({ candidate_id: 'manual', provider: 'manual_downloads', local_path: '/downloads/manual.epub' }),
      candidate({ candidate_id: 'video', provider: 'local_epub', media_kind: 'video' }),
      candidate({ candidate_id: 'placeholder', provider: 'local_epub', local_path: null, capabilities: [] }),
    ], ['local_epub']));

    const { result } = renderHook(() => useBookNarrationDiscovery({
      isGeneratedSource: false,
    }));

    await act(async () => {
      await result.current.runDiscoverySearch('dan brown');
    });

    expect(mockDiscoverAcquisitionCandidates).toHaveBeenCalledWith({
      mediaKind: 'book',
      query: 'dan brown',
      provider: null,
      limit: 25,
    });
    expect(result.current.discoveryCandidates.map((entry) => entry.candidate_id)).toEqual(['local']);
  });

  it('does not search generated-book sources', async () => {
    const { result } = renderHook(() => useBookNarrationDiscovery({
      isGeneratedSource: true,
    }));

    await act(async () => {
      await result.current.runDiscoverySearch('ignored');
    });

    expect(mockDiscoverAcquisitionCandidates).not.toHaveBeenCalled();
    expect(result.current.discoveryCandidates).toEqual([]);
    expect(mockAcquireAcquisitionCandidate).not.toHaveBeenCalled();
    expect(mockFetchAcquisitionProviders).not.toHaveBeenCalled();
    expect(mockPrepareAcquisitionArtifact).not.toHaveBeenCalled();
  });
});
