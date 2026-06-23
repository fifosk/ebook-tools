import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { JobState } from '../../components/JobList';
import { useSubtitleTabState } from '../subtitle-tool/useSubtitleTabState';

function job(overrides: {
  jobId: string;
  createdAt: string;
  jobType?: string;
  status?: string;
}): JobState {
  return {
    jobId: overrides.jobId,
    status: {
      job_id: overrides.jobId,
      job_type: overrides.jobType ?? 'subtitle',
      status: overrides.status ?? 'completed',
      created_at: overrides.createdAt,
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

describe('useSubtitleTabState', () => {
  it('starts on the subtitles tab and switches tabs through the shared setter', () => {
    const { result } = renderHook(() => useSubtitleTabState([]));

    expect(result.current.activeTab).toBe('subtitles');

    act(() => {
      result.current.setActiveTab('jobs');
    });

    expect(result.current.activeTab).toBe('jobs');
  });

  it('sorts subtitle jobs newest first for tab counts and the jobs panel', () => {
    const { result } = renderHook(() =>
      useSubtitleTabState([
        job({ jobId: 'older', createdAt: '2026-06-23T10:00:00Z' }),
        job({ jobId: 'newer', createdAt: '2026-06-23T12:00:00Z' }),
        job({ jobId: 'middle', createdAt: '2026-06-23T11:00:00Z' })
      ])
    );

    expect(result.current.sortedSubtitleJobs.map((item) => item.jobId)).toEqual([
      'newer',
      'middle',
      'older'
    ]);
  });
});
