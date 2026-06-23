import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { deleteSubtitleSource, fetchSubtitleSources } from '../../api/client';
import type { SubtitleSourceEntry } from '../../api/dtos';
import { useSubtitleSources } from '../subtitle-tool/useSubtitleSources';

vi.mock('../../api/client', () => ({
  deleteSubtitleSource: vi.fn(),
  fetchSubtitleSources: vi.fn()
}));

const mockDeleteSubtitleSource = vi.mocked(deleteSubtitleSource);
const mockFetchSubtitleSources = vi.mocked(fetchSubtitleSources);

function source(overrides: Partial<SubtitleSourceEntry>): SubtitleSourceEntry {
  return {
    name: overrides.name ?? overrides.path ?? 'source.srt',
    path: overrides.path ?? '/media/source.srt',
    format: overrides.format ?? 'srt',
    language: overrides.language ?? null,
    modified_at: overrides.modified_at ?? null
  };
}

describe('useSubtitleSources', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    mockDeleteSubtitleSource.mockResolvedValue({ subtitle_path: '', removed: [], missing: [] });
    mockFetchSubtitleSources.mockResolvedValue([
      source({ name: 'Generated', path: '/subtitles/generated.ass', format: 'ass' }),
      source({ name: 'Source', path: '/subtitles/source.srt', format: 'srt' })
    ]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loads sources and selects the latest usable source while sorting generated ASS after source subtitles', async () => {
    const { result } = renderHook(() =>
      useSubtitleSources({ sourceDirectory: '/subtitles', refreshSignal: 0 })
    );

    await waitFor(() => expect(result.current.sources).toHaveLength(2));

    expect(mockFetchSubtitleSources).toHaveBeenCalledWith('/subtitles');
    expect(result.current.selectedSource).toBe('/subtitles/source.srt');
    expect(result.current.sortedSources.map((entry) => entry.path)).toEqual([
      '/subtitles/source.srt',
      '/subtitles/generated.ass'
    ]);
    expect(result.current.selectedSourceEntry?.name).toBe('Source');
  });

  it('preserves a current selection on refresh and resets when requested', async () => {
    const { result } = renderHook(() =>
      useSubtitleSources({ sourceDirectory: '/subtitles', refreshSignal: 0 })
    );

    await waitFor(() => expect(result.current.selectedSource).toBe('/subtitles/source.srt'));

    act(() => {
      result.current.setSelectedSource('/subtitles/generated.ass');
    });
    await act(async () => {
      await result.current.refreshSources();
    });

    expect(result.current.selectedSource).toBe('/subtitles/generated.ass');

    await act(async () => {
      await result.current.refreshSources(true);
    });

    expect(result.current.selectedSource).toBe('/subtitles/source.srt');
  });

  it('deletes a confirmed selected source, refreshes, and reports the deletion', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    mockFetchSubtitleSources
      .mockResolvedValueOnce([
        source({ name: 'Source', path: '/subtitles/source.srt', format: 'srt' }),
        source({ name: 'Other', path: '/subtitles/other.srt', format: 'srt' })
      ])
      .mockResolvedValueOnce([
        source({ name: 'Other', path: '/subtitles/other.srt', format: 'srt' })
      ]);

    const { result } = renderHook(() =>
      useSubtitleSources({ sourceDirectory: '/subtitles', refreshSignal: 0 })
    );
    await waitFor(() => expect(result.current.sources).toHaveLength(2));
    act(() => {
      result.current.setSelectedSource('/subtitles/source.srt');
    });

    await act(async () => {
      await result.current.handleDeleteSource(source({ name: 'Source', path: '/subtitles/source.srt' }));
    });

    expect(mockDeleteSubtitleSource).toHaveBeenCalledWith('/subtitles/source.srt');
    expect(result.current.selectedSource).toBe('/subtitles/other.srt');
    expect(result.current.sourceMessage).toBe('Deleted Source');

    confirmSpy.mockRestore();
  });

  it('leaves sources untouched when delete confirmation is cancelled', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
    const { result } = renderHook(() =>
      useSubtitleSources({ sourceDirectory: '/subtitles', refreshSignal: 0 })
    );
    await waitFor(() => expect(result.current.sources).toHaveLength(2));

    await act(async () => {
      await result.current.handleDeleteSource(source({ name: 'Source', path: '/subtitles/source.srt' }));
    });

    expect(mockDeleteSubtitleSource).not.toHaveBeenCalled();
    expect(result.current.sources).toHaveLength(2);
    expect(result.current.sourceError).toBeNull();

    confirmSpy.mockRestore();
  });

  it('reports source list failures without clearing the previous source list', async () => {
    const { result } = renderHook(() =>
      useSubtitleSources({ sourceDirectory: '/subtitles', refreshSignal: 0 })
    );
    await waitFor(() => expect(result.current.sources).toHaveLength(2));
    mockFetchSubtitleSources.mockRejectedValueOnce(new Error('backend unavailable'));

    await act(async () => {
      await result.current.refreshSources();
    });

    expect(result.current.sources).toHaveLength(2);
    expect(result.current.sourceError).toBe('backend unavailable');
    expect(result.current.isLoadingSources).toBe(false);
  });
});
