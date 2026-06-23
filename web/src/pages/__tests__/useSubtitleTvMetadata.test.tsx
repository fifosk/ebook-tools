import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { lookupSubtitleTvMetadataPreview } from '../../api/client';
import { useSubtitleTvMetadata } from '../subtitle-tool/useSubtitleTvMetadata';

vi.mock('../../api/client', () => ({
  lookupSubtitleTvMetadataPreview: vi.fn()
}));

const mockLookupSubtitleTvMetadataPreview = vi.mocked(lookupSubtitleTvMetadataPreview);

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}

describe('useSubtitleTvMetadata', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLookupSubtitleTvMetadataPreview.mockResolvedValue({
      source_name: 'Show.S01E02.srt',
      parsed: null,
      media_metadata: { tv: { title: 'Show', season: 1, episode: 2 } }
    });
  });

  it('looks up metadata for the resolved source name and seeds the editable draft', async () => {
    const { result } = renderHook(({ sourceName }) => useSubtitleTvMetadata(sourceName), {
      initialProps: { sourceName: '  Show.S01E02.srt  ' }
    });

    await waitFor(() => expect(result.current.metadataPreview?.source_name).toBe('Show.S01E02.srt'));

    expect(mockLookupSubtitleTvMetadataPreview).toHaveBeenCalledWith({
      source_name: 'Show.S01E02.srt',
      force: false
    });
    expect(result.current.metadataLookupSourceName).toBe('Show.S01E02.srt');
    expect(result.current.mediaMetadataDraft).toEqual({
      tv: { title: 'Show', season: 1, episode: 2 }
    });
  });

  it('clears preview state when the source name becomes blank', async () => {
    const { result, rerender } = renderHook(({ sourceName }) => useSubtitleTvMetadata(sourceName), {
      initialProps: { sourceName: 'Show.S01E02.srt' }
    });

    await waitFor(() => expect(result.current.metadataPreview).not.toBeNull());

    rerender({ sourceName: '   ' });

    await waitFor(() => expect(result.current.metadataPreview).toBeNull());
    expect(result.current.metadataLookupSourceName).toBe('');
    expect(result.current.mediaMetadataDraft).toBeNull();
    expect(result.current.metadataError).toBeNull();
  });

  it('keeps the latest lookup when an older request resolves last', async () => {
    const first = deferred<Awaited<ReturnType<typeof lookupSubtitleTvMetadataPreview>>>();
    const second = deferred<Awaited<ReturnType<typeof lookupSubtitleTvMetadataPreview>>>();
    mockLookupSubtitleTvMetadataPreview
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);

    const { result, rerender } = renderHook(({ sourceName }) => useSubtitleTvMetadata(sourceName), {
      initialProps: { sourceName: 'old.srt' }
    });
    rerender({ sourceName: 'new.srt' });

    await act(async () => {
      second.resolve({
        source_name: 'new.srt',
        parsed: null,
        media_metadata: { tv: { title: 'New' } }
      });
    });
    await waitFor(() => expect(result.current.metadataPreview?.source_name).toBe('new.srt'));

    await act(async () => {
      first.resolve({
        source_name: 'old.srt',
        parsed: null,
        media_metadata: { tv: { title: 'Old' } }
      });
    });

    expect(result.current.metadataPreview?.source_name).toBe('new.srt');
    expect(result.current.mediaMetadataDraft).toEqual({ tv: { title: 'New' } });
  });

  it('updates and clears editable draft metadata without replacing unrelated sections', async () => {
    const { result } = renderHook(({ sourceName }) => useSubtitleTvMetadata(sourceName), {
      initialProps: { sourceName: 'Show.S01E02.srt' }
    });

    await waitFor(() => expect(result.current.mediaMetadataDraft).not.toBeNull());

    act(() => {
      result.current.updateMediaMetadataSection('tv', (section) => {
        section['title'] = 'Edited';
      });
      result.current.updateMediaMetadataDraft((draft) => {
        draft['custom'] = { reviewed: true };
      });
    });

    expect(result.current.mediaMetadataDraft).toEqual({
      tv: { title: 'Edited', season: 1, episode: 2 },
      custom: { reviewed: true }
    });

    act(() => {
      result.current.handleMetadataClear();
    });

    expect(result.current.metadataPreview).toBeNull();
    expect(result.current.mediaMetadataDraft).toBeNull();
    expect(result.current.metadataError).toBeNull();
  });
});
