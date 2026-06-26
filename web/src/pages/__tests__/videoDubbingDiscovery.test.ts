import { describe, expect, it } from 'vitest';
import type {
  AcquisitionCandidate,
  AcquisitionDiscoveryResponse,
  AcquisitionProvider
} from '../../api/dtos';
import {
  buildVideoDiscoveryProviderOptions,
  filterDiscoveredVideoCandidates,
  resolveVideoDiscoveryProviderState
} from '../video-dubbing/videoDubbingDiscovery';

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
    local_path: null,
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

function discoveryResponse(candidates: AcquisitionCandidate[]): AcquisitionDiscoveryResponse {
  return {
    candidates,
    policy_notes: [],
    providers_queried: []
  };
}

describe('videoDubbingDiscovery', () => {
  it('returns familiar fallback provider options before the backend registry loads', () => {
    expect(buildVideoDiscoveryProviderOptions([])).toEqual([
      { id: 'nas_video', label: 'NAS videos', available: true },
      { id: 'manual_downloads', label: 'Manual downloads', available: true },
      { id: 'youtube_search', label: 'YouTube search', available: true },
      { id: 'newznab_torznab', label: 'Indexers', available: true }
    ]);
  });

  it('keeps backend video providers in stable UI order and excludes acquire-only providers', () => {
    const options = buildVideoDiscoveryProviderOptions([
      provider({ id: 'download_station', label: 'Download Station', capabilities: ['acquire'] }),
      provider({ id: 'youtube_search', label: 'YouTube backend', capabilities: ['search'] }),
      provider({ id: 'other_video', label: 'Other Video', capabilities: ['search'] }),
      provider({ id: 'manual_downloads', label: 'Manual backend', media_kinds: ['book', 'video'], capabilities: ['import_local'] }),
      provider({ id: 'nas_video', label: 'NAS backend', capabilities: ['import_local'] }),
      provider({ id: 'book_only', label: 'Book only', media_kinds: ['book'], capabilities: ['search'] }),
      provider({ id: 'newznab_torznab', label: 'Indexer backend', capabilities: ['search'] })
    ]);

    expect(options).toEqual([
      { id: 'nas_video', label: 'NAS videos', available: true },
      { id: 'manual_downloads', label: 'Manual downloads', available: true },
      { id: 'youtube_search', label: 'YouTube search', available: true },
      { id: 'newznab_torznab', label: 'Indexers', available: true },
      { id: 'other_video', label: 'Other Video', available: true }
    ]);
  });

  it('resolves selected-provider availability and keeps specific guidance messages', () => {
    const state = resolveVideoDiscoveryProviderState({
      selectedProvider: 'youtube_search',
      providers: [
        provider({ id: 'nas_video', capabilities: ['import_local'] }),
        provider({
          id: 'youtube_search',
          label: 'YouTube search',
          capabilities: ['search'],
          status: 'not_configured',
          configured: false,
          available: false
        })
      ]
    });

    expect(state.isSelectedVideoDiscoveryProviderAvailable).toBe(false);
    expect(state.youtubeSearchUnavailableMessage).toContain('Configure the YouTube Data API key');
    expect(state.selectedVideoDiscoveryProviderUnavailableMessage).toBe(state.youtubeSearchUnavailableMessage);
  });

  it('filters candidates by provider-specific review requirements', () => {
    const response = discoveryResponse([
      candidate({ provider: 'youtube_search', source_url: 'https://youtube.com/watch?v=abc' }),
      candidate({ provider: 'youtube_search', source_url: ' ', metadata: { youtube_url: 'https://youtu.be/def' } }),
      candidate({ provider: 'youtube_search', source_url: null, metadata: {} }),
      candidate({ provider: 'newznab_torznab', requires_confirmation: true }),
      candidate({ provider: 'newznab_torznab', requires_confirmation: false }),
      candidate({ provider: 'manual_downloads', local_path: '/downloads/movie.mkv' }),
      candidate({ provider: 'manual_downloads', local_path: null })
    ]);

    const youtubeUrls = filterDiscoveredVideoCandidates(response, 'youtube_search').map((entry) => {
      const sourceUrl = entry.source_url?.trim();
      return sourceUrl || entry.metadata.youtube_url;
    });

    expect(youtubeUrls).toEqual(['https://youtube.com/watch?v=abc', 'https://youtu.be/def']);
    expect(filterDiscoveredVideoCandidates(response, 'newznab_torznab')).toHaveLength(1);
    expect(filterDiscoveredVideoCandidates(response, 'manual_downloads').map((entry) => entry.local_path)).toEqual([
      '/downloads/movie.mkv'
    ]);
  });
});
