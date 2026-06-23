import { describe, expect, it } from 'vitest';
import type { SubtitleSourceEntry } from '../../api/dtos';
import {
  formatSubmittedSubtitleSummary,
  pickLatestSubtitleSource,
  sortSubtitleSourcesForSelection
} from '../subtitle-tool/subtitleToolUtils';

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

describe('formatSubmittedSubtitleSummary', () => {
  it('describes auto-detected submissions when no tuning details were captured', () => {
    expect(
      formatSubmittedSubtitleSummary({
        jobId: 'job-1',
        workerCount: null,
        batchSize: null,
        translationBatchSize: null,
        startTime: '00:00',
        defaultStartTime: '00:00',
        endTime: null,
        model: null,
        format: null,
        assFontSize: null,
        assEmphasis: null
      })
    ).toBe(
      'Submitted subtitle job job-1 using auto-detected concurrency. Live status appears in the Jobs tab.'
    );
  });

  it('joins tuning, clip window, model, and ASS settings in display order', () => {
    expect(
      formatSubmittedSubtitleSummary({
        jobId: 'job-2',
        workerCount: 4,
        batchSize: 20,
        translationBatchSize: 8,
        startTime: '01:02',
        defaultStartTime: '00:00',
        endTime: '+03:00',
        model: 'gpt-test',
        format: 'ass',
        assFontSize: 44,
        assEmphasis: 1.2
      })
    ).toBe(
      'Submitted subtitle job job-2 using 4 threads, batch size 20, LLM batch 8, starting at 01:02, ending after 03:00, LLM gpt-test, ASS subtitles, font size 44 and scale 1.2\u00d7. Live status appears in the Jobs tab.'
    );
  });

  it('uses singular thread and absolute end time labels', () => {
    expect(
      formatSubmittedSubtitleSummary({
        jobId: 'job-3',
        workerCount: 1,
        batchSize: null,
        translationBatchSize: null,
        startTime: '00:00',
        defaultStartTime: '00:00',
        endTime: '12:34',
        model: null,
        format: 'srt',
        assFontSize: null,
        assEmphasis: null
      })
    ).toBe(
      'Submitted subtitle job job-3 using 1 thread, ending at 12:34 and SRT subtitles. Live status appears in the Jobs tab.'
    );
  });
});
