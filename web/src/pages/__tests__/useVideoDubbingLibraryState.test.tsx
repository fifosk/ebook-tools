import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  deleteYoutubeVideo,
  fetchYoutubeLibrary
} from '../../api/client';
import type {
  JobParameterSnapshot,
  YoutubeNasLibraryResponse,
  YoutubeNasVideo
} from '../../api/dtos';
import { useVideoDubbingLibraryState } from '../video-dubbing/useVideoDubbingLibraryState';

vi.mock('../../api/client', () => ({
  deleteYoutubeVideo: vi.fn(),
  fetchYoutubeLibrary: vi.fn()
}));

const mockDeleteYoutubeVideo = vi.mocked(deleteYoutubeVideo);
const mockFetchYoutubeLibrary = vi.mocked(fetchYoutubeLibrary);

function video(overrides: Partial<YoutubeNasVideo> = {}): YoutubeNasVideo {
  return {
    path: '/nas/videos/episode.mkv',
    filename: 'episode.mkv',
    folder: '/nas/videos',
    size_bytes: 1024,
    modified_at: '2026-06-24T00:00:00Z',
    subtitles: [],
    ...overrides
  };
}

function library(videos: YoutubeNasVideo[], baseDir = '/nas/videos'): YoutubeNasLibraryResponse {
  return {
    base_dir: baseDir,
    videos
  };
}

function renderLibraryHook(
  overrides: Partial<Parameters<typeof useVideoDubbingLibraryState>[0]> = {}
) {
  const callbacks = {
    onBaseDirChange: vi.fn(),
    onSelectedVideoPathChange: vi.fn(),
    onSelectedSubtitlePathChange: vi.fn(),
    onStatusMessageChange: vi.fn()
  };
  const selectedVideoPathRef = { current: '/nas/videos/current.mkv' };
  const selectedSubtitlePathRef = { current: '/nas/videos/current.en.ass' };

  const result = renderHook((props: Parameters<typeof useVideoDubbingLibraryState>[0]) =>
    useVideoDubbingLibraryState(props),
    {
      initialProps: {
        baseDir: '  /nas/videos  ',
        selectedVideoPath: selectedVideoPathRef.current,
        selectedSubtitlePath: selectedSubtitlePathRef.current,
        selectedVideoPathRef,
        selectedSubtitlePathRef,
        prefillParameters: null,
        ...callbacks,
        ...overrides
      }
    }
  );

  return { ...result, callbacks, selectedVideoPathRef, selectedSubtitlePathRef };
}

