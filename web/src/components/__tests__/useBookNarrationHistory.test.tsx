import { renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { PipelineStatusResponse } from '../../api/dtos';
import { useBookNarrationHistory } from '../book-narration/useBookNarrationHistory';

function makeJob(
  id: string,
  createdAt: string,
  parameters: PipelineStatusResponse['parameters'],
  jobType: PipelineStatusResponse['job_type'] = 'pipeline',
): PipelineStatusResponse {
  return {
    job_id: id,
    job_type: jobType,
    status: 'completed',
    created_at: createdAt,
    started_at: null,
    completed_at: createdAt,
    result: null,
    generated_files: null,
    error: null,
    parameters,
    latest_event: null,
    tuning: null,
    user_id: 'user',
  };
}

describe('useBookNarrationHistory', () => {
  it('normalizes paths through the shared narration helper', () => {
    const { result } = renderHook(() => useBookNarrationHistory({ recentJobs: null }));

    expect(result.current.normalizePath(' /Volumes/Books/Example.EPUB/// ')).toBe('/volumes/books/example.epub');
    expect(result.current.normalizePath('')).toBeNull();
  });

  it('uses the latest recent-jobs snapshot from stable callbacks', async () => {
    const olderJobs = [
      makeJob('older', '2026-06-20T10:00:00Z', {
        input_file: '/books/current.epub',
        end_sentence: 12,
        base_output_file: 'older-output',
      }),
    ];
    const newerJobs = [
      makeJob('newer', '2026-06-22T10:00:00Z', {
        input_file: '/BOOKS/CURRENT.EPUB/',
        start_sentence: 40,
        base_output_file: 'newer-output',
        input_language: 'Turkish',
        target_languages: ['Dutch', 'Italian'],
        enable_lookup_cache: true,
      }),
    ];

    const { result, rerender } = renderHook(
      ({ recentJobs }: { recentJobs: PipelineStatusResponse[] | null }) =>
        useBookNarrationHistory({ recentJobs }),
      { initialProps: { recentJobs: olderJobs } },
    );
    const firstResolveStart = result.current.resolveStartFromHistory;
    const firstResolveSelection = result.current.resolveLatestJobSelection;

    expect(result.current.resolveStartFromHistory('/books/current.epub')).toBe(7);
    expect(result.current.resolveLatestJobSelection()).toEqual({
      input: '/books/current.epub',
      base: 'older-output',
    });

    rerender({ recentJobs: newerJobs });

    await waitFor(() => {
      expect(result.current.resolveStartFromHistory('/books/current.epub')).toBe(35);
    });
    expect(result.current.resolveLatestJobSelection()).toEqual({
      input: '/BOOKS/CURRENT.EPUB/',
      base: 'newer-output',
    });
    expect(result.current.resolveLatestJobSettings()).toEqual({
      inputLanguage: 'Turkish',
      targetLanguages: ['Dutch', 'Italian'],
      enableLookupCache: true,
    });
    expect(result.current.resolveStartFromHistory).toBe(firstResolveStart);
    expect(result.current.resolveLatestJobSelection).toBe(firstResolveSelection);
  });

  it('ignores subtitle jobs when deriving narration history', () => {
    const { result } = renderHook(() => useBookNarrationHistory({
      recentJobs: [
        makeJob('subtitle', '2026-06-23T10:00:00Z', {
          input_file: '/books/current.epub',
          end_sentence: 999,
        }, 'subtitle'),
      ],
    }));

    expect(result.current.resolveStartFromHistory('/books/current.epub')).toBeNull();
    expect(result.current.resolveLatestJobSelection()).toBeNull();
    expect(result.current.resolveLatestJobSettings()).toBeNull();
  });
});
