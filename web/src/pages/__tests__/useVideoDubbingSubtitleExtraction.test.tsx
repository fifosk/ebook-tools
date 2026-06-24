import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  deleteNasSubtitle,
  extractInlineSubtitles,
  fetchInlineSubtitleStreams
} from '../../api/client';
import type { YoutubeNasVideo } from '../../api/dtos';
import { useVideoDubbingSubtitleExtraction } from '../video-dubbing/useVideoDubbingSubtitleExtraction';

vi.mock('../../api/client', () => ({
  deleteNasSubtitle: vi.fn(),
  extractInlineSubtitles: vi.fn(),
  fetchInlineSubtitleStreams: vi.fn()
}));

const mockDeleteNasSubtitle = vi.mocked(deleteNasSubtitle);
const mockExtractInlineSubtitles = vi.mocked(extractInlineSubtitles);
const mockFetchInlineSubtitleStreams = vi.mocked(fetchInlineSubtitleStreams);

const selectedVideo: YoutubeNasVideo = {
  path: '/nas/show/video.mkv',
  filename: 'video.mkv',
  folder: '/nas/show',
  size_bytes: 1024,
  modified_at: '2026-06-24T00:00:00Z',
  subtitles: [
    {
      path: '/nas/show/video.en.ass',
      filename: 'video.en.ass',
      language: 'en',
      format: 'ass'
    }
  ]
};

function renderExtractionHook(overrides: Partial<Parameters<typeof useVideoDubbingSubtitleExtraction>[0]> = {}) {
  const callbacks = {
    onRefresh: vi.fn().mockResolvedValue(undefined),
    onSelectedVideoPathChange: vi.fn(),
    onSelectedSubtitlePathChange: vi.fn(),
    onStatusMessageChange: vi.fn()
  };
  const result = renderHook((props: Parameters<typeof useVideoDubbingSubtitleExtraction>[0]) =>
    useVideoDubbingSubtitleExtraction(props),
    {
      initialProps: {
        selectedVideo,
        selectedSubtitlePath: selectedVideo.subtitles[0].path,
        ...callbacks,
        ...overrides
      }
    }
  );
  return { ...result, callbacks };
}

