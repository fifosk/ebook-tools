import { describe, expect, it } from 'vitest';
import { formatProgressStageLabel, resolveProgressStage } from '../progressEvents';
import type { ProgressEventPayload } from '../../api/dtos';

function event(metadata: Record<string, unknown>, eventType = 'update'): ProgressEventPayload {
  return {
    event_type: eventType,
    timestamp: 0,
    metadata,
    snapshot: {
      completed: 0,
      total: null,
      elapsed: 0,
      speed: 0,
      eta: null,
    },
    error: null,
  };
}

describe('progressEvents', () => {
  it('formats backend stage labels with shared acronym handling', () => {
    expect(formatProgressStageLabel('nas.mirror.start')).toBe('NAS mirror start');
    expect(formatProgressStageLabel('epub_parse')).toBe('EPUB parse');
    expect(formatProgressStageLabel('llm-batch')).toBe('LLM batch');
    expect(formatProgressStageLabel('')).toBeNull();
  });

  it('resolves explicit event metadata stage before completion fallback', () => {
    expect(resolveProgressStage(event({ stage: 'tts.render' }))).toBe('tts.render');
    expect(resolveProgressStage(event({}, 'complete'))).toBe('media');
    expect(resolveProgressStage(event({}))).toBeNull();
  });
});
