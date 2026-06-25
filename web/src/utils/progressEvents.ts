import type { ProgressEventPayload } from '../api/dtos';

export type ProgressStage = 'translation' | 'media' | 'playable' | string;

const STAGE_ACRONYMS = new Set(['api', 'ass', 'epub', 'html', 'llm', 'nas', 'pdf', 'tts']);

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

export function formatProgressStageLabel(stage: string | null | undefined): string | null {
  if (!stage) {
    return null;
  }
  const normalized = stage.trim();
  if (!normalized) {
    return null;
  }
  const words = normalized.split(/[._\-\s]+/).filter((part) => part.length > 0);
  if (words.length === 0) {
    return null;
  }
  return words
    .map((word, index) => {
      const lower = word.toLowerCase();
      if (STAGE_ACRONYMS.has(lower)) {
        return lower.toUpperCase();
      }
      if (index === 0) {
        return `${lower.charAt(0).toUpperCase()}${lower.slice(1)}`;
      }
      return lower;
    })
    .join(' ');
}
