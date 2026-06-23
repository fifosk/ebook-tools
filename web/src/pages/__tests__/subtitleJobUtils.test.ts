import { describe, expect, it } from 'vitest';
import type { JobState } from '../../components/JobList';
import {
  extractSubtitleFile,
  formatSubtitleRetryCounts,
  selectMissingCompletedSubtitleJobs,
  sortSubtitleJobsNewestFirst
} from '../subtitle-tool/subtitleJobUtils';

function job(overrides: {
  jobId: string;
  jobType?: string;
  status?: string;
  createdAt?: string;
  generatedFiles?: Record<string, unknown> | null;
}): JobState {
  return {
    jobId: overrides.jobId,
    status: {
      job_id: overrides.jobId,
      job_type: overrides.jobType ?? 'subtitle',
      status: overrides.status ?? 'completed',
      created_at: overrides.createdAt ?? '2026-06-23T10:00:00Z',
      started_at: null,
      completed_at: null,
      result: null,
      error: null,
      latest_event: null,
      tuning: null,
      generated_files: overrides.generatedFiles ?? null
    } as JobState['status'],
    isReloading: false,
    isMutating: false,
    canManage: true
  };
}

describe('subtitle job helpers', () => {
  it('formats retry counts by descending count and reason label', () => {
    expect(
      formatSubtitleRetryCounts({
        timeout: 2,
        rate_limit: 5,
        network: 5,
        ignored: 0
      })
    ).toBe('network (5), rate_limit (5), timeout (2)');
    expect(formatSubtitleRetryCounts({ ignored: 0 })).toBeNull();
    expect(formatSubtitleRetryCounts(null)).toBeNull();
  });

  it('extracts the first generated subtitle file from status payloads', () => {
    const status = job({
      jobId: 'subtitle-file',
      generatedFiles: {
        files: [
          { type: 'audio', name: 'audio.mp3', relative_path: 'audio.mp3' },
          {
            type: 'Subtitle',
            name: 'translated.ass',
            relative_path: 'subtitles/translated.ass',
            url: 'https://example.test/translated.ass'
          }
        ]
      }
    }).status;

    expect(extractSubtitleFile(status)).toEqual({
      name: 'translated.ass',
      relativePath: 'subtitles/translated.ass',
      url: 'https://example.test/translated.ass'
    });
  });

  it('uses safe defaults for sparse generated subtitle file entries', () => {
    const status = job({
      jobId: 'sparse-file',
      generatedFiles: {
        files: [
          {
            type: 'subtitle'
          }
        ]
      }
    }).status;

    expect(extractSubtitleFile(status)).toEqual({
      name: 'subtitle',
      relativePath: null,
      url: null
    });
    expect(extractSubtitleFile(job({ jobId: 'none' }).status)).toBeNull();
  });

  it('selects completed subtitle jobs that are missing cached result payloads', () => {
    const jobs = [
      job({ jobId: 'ready-missing' }),
      job({ jobId: 'ready-cached' }),
      job({ jobId: 'running', status: 'running' }),
      job({ jobId: 'book', jobType: 'book' })
    ];

    expect(selectMissingCompletedSubtitleJobs(jobs, { 'ready-cached': { ok: true } }).map((entry) => entry.jobId)).toEqual([
      'ready-missing'
    ]);
  });

  it('sorts subtitle jobs newest first without mutating the input array', () => {
    const oldest = job({ jobId: 'oldest', createdAt: '2026-06-23T09:00:00Z' });
    const newest = job({ jobId: 'newest', createdAt: '2026-06-23T11:00:00Z' });
    const middle = job({ jobId: 'middle', createdAt: '2026-06-23T10:00:00Z' });
    const input = [oldest, newest, middle];

    expect(sortSubtitleJobsNewestFirst(input).map((entry) => entry.jobId)).toEqual([
      'newest',
      'middle',
      'oldest'
    ]);
    expect(input.map((entry) => entry.jobId)).toEqual(['oldest', 'newest', 'middle']);
  });
});
