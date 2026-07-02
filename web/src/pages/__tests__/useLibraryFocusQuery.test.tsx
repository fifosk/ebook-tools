import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  useLibraryFocusQuery,
  type LibraryFocusRequest,
} from '../library/useLibraryFocusQuery';

const focusRequest: LibraryFocusRequest = {
  jobId: 'job-123',
  itemType: 'video',
  token: 1,
};

describe('useLibraryFocusQuery', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    act(() => {
      vi.runOnlyPendingTimers();
    });
    vi.useRealTimers();
  });

  it('debounces ordinary query changes before exposing the effective query', () => {
    const applyFocusRequest = vi.fn();
    const { result } = renderHook(() =>
      useLibraryFocusQuery({
        focusRequest: null,
        onApplyFocusRequest: applyFocusRequest,
      }),
    );

    act(() => {
      result.current.handleQueryChange('dan brown');
    });

    expect(result.current.query).toBe('dan brown');
    expect(result.current.effectiveQuery).toBe('');
    expect(applyFocusRequest).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(249);
    });
    expect(result.current.effectiveQuery).toBe('');

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(result.current.effectiveQuery).toBe('dan brown');
  });

  it('applies external focus requests immediately and consumes them once', () => {
    const applyFocusRequest = vi.fn();
    const consumeFocusRequest = vi.fn();
    const { result, rerender } = renderHook((request: LibraryFocusRequest | null) =>
      useLibraryFocusQuery({
        focusRequest: request,
        onConsumeFocusRequest: consumeFocusRequest,
        onApplyFocusRequest: applyFocusRequest,
      }),
      { initialProps: null as LibraryFocusRequest | null },
    );

    act(() => {
      rerender(focusRequest);
    });

    expect(result.current.query).toBe('job-123');
    expect(result.current.effectiveQuery).toBe('job-123');
    expect(result.current.pendingFocus).toEqual(focusRequest);
    expect(consumeFocusRequest).toHaveBeenCalledTimes(1);
    expect(applyFocusRequest).toHaveBeenCalledWith(focusRequest);
  });

  it('clears a pending focus request when the user searches for another job', () => {
    const applyFocusRequest = vi.fn();
    const { result, rerender } = renderHook((request: LibraryFocusRequest | null) =>
      useLibraryFocusQuery({
        focusRequest: request,
        onApplyFocusRequest: applyFocusRequest,
      }),
      { initialProps: null as LibraryFocusRequest | null },
    );

    act(() => {
      rerender(focusRequest);
    });

    act(() => {
      result.current.handleQueryChange('other-job');
    });

    expect(result.current.query).toBe('other-job');
    expect(result.current.pendingFocus).toBeNull();
  });

  it('allows the page to clear matched focus requests after selecting an item', () => {
    const applyFocusRequest = vi.fn();
    const { result, rerender } = renderHook((request: LibraryFocusRequest | null) =>
      useLibraryFocusQuery({
        focusRequest: request,
        onApplyFocusRequest: applyFocusRequest,
      }),
      { initialProps: null as LibraryFocusRequest | null },
    );

    act(() => {
      rerender(focusRequest);
    });

    expect(result.current.pendingFocus).toEqual(focusRequest);

    act(() => {
      result.current.clearPendingFocus();
    });

    expect(result.current.pendingFocus).toBeNull();
  });
});
