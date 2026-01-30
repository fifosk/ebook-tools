import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
} from 'react';
import type {
  AudioHTMLAttributes,
  MutableRefObject,
  RefCallback,
} from 'react';
import { isLargeSeek } from '../utils/timingSearch';

export type PlayerCoreEvent = 'time' | 'rate' | 'seeked' | 'playing' | 'paused';

type PlayerCoreEventPayload = {
  time: number;
  rate: number;
  seeked: number;
  playing: undefined;
  paused: undefined;
};

type PlayerCoreEventCallback<T extends PlayerCoreEvent> = PlayerCoreEventPayload[T] extends void
  ? () => void
  : (payload: PlayerCoreEventPayload[T]) => void;

type CallbackRegistry = {
  [Type in PlayerCoreEvent]: Set<(payload: PlayerCoreEventPayload[Type]) => void>;
};

export interface PlayerCoreHandle {
  play(): Promise<void> | void;
  pause(): void;
  seek(time: number): void;
  setRate(rate: number): void;
  getCurrentTime(): number;
  getRate(): number;
  getDuration(): number;
  isPaused(): boolean;
  getElement(): HTMLAudioElement | null;
  on<T extends PlayerCoreEvent>(
    event: T,
    callback: PlayerCoreEventCallback<T>
  ): () => void;
}

type MediaRefProp =
  | MutableRefObject<HTMLAudioElement | null>
  | RefCallback<HTMLAudioElement | null>;

export interface PlayerCoreProps extends Omit<AudioHTMLAttributes<HTMLAudioElement>, 'ref'> {
  mediaRef?: MediaRefProp;
}

const DEFAULT_PRELOAD: HTMLMediaElement['preload'] = 'auto';

function assignMediaRef(ref: MediaRefProp | undefined, element: HTMLAudioElement | null): void {
  if (!ref) {
    return;
  }
  if (typeof ref === 'function') {
    ref(element);
    return;
  }
  ref.current = element;
}

function sanitiseTime(value: number | null | undefined): number {
  if (typeof value !== 'number' || Number.isNaN(value) || !Number.isFinite(value)) {
    return 0;
  }
  return value < 0 ? 0 : value;
}

function sanitiseRate(value: number | null | undefined): number {
  if (typeof value !== 'number' || Number.isNaN(value) || !Number.isFinite(value) || value <= 0) {
    return 1;
  }
  return value;
}

