import { describe, expect, it } from 'vitest';
import type { SubtitleSourceEntry } from '../../api/dtos';
import {
  isAssSubtitleSelection,
  pickLatestSubtitleSource,
  resolveSubtitleMetadataSourceName,
  resolveSubtitleSourceFormat,
  resolveSubtitleSourceSelectionAfterRefresh,
  sortSubtitleSourcesForSelection
} from '../subtitle-tool/subtitleSourceUtils';

function source(overrides: Partial<SubtitleSourceEntry>): SubtitleSourceEntry {
  return {
    name: overrides.name ?? overrides.path ?? 'source.srt',
    path: overrides.path ?? '/media/source.srt',
    format: overrides.format ?? 'srt',
    language: overrides.language ?? null,
    modified_at: overrides.modified_at ?? null
  };
}

describe('sortSubtitleSourcesForSelection', () => {
  it('keeps original relative order while moving generated ASS files after source subtitles', () => {
    const inputs = [
      source({ path: '/subtitles/generated.ass', format: 'ass' }),
      source({ path: '/subtitles/source.srt', format: 'srt' }),
      source({ path: '/subtitles/source.vtt', format: 'vtt' }),
      source({ path: '/subtitles/other.ass', format: 'ass' })
    ];

    expect(sortSubtitleSourcesForSelection(inputs).map((entry) => entry.path)).toEqual([
      '/subtitles/source.srt',
      '/subtitles/source.vtt',
      '/subtitles/generated.ass',
      '/subtitles/other.ass'
    ]);
  });

  it('uses the path extension when the backend entry has no format', () => {
    const inputs = [
      source({ path: '/subtitles/generated.ass', format: '' }),
      source({ path: '/subtitles/source.srt', format: '' })
    ];

    expect(sortSubtitleSourcesForSelection(inputs).map((entry) => entry.path)).toEqual([
      '/subtitles/source.srt',
      '/subtitles/generated.ass'
    ]);
  });
});

describe('source metadata helpers', () => {
  it('resolves source format from explicit format or file extension', () => {
    expect(resolveSubtitleSourceFormat(source({ path: '/a/generated.ass', format: '' }))).toBe('ass');
    expect(resolveSubtitleSourceFormat(source({ path: '/a/source.srt', format: 'VTT' }))).toBe('vtt');
    expect(resolveSubtitleSourceFormat(null)).toBe('');
  });

  it('flags generated ASS selections only for existing-source mode', () => {
    const ass = source({ path: '/a/generated.ass', format: 'ass' });

    expect(isAssSubtitleSelection('existing', ass)).toBe(true);
    expect(isAssSubtitleSelection('upload', ass)).toBe(false);
    expect(isAssSubtitleSelection('existing', source({ path: '/a/source.srt', format: 'srt' }))).toBe(false);
  });

  it('resolves metadata source names from upload files, selected names, or path basenames', () => {
    expect(
      resolveSubtitleMetadataSourceName({
        sourceMode: 'upload',
        uploadFileName: 'upload.srt',
        selectedSourcePath: '/ignored/source.srt'
      })
    ).toBe('upload.srt');
    expect(
      resolveSubtitleMetadataSourceName({
        sourceMode: 'existing',
        selectedSourceName: 'Friendly Source',
        selectedSourcePath: '/media/source.srt'
      })
    ).toBe('Friendly Source');
    expect(
      resolveSubtitleMetadataSourceName({
        sourceMode: 'existing',
        selectedSourcePath: '/media/fallback.srt'
      })
    ).toBe('fallback.srt');
  });
});

describe('pickLatestSubtitleSource', () => {
  it('prefers the newest non-ASS source over a newer generated ASS subtitle', () => {
    const inputs = [
      source({
        path: '/subtitles/generated.ass',
        format: 'ass',
        modified_at: '2026-06-23T12:00:00Z'
      }),
      source({
        path: '/subtitles/source.srt',
        format: 'srt',
        modified_at: '2026-06-23T10:00:00Z'
      }),
      source({
        path: '/subtitles/source.vtt',
        format: 'vtt',
        modified_at: '2026-06-23T11:00:00Z'
      })
    ];

    expect(pickLatestSubtitleSource(inputs)).toBe('/subtitles/source.vtt');
  });

  it('falls back to ASS files when they are the only available subtitle sources', () => {
    const inputs = [
      source({
        path: '/subtitles/older.ass',
        format: 'ass',
        modified_at: '2026-06-23T09:00:00Z'
      }),
      source({
        path: '/subtitles/newer.ass',
        format: 'ass',
        modified_at: '2026-06-23T10:00:00Z'
      })
    ];

    expect(pickLatestSubtitleSource(inputs)).toBe('/subtitles/newer.ass');
  });

  it('uses lexical path order as a stable tie breaker', () => {
    const inputs = [
      source({ path: '/subtitles/z.srt', modified_at: '2026-06-23T10:00:00Z' }),
      source({ path: '/subtitles/a.srt', modified_at: '2026-06-23T10:00:00Z' })
    ];

    expect(pickLatestSubtitleSource(inputs)).toBe('/subtitles/a.srt');
  });

  it('returns an empty path when no sources are available', () => {
    expect(pickLatestSubtitleSource([])).toBe('');
  });
});

describe('resolveSubtitleSourceSelectionAfterRefresh', () => {
  it('keeps the current source when it is still available and selection was not reset', () => {
    const current = source({ path: '/subtitles/current.srt', modified_at: '2026-06-23T10:00:00Z' });
    const newer = source({ path: '/subtitles/newer.srt', modified_at: '2026-06-23T11:00:00Z' });

    expect(
      resolveSubtitleSourceSelectionAfterRefresh({
        sources: [current, newer],
        currentSelection: current.path,
        resetSelection: false,
      }),
    ).toBe(current.path);
  });

  it('chooses the latest source when selection is reset or stale', () => {
    const older = source({ path: '/subtitles/older.srt', modified_at: '2026-06-23T10:00:00Z' });
    const newer = source({ path: '/subtitles/newer.srt', modified_at: '2026-06-23T11:00:00Z' });

    expect(
      resolveSubtitleSourceSelectionAfterRefresh({
        sources: [older, newer],
        currentSelection: older.path,
        resetSelection: true,
      }),
    ).toBe(newer.path);
    expect(
      resolveSubtitleSourceSelectionAfterRefresh({
        sources: [older, newer],
        currentSelection: '/subtitles/deleted.srt',
        resetSelection: false,
      }),
    ).toBe(newer.path);
  });

  it('clears the selected source when refreshed sources are empty', () => {
    expect(
      resolveSubtitleSourceSelectionAfterRefresh({
        sources: [],
        currentSelection: '/subtitles/deleted.srt',
        resetSelection: true,
      }),
    ).toBe('');
  });
});
