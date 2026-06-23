import type { PipelineIntakeStatusResponse } from '../../api/dtos';

export interface PipelineIntakeStatusPresentation {
  message: string;
  detailLines: string[];
  tone: 'info' | 'success' | 'warning';
  role: 'status' | 'alert';
}

export function resolvePipelineIntakeStatusPresentation(
  status: PipelineIntakeStatusResponse | null,
  isLoading: boolean,
): PipelineIntakeStatusPresentation | null {
  if (!status) {
    return isLoading
      ? {
          message: 'Checking job intake...',
          detailLines: [],
          tone: 'info',
          role: 'status',
        }
      : null;
  }

  const detailLines = [
    `Delayed jobs: ${status.delayCount}`,
    status.softLimit ? `Slowdown starts at ${status.softLimit} pending` : null,
    status.hardLimit ? `Capacity limit is ${status.hardLimit} pending` : null,
  ].filter((line): line is string => Boolean(line));

  if (!status.acceptingJobs) {
    const limit = status.hardLimit ? ` of ${status.hardLimit}` : '';
    return {
      message: `Job queue is at capacity: ${status.queueDepth} pending${limit}. New submissions are paused until pending jobs clear.`,
      detailLines,
      tone: 'warning',
      role: 'alert',
    };
  }

  if (status.isUnderPressure) {
    return {
      message: `Queue pressure: ${status.queueDepth} pending and ${status.activeCount} running. New jobs may start more slowly.`,
      detailLines,
      tone: 'warning',
      role: 'status',
    };
  }

  return {
    message: `Job intake is available: ${status.queueDepth} pending and ${status.activeCount} running.`,
    detailLines,
    tone: 'success',
    role: 'status',
  };
}
