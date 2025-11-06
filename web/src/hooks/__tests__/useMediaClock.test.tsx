import { renderHook } from '@testing-library/react';
import type { MutableRefObject } from 'react';
import { useMediaClock } from '../useLiveMedia';

describe('useMediaClock', () => {
  it('normalises effective time based on playback and tempo', () => {
    const audioElement = {
      currentTime: 12,
      playbackRate: 1.5,
    } as unknown as HTMLAudioElement;
    const ref = { current: audioElement } as MutableRefObject<HTMLAudioElement | null>;
    const { result } = renderHook(() => useMediaClock(ref));

    expect(result.current.mediaTime()).toBe(12);
    expect(result.current.playbackRate()).toBe(1.5);
    expect(result.current.effectiveTime({ trackOffset: 2, tempoFactor: 0.5 })).toBeCloseTo(6.667, 3);
  });

  it('guards against invalid offsets, rates, and tempo factors', () => {
    const audioElement = {
      currentTime: 4,
      playbackRate: 0,
    } as unknown as HTMLAudioElement;
    const ref = { current: audioElement } as MutableRefObject<HTMLAudioElement | null>;
    const { result } = renderHook(() => useMediaClock(ref));

    expect(result.current.playbackRate()).toBe(1);
    expect(result.current.effectiveTime({ trackOffset: 10, tempoFactor: -2 })).toBe(0);

    audioElement.currentTime = 9;
    audioElement.playbackRate = 2;
    expect(result.current.effectiveTime({ trackOffset: 3, tempoFactor: 0 })).toBeCloseTo(3, 3);
  });
});
