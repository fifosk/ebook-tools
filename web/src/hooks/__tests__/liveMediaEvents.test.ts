import { describe, expect, it } from 'vitest';
import type { ProgressEventPayload } from '../../api/dtos';
import {
  liveMediaEventMetadata,
  resolveLiveMediaEventAction,
  shouldRefreshMediaFromEvent,
} from '../liveMediaEvents';

const baseEvent: ProgressEventPayload = {
  event_type: 'progress',
  timestamp: 1,
  metadata: {},
  snapshot: { completed: 0, total: null, elapsed: 0, speed: 0, eta: null },
  error: null,
};

describe('liveMediaEvents', () => {
  it('requests a final media refresh for complete events and complete progress stages', () => {
    expect(shouldRefreshMediaFromEvent({ ...baseEvent, event_type: 'complete' })).toBe(true);
    expect(shouldRefreshMediaFromEvent({
      ...baseEvent,
      metadata: { stage: 'complete', generated_files: { files: [] } },
    })).toBe(true);
    expect(resolveLiveMediaEventAction({
      ...baseEvent,
      metadata: { stage: 'complete', generated_files: { files: [] } },
    })).toEqual({ kind: 'refresh' });
  });

  it('recognizes media reset snapshots before chunk merges', () => {
    const generatedFiles = { files: [{ type: 'audio', path: 'audio/001.mp3' }] };

    expect(resolveLiveMediaEventAction({
      ...baseEvent,
      metadata: {
        media_reset: true,
        generated_files: generatedFiles,
      },
    })).toEqual({ kind: 'reset', generatedFiles });
  });

  it('recognizes generated file chunks as merge events', () => {
    const generatedFiles = { files: [{ type: 'html', path: 'html/001.html' }] };

    expect(resolveLiveMediaEventAction({
      ...baseEvent,
      event_type: 'file_chunk_generated',
      metadata: { generated_files: generatedFiles },
    })).toEqual({ kind: 'merge', generatedFiles });
  });

  it('ignores ordinary progress and malformed metadata', () => {
    expect(resolveLiveMediaEventAction(baseEvent)).toEqual({ kind: 'ignore' });
    expect(resolveLiveMediaEventAction({
      ...baseEvent,
      metadata: null as unknown as Record<string, unknown>,
    })).toEqual({ kind: 'ignore' });
    expect(liveMediaEventMetadata({
      ...baseEvent,
      metadata: null as unknown as Record<string, unknown>,
    })).toEqual({});
  });
});
