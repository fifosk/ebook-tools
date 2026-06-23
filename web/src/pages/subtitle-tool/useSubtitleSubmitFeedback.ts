import { useCallback, useMemo, useState } from 'react';
import type { PipelineSubmissionResponse } from '../../api/dtos';
import type { SubtitleOutputFormat } from './subtitleToolTypes';
import type { ResolvedSubtitleSubmitValues } from './subtitleSubmitUtils';
import { formatSubmittedSubtitleSummary } from './subtitleSubmitFeedbackUtils';

type SubtitleSubmitFeedbackInput = {
  defaultStartTime: string;
};

export type RecordSubtitleSubmitInput = {
  response: PipelineSubmissionResponse;
  values: ResolvedSubtitleSubmitValues;
  workerCount: number | '';
  batchSize: number | '';
  translationBatchSize: number | '';
  outputFormat: SubtitleOutputFormat;
};

type SubtitleSubmitFeedbackState = {
  jobId: string;
  workerCount: number | null;
  batchSize: number | null;
  translationBatchSize: number | null;
  startTime: string;
  endTime: string | null;
  model: string | null;
  format: SubtitleOutputFormat | null;
  assFontSize: number | null;
  assEmphasis: number | null;
};

export function useSubtitleSubmitFeedback({ defaultStartTime }: SubtitleSubmitFeedbackInput) {
  const [lastSubmission, setLastSubmission] = useState<SubtitleSubmitFeedbackState | null>(null);

  const recordSubmission = useCallback((input: RecordSubtitleSubmitInput) => {
    const { values } = input;
    setLastSubmission({
      jobId: input.response.job_id,
      workerCount: typeof input.workerCount === 'number' ? input.workerCount : null,
      batchSize: typeof input.batchSize === 'number' ? input.batchSize : null,
      translationBatchSize:
        typeof input.translationBatchSize === 'number' ? input.translationBatchSize : null,
      startTime: values.normalizedStartTime,
      endTime: values.normalizedEndTime || null,
      model: values.selectedModel,
      format: input.outputFormat,
      assFontSize: values.resolvedAssFontSize,
      assEmphasis: values.resolvedAssEmphasis
    });
  }, []);

  const summary = useMemo(() => {
    if (!lastSubmission) {
      return null;
    }
    return formatSubmittedSubtitleSummary({
      ...lastSubmission,
      defaultStartTime
    });
  }, [defaultStartTime, lastSubmission]);

  return {
    lastSubmittedJobId: lastSubmission?.jobId ?? null,
    submittedSummary: summary,
    recordSubmission
  };
}
