import { useEffect } from 'react';
import { buildEventStreamUrl } from '../api/client';
import { ProgressEventPayload } from '../api/dtos';

export function usePipelineEvents(
  jobId: string,
  enabled: boolean,
  onEvent: (event: ProgressEventPayload) => void
): void {
  const eventStreamUrl = buildEventStreamUrl(jobId);
  useEffect(() => {
    if (!enabled) {
      return;
    }

    const eventSource = new EventSource(eventStreamUrl);

    eventSource.onmessage = (message) => {
      try {
        const payload = JSON.parse(message.data) as ProgressEventPayload;
        onEvent(payload);
      } catch (error) {
        console.error('Failed to parse progress event', error);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [eventStreamUrl, enabled, onEvent]);
}