const PlayerCore = forwardRef<PlayerCoreHandle, PlayerCoreProps>(function PlayerCoreComponent(
  props,
  ref
) {
  const { preload = DEFAULT_PRELOAD, mediaRef, src, children, ...rest } = props;
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const playingRef = useRef(false);
  const rafRef = useRef<number | null>(null);
  const lastTimeRef = useRef(0);
  const lastRateRef = useRef(1);
  const lastSeekTimeRef = useRef<number | null>(null);
  const lastEmittedTimeRef = useRef<number | null>(null);
  const initialisedRef = useRef(false);

  const listenersRef = useRef<CallbackRegistry>({
    time: new Set(),
    rate: new Set(),
    seeked: new Set(),
    playing: new Set(),
    paused: new Set(),
  });

  const emit = useCallback(
    <T extends PlayerCoreEvent>(event: T, payload: PlayerCoreEventPayload[T]) => {
      const listeners = listenersRef.current[event];
      if (!listeners || listeners.size === 0) {
        return;
      }
      listeners.forEach((listener) => {
        try {
          listener(payload);
        } catch {
          // Listeners are user-land; swallow errors to avoid cascading failures.
        }
      });
    },
    []
  );

  const updateTime = useCallback(
    (time: number) => {
      lastTimeRef.current = time;
      if (lastEmittedTimeRef.current === time) {
        return;
      }
      lastEmittedTimeRef.current = time;
      emit('time', time);
    },
    [emit]
  );

  const notifySeek = useCallback(
    (time: number) => {
      const clamped = time < 0 ? 0 : time;
      lastSeekTimeRef.current = clamped;
      initialisedRef.current = true;
      lastEmittedTimeRef.current = null;
      updateTime(clamped);
      emit('seeked', clamped);
    },
    [emit, updateTime]
  );

  const sampleTime = useCallback(() => {
    const element = audioRef.current;
    if (!element) {
      return;
    }
    const current = sanitiseTime(element.currentTime);
    if (
      initialisedRef.current &&
      isLargeSeek(lastTimeRef.current, current) &&
      lastSeekTimeRef.current !== current
    ) {
      notifySeek(current);
      return;
    }
    updateTime(current);
    initialisedRef.current = true;
  }, [notifySeek, updateTime]);

  const cancelAnimation = useCallback(() => {
    if (rafRef.current !== null) {
      if (typeof window !== 'undefined') {
        window.cancelAnimationFrame(rafRef.current);
      }
      rafRef.current = null;
    }
  }, []);

  const ensureAnimation = useCallback(() => {
    if (typeof window === 'undefined') {
      sampleTime();
      return;
    }
    if (rafRef.current !== null) {
      return;
    }
    const tick = () => {
      sampleTime();
      if (playingRef.current) {
        rafRef.current = window.requestAnimationFrame(tick);
      } else {
        rafRef.current = null;
      }
    };
    rafRef.current = window.requestAnimationFrame(tick);
  }, [sampleTime]);

  useEffect(() => {
    const element = audioRef.current;
    assignMediaRef(mediaRef, element);
    if (!element) {
      return;
    }
    lastTimeRef.current = sanitiseTime(element.currentTime);
    lastRateRef.current = sanitiseRate(element.playbackRate);
    initialisedRef.current = false;
    lastSeekTimeRef.current = null;
    lastEmittedTimeRef.current = null;

    const handlePlay = () => {
      playingRef.current = true;
      emit('playing', undefined);
      ensureAnimation();
    };

    const handlePause = () => {
      playingRef.current = false;
      cancelAnimation();
      emit('paused', undefined);
      sampleTime();
    };

    const handleRateChange = () => {
      const rate = sanitiseRate(element.playbackRate);
      if (rate === lastRateRef.current) {
        return;
      }
      lastRateRef.current = rate;
      emit('rate', rate);
    };

    const handleSeeked = () => {
      notifySeek(sanitiseTime(element.currentTime));
    };

    const handleTimeUpdate = () => {
      if (playingRef.current) {
        return;
      }
      sampleTime();
    };

    const handleLoadedMetadata = () => {
      sampleTime();
    };

    const handleSeeking = () => {
      initialisedRef.current = false;
    };

    element.addEventListener('play', handlePlay);
    element.addEventListener('playing', handlePlay);
    element.addEventListener('pause', handlePause);
    element.addEventListener('timeupdate', handleTimeUpdate);
    element.addEventListener('ratechange', handleRateChange);
    element.addEventListener('seeked', handleSeeked);
    element.addEventListener('loadedmetadata', handleLoadedMetadata);
    element.addEventListener('seeking', handleSeeking);

    return () => {
      element.removeEventListener('play', handlePlay);
      element.removeEventListener('playing', handlePlay);
      element.removeEventListener('pause', handlePause);
      element.removeEventListener('timeupdate', handleTimeUpdate);
      element.removeEventListener('ratechange', handleRateChange);
      element.removeEventListener('seeked', handleSeeked);
      element.removeEventListener('loadedmetadata', handleLoadedMetadata);
      element.removeEventListener('seeking', handleSeeking);
      cancelAnimation();
      playingRef.current = false;
      assignMediaRef(mediaRef, null);
    };
  }, [mediaRef, cancelAnimation, ensureAnimation, sampleTime, notifySeek]);

  useEffect(() => {
    return () => {
      cancelAnimation();
      listenersRef.current.time.clear();
      listenersRef.current.rate.clear();
      listenersRef.current.seeked.clear();
      listenersRef.current.playing.clear();
      listenersRef.current.paused.clear();
    };
  }, [cancelAnimation]);

  // Track previous src to detect changes
  const prevSrcRef = useRef<string | undefined>(src);
  useEffect(() => {
    const element = audioRef.current;
    if (!element) {
      prevSrcRef.current = src;
      return;
    }
    // If src changed, we need to explicitly load the new source
    if (prevSrcRef.current !== src && src) {
      prevSrcRef.current = src;
      // Reset state for the new source
      initialisedRef.current = false;
      lastSeekTimeRef.current = null;
      lastEmittedTimeRef.current = null;
      // Load the new source - this will trigger loadedmetadata when ready
      element.load();
      if (import.meta.env.DEV) {
        console.debug('[PlayerCore] src changed, calling load()', {
          newSrc: src,
        });
      }
    } else {
      prevSrcRef.current = src;
    }
  }, [src]);

  const setAudioRef = useCallback(
    (node: HTMLAudioElement | null) => {
      audioRef.current = node;
      assignMediaRef(mediaRef, node);
    },
    [mediaRef]
  );

  const handle = useMemo<PlayerCoreHandle>(() => {
    return {
      play: () => {
        const element = audioRef.current;
        if (!element) {
          return;
        }
        try {
          const result = element.play();
          if (result && typeof result.catch === 'function') {
            result.catch(() => undefined);
          }
          return result;
        } catch {
          return undefined;
        }
      },
      pause: () => {
        const element = audioRef.current;
        if (!element) {
          return;
        }
        try {
          element.pause();
        } catch {
          // Ignored: environments without media support may throw.
        }
      },
      seek: (time: number) => {
        const element = audioRef.current;
        if (!element) {
          return;
        }
        const target = sanitiseTime(time);
        if (Math.abs(element.currentTime - target) < 1e-3) {
          return;
        }
        try {
          element.currentTime = target;
        } catch {
          // Ignore seek failures in restricted environments.
        }
      },
      setRate: (rate: number) => {
        const element = audioRef.current;
        if (!element) {
          return;
        }
        const safeRate = sanitiseRate(rate);
        if (Math.abs(element.playbackRate - safeRate) < 1e-3) {
          return;
        }
        element.playbackRate = safeRate;
        lastRateRef.current = safeRate;
        emit('rate', safeRate);
      },
      getCurrentTime: () => {
        const element = audioRef.current;
        return sanitiseTime(element?.currentTime);
      },
      getRate: () => {
        const element = audioRef.current;
        return sanitiseRate(element?.playbackRate ?? lastRateRef.current);
      },
      getDuration: () => {
        const element = audioRef.current;
        const raw = element?.duration;
        if (typeof raw !== 'number' || Number.isNaN(raw) || !Number.isFinite(raw) || raw <= 0) {
          return 0;
        }
        return raw;
      },
      isPaused: () => {
        const element = audioRef.current;
        if (!element) {
          return true;
        }
        return element.paused;
      },
      getElement: () => audioRef.current,
      on: <T extends PlayerCoreEvent>(event: T, callback: PlayerCoreEventCallback<T>) => {
        const set = listenersRef.current[event] as Set<PlayerCoreEventCallback<T>>;
        set.add(callback);
        return () => {
          set.delete(callback);
        };
      },
    };
  }, [emit]);

  useImperativeHandle(ref, () => handle, [handle]);

  return (
    <audio {...rest} ref={setAudioRef} preload={preload} src={src}>
      {children}
    </audio>
  );
});

export default PlayerCore;
