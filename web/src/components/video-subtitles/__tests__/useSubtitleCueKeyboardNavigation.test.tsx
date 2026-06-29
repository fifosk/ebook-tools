import { act, renderHook } from '@testing-library/react';
import type { MutableRefObject } from 'react';
import { describe, expect, it, vi } from 'vitest';
import type { AssSubtitleCue } from '../../../lib/subtitles';
import { useSubtitleCueKeyboardNavigation } from '../useSubtitleCueKeyboardNavigation';

const CUES: AssSubtitleCue[] = [
  { start: 1, end: 3, tracks: { translation: { tokens: ['one'], currentIndex: 0 } } },
  { start: 4, end: 6, tracks: { translation: { tokens: ['two'], currentIndex: 0 } } },
  { start: 8, end: 10, tracks: { translation: { tokens: ['three'], currentIndex: 0 } } },
];

function videoRef({
  currentTime = 0,
  paused = false,
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

function keyEvent(key: string, code = key): KeyboardEvent {
  return new KeyboardEvent('keydown', {
    key,
    code,
    bubbles: true,
    cancelable: true,
  });
}

describe('useSubtitleCueKeyboardNavigation', () => {
  it('seeks to adjacent cues and commits the active cue index', () => {
    const commitActiveCueIndex = vi.fn();
    const activeCueIndexRef = { current: 0 };
    const ref = videoRef({ currentTime: 1.5, paused: false });
    const { result } = renderHook(() =>
      useSubtitleCueKeyboardNavigation({
        videoRef: ref,
        cues: CUES,
        activeCueIndexRef,
        overlayActive: true,
        isPlaying: true,
        openSelectionLookup: vi.fn(),
        commitActiveCueIndex,
      }),
    );

    act(() => {
      expect(result.current.seekCueByOffset(1)).toBe(true);
    });

    expect(ref.current?.currentTime).toBeCloseTo(4.001);
    expect(commitActiveCueIndex).toHaveBeenCalledWith(1);
  });

  it('uses the insertion point when playback is between cues', () => {
    const commitActiveCueIndex = vi.fn();
    const ref = videoRef({ currentTime: 6.5, paused: false });
    const { result } = renderHook(() =>
      useSubtitleCueKeyboardNavigation({
        videoRef: ref,
        cues: CUES,
        activeCueIndexRef: { current: -1 },
        overlayActive: true,
        isPlaying: true,
        openSelectionLookup: vi.fn(),
        commitActiveCueIndex,
      }),
    );

    act(() => {
      expect(result.current.seekCueByOffset(-1)).toBe(true);
    });

    expect(ref.current?.currentTime).toBeCloseTo(4.001);
    expect(commitActiveCueIndex).toHaveBeenCalledWith(1);
  });

  it('opens selection lookup with Enter while paused and ignores typing targets', () => {
    const openSelectionLookup = vi.fn(() => true);
    const ref = videoRef({ currentTime: 1.5, paused: true });
    renderHook(() =>
      useSubtitleCueKeyboardNavigation({
        videoRef: ref,
        cues: CUES,
        activeCueIndexRef: { current: 0 },
        overlayActive: true,
        isPlaying: false,
        openSelectionLookup,
        commitActiveCueIndex: vi.fn(),
      }),
    );

    const enter = keyEvent('Enter');
    act(() => {
      window.dispatchEvent(enter);
    });

    expect(openSelectionLookup).toHaveBeenCalledTimes(1);
    expect(enter.defaultPrevented).toBe(true);

    const input = document.createElement('input');
    document.body.appendChild(input);
    const inputEnter = keyEvent('Enter');
    act(() => {
      input.dispatchEvent(inputEnter);
    });
    input.remove();

    expect(openSelectionLookup).toHaveBeenCalledTimes(1);
    expect(inputEnter.defaultPrevented).toBe(false);
  });

  it('maps global arrows to cue seeks only while the video is playing', () => {
    const commitActiveCueIndex = vi.fn();
    let paused = false;
    let currentTime = 1.5;
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
    const ref = { current: video } as MutableRefObject<HTMLVideoElement | null>;
    renderHook(() =>
      useSubtitleCueKeyboardNavigation({
        videoRef: ref,
        cues: CUES,
        activeCueIndexRef: { current: 0 },
        overlayActive: true,
        isPlaying: true,
        openSelectionLookup: vi.fn(),
        commitActiveCueIndex,
      }),
    );

    const right = keyEvent('ArrowRight');
    act(() => {
      window.dispatchEvent(right);
    });

    expect(ref.current?.currentTime).toBeCloseTo(4.001);
    expect(commitActiveCueIndex).toHaveBeenCalledWith(1);
    expect(right.defaultPrevented).toBe(true);

    paused = true;
    const left = keyEvent('ArrowLeft');
    act(() => {
      window.dispatchEvent(left);
    });

    expect(commitActiveCueIndex).toHaveBeenCalledTimes(1);
    expect(left.defaultPrevented).toBe(false);
  });
});
