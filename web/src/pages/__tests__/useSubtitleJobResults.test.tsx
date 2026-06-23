import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchSubtitleResult } from '../../api/client';
import type { SubtitleJobResultPayload } from '../../api/dtos';
import type { JobState } from '../../components/JobList';
import { useSubtitleJobResults } from '../subtitle-tool/useSubtitleJobResults';

vi.mock('../../api/client', () => ({
  fetchSubtitleResult: vi.fn()
}));

const mockFetchSubtitleResult = vi.mocked(fetchSubtitleResult);

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}

function result(overrides: Partial<SubtitleJobResultPayload> = {}): SubtitleJobResultPayload {
  return {
    job_id: overrides.job_id ?? 'job-1',
    source_path: overrides.source_path ?? '/subtitles/source.srt',
    output_path: overrides.output_path ?? '/subtitles/source.ass',
    html_path: overrides.html_path ?? null,
    format: overrides.format ?? 'ass',
    language: overrides.language ?? 'French',
    media_metadata: overrides.media_metadata ?? null
  };
}

function job(overrides: {
  jobId: string;
  status?: string;
  jobType?: string;
}): JobState {
  return {
    jobId: overrides.jobId,
    status: {
      job_id: overrides.jobId,
      job_type: overrides.jobType ?? 'subtitle',
      status: overrides.status ?? 'completed',
      created_at: '2026-06-23T10:00:00Z',
      started_at: null,
      completed_at: null,
      result: null,
      error: null,
      latest_event: null,
      tuning: null
    } as JobState['status'],
    isReloading: false,
    isMutating: false,
    canManage: true
  };
}

describe('useSubtitleJobResults', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    mockFetchSubtitleResult.mockImplementation(async (jobId) => result({ job_id: jobId }));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches result payloads for completed subtitle jobs', async () => {
    const jobs = [
      job({ jobId: 'subtitle-1' }),
      job({ jobId: 'running-1', status: 'running' }),
      job({ jobId: 'book-1', jobType: 'book' })
    ];

    const { result: hook } = renderHook(() => useSubtitleJobResults(jobs));

    await waitFor(() => expect(hook.current['subtitle-1']).toBeTruthy());

    expect(mockFetchSubtitleResult).toHaveBeenCalledTimes(1);
    expect(mockFetchSubtitleResult).toHaveBeenCalledWith('subtitle-1');
    expect(hook.current['subtitle-1']).toEqual(result({ job_id: 'subtitle-1' }));
  });

  it('does not refetch completed jobs whose results are already loaded', async () => {
    const jobs = [job({ jobId: 'subtitle-1' })];
    const { result: hook, rerender } = renderHook(
      ({ nextJobs }) => useSubtitleJobResults(nextJobs),
      { initialProps: { nextJobs: jobs } }
    );

    await waitFor(() => expect(hook.current['subtitle-1']).toBeTruthy());
    rerender({ nextJobs: [...jobs] });

    await waitFor(() => expect(mockFetchSubtitleResult).toHaveBeenCalledTimes(1));
  });

  it('keeps successful results when another completed result fails to load', async () => {
    mockFetchSubtitleResult.mockImplementation(async (jobId) => {
      if (jobId === 'subtitle-2') {
        throw new Error('missing result');
      }
      return result({ job_id: jobId });
    });

    const { result: hook } = renderHook(() =>
      useSubtitleJobResults([
        job({ jobId: 'subtitle-1' }),
        job({ jobId: 'subtitle-2' })
      ])
    );

    await waitFor(() => expect(hook.current['subtitle-1']).toBeTruthy());

    expect(hook.current['subtitle-2']).toBeUndefined();
    expect(console.warn).toHaveBeenCalledWith(
      'Unable to load subtitle result',
      'subtitle-2',
      expect.any(Error)
    );
  });

  it('ignores late result payloads after the jobs input changes', async () => {
    const first = deferred<SubtitleJobResultPayload>();
    mockFetchSubtitleResult
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce(result({ job_id: 'subtitle-2' }));

    const { result: hook, rerender } = renderHook(
      ({ jobs }) => useSubtitleJobResults(jobs),
      { initialProps: { jobs: [job({ jobId: 'subtitle-1' })] } }
    );
    rerender({ jobs: [job({ jobId: 'subtitle-2' })] });

    await waitFor(() => expect(hook.current['subtitle-2']).toBeTruthy());

    first.resolve(result({ job_id: 'subtitle-1' }));

    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(hook.current['subtitle-1']).toBeUndefined();
    expect(hook.current['subtitle-2']).toEqual(result({ job_id: 'subtitle-2' }));
  });
});
