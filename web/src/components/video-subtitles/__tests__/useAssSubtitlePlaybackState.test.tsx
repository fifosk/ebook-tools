import { act, renderHook } from '@testing-library/react';
import type { MutableRefObject } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AssSubtitleCue } from '../../../lib/subtitles';
import { useAssSubtitlePlaybackState } from '../useAssSubtitlePlaybackState';

const CUES: AssSubtitleCue[] = [
  { start: 1, end: 3, tracks: { translation: { tokens: ['one'], currentIndex: 0 } } },
  { start: 4, end: 6, tracks: { translation: { tokens: ['two'], currentIndex: 0 } } },
];

function videoRef({
  currentTime = 0,
  paused = true,
}: {
  currentTime?: number;
  paused?: boolean;
} = {}): MutableRefObject<HTMLVideoElement | null> {
  const video = document.createElement('video');
  Object.defineProperty(video, 'paused', {
    configurable: true,
    get: () => paused,
  });
  Object.defineProperty(video, 'currentTime', {
    configurable: true,
    get: () => currentTime,
    set: (value: number) => {
      currentTime = value;
    },
  });
  return { current: video };
}

describe('useAssSubtitlePlaybackState', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('resolves the active cue on mount and paused seek updates', () => {
    const ref = videoRef({ currentTime: 1.5, paused: true });
    const { result } = renderHook(() =>
      useAssSubtitlePlaybackState({ videoRef: ref, cues: CUES, overlayActive: true }),
    );

    expect(result.current.activeCueIndex).toBe(0);
    expect(result.current.activeCueIndexRef.current).toBe(0);
    expect(result.current.isPlaying).toBe(false);

    act(() => {
      ref.current!.currentTime = 4.5;
      ref.current?.dispatchEvent(new Event('timeupdate'));
    });

    expect(result.current.activeCueIndex).toBe(1);
    expect(result.current.activeCueIndexRef.current).toBe(1);
  });

  it('tracks play and pause state while cleaning up animation frames', () => {
    let paused = true;
    const video = document.createElement('video');
    Object.defineProperty(video, 'paused', {
      configurable: true,
      get: () => paused,
    });
    Object.defineProperty(video, 'currentTime', {
      configurable: true,
      value: 4.5,
      writable: true,
    });
    const requestAnimationFrameSpy = vi
      .spyOn(window, 'requestAnimationFrame')
      .mockImplementation(() => 23);
    const cancelAnimationFrameSpy = vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
    const ref = { current: video } as MutableRefObject<HTMLVideoElement | null>;
    const { result, unmount } = renderHook(() =>
      useAssSubtitlePlaybackState({ videoRef: ref, cues: CUES, overlayActive: true }),
    );

    act(() => {
      paused = false;
      video.dispatchEvent(new Event('play'));
    });

    expect(result.current.isPlaying).toBe(true);
    expect(requestAnimationFrameSpy).toHaveBeenCalled();

    act(() => {
      paused = true;
      video.dispatchEvent(new Event('pause'));
    });

    expect(result.current.isPlaying).toBe(false);
    expect(result.current.activeCueIndex).toBe(1);
    expect(cancelAnimationFrameSpy).toHaveBeenCalledWith(23);

    unmount();
  });

  it('resets inactive overlays and allows explicit active cue commits', () => {
    const ref = videoRef({ currentTime: 1.5, paused: true });
    const { result, rerender } = renderHook(
      ({ overlayActive }) =>
        useAssSubtitlePlaybackState({ videoRef: ref, cues: CUES, overlayActive }),
      { initialProps: { overlayActive: true } },
    );

    expect(result.current.activeCueIndex).toBe(0);

    act(() => {
      result.current.commitActiveCueIndex(1);
    });
    expect(result.current.activeCueIndex).toBe(1);
    expect(result.current.activeCueIndexRef.current).toBe(1);

    rerender({ overlayActive: false });

    expect(result.current.activeCueIndex).toBe(-1);
    expect(result.current.activeCueIndexRef.current).toBe(-1);
    expect(result.current.isPlaying).toBe(false);
  });
});
