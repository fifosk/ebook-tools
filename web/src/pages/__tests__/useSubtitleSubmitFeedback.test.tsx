import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { PipelineSubmissionResponse } from '../../api/dtos';
import { useSubtitleSubmitFeedback } from '../subtitle-tool/useSubtitleSubmitFeedback';
import type { ResolvedSubtitleSubmitValues } from '../subtitle-tool/subtitleToolUtils';

function response(jobId = 'subtitle-job-1'): PipelineSubmissionResponse {
  return {
    job_id: jobId,
    job_type: 'subtitle',
    created_at: '2026-06-23T10:00:00Z',
    status: 'pending'
  };
}

function resolvedValues(overrides: Partial<ResolvedSubtitleSubmitValues> = {}): ResolvedSubtitleSubmitValues {
  const optional = <K extends keyof ResolvedSubtitleSubmitValues>(
    key: K,
    fallback: ResolvedSubtitleSubmitValues[K]
  ): ResolvedSubtitleSubmitValues[K] =>
    Object.prototype.hasOwnProperty.call(overrides, key) ? overrides[key] as ResolvedSubtitleSubmitValues[K] : fallback;

  return {
    originalLanguage: overrides.originalLanguage ?? 'English',
    targetLanguage: overrides.targetLanguage ?? 'French',
    normalizedStartTime: overrides.normalizedStartTime ?? '00:30',
    normalizedEndTime: overrides.normalizedEndTime ?? '+02:00',
    resolvedAssFontSize: overrides.resolvedAssFontSize ?? 42,
    resolvedAssEmphasis: overrides.resolvedAssEmphasis ?? 1.25,
    selectedModel: optional('selectedModel', 'gpt-5-mini'),
    translationProvider: optional('translationProvider', 'llm'),
    transliterationMode: optional('transliterationMode', 'default'),
    transliterationModel: optional('transliterationModel', null),
    sourcePath: overrides.sourcePath ?? '/subtitles/source.srt',
    workerCount: overrides.workerCount ?? 4,
    batchSize: overrides.batchSize ?? 12,
    translationBatchSize: overrides.translationBatchSize ?? 8
  };
}

describe('useSubtitleSubmitFeedback', () => {
  it('starts without feedback until a submission is recorded', () => {
    const { result } = renderHook(() =>
      useSubtitleSubmitFeedback({ defaultStartTime: '00:00' })
    );

    expect(result.current.lastSubmittedJobId).toBeNull();
    expect(result.current.submittedSummary).toBeNull();
  });

  it('formats the last submitted subtitle controls for display', () => {
    const { result } = renderHook(() =>
      useSubtitleSubmitFeedback({ defaultStartTime: '00:00' })
    );

    act(() => {
      result.current.recordSubmission({
        response: response('subtitle-job-2'),
        values: resolvedValues(),
        workerCount: 4,
        batchSize: 12,
        translationBatchSize: 8,
        outputFormat: 'ass'
      });
    });

    expect(result.current.lastSubmittedJobId).toBe('subtitle-job-2');
    expect(result.current.submittedSummary).toBe(
      'Submitted subtitle job subtitle-job-2 using 4 threads, batch size 12, LLM batch 8, starting at 00:30, ending after 02:00, LLM gpt-5-mini, ASS subtitles, font size 42 and scale 1.25\u00d7. Live status appears in the Jobs tab.'
    );
  });

  it('falls back to auto-detected concurrency when optional details are absent', () => {
    const { result } = renderHook(() =>
      useSubtitleSubmitFeedback({ defaultStartTime: '00:00' })
    );

    act(() => {
      result.current.recordSubmission({
        response: response('subtitle-job-3'),
        values: resolvedValues({
          normalizedStartTime: '00:00',
          normalizedEndTime: '',
          resolvedAssFontSize: null,
          resolvedAssEmphasis: null,
          selectedModel: null
        }),
        workerCount: '',
        batchSize: '',
        translationBatchSize: '',
        outputFormat: 'srt'
      });
    });

    expect(result.current.submittedSummary).toBe(
      'Submitted subtitle job subtitle-job-3 using SRT subtitles. Live status appears in the Jobs tab.'
    );
  });
});
