import { useCallback, useState } from 'react';

export const SUBTITLE_INTAKE_AT_CAPACITY_MESSAGE =
  'Job queue is at capacity. Wait for pending jobs to clear before creating a subtitle job.';

const DEFAULT_SUBTITLE_SUBMIT_ERROR = 'Unable to submit subtitle job.';

export function resolveSubtitleSubmitErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : DEFAULT_SUBTITLE_SUBMIT_ERROR;
}

export function useSubtitleSubmitStatus() {
  const [isSubmitting, setSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const resetSubmitError = useCallback(() => {
    setSubmitError(null);
  }, []);

  const beginSubmit = useCallback(() => {
    setSubmitError(null);
    setSubmitting(true);
  }, []);

  const finishSubmit = useCallback(() => {
    setSubmitting(false);
  }, []);

  const rejectAtCapacity = useCallback(() => {
    setSubmitError(SUBTITLE_INTAKE_AT_CAPACITY_MESSAGE);
  }, []);

  const failSubmit = useCallback((error: unknown) => {
    setSubmitError(resolveSubtitleSubmitErrorMessage(error));
  }, []);

  return {
    isSubmitting,
    submitError,
    setSubmitError,
    resetSubmitError,
    beginSubmit,
    finishSubmit,
    rejectAtCapacity,
    failSubmit
  };
}