describe('useVideoDubbingSubtitleExtraction', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchInlineSubtitleStreams.mockResolvedValue({ video_path: selectedVideo.path, streams: [] });
    mockExtractInlineSubtitles.mockResolvedValue({ video_path: selectedVideo.path, extracted: [] });
    mockDeleteNasSubtitle.mockResolvedValue({
      video_path: selectedVideo.path,
      subtitle_path: selectedVideo.subtitles[0].path,
      removed: [],
      missing: []
    });
  });

  it('reports when inspected subtitle streams cannot be extracted', async () => {
    mockFetchInlineSubtitleStreams.mockResolvedValueOnce({
      video_path: selectedVideo.path,
      streams: [
        {
          index: 3,
          position: 0,
          language: 'en',
          codec: 'hdmv_pgs_subtitle',
          can_extract: false
        }
      ]
    });
    const { result } = renderExtractionHook();

    await act(async () => {
      await result.current.inspectSubtitleStreams();
    });

    expect(mockFetchInlineSubtitleStreams).toHaveBeenCalledWith(selectedVideo.path);
    expect(result.current.extractError).toBe(
      'No text-based subtitle streams were found. Image-based subtitle tracks cannot be extracted automatically.'
    );
    expect(result.current.availableSubtitleStreams).toHaveLength(1);
    expect(result.current.extractableStreams).toEqual([]);
    expect(mockExtractInlineSubtitles).not.toHaveBeenCalled();
  });

  it('auto-extracts a single text stream and refreshes the video list', async () => {
    mockFetchInlineSubtitleStreams.mockResolvedValueOnce({
      video_path: selectedVideo.path,
      streams: [
        {
          index: 2,
          position: 0,
          language: 'es',
          codec: 'subrip',
          can_extract: true
        }
      ]
    });
    mockExtractInlineSubtitles.mockResolvedValueOnce({
      video_path: selectedVideo.path,
      extracted: [
        {
          path: '/nas/show/video.es.srt',
          filename: 'video.es.srt',
          language: 'es',
          format: 'srt'
        }
      ]
    });
    const { callbacks, result } = renderExtractionHook();

    await act(async () => {
      await result.current.inspectSubtitleStreams();
    });

    expect(mockExtractInlineSubtitles).toHaveBeenCalledWith(selectedVideo.path, ['es']);
    expect(callbacks.onStatusMessageChange).toHaveBeenLastCalledWith('Extracted 1 subtitle track from video.mkv.');
    expect(callbacks.onRefresh).toHaveBeenCalledTimes(1);
    expect(callbacks.onSelectedVideoPathChange).toHaveBeenCalledWith(selectedVideo.path);
    expect(result.current.isExtractingSubtitles).toBe(false);
    expect(result.current.availableSubtitleStreams).toEqual([]);
  });

  it('lets the caller choose among multiple extractable streams', async () => {
    mockFetchInlineSubtitleStreams.mockResolvedValueOnce({
      video_path: selectedVideo.path,
      streams: [
        { index: 1, position: 0, language: 'en', codec: 'ass', can_extract: true },
        { index: 2, position: 1, language: 'es', codec: 'subrip', can_extract: true }
      ]
    });
    const { result } = renderExtractionHook();

    await act(async () => {
      await result.current.inspectSubtitleStreams();
    });

    expect(result.current.isChoosingStreams).toBe(true);
    expect(result.current.selectedStreamLanguages).toEqual(new Set(['en']));

    act(() => {
      result.current.toggleSubtitleStream('en', false);
      result.current.toggleSubtitleStream('es', true);
    });
    await act(async () => {
      await result.current.confirmSubtitleStreams();
    });

    expect(mockExtractInlineSubtitles).toHaveBeenCalledWith(selectedVideo.path, ['es']);
  });

  it('requires at least one selected stream when confirming multiple choices', async () => {
    mockFetchInlineSubtitleStreams.mockResolvedValueOnce({
      video_path: selectedVideo.path,
      streams: [
        { index: 1, position: 0, language: 'en', codec: 'ass', can_extract: true },
        { index: 2, position: 1, language: 'es', codec: 'subrip', can_extract: true }
      ]
    });
    const { result } = renderExtractionHook();

    await act(async () => {
      await result.current.inspectSubtitleStreams();
    });
    act(() => {
      result.current.toggleSubtitleStream('en', false);
      result.current.toggleSubtitleStream('es', false);
    });
    await act(async () => {
      await result.current.confirmSubtitleStreams();
    });

    expect(result.current.extractError).toBe('Select at least one subtitle language to extract.');
    expect(mockExtractInlineSubtitles).not.toHaveBeenCalled();
  });

  it('deletes a selected subtitle and clears the selected subtitle path', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const { callbacks, result } = renderExtractionHook();

    await act(async () => {
      await result.current.deleteSubtitle(selectedVideo.subtitles[0]);
    });

    expect(confirmSpy).toHaveBeenCalled();
    expect(mockDeleteNasSubtitle).toHaveBeenCalledWith(selectedVideo.path, selectedVideo.subtitles[0].path);
    expect(callbacks.onRefresh).toHaveBeenCalledTimes(1);
    expect(callbacks.onSelectedVideoPathChange).toHaveBeenCalledWith(selectedVideo.path);
    expect(callbacks.onSelectedSubtitlePathChange).toHaveBeenCalledWith(null);
    expect(callbacks.onStatusMessageChange).toHaveBeenLastCalledWith('Deleted video.en.ass');

    confirmSpy.mockRestore();
  });

  it('resets stream selection state when the selected video path changes', async () => {
    mockFetchInlineSubtitleStreams.mockResolvedValueOnce({
      video_path: selectedVideo.path,
      streams: [
        { index: 1, position: 0, language: 'en', codec: 'ass', can_extract: true },
        { index: 2, position: 1, language: 'es', codec: 'subrip', can_extract: true }
      ]
    });
    const { rerender, result } = renderExtractionHook();

    await act(async () => {
      await result.current.inspectSubtitleStreams();
    });
    expect(result.current.isChoosingStreams).toBe(true);

    rerender({
      selectedVideo: { ...selectedVideo, path: '/nas/show/next-video.mkv' },
      selectedSubtitlePath: null,
      onRefresh: vi.fn().mockResolvedValue(undefined),
      onSelectedVideoPathChange: vi.fn(),
      onSelectedSubtitlePathChange: vi.fn(),
      onStatusMessageChange: vi.fn()
    });

    await waitFor(() => expect(result.current.availableSubtitleStreams).toEqual([]));
    expect(result.current.selectedStreamLanguages).toEqual(new Set());
    expect(result.current.isChoosingStreams).toBe(false);
  });
});
