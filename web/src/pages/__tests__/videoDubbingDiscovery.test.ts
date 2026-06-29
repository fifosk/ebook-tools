import { describe, expect, it } from 'vitest';
import type {
  AcquisitionCandidate,
  AcquisitionDiscoveryResponse,
  AcquisitionProvider
} from '../../api/dtos';
import {
  buildVideoDiscoveryProviderOptions,
  DEFAULT_VIDEO_DISCOVERY_PROVIDER,
  filterDiscoveredVideoCandidates,
  resolveDefaultVideoDiscoveryProvider,
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
      { id: 'youtube_url', label: 'YouTube URL', available: true },
      { id: 'youtube_search', label: 'YouTube search', available: true },
      { id: 'newznab_torznab', label: 'Indexers', available: true }
    ]);
  });

  it('keeps backend video providers in stable UI order and excludes acquire-only providers', () => {
    const options = buildVideoDiscoveryProviderOptions([
      provider({ id: 'download_station', label: 'Download Station', capabilities: ['acquire'] }),
      provider({ id: 'youtube_url', label: 'YouTube URL backend', capabilities: ['metadata'], discovery_media_kinds: ['video'] }),
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
      { id: 'youtube_url', label: 'YouTube URL', available: true },
      { id: 'youtube_search', label: 'YouTube search', available: true },
      { id: 'newznab_torznab', label: 'Indexers', available: true },
      { id: 'other_video', label: 'Other Video', available: true }
    ]);
  });

  it('uses backend default video provider ids before falling back to the local default order', () => {
    const options = buildVideoDiscoveryProviderOptions([
      provider({ id: 'manual_downloads', label: 'Manual backend', media_kinds: ['book', 'video'], capabilities: ['import_local'] }),
      provider({ id: 'youtube_search', label: 'YouTube backend', capabilities: ['search'] }),
      provider({ id: 'nas_video', label: 'NAS backend', capabilities: ['import_local'] })
    ]);

    expect(resolveDefaultVideoDiscoveryProvider({
      defaultProviderIds: { video: ['youtube_search', 'nas_video'] },
      options
    })).toBe('youtube_search');
    expect(resolveDefaultVideoDiscoveryProvider({
      defaultProviderIds: { video: ['missing_provider'] },
      options
    })).toBe('nas_video');
  });

  it('offers backend default sources when multiple available default providers are advertised', () => {
    const options = buildVideoDiscoveryProviderOptions(
      [
        provider({ id: 'manual_downloads', label: 'Manual backend', media_kinds: ['book', 'video'], capabilities: ['import_local'] }),
        provider({ id: 'newznab_torznab', label: 'Indexer backend', capabilities: ['search'] }),
        provider({ id: 'nas_video', label: 'NAS backend', capabilities: ['import_local'] })
      ],
      { video: ['nas_video', 'newznab_torznab'] }
    );

    expect(options[0]).toEqual({
      id: DEFAULT_VIDEO_DISCOVERY_PROVIDER,
      label: 'Default sources',
      available: true
    });
    expect(resolveDefaultVideoDiscoveryProvider({
      defaultProviderIds: { video: ['nas_video', 'newznab_torznab'] },
      options
    })).toBe(DEFAULT_VIDEO_DISCOVERY_PROVIDER);
  });

  it('does not let explicit YouTube URL handoff create backend default sources', () => {
    const options = buildVideoDiscoveryProviderOptions(
      [
        provider({
          id: 'youtube_url',
          label: 'YouTube URL backend',
          capabilities: ['metadata'],
          discovery_media_kinds: ['video'],
          default_eligible_media_kinds: []
        }),
        provider({
          id: 'nas_video',
          label: 'NAS backend',
          capabilities: ['import_local'],
          default_eligible_media_kinds: ['video']
        })
      ],
      { video: ['youtube_url', 'nas_video'] }
    );

    expect(options.map((entry) => entry.id)).toEqual(['nas_video', 'youtube_url']);
    expect(resolveDefaultVideoDiscoveryProvider({
      defaultProviderIds: { video: ['youtube_url', 'nas_video'] },
      options,
      providers: [
        provider({
          id: 'youtube_url',
          label: 'YouTube URL backend',
          capabilities: ['metadata'],
          discovery_media_kinds: ['video'],
          default_eligible_media_kinds: []
        }),
        provider({
          id: 'nas_video',
          label: 'NAS backend',
          capabilities: ['import_local'],
          default_eligible_media_kinds: ['video']
        })
      ]
    })).toBe('nas_video');
  });

  it('falls back to legacy explicit-only filtering when backend eligibility is absent', () => {
    const providers = [
      provider({ id: 'youtube_url', label: 'YouTube URL backend', capabilities: ['metadata'], discovery_media_kinds: ['video'] }),
      provider({ id: 'nas_video', label: 'NAS backend', capabilities: ['import_local'] })
    ];
    const options = buildVideoDiscoveryProviderOptions(providers, { video: ['youtube_url', 'nas_video'] });

    expect(options.map((entry) => entry.id)).toEqual(['nas_video', 'youtube_url']);
    expect(resolveDefaultVideoDiscoveryProvider({
      defaultProviderIds: { video: ['youtube_url', 'nas_video'] },
      options,
      providers
    })).toBe('nas_video');
  });

  it('uses backend default eligibility for non-legacy video providers', () => {
    const providers = [
      provider({
        id: 'partner_video',
        label: 'Partner Video',
        capabilities: ['search'],
        discovery_media_kinds: ['video'],
        default_eligible_media_kinds: []
      }),
      provider({
        id: 'nas_video',
        label: 'NAS backend',
        capabilities: ['import_local'],
        default_eligible_media_kinds: ['video']
      })
    ];
    const options = buildVideoDiscoveryProviderOptions(providers, { video: ['partner_video', 'nas_video'] });

    expect(options.map((entry) => entry.id)).toEqual(['nas_video', 'partner_video']);
    expect(resolveDefaultVideoDiscoveryProvider({
      defaultProviderIds: { video: ['partner_video', 'nas_video'] },
      options,
      providers
    })).toBe('nas_video');
  });

  it('skips unavailable backend default video providers when another default is available', () => {
    const options = buildVideoDiscoveryProviderOptions([
      provider({ id: 'manual_downloads', label: 'Manual backend', media_kinds: ['book', 'video'], capabilities: ['import_local'] }),
      provider({ id: 'youtube_search', label: 'YouTube backend', capabilities: ['search'] }),
      provider({ id: 'nas_video', label: 'NAS backend', capabilities: ['import_local'], status: 'not_configured', available: false })
    ]);

    expect(resolveDefaultVideoDiscoveryProvider({
      defaultProviderIds: { video: ['nas_video', 'manual_downloads', 'youtube_search'] },
      options
    })).toBe('manual_downloads');
  });

  it('prefers backend discovery media kind declarations over capability guesses', () => {
    const options = buildVideoDiscoveryProviderOptions([
      provider({
        id: 'search_not_discoverable',
        label: 'Search only metadata',
        capabilities: ['search'],
        discovery_media_kinds: []
      }),
      provider({
        id: 'metadata_video_discovery',
        label: 'Metadata Video Discovery',
        capabilities: ['metadata'],
        discovery_media_kinds: ['video']
      })
    ]);

    expect(options).toEqual([
      { id: 'metadata_video_discovery', label: 'Metadata Video Discovery', available: true }
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

  it('uses backend source labels for unavailable video source providers', () => {
    const state = resolveVideoDiscoveryProviderState({
      selectedProvider: 'nas_video',
      providers: [
        provider({
          id: 'nas_video',
          label: 'NAS video library',
          capabilities: ['import_local'],
          status: 'not_configured',
          configured: true,
          available: false,
          source_label: 'NAS video root'
        })
      ]
    });

    expect(state.isSelectedVideoDiscoveryProviderAvailable).toBe(false);
    expect(state.selectedVideoDiscoveryProviderUnavailableMessage).toBe(
      'NAS video library is not configured. Configure nas video root or choose another discovery source.'
    );
  });

  it('resolves default-provider availability from available backend defaults', () => {
    const state = resolveVideoDiscoveryProviderState({
      selectedProvider: DEFAULT_VIDEO_DISCOVERY_PROVIDER,
      defaultProviderIds: { video: ['nas_video', 'newznab_torznab'] },
      providers: [
        provider({ id: 'nas_video', capabilities: ['import_local'] }),
        provider({ id: 'newznab_torznab', label: 'Indexer backend', capabilities: ['search'] })
      ]
    });

    expect(state.videoDiscoveryProviderOptions[0].id).toBe(DEFAULT_VIDEO_DISCOVERY_PROVIDER);
    expect(state.isSelectedVideoDiscoveryProviderAvailable).toBe(true);
    expect(state.selectedVideoDiscoveryProviderUnavailableMessage).toBeNull();
  });

  it('filters candidates by provider-specific review requirements', () => {
    const response = discoveryResponse([
      candidate({ provider: 'youtube_search', source_url: 'https://youtube.com/watch?v=abc' }),
      candidate({ provider: 'youtube_search', source_url: ' ', metadata: { youtube_url: 'https://youtu.be/def' } }),
      candidate({ provider: 'youtube_search', source_url: null, metadata: {} }),
      candidate({ provider: 'youtube_url', source_url: null, metadata: { youtube_url: 'https://youtu.be/url' } }),
      candidate({ provider: 'youtube_url', source_url: null, metadata: {} }),
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
    expect(
      filterDiscoveredVideoCandidates(response, 'youtube_url').map((entry) => entry.metadata.youtube_url)
    ).toEqual(['https://youtu.be/url']);
    expect(filterDiscoveredVideoCandidates(response, 'newznab_torznab')).toHaveLength(1);
    expect(
      filterDiscoveredVideoCandidates(
        {
          ...response,
          providers_queried: ['nas_video', 'newznab_torznab', 'youtube_url']
        },
        DEFAULT_VIDEO_DISCOVERY_PROVIDER
      ).map((entry) => entry.provider)
    ).toEqual(['newznab_torznab']);
    expect(filterDiscoveredVideoCandidates(response, 'manual_downloads').map((entry) => entry.local_path)).toEqual([
      '/downloads/movie.mkv'
    ]);
  });
});
