import { renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { YoutubeNasSubtitle, YoutubeNasVideo } from '../../api/dtos';
import { useVideoDubbingResolvedSelection } from '../video-dubbing/useVideoDubbingResolvedSelection';

function subtitle(overrides: Partial<YoutubeNasSubtitle>): YoutubeNasSubtitle {
  return {
    path: '/subs/example.ass',
    filename: 'example.ass',
    language: 'en',
    format: 'ass',
    ...overrides
  };
}

function video(overrides: Partial<YoutubeNasVideo>): YoutubeNasVideo {
  return {
    path: '/videos/example.mkv',
    filename: 'example.mkv',
    folder: '/videos',
    size_bytes: 100,
    modified_at: '2026-06-23T00:00:00Z',
    subtitles: [],
    ...overrides
  };
}

describe('useVideoDubbingResolvedSelection', () => {
  it('resolves selected video, playable subtitles, and subtitle language metadata', () => {
    const dutch = subtitle({
      path: '/subs/show.nl.srt',
      filename: 'show.nl.srt',
      language: 'nl',
      format: 'srt'
    });
    const metadataOnly = subtitle({
      path: '',
      filename: 'show.meta',
      language: 'tr',
      format: 'json'
    });
    const selected = video({
      path: '/videos/show.mkv',
      subtitles: [metadataOnly, dutch]
    });

    const { result } = renderHook(() =>
      useVideoDubbingResolvedSelection({
        videos: [video({ path: '/videos/other.mkv' }), selected],
        selectedVideoPath: selected.path,
        selectedSubtitlePath: dutch.path
      })
    );

    expect(result.current.selectedVideo).toBe(selected);
    expect(result.current.playableSubtitles).toEqual([dutch]);
    expect(result.current.selectedSubtitle).toBe(dutch);
    expect(result.current.subtitleLanguageLabel).toBe('Dutch');
    expect(result.current.subtitleLanguageCode).toBe('nl');
  });

  it('returns empty selection details when stored paths no longer match the NAS listing', () => {
    const { result } = renderHook(() =>
      useVideoDubbingResolvedSelection({
        videos: [video({ path: '/videos/current.mkv' })],
        selectedVideoPath: '/videos/missing.mkv',
        selectedSubtitlePath: '/subs/missing.en.srt'
      })
    );

    expect(result.current.selectedVideo).toBeNull();
    expect(result.current.playableSubtitles).toEqual([]);
    expect(result.current.selectedSubtitle).toBeNull();
    expect(result.current.subtitleLanguageLabel).toBe('');
    expect(result.current.subtitleLanguageCode).toBe('');
  });
});
