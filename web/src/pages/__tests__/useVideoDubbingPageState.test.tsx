import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import {
  useVideoDubbingInitialRefresh,
  useVideoDubbingPageState
} from '../video-dubbing/useVideoDubbingPageState';

describe('useVideoDubbingPageState', () => {
  it('starts on the video source tab with no status or handoff extras', () => {
    const { result } = renderHook(() => useVideoDubbingPageState());

    expect(result.current.activeTab).toBe('videos');
    expect(result.current.statusMessage).toBeNull();
    expect(result.current.templatePayloadExtras).toBeNull();
  });

  it('updates active tab and status message independently', () => {
    const { result } = renderHook(() => useVideoDubbingPageState());

    act(() => {
      result.current.setActiveTab('metadata');
      result.current.setStatusMessage('Download Station task completed.');
    });

    expect(result.current.activeTab).toBe('metadata');
    expect(result.current.statusMessage).toBe('Download Station task completed.');
  });

  it('normalizes safe creation-template handoff source extras', () => {
    const { result, rerender } = renderHook(
      ({ source }: { source: string | null }) =>
        useVideoDubbingPageState({ creationTemplateHandoffSource: source }),
      {
        initialProps: { source: ' Apple_Create ' }
      }
    );

    expect(result.current.templatePayloadExtras).toEqual({ handoff_source: 'apple_create' });

    rerender({ source: 'not safe!' });

    expect(result.current.templatePayloadExtras).toBeNull();
  });

  it('runs the initial library refresh once on mount', () => {
    const firstRefresh = vi.fn();
    const secondRefresh = vi.fn();
    const { rerender } = renderHook(
      ({ onRefresh }: { onRefresh: () => void }) => useVideoDubbingInitialRefresh(onRefresh),
      {
        initialProps: { onRefresh: firstRefresh }
      }
    );

    expect(firstRefresh).toHaveBeenCalledTimes(1);

    rerender({ onRefresh: secondRefresh });

    expect(firstRefresh).toHaveBeenCalledTimes(1);
    expect(secondRefresh).not.toHaveBeenCalled();
  });
});
