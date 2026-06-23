import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { SubtitleSourceEntry } from '../../api/dtos';
import { useSubtitleSourceMode } from '../subtitle-tool/useSubtitleSourceMode';

function source(overrides: Partial<SubtitleSourceEntry>): SubtitleSourceEntry {
  return {
    name: overrides.name ?? overrides.path ?? 'source.srt',
    path: overrides.path ?? '/subtitles/source.srt',
    format: overrides.format ?? 'srt',
    language: overrides.language ?? null,
    modified_at: overrides.modified_at ?? null
  };
}

describe('useSubtitleSourceMode', () => {
  it('flags generated ASS files only for existing-source mode', () => {
    const assSource = source({
      name: 'Generated ASS',
      path: '/subtitles/generated.ass',
      format: 'ass'
    });
    const { result } = renderHook(() =>
      useSubtitleSourceMode({
        selectedSource: assSource.path,
        selectedSourceEntry: assSource
      })
    );

    expect(result.current.sourceMode).toBe('existing');
    expect(result.current.isAssSelection).toBe(true);
    expect(result.current.metadataSourceName).toBe('Generated ASS');

    act(() => {
      result.current.handleSourceModeChange('upload');
    });

    expect(result.current.isAssSelection).toBe(false);
  });

  it('uses uploaded file names for metadata lookup labels in upload mode', () => {
    const { result } = renderHook(() =>
      useSubtitleSourceMode({
        selectedSource: '/subtitles/fallback.srt',
        selectedSourceEntry: null
      })
    );

    expect(result.current.metadataSourceName).toBe('fallback.srt');

    act(() => {
      result.current.handleSourceModeChange('upload');
      result.current.handleUploadFileChange(new File(['1\n00:00:00,000 --> 00:00:01,000\nHi'], 'upload.srt'));
    });

    expect(result.current.uploadFile?.name).toBe('upload.srt');
    expect(result.current.metadataSourceName).toBe('upload.srt');

    act(() => {
      result.current.clearUploadFile();
    });

    expect(result.current.uploadFile).toBeNull();
    expect(result.current.metadataSourceName).toBe('');
  });

  it('clears stale submit errors when switching source modes', () => {
    const resetSubmitError = vi.fn();
    const { result } = renderHook(() =>
      useSubtitleSourceMode({
        selectedSource: '/subtitles/source.srt',
        selectedSourceEntry: source({ path: '/subtitles/source.srt' }),
        onSubmitErrorReset: resetSubmitError
      })
    );

    act(() => {
      result.current.handleSourceModeChange('upload');
    });

    expect(resetSubmitError).toHaveBeenCalledTimes(1);
  });
});
