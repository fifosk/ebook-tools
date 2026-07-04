import { useCallback, useMemo } from 'react';
import type { RefObject } from 'react';
import type { TrackTimingPayload } from '../api/dtos';

export interface MediaClock {
  mediaTime: () => number;
  playbackRate: () => number;
  effectiveTime: (track: Pick<TrackTimingPayload, 'trackOffset' | 'tempoFactor'>) => number;
}

function sanitiseRate(value: number | null | undefined): number {
  if (typeof value !== 'number' || Number.isNaN(value) || !Number.isFinite(value) || value <= 0) {
    return 1;
  }
  return value;
}

export function useMediaClock(audioRef: RefObject<HTMLAudioElement | null>): MediaClock {
  const mediaTime = useCallback(() => {
    const element = audioRef.current;
    if (!element) {
      return 0;
    }
    const raw = element.currentTime;
    if (typeof raw !== 'number' || Number.isNaN(raw) || !Number.isFinite(raw)) {
      return 0;
    }
    return raw;
  }, [audioRef]);

  const effectiveTime = useCallback(
    (track: Pick<TrackTimingPayload, 'trackOffset' | 'tempoFactor'>) => {
      const offset =
        typeof track.trackOffset === 'number' && Number.isFinite(track.trackOffset)
          ? track.trackOffset
          : 0;
      const tempoFactor =
        typeof track.tempoFactor === 'number' && Number.isFinite(track.tempoFactor) && track.tempoFactor > 0
          ? track.tempoFactor
          : 1;
      const adjusted = (mediaTime() - offset) / tempoFactor;
      if (!Number.isFinite(adjusted) || Number.isNaN(adjusted)) {
        return 0;
      }
      return adjusted < 0 ? 0 : adjusted;
    },
    [mediaTime],
  );

  const playbackRate = useCallback(() => {
    const element = audioRef.current;
    return sanitiseRate(element?.playbackRate ?? 1);
  }, [audioRef]);

  return useMemo(
    () => ({
      mediaTime,
      playbackRate,
      effectiveTime,
    }),
    [mediaTime, playbackRate, effectiveTime],
  );
}
