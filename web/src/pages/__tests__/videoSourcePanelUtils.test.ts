import { describe, expect, it } from 'vitest';
import type { AcquisitionCandidate } from '../../api/dtos';
import { DEFAULT_VIDEO_DISCOVERY_PROVIDER } from '../video-dubbing/videoDubbingDiscovery';
import {
  filenameFromPath,
  formatDiscoveryCandidateMeta,
  resolveDiscoveryHint,
  resolveDiscoveryPlaceholder
} from '../video-dubbing/videoSourcePanelUtils';

function candidate(overrides: Partial<AcquisitionCandidate> = {}): AcquisitionCandidate {
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

describe('videoSourcePanelUtils', () => {
  it('resolves discovery placeholders and hints for Web/Apple provider parity', () => {
    expect(resolveDiscoveryPlaceholder(DEFAULT_VIDEO_DISCOVERY_PROVIDER)).toBe('Search default video sources');
    expect(resolveDiscoveryPlaceholder('youtube_url')).toBe('Paste a YouTube video URL or ID');
    expect(resolveDiscoveryPlaceholder('youtube_search')).toBe('Search YouTube videos by title or channel');
    expect(resolveDiscoveryPlaceholder('newznab_torznab')).toBe('Search configured indexers');
    expect(resolveDiscoveryPlaceholder('nas_video')).toBe('Search title or filename');

    expect(resolveDiscoveryHint(DEFAULT_VIDEO_DISCOVERY_PROVIDER)).toContain('backend-owned default video sources');
    expect(resolveDiscoveryHint('manual_downloads')).toContain('manual download video inboxes');
    expect(resolveDiscoveryHint('newznab_torznab')).toContain('lawful access');
  });

  it('extracts filenames from POSIX, Windows, and trimmed paths', () => {
    expect(filenameFromPath(' /videos/show.mkv ')).toBe('show.mkv');
    expect(filenameFromPath('C:\\Videos\\show.srt')).toBe('show.srt');
    expect(filenameFromPath('folder/')).toBe('folder');
  });

  it('formats YouTube metadata candidates with channel, duration, URL, subtitles, and review flags', () => {
    expect(
      formatDiscoveryCandidateMeta(candidate({
        provider: 'youtube_search',
        contributors: ['Demo Channel'],
        duration_seconds: 125,
        source_url: 'https://youtu.be/demo',
        subtitles: [{ language: 'en', format: 'srt', filename: 'demo.en.srt', path: '/subs/demo.en.srt' }],
        requires_confirmation: true
      }))
    ).toBe('YouTube metadata · Demo Channel · 2:05 · https://youtu.be/demo · 1 subtitle · review required');
  });

  it('formats indexer metadata and Download Station handoff affordance', () => {
    expect(
      formatDiscoveryCandidateMeta(candidate({
        provider: 'newznab_torznab',
        contributors: ['Indexer A'],
        size_bytes: 1_048_576,
        metadata: {
          seeders: 12,
          peers: 4,
          handoff_provider: 'download_station'
        }
      }))
    ).toBe('Indexer metadata · Indexer A · 1.0 MiB · 12 seeders · 4 peers · Download Station handoff');
  });

  it('falls back to local path or provider id for non-remote candidates', () => {
    expect(formatDiscoveryCandidateMeta(candidate({ local_path: '/manual/video.mkv' }))).toBe('/manual/video.mkv');
    expect(formatDiscoveryCandidateMeta(candidate({ provider: 'manual_downloads' }))).toBe('manual_downloads');
  });
});
