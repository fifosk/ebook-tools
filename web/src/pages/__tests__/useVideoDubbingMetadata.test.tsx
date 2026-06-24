import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  clearTvMetadataCache,
  clearYoutubeMetadataCache,
  lookupSubtitleTvMetadataPreview,
  lookupYoutubeVideoMetadataPreview
} from '../../api/client';
import type { VideoDubbingTab } from '../video-dubbing/videoDubbingTypes';
import { useVideoDubbingMetadata } from '../video-dubbing/useVideoDubbingMetadata';

vi.mock('../../api/client', () => ({
  clearTvMetadataCache: vi.fn(),
  clearYoutubeMetadataCache: vi.fn(),
  lookupSubtitleTvMetadataPreview: vi.fn(),
  lookupYoutubeVideoMetadataPreview: vi.fn()
}));

const mockLookupSubtitleTvMetadataPreview = vi.mocked(lookupSubtitleTvMetadataPreview);
const mockLookupYoutubeVideoMetadataPreview = vi.mocked(lookupYoutubeVideoMetadataPreview);
const mockClearTvMetadataCache = vi.mocked(clearTvMetadataCache);
const mockClearYoutubeMetadataCache = vi.mocked(clearYoutubeMetadataCache);

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}

describe('useVideoDubbingMetadata', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLookupSubtitleTvMetadataPreview.mockResolvedValue({
      source_name: 'Show.S01E02.mkv',
      parsed: null,
      media_metadata: { show: { name: 'Show' }, episode: { season: 1, number: 2 } }
    });
    mockLookupYoutubeVideoMetadataPreview.mockResolvedValue({
      source_name: 'Show.S01E02.mkv',
      parsed: null,
      youtube_metadata: { title: 'Episode upload', channel: 'Archive' }
    });
    mockClearTvMetadataCache.mockResolvedValue({ cleared: 1 });
    mockClearYoutubeMetadataCache.mockResolvedValue({ cleared: 1 });
  });

  it('looks up TV metadata for the selected NAS source and seeds the draft', async () => {
    const { result } = renderHook(({ sourceName }) =>
      useVideoDubbingMetadata({ activeTab: 'videos', metadataSourceName: sourceName }), {
        initialProps: { sourceName: '  Show.S01E02.mkv  ' }
      }
    );

    await waitFor(() => expect(result.current.metadataPreview?.source_name).toBe('Show.S01E02.mkv'));

    expect(mockLookupSubtitleTvMetadataPreview).toHaveBeenCalledWith({
      source_name: 'Show.S01E02.mkv',
      force: false
    });
    expect(result.current.metadataLookupSourceName).toBe('Show.S01E02.mkv');
    expect(result.current.youtubeLookupSourceName).toBe('Show.S01E02.mkv');
    expect(result.current.mediaMetadataDraft).toEqual({
      show: { name: 'Show' },
      episode: { season: 1, number: 2 }
    });
  });

  it('keeps the newest TV lookup when an older request resolves last', async () => {
    const first = deferred<Awaited<ReturnType<typeof lookupSubtitleTvMetadataPreview>>>();
    const second = deferred<Awaited<ReturnType<typeof lookupSubtitleTvMetadataPreview>>>();
    mockLookupSubtitleTvMetadataPreview
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);

    const { result, rerender } = renderHook(({ sourceName }) =>
      useVideoDubbingMetadata({ activeTab: 'videos', metadataSourceName: sourceName }), {
        initialProps: { sourceName: 'old.mkv' }
      }
    );
    rerender({ sourceName: 'new.mkv' });

    await act(async () => {
      second.resolve({
        source_name: 'new.mkv',
        parsed: null,
        media_metadata: { show: { name: 'New' } }
      });
    });
    await waitFor(() => expect(result.current.metadataPreview?.source_name).toBe('new.mkv'));

    await act(async () => {
      first.resolve({
        source_name: 'old.mkv',
        parsed: null,
        media_metadata: { show: { name: 'Old' } }
      });
    });

    expect(result.current.metadataPreview?.source_name).toBe('new.mkv');
    expect(result.current.mediaMetadataDraft).toEqual({ show: { name: 'New' } });
  });

  it('loads YouTube metadata when the metadata tab switches to YouTube and preserves it across manual TV refreshes', async () => {
    const { result } = renderHook(() =>
      useVideoDubbingMetadata({ activeTab: 'metadata', metadataSourceName: 'Show.S01E02.mkv' })
    );

    await waitFor(() => expect(result.current.mediaMetadataDraft).toEqual({
      show: { name: 'Show' },
      episode: { season: 1, number: 2 }
    }));

    act(() => {
      result.current.setMetadataSection('youtube');
    });

    await waitFor(() => expect(result.current.youtubeMetadataPreview?.source_name).toBe('Show.S01E02.mkv'));
    expect(result.current.mediaMetadataDraft).toEqual({
      show: { name: 'Show' },
      episode: { season: 1, number: 2 },
      youtube: { title: 'Episode upload', channel: 'Archive' }
    });

    mockLookupSubtitleTvMetadataPreview.mockResolvedValueOnce({
      source_name: 'Show.S01E02.mkv',
      parsed: null,
      media_metadata: { show: { name: 'Show refreshed' } }
    });

    await act(async () => {
      await result.current.performMetadataLookup('Show.S01E02.mkv', true);
    });

    expect(result.current.mediaMetadataDraft).toEqual({
      show: { name: 'Show refreshed' },
      youtube: { title: 'Episode upload', channel: 'Archive' }
    });
  });

  it('clears stale YouTube metadata when the selected source changes', async () => {
    const { result, rerender } = renderHook(({ activeTab, sourceName }) =>
      useVideoDubbingMetadata({ activeTab, metadataSourceName: sourceName }), {
        initialProps: { activeTab: 'metadata' as VideoDubbingTab, sourceName: 'old.mkv' }
      }
    );

    await waitFor(() => expect(result.current.metadataPreview?.source_name).toBe('Show.S01E02.mkv'));
    act(() => {
      result.current.setMetadataSection('youtube');
    });
    await waitFor(() => expect(result.current.mediaMetadataDraft?.['youtube']).toEqual({
      title: 'Episode upload',
      channel: 'Archive'
    }));

    mockLookupSubtitleTvMetadataPreview.mockResolvedValueOnce({
      source_name: 'new.mkv',
      parsed: null,
      media_metadata: { show: { name: 'New source' } }
    });
    rerender({ activeTab: 'videos', sourceName: 'new.mkv' });

    await waitFor(() => expect(result.current.metadataPreview?.source_name).toBe('new.mkv'));
    expect(result.current.mediaMetadataDraft).toEqual({ show: { name: 'New source' } });
  });

  it('clears frontend metadata and backend caches using the matching lookup names', async () => {
    const { result } = renderHook(() =>
      useVideoDubbingMetadata({ activeTab: 'metadata', metadataSourceName: 'Show.S01E02.mkv' })
    );

    await waitFor(() => expect(result.current.metadataPreview).not.toBeNull());
    act(() => {
      result.current.setYoutubeLookupSourceName('youtube-id [abc123]');
    });

    await act(async () => {
      await result.current.handleClearYoutubeMetadata();
      await result.current.handleClearTvMetadata();
    });

    expect(mockClearYoutubeMetadataCache).toHaveBeenCalledWith('youtube-id [abc123]');
    expect(mockClearTvMetadataCache).toHaveBeenCalledWith('Show.S01E02.mkv');
    expect(result.current.youtubeMetadataPreview).toBeNull();
    expect(result.current.metadataPreview).toBeNull();
    expect(result.current.mediaMetadataDraft).toBeNull();
  });
});
