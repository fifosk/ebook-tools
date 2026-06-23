import { describe, expect, it } from 'vitest';
import type { JobState } from '../JobList';
import {
  isPipelineView,
  resolveImageWaitStatus,
  resolveJobGlyph,
  resolveSidebarLabel,
  resolveSidebarLanguage,
  resolveSidebarProgress,
  resolveSidebarStage,
  resolveSidebarStatus,
} from '../sidebar/sidebarUtils';

function makeJob(overrides: Partial<JobState> = {}): JobState {
  const status = overrides.status ?? {
    job_id: 'job-1',
    job_type: 'pipeline',
    status: 'pending',
    created_at: '2026-06-23T12:00:00Z',
    started_at: null,
    completed_at: null,
    result: null,
    error: null,
    latest_event: null,
    tuning: null,
    user_id: 'user',
  };
  return {
    jobId: status.job_id ?? 'job-1',
    status,
    latestEvent: undefined,
    isReloading: false,
    isMutating: false,
    canManage: true,
    ...overrides,
  };
}

describe('sidebarUtils', () => {
  it('detects pipeline views without depending on the app view union', () => {
    expect(isPipelineView('pipeline:source')).toBe(true);
    expect(isPipelineView('library:list')).toBe(false);
    expect(isPipelineView(null)).toBe(false);
  });

  it('resolves book labels from metadata before falling back to file stems', () => {
    const job = makeJob({
      status: {
        job_id: 'book-1',
        job_type: 'pipeline',
        status: 'pending',
        created_at: '2026-06-23T12:00:00Z',
        started_at: null,
        completed_at: null,
        result: {
          pipeline_config: {
            book_title: 'A Very Long Cross Surface Refactor Story',
          },
        },
        error: null,
        latest_event: null,
        tuning: null,
        parameters: {
          input_file: '/Volumes/Books/less-useful.epub',
        },
      },
    });

    expect(resolveSidebarLabel(job)).toEqual({
      label: 'A Very Long Cross Surface R…',
      tooltip: 'A Very Long Cross Surface Refactor Story',
    });
  });

  it('resolves subtitle labels and target language from subtitle metadata', () => {
    const job = makeJob({
      jobId: 'sub-1',
      status: {
        job_id: 'sub-1',
        job_type: 'subtitle',
        status: 'pending',
        created_at: '2026-06-23T12:00:00Z',
        started_at: null,
        completed_at: null,
        result: {
          subtitle: {
            metadata: {
              input_file: '/Volumes/Subtitles/show.s02e05.en.ass',
              target_language: 'es',
            },
          },
        },
        error: null,
        latest_event: null,
        tuning: null,
      },
    });

    expect(resolveSidebarLabel(job)).toEqual({
      label: 'show.s02e05.en',
      tooltip: 'show.s02e05.en',
    });
    expect(resolveSidebarLanguage(job).label).toBe('Spanish');
  });

  it('prefers explicit target-language arrays for language badges', () => {
    const job = makeJob({
      status: {
        job_id: 'dub-1',
        job_type: 'youtube_dub',
        status: 'running',
        created_at: '2026-06-23T12:00:00Z',
        started_at: '2026-06-23T12:01:00Z',
        completed_at: null,
        result: null,
        error: null,
        latest_event: null,
        tuning: null,
        parameters: {
          target_languages: ['de', 'fr'],
          video_path: '/Volumes/Video/episode.mp4',
        },
      },
    });

    expect(resolveSidebarLanguage(job)).toMatchObject({
      label: 'German +1',
      tooltip: 'German, French',
    });
    expect(resolveSidebarLabel(job)).toEqual({ label: 'episode', tooltip: 'episode' });
  });

  it('uses playable progress before generated-file and media-event progress', () => {
    const job = makeJob({
      status: {
        job_id: 'job-progress',
        job_type: 'pipeline',
        status: 'running',
        created_at: '2026-06-23T12:00:00Z',
        started_at: '2026-06-23T12:01:00Z',
        completed_at: null,
        result: null,
        generated_files: {
          media_batch_stats: {
            items_completed: 2,
            items_total: 10,
          },
        },
        error: null,
        latest_event: null,
        tuning: null,
      },
      latestEvent: {
        event_type: 'progress',
        timestamp: Date.now(),
        metadata: {},
        snapshot: { completed: 1, total: 10, elapsed: 1, speed: 1, eta: 9 },
        error: null,
      },
      latestPlayableEvent: {
        event_type: 'progress',
        timestamp: Date.now(),
        metadata: {},
        snapshot: { completed: 7, total: 10, elapsed: 7, speed: 1, eta: 3 },
        error: null,
      },
    });

    expect(resolveSidebarProgress(job)).toBe(70);
  });

  it('detects image wait status after text generation has completed', () => {
    const job = makeJob({
      status: {
        job_id: 'image-job',
        job_type: 'pipeline',
        status: 'running',
        created_at: '2026-06-23T12:00:00Z',
        started_at: '2026-06-23T12:01:00Z',
        completed_at: null,
        result: null,
        image_generation: {
          enabled: true,
          expected: 8,
          generated: 2,
          sentence_total: 40,
          percent: 25,
        },
        error: null,
        latest_event: null,
        tuning: null,
      },
      latestEvent: {
        event_type: 'progress',
        timestamp: Date.now(),
        metadata: {},
        snapshot: { completed: 40, total: 40, elapsed: 40, speed: 1, eta: 0 },
        error: null,
      },
    });

    expect(resolveImageWaitStatus(job)).toEqual({
      icon: '🖼️',
      tooltip: 'Waiting for images (2/8)',
      percent: 25,
    });
  });

  it('resolves stage, status, and TV glyph metadata for compact rows', () => {
    const job = makeJob({
      status: {
        job_id: 'tv-job',
        job_type: 'youtube_dub',
        status: 'completed',
        created_at: '2026-06-23T12:00:00Z',
        started_at: '2026-06-23T12:01:00Z',
        completed_at: '2026-06-23T12:02:00Z',
        result: {
          youtube_dub: {
            media_metadata: {
              kind: 'tv_episode',
              season_number: 1,
              episode_number: 2,
            },
          },
        },
        error: null,
        latest_event: null,
        tuning: null,
      },
      latestEvent: {
        event_type: 'stage',
        timestamp: Date.now(),
        metadata: { stage: 'nas.mirror.start' },
        snapshot: { completed: 0, total: 1, elapsed: 0, speed: 0, eta: 0 },
        error: null,
      },
    });

    expect(resolveSidebarStage(job)).toEqual({ icon: '🗄️', tooltip: 'Copying stitched output to NAS' });
    expect(resolveSidebarStatus('completed')).toEqual({ icon: '✅', tooltip: 'Completed' });
    expect(resolveJobGlyph(job)).toMatchObject({ variant: 'tv' });
  });
});
