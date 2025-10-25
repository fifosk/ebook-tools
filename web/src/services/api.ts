import { buildEventStreamUrl } from '../api/client';
import { ProgressEventPayload } from '../api/dtos';

type EventSourceConstructor = new (
  url: string,
  eventSourceInitDict?: EventSourceInit,
) => EventSource;

function resolveEventSource(): EventSourceConstructor | null {
  if (typeof window !== 'undefined' && typeof window.EventSource === 'function') {
    return window.EventSource;
  }

  const globalSource = (globalThis as typeof globalThis & {
    EventSource?: EventSourceConstructor;
  }).EventSource;

  return typeof globalSource === 'function' ? globalSource : null;
}

export interface JobEventSubscribeOptions {
  onEvent?: (event: ProgressEventPayload) => void;
  onError?: (event: Event) => void;
  withCredentials?: boolean;
}

export function subscribeToJobEvents(
  jobId: string,
  { onEvent, onError, withCredentials = false }: JobEventSubscribeOptions = {},
): () => void {
  const eventSourceCtor = resolveEventSource();
  if (!eventSourceCtor) {
    console.warn('EventSource is not available in this environment.');
    return () => {};
  }

  const eventStreamUrl = buildEventStreamUrl(jobId);

  let eventSource: EventSource;
  try {
    eventSource = new eventSourceCtor(
      eventStreamUrl,
      withCredentials ? { withCredentials: true } : undefined,
    );
  } catch (error) {
    console.error('Unable to subscribe to job events', error);
    return () => {};
  }

  const handleMessage = (event: MessageEvent<string>) => {
    if (!onEvent) {
      return;
    }

    const raw = typeof event.data === 'string' ? event.data.trim() : '';
    if (!raw) {
      return;
    }

    try {
      const payload = JSON.parse(raw) as ProgressEventPayload;
      onEvent(payload);
    } catch (parseError) {
      console.warn('Failed to parse job event payload', parseError);
    }
  };

  const handleError = (event: Event) => {
    onError?.(event);
  };

  eventSource.onmessage = handleMessage;
  eventSource.onerror = handleError;

  return () => {
    eventSource.onmessage = null;
    eventSource.onerror = null;
    eventSource.close();
  };
}
