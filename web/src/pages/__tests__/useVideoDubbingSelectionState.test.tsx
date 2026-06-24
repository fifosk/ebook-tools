import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { VIDEO_DUB_STORAGE_KEYS } from '../video-dubbing/videoDubbingConfig';
import { useVideoDubbingSelectionState } from '../video-dubbing/useVideoDubbingSelectionState';

describe('useVideoDubbingSelectionState', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('restores the last NAS base dir and selected media paths', () => {
    window.localStorage.setItem(
      VIDEO_DUB_STORAGE_KEYS.baseDir,
      '  /Volumes/Data/Download/DStation  '
    );
    window.localStorage.setItem(
      VIDEO_DUB_STORAGE_KEYS.selectedVideoPath,
      '  /Volumes/Data/Download/DStation/book-video.mkv  '
    );
    window.localStorage.setItem(
      VIDEO_DUB_STORAGE_KEYS.selectedSubtitlePath,
      '  /Volumes/Data/Download/DStation/book-video.en.srt  '
    );

    const { result } = renderHook(() => useVideoDubbingSelectionState());

    expect(result.current.baseDir).toBe('/Volumes/Data/Download/DStation');
    expect(result.current.selectedVideoPath).toBe('/Volumes/Data/Download/DStation/book-video.mkv');
    expect(result.current.selectedVideoPathRef.current).toBe('/Volumes/Data/Download/DStation/book-video.mkv');
    expect(result.current.selectedSubtitlePath).toBe('/Volumes/Data/Download/DStation/book-video.en.srt');
    expect(result.current.selectedSubtitlePathRef.current).toBe(
      '/Volumes/Data/Download/DStation/book-video.en.srt'
    );
  });

  it('persists trimmed selection changes for the next visit', async () => {
    const { result } = renderHook(() => useVideoDubbingSelectionState());

    act(() => {
      result.current.setBaseDir('  /nas/videos  ');
      result.current.setSelectedVideoPath('  /nas/videos/dan-brown.mkv  ');
      result.current.setSelectedSubtitlePath('  /nas/videos/dan-brown.en.ass  ');
    });

    await waitFor(() => {
      expect(window.localStorage.getItem(VIDEO_DUB_STORAGE_KEYS.baseDir)).toBe('/nas/videos');
      expect(window.localStorage.getItem(VIDEO_DUB_STORAGE_KEYS.selectedVideoPath)).toBe(
        '/nas/videos/dan-brown.mkv'
      );
      expect(window.localStorage.getItem(VIDEO_DUB_STORAGE_KEYS.selectedSubtitlePath)).toBe(
        '/nas/videos/dan-brown.en.ass'
      );
    });
    expect(result.current.selectedVideoPathRef.current).toBe('/nas/videos/dan-brown.mkv');
    expect(result.current.selectedSubtitlePathRef.current).toBe('/nas/videos/dan-brown.en.ass');
  });

  it('clears stored selections when values are emptied', async () => {
    window.localStorage.setItem(VIDEO_DUB_STORAGE_KEYS.baseDir, '/nas/videos');
    window.localStorage.setItem(VIDEO_DUB_STORAGE_KEYS.selectedVideoPath, '/nas/videos/movie.mkv');
    window.localStorage.setItem(VIDEO_DUB_STORAGE_KEYS.selectedSubtitlePath, '/nas/videos/movie.en.srt');

    const { result } = renderHook(() => useVideoDubbingSelectionState());

    act(() => {
      result.current.setBaseDir('   ');
      result.current.setSelectedVideoPath(null);
      result.current.setSelectedSubtitlePath('');
    });

    await waitFor(() => {
      expect(window.localStorage.getItem(VIDEO_DUB_STORAGE_KEYS.baseDir)).toBeNull();
      expect(window.localStorage.getItem(VIDEO_DUB_STORAGE_KEYS.selectedVideoPath)).toBeNull();
      expect(window.localStorage.getItem(VIDEO_DUB_STORAGE_KEYS.selectedSubtitlePath)).toBeNull();
    });
    expect(result.current.selectedVideoPathRef.current).toBeNull();
    expect(result.current.selectedSubtitlePathRef.current).toBeNull();
  });
});
