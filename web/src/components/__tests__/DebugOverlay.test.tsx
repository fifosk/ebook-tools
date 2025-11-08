import { describe, expect, it, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';

import { DebugOverlay } from '../../player/DebugOverlay';
import { timingStore } from '../../stores/timingStore';
import type { TimingPayload } from '../../types/timing';

describe('DebugOverlay', () => {
  afterEach(() => {
    timingStore.setPayload({ trackKind: 'translation_only', segments: [] });
    timingStore.setActiveGate(null);
    timingStore.setLast(null);
    cleanup();
  });

  it('renders lane information when enabled', () => {
    window.__HL_DEBUG__ = { enabled: true, showGates: true, showPauses: true, showDrift: true };
    const payload: TimingPayload = {
      trackKind: 'translation_only',
      segments: [
        {
          id: 'seg-1',
          t0: 0,
          t1: 2,
          sentenceIdx: 3,
          tokens: [
            {
              id: 'tok-1',
              text: 'Hello',
              t0: 0,
              t1: 1,
              lane: 'tran',
              segId: 'seg-1',
              sentenceIdx: 3,
              startGate: 1,
              endGate: 3,
              pauseBeforeMs: 120,
              pauseAfterMs: 80,
              validation: { drift: 0.01, count: 5 },
            },
          ],
        },
      ],
    };

    timingStore.setPayload(payload);
    timingStore.setActiveGate({ start: 1, end: 3, sentenceIdx: 3, segmentIndex: 0 });
    timingStore.setLast({ segIndex: 0, tokIndex: 0, lane: 'translation' });

    const { getByText } = render(<DebugOverlay audioEl={null} />);
    const laneRow = getByText(/Lane:/).parentElement;
    expect(laneRow).not.toBeNull();
    expect(laneRow).toHaveTextContent(/Lane:\s*translation/);
    const sentenceRow = getByText(/SentenceIdx:/).parentElement;
    expect(sentenceRow).not.toBeNull();
    expect(sentenceRow).toHaveTextContent(/SentenceIdx:\s*3/);
  });
});
