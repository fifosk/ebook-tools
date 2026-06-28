import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { YoutubeNasVideo } from '../../api/dtos';
import { useVideoDubbingLibraryActions } from '../video-dubbing/useVideoDubbingLibraryActions';

function video(overrides: Partial<YoutubeNasVideo> = {}): YoutubeNasVideo {
  return {
    path: '/nas/videos/example.mkv',
    filename: 'example.mkv',
    folder: '/nas/videos',
    size_bytes: 1024,
    modified_at: '2026-06-28T00:00:00Z',
    subtitles: [],
    ...overrides
  };
}

describe('useVideoDubbingLibraryActions', () => {
  it('refreshes the library and applies the resolved target language', async () => {
    const refreshLibrary = vi.fn().mockResolvedValue('nl');
    const deleteVideo = vi.fn();
    const ensureTargetLanguage = vi.fn();

    const { result } = renderHook(() =>
      useVideoDubbingLibraryActions({
        refreshLibrary,
        deleteVideo,
        ensureTargetLanguage
      })
    );

    await act(async () => {
      await result.current.handleRefresh();
    });

    expect(refreshLibrary).toHaveBeenCalledOnce();
    expect(ensureTargetLanguage).toHaveBeenCalledWith('nl');
    expect(deleteVideo).not.toHaveBeenCalled();
  });

  it('deletes a video and applies the fallback target language', async () => {
    const target = video({ path: '/nas/videos/remove.mkv' });
    const refreshLibrary = vi.fn();
    const deleteVideo = vi.fn().mockResolvedValue(null);
    const ensureTargetLanguage = vi.fn();

    const { result } = renderHook(() =>
      useVideoDubbingLibraryActions({
        refreshLibrary,
        deleteVideo,
        ensureTargetLanguage
      })
    );

    await act(async () => {
      await result.current.handleDeleteVideo(target);
    });

    expect(deleteVideo).toHaveBeenCalledWith(target);
    expect(ensureTargetLanguage).toHaveBeenCalledWith(null);
    expect(refreshLibrary).not.toHaveBeenCalled();
  });
});
