import { useEffect } from 'react';
import { subscribeToJobEvents } from '../services/api';
import { ProgressEventPayload } from '../api/dtos';

export function usePipelineEvents(
  jobId: string,
  enabled: boolean,
  onEvent: (event: ProgressEventPayload) => void
): void {
  useEffect(() => {
    if (!enabled || !jobId) {
      return;
    }

    const unsubscribe = subscribeToJobEvents(jobId, {
      onEvent: (payload) => {
        onEvent(payload);
      },
      onError: () => {
        /* no-op: connection errors will trigger retries on next render */
      }
    });

    return () => {
      unsubscribe();
    };
  }, [enabled, jobId, onEvent]);
}
