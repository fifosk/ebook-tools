import { describe, expect, it } from 'vitest';
import type { ProgressEventPayload, SubtitleJobResultPayload } from '../../api/dtos';
import type { JobState } from '../../components/JobList';
import { buildSubtitleJobPresentation } from '../subtitle-tool/subtitleJobPresentation';

function event(overrides: Partial<ProgressEventPayload> = {}): ProgressEventPayload {
  return {
    event_type: 'progress',
    timestamp: 1782212400,
    metadata: { stage: 'translating' },
    snapshot: {
      completed: 7,
      total: 12,
      elapsed: 3,
      speed: 2,
      eta: 5
    },
    error: null,
    ...overrides
  };
}

function job(overrides: {
  jobId?: string;
  status?: string;
  canManage?: boolean;
  generatedFiles?: Record<string, unknown> | null;
  latestEvent?: ProgressEventPayload | null;
  result?: Record<string, unknown> | null;
  mediaCompleted?: boolean | null;
  retrySummary?: Record<string, Record<string, number>> | null;
  startedAt?: string | null;
  completedAt?: string | null;
} = {}): JobState {
  const jobId = overrides.jobId ?? 'subtitle-job';
  return {
    jobId,
    status: {
      job_id: jobId,
      job_type: 'subtitle',
      status: overrides.status ?? 'completed',
      created_at: '2026-06-23T10:00:00Z',
      started_at: overrides.startedAt ?? null,
      completed_at: overrides.completedAt ?? null,
      result: overrides.result ?? null,
      error: null,
      latest_event: null,
      tuning: null,
      generated_files: overrides.generatedFiles ?? null,
      media_completed: overrides.mediaCompleted ?? null,
      retry_summary: overrides.retrySummary ?? null
    } as JobState['status'],
    latestEvent: overrides.latestEvent ?? undefined,
    isReloading: false,
    isMutating: false,
    canManage: overrides.canManage ?? true
  };
}

describe('subtitle job presentation helpers', () => {
  it('prefers generated subtitle file metadata for download labels and URLs', () => {
    const presentation = buildSubtitleJobPresentation(
      job({
        generatedFiles: {
          files: [
            {
              type: 'subtitle',
              name: 'translated.ass',
              relative_path: 'exports/translated.ass',
              url: 'https://storage.test/generated.ass'
            }
          ]
        }
      }),
      {
        relative_path: 'fallback/fallback.ass',
        metadata: {
          download_url: 'https://storage.test/metadata.ass'
        }
      },
      true
    );

    expect(presentation.resolvedName).toBe('translated.ass');
    expect(presentation.directUrl).toBe('https://storage.test/generated.ass');
  });

  it('derives download names and URLs from completed result output paths', () => {
    const presentation = buildSubtitleJobPresentation(
      job({ jobId: 'job-123' }),
      {
        output_path: '/srv/ebook-tools/jobs/job-123/nested/final.srt'
      },
      false
    );

    expect(presentation.resolvedName).toBe('final.srt');
    expect(presentation.directUrl).toContain('/job-123/nested/final.srt');
  });

  it('coerces metadata into user-facing labels without mutating sparse values', () => {
    const presentation = buildSubtitleJobPresentation(
      job({ latestEvent: event() }),
      {
        metadata: {
          original_language: 'en',
          target_language: 'sk',
          output_format: 'ass',
          ass_font_size: '42',
          ass_emphasis_scale: 1.25,
          show_original: 'off',
          workers: 3,
          batch_size: 8,
          translation_batch_size: 4,
          start_time_offset_label: '00:01:02',
          end_time_offset_label: '00:10:03'
        }
      },
      false
    );

    expect(presentation).toMatchObject({
      assEmphasisLabel: 1.25,
      assFontSizeLabel: 42,
      batchSetting: 8,
      completed: 7,
      endTimeLabel: '00:10:03',
      originalLanguageLabel: 'en',
      outputFormatLabel: 'ASS',
      showOriginalSetting: false,
      stage: 'translating',
      startTimeLabel: '00:01:02',
      total: 12,
      translationBatchSetting: 4,
      translationLanguage: 'sk',
      updatedAt: '2026-06-23T11:00:00.000Z',
      workerSetting: 3
    });
  });

  it('formats retry summaries from status payloads', () => {
    const presentation = buildSubtitleJobPresentation(
      job({
        retrySummary: {
          translation: { timeout: 1, rate_limit: 3 },
          transliteration: { network: 2, ignored: 0 }
        }
      }),
      undefined,
      false
    );

    expect(presentation.translationRetries).toBe('rate_limit (3), timeout (1)');
    expect(presentation.transliterationRetries).toBe('network (2)');
  });

  it('enables library moves only for manageable narrated completed or media-completed paused jobs', () => {
    const result: SubtitleJobResultPayload['subtitle'] = {
      metadata: {
        generate_audio_book: 'yes'
      }
    };

    expect(buildSubtitleJobPresentation(job(), result, true).canMoveToLibrary).toBe(true);
    expect(
      buildSubtitleJobPresentation(job({ status: 'paused', mediaCompleted: true }), result, true)
        .canMoveToLibrary
    ).toBe(true);
    expect(buildSubtitleJobPresentation(job({ status: 'paused' }), result, true).canMoveToLibrary).toBe(false);
    expect(buildSubtitleJobPresentation(job({ canManage: false }), result, true).canMoveToLibrary).toBe(false);
    expect(buildSubtitleJobPresentation(job(), result, false).canMoveToLibrary).toBe(false);
    expect(
      buildSubtitleJobPresentation(
        job({
          result: {
            subtitle: {
              metadata: {
                generate_audio_book: true
              }
            }
          }
        }),
        undefined,
        true
      ).canMoveToLibrary
    ).toBe(true);
  });
});
