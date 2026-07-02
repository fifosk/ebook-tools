import { describe, expect, it } from 'vitest';
import type {
  AcquisitionCandidate,
  AcquisitionProvider,
  YoutubeNasVideo,
  YoutubeSubtitleTrack
} from '../../api/dtos';
import {
  describeFormat,
  findProvider,
  formatBytes,
  formatDiscoveryCandidateMeta,
  isYoutubeSource,
  resolveDefaultTrack,
  subtitleBadgeLabel,
  trackKey,
  videoSourceBadge
} from '../youtube-video/youtubeVideoPageUtils';

function track(
  language: string,
  kind: YoutubeSubtitleTrack['kind'],
  overrides: Partial<YoutubeSubtitleTrack> = {}
): YoutubeSubtitleTrack {
  return {
    language,
    kind,
    name: language,
    formats: ['srt'],
    ...overrides
  };
}

function video(overrides: Partial<YoutubeNasVideo> = {}): YoutubeNasVideo {
  return {
    filename: 'demo.mp4',
    path: '/videos/demo.mp4',
    folder: '/videos',
    size_bytes: 1024,
    modified_at: '2026-07-02T10:00:00Z',
    subtitles: [],
    source: 'youtube',
    ...overrides
  } as YoutubeNasVideo;
}

function provider(id: string, overrides: Partial<AcquisitionProvider> = {}): AcquisitionProvider {
  return {
    id,
    label: id,
    media_kinds: ['video'],
    capabilities: ['search'],
    status: 'available',
    configured: true,
    available: true,
    rights: ['unknown'],
    policy_notes: [],
    next_actions: [],
    ...overrides
  };
}

function candidate(overrides: Partial<AcquisitionCandidate> = {}): AcquisitionCandidate {
  return {
    candidate_id: 'youtube_search:demo',
    provider: 'youtube_search',
    media_kind: 'video',
    title: 'Demo upload',
    rights: 'unknown',
    capabilities: ['metadata'],
    candidate_token: 'candidate-token',
    contributors: [],
    subtitles: [],
    metadata: {},
    requires_confirmation: false,
    policy_notes: [],
    ...overrides
  } as AcquisitionCandidate;
}

describe('youtubeVideoPageUtils', () => {
  it('prefers manual English subtitles, then any English subtitle, then the first manual track', () => {
    const spanishManual = track('es', 'manual');
    const englishAuto = track('en-US', 'auto');
    const englishManual = track('en', 'manual');

    expect(resolveDefaultTrack([spanishManual, englishAuto, englishManual])).toBe(englishManual);
    expect(resolveDefaultTrack([spanishManual, englishAuto])).toBe(englishAuto);
    expect(resolveDefaultTrack([track('fr', 'auto'), spanishManual])).toBe(spanishManual);
    expect(resolveDefaultTrack([])).toBeNull();
  });

  it('formats tracks, video quality, and byte labels used by the download picker', () => {
    expect(trackKey(track('en', 'manual'))).toBe('en__manual');
    expect(
      describeFormat({
        format_id: '22',
        ext: 'mp4',
        resolution: '720p',
        fps: 30,
        note: 'best',
        bitrate_kbps: 192.4,
        filesize: '12 MiB'
      })
    ).toBe('mp4 • 720p • 30 fps • best • 192 kbps • 12 MiB • itag 22');
    expect(formatBytes(null)).toBe('—');
    expect(formatBytes(512)).toBe('512 B');
    expect(formatBytes(1536)).toBe('1.5 KB');
    expect(formatBytes(10 * 1024 * 1024)).toBe('10 MB');
  });

  it('keeps YouTube download badges and provider lookup token-safe', () => {
    expect(isYoutubeSource(video({ source: 'YouTube' }))).toBe(true);
    expect(isYoutubeSource(video({ source: 'nas' }))).toBe(false);
    expect(videoSourceBadge(video({ source: 'youtube' }))).toMatchObject({
      label: 'YT',
      title: 'YouTube download'
    });
    expect(videoSourceBadge(video({ source: 'nas' }))).toMatchObject({
      label: 'NAS',
      title: 'NAS video'
    });
    expect(findProvider([provider('manual_downloads'), provider('youtube_search')], 'youtube_search')?.id).toBe(
      'youtube_search'
    );
    expect(findProvider([provider('manual_downloads')], 'youtube_search')).toBeNull();
  });

  it('formats subtitle and discovery metadata summaries for review before download', () => {
    expect(
      subtitleBadgeLabel({
        language: 'es',
        format: 'srt',
        filename: 'demo.es.srt',
        path: '/subs/demo.es.srt'
      })
    ).toBe('Spanish SRT');

    expect(
      formatDiscoveryCandidateMeta(
        candidate({
          contributors: ['Demo Channel'],
          duration_seconds: 125,
          source_url: 'https://youtu.be/demo',
          requires_confirmation: true
        })
      )
    ).toBe('Demo Channel · 2:05 · https://youtu.be/demo · review required');
    expect(formatDiscoveryCandidateMeta(candidate())).toBe('YouTube search result');
  });
});
