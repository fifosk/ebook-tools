import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { useWordHighlighting } from '../useWordHighlighting';
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
          text: 'gamma',
          t0: 1,
          t1: 1.5,
          lane: 'orig',
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

describe('useWordHighlighting', () => {
  it('prevents backward movement inside a segment once revealed', () => {
    const { result } = renderHook(() => useWordHighlighting());

    act(() => {
      timingStore.setPayload(payload);
      timingStore.setLast({ segIndex: 0, tokIndex: 2 });
    });
    expect(result.current.current).toEqual({ segIndex: 0, tokIndex: 2 });

    act(() => {
      timingStore.setLast({ segIndex: 0, tokIndex: 1 });
    });

    expect(result.current.current).toEqual({ segIndex: 0, tokIndex: 2 });
  });
});