describe('useVideoDubbingLibraryState', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDeleteYoutubeVideo.mockResolvedValue({ video_path: '', removed: [], missing: [] });
    mockFetchYoutubeLibrary.mockResolvedValue(library([]));
  });

  it('refreshes NAS videos with trimmed base dir and applies prefill selection', async () => {
    const prefillParameters: JobParameterSnapshot = {
      input_file: '/nas/videos/prefilled.mkv',
      subtitle_path: '/nas/videos/prefilled.es.srt'
    };
    mockFetchYoutubeLibrary.mockResolvedValueOnce(
      library([
        video({
          path: '/nas/videos/current.mkv',
          subtitles: [
            { path: '/nas/videos/current.en.ass', filename: 'current.en.ass', language: 'en', format: 'ass' }
          ]
        }),
        video({
          path: '/nas/videos/prefilled.mkv',
          filename: 'prefilled.mkv',
          subtitles: [
            { path: '/nas/videos/prefilled.es.srt', filename: 'prefilled.es.srt', language: 'es', format: 'srt' }
          ]
        })
      ], '/nas/from-api')
    );
    const { callbacks, result } = renderLibraryHook({ prefillParameters });

    let resolvedLanguage: string | null | undefined;
    await act(async () => {
      resolvedLanguage = await result.current.refreshLibrary();
    });

    expect(mockFetchYoutubeLibrary).toHaveBeenCalledWith('/nas/videos');
    expect(callbacks.onStatusMessageChange).toHaveBeenCalledWith(null);
    expect(callbacks.onBaseDirChange).toHaveBeenCalledWith('/nas/from-api');
    expect(callbacks.onSelectedVideoPathChange).toHaveBeenCalledWith('/nas/videos/prefilled.mkv');
    expect(callbacks.onSelectedSubtitlePathChange).toHaveBeenCalledWith('/nas/videos/prefilled.es.srt');
    expect(resolvedLanguage).toBe('es');
    expect(result.current.library?.videos).toHaveLength(2);
    expect(result.current.isLoading).toBe(false);
  });

  it('clears selected media paths when the refreshed library is empty', async () => {
    mockFetchYoutubeLibrary.mockResolvedValueOnce(library([], ''));
    const { callbacks, result } = renderLibraryHook();

    let resolvedLanguage: string | null | undefined;
    await act(async () => {
      resolvedLanguage = await result.current.refreshLibrary();
    });

    expect(callbacks.onSelectedVideoPathChange).toHaveBeenCalledWith(null);
    expect(callbacks.onSelectedSubtitlePathChange).toHaveBeenCalledWith(null);
    expect(resolvedLanguage).toBeNull();
    expect(result.current.library?.videos).toEqual([]);
  });

  it('reports refresh failures and clears loading state', async () => {
    mockFetchYoutubeLibrary.mockRejectedValueOnce(new Error('NAS unavailable'));
    const { result } = renderLibraryHook();

    await act(async () => {
      await result.current.refreshLibrary();
    });

    expect(result.current.loadError).toBe('NAS unavailable');
    expect(result.current.isLoading).toBe(false);
  });

  it('does not delete videos linked to existing jobs or when confirmation is cancelled', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
    const blockedVideo = video({ linked_job_ids: ['job-1'] });
    const { result } = renderLibraryHook();

    await act(async () => {
      await result.current.deleteVideo(blockedVideo);
      await result.current.deleteVideo(video());
    });

    expect(confirmSpy).toHaveBeenCalledTimes(1);
    expect(mockDeleteYoutubeVideo).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it('deletes videos locally and returns the fallback subtitle language', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const deleted = video({
      path: '/nas/videos/current.mkv',
      subtitles: [
        { path: '/nas/videos/current.en.ass', filename: 'current.en.ass', language: 'en', format: 'ass' }
      ]
    });
    const fallback = video({
      path: '/nas/videos/next.mkv',
      filename: 'next.mkv',
      subtitles: [
        { path: '/nas/videos/next.fr.srt', filename: 'next.fr.srt', language: 'fr', format: 'srt' },
        { path: '/nas/videos/next.en.ass', filename: 'next.en.ass', language: 'en-US', format: 'ass' }
      ]
    });
    mockFetchYoutubeLibrary.mockResolvedValueOnce(library([deleted, fallback]));
    const { callbacks, result } = renderLibraryHook();

    await act(async () => {
      await result.current.refreshLibrary();
    });
    let resolvedLanguage: string | null | undefined;
    await act(async () => {
      resolvedLanguage = await result.current.deleteVideo(deleted);
    });

    expect(mockDeleteYoutubeVideo).toHaveBeenCalledWith({ video_path: '/nas/videos/current.mkv' });
    expect(callbacks.onSelectedVideoPathChange).toHaveBeenLastCalledWith('/nas/videos/next.mkv');
    expect(callbacks.onSelectedSubtitlePathChange).toHaveBeenLastCalledWith('/nas/videos/next.en.ass');
    expect(resolvedLanguage).toBe('en-US');
    expect(result.current.library?.videos.map((entry) => entry.path)).toEqual(['/nas/videos/next.mkv']);
    expect(result.current.deletingVideoPath).toBeNull();
    confirmSpy.mockRestore();
  });

  it('reports delete failures and clears deleting state', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    mockDeleteYoutubeVideo.mockRejectedValueOnce(new Error('delete failed'));
    const { result } = renderLibraryHook();

    await act(async () => {
      await result.current.deleteVideo(video());
    });

    await waitFor(() => expect(result.current.deletingVideoPath).toBeNull());
    expect(result.current.loadError).toBe('delete failed');
    confirmSpy.mockRestore();
  });
});
