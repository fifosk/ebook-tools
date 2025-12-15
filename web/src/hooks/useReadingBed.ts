import { useCallback, useEffect, useMemo, useRef } from 'react';

const clamp01 = (value: number) => Math.min(Math.max(value, 0), 1);

function normaliseAudioSrc(src: string): string {
  const trimmed = src.trim();
  if (!trimmed) {
    return '';
  }
  if (typeof window === 'undefined') {
    return trimmed;
  }
  try {
    return new URL(trimmed, window.location.href).toString();
  } catch {
    return trimmed;
  }
}

export type ReadingBedHandle = {
  supported: boolean;
  play: () => Promise<void>;
  pause: () => Promise<void>;
  setVolume: (volume: number) => void;
  setSource: (src: string | null) => void;
};

export function useReadingBed(): ReadingBedHandle {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const desiredPlayingRef = useRef(false);
  const desiredSourceRef = useRef<string | null>(null);
  const volumeRef = useRef(0);

  const supported = typeof window !== 'undefined' && typeof Audio === 'function';

  const ensureAudio = useCallback(() => {
    if (!supported) {
      return null;
    }
    if (audioRef.current) {
      return audioRef.current;
    }
    const audio = new Audio();
    audio.preload = 'auto';
    audio.loop = true;
    audio.volume = volumeRef.current;
    audioRef.current = audio;
    return audio;
  }, [supported]);

  const setSource = useCallback(
    (src: string | null) => {
      desiredSourceRef.current = src ? normaliseAudioSrc(src) : null;
      const audio = ensureAudio();
      if (!audio) {
        return;
      }
      const resolved = src?.trim() ? normaliseAudioSrc(src) : '';
      if (audio.src !== resolved) {
        audio.pause();
        audio.src = resolved;
        audio.currentTime = 0;
        if (resolved && desiredPlayingRef.current) {
          void audio.play().catch(() => undefined);
        }
      }
    },
    [ensureAudio],
  );

  const setVolume = useCallback(
    (volume: number) => {
      const clamped = clamp01(volume);
      volumeRef.current = clamped;
      const audio = audioRef.current;
      if (!audio) {
        return;
      }
      audio.volume = clamped;
    },
    [],
  );

  const play = useCallback(async () => {
    desiredPlayingRef.current = true;
    const audio = ensureAudio();
    if (!audio) {
      return;
    }
    const desiredSource = desiredSourceRef.current;
    if (!desiredSource || !desiredSource.trim()) {
      return;
    }
    const resolved = normaliseAudioSrc(desiredSource);
    if (audio.src !== resolved) {
      audio.src = resolved;
      audio.currentTime = 0;
    }
    audio.volume = volumeRef.current;
    try {
      await audio.play();
    } catch {
      // Autoplay restrictions: ignored until a user gesture.
    }
  }, [ensureAudio]);

  const pause = useCallback(async () => {
    desiredPlayingRef.current = false;
    const audio = audioRef.current;
    if (!audio) {
      return;
    }
    try {
      audio.pause();
    } catch {
      // Ignore.
    }
  }, []);

  useEffect(() => {
    if (typeof document === 'undefined') {
      return;
    }
    const handleVisibility = () => {
      const audio = audioRef.current;
      if (!audio) {
        return;
      }
      if (document.visibilityState !== 'visible') {
        audio.pause();
        return;
      }
      if (desiredPlayingRef.current) {
        void audio.play().catch(() => undefined);
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, []);

  useEffect(() => {
    return () => {
      const audio = audioRef.current;
      audioRef.current = null;
      if (!audio) {
        return;
      }
      try {
        audio.pause();
        audio.src = '';
      } catch {
        // Ignore.
      }
    };
  }, []);

  return useMemo(() => ({ supported, play, pause, setVolume, setSource }), [pause, play, setSource, setVolume, supported]);
}
