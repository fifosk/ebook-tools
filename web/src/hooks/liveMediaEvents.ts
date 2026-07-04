import type { ProgressEventPayload } from '../api/dtos';
import { extractGeneratedFiles } from './liveMediaState';

export type LiveMediaEventAction =
  | { kind: 'refresh' }
  | { kind: 'reset'; generatedFiles: unknown }
  | { kind: 'merge'; generatedFiles: unknown }
  | { kind: 'ignore' };

export function liveMediaEventMetadata(event: ProgressEventPayload): Record<string, unknown> {
  return event.metadata && typeof event.metadata === 'object' ? event.metadata : {};
}

export function shouldRefreshMediaFromEvent(event: ProgressEventPayload): boolean {
  if (event.event_type === 'complete') {
    return true;
  }
  const metadata = liveMediaEventMetadata(event);
  return event.event_type === 'progress' && metadata.stage === 'complete';
}

export function resolveLiveMediaEventAction(event: ProgressEventPayload): LiveMediaEventAction {
  if (shouldRefreshMediaFromEvent(event)) {
    return { kind: 'refresh' };
  }

  const metadata = liveMediaEventMetadata(event);
  const generatedFiles = extractGeneratedFiles(metadata);
  if (!generatedFiles) {
    return { kind: 'ignore' };
  }

  if (event.event_type === 'progress' && metadata.media_reset === true) {
    return { kind: 'reset', generatedFiles };
  }

  if (event.event_type === 'file_chunk_generated') {
    return { kind: 'merge', generatedFiles };
  }

  return { kind: 'ignore' };
}
