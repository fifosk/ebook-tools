import type { ProgressEventPayload } from '../api/dtos';

export type ProgressStage = 'translation' | 'media' | 'playable' | string;

export function resolveProgressStage(
  event: ProgressEventPayload | null | undefined,
): ProgressStage | null {
  if (!event || !event.metadata || typeof event.metadata !== 'object') {
    return event?.event_type === 'complete' ? 'media' : null;
  }
  const stageRaw = (event.metadata as Record<string, unknown>).stage;
  if (typeof stageRaw === 'string') {
    const stage = stageRaw.trim();
    if (stage) {
      return stage;
    }
  }
  return event.event_type === 'complete' ? 'media' : null;
}
