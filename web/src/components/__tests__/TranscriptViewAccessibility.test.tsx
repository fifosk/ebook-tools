import { act, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import TranscriptView from '../transcript/TranscriptView';
import { timingStore } from '../../stores/timingStore';
import type { TimingPayload } from '../../types/timing';

const emptyPayload: TimingPayload = {
  trackKind: 'translation_only',
  segments: [],
};

const payload: TimingPayload = {
  trackKind: 'original_translation_combined',
  segments: [
    {
      id: 'seg-0',
      t0: 0,
      t1: 1.5,
      tokens: [
        {
          id: 'tok-0',
          text: 'alpha',
          t0: 0,
          t1: 0.5,
          lane: 'orig',
          segId: 'seg-0',
        },
        {
          id: 'tok-1',
          text: 'beta',
          t0: 0.5,
          t1: 1,
          lane: 'tran',
          segId: 'seg-0',
        },
        {
          id: 'tok-2',
          text: '',
          t0: 1,
          t1: 1.5,
          lane: 'tran',
          segId: 'seg-0',
        },
      ],
    },
  ],
};

afterEach(() => {
  act(() => {
    timingStore.setPayload(emptyPayload);
    timingStore.setLast(null);
  });
});

describe('TranscriptView accessibility', () => {
  it('announces the current highlighted word through a polite live region', async () => {
    render(<TranscriptView segments={payload.segments} />);

    act(() => {
      timingStore.setPayload(payload);
      timingStore.setLast({ segIndex: 0, tokIndex: 1 });
    });

    expect(await screen.findByRole('status')).toHaveTextContent('Current word: beta');
  });

  it('uses the accessible pause label for silent active tokens', async () => {
    render(<TranscriptView segments={payload.segments} />);

    act(() => {
      timingStore.setPayload(payload);
      timingStore.setLast({ segIndex: 0, tokIndex: 2 });
    });

    expect(await screen.findByRole('status')).toHaveTextContent('Current word: Pause');
  });

  it('clears the live region when playback has no active word', () => {
    render(<TranscriptView segments={payload.segments} />);

    expect(screen.getByRole('status')).toBeEmptyDOMElement();
  });
});
