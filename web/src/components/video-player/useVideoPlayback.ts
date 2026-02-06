/**
 * Hook for managing video playback state, position, and controls.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { ExtendedPlaybackControls } from '../../lib/playback';
import { sanitiseRate } from './utils';

export interface UseVideoPlaybackOptions {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  activeFileId: string | null;
  autoPlay: boolean;
  playbackPosition?: number | null;
  playbackRate?: number | null;
  onPlaybackPositionChange?: (position: number) => void;
  onPlaybackStateChange?: (state: 'playing' | 'paused') => void;
  onPlaybackRateChange?: (rate: number) => void;
  onPlaybackEnded?: () => void;
  /** Optional ref for native fullscreen re-entry tracking (provided by useVideoFullscreen when integrated). */
  nativeFullscreenReentryRef?: React.MutableRefObject<boolean>;
}

export interface PlaybackClock {
  current: number;
  duration: number;
}

export interface VideoPlaybackState {
  isPlaying: boolean;
  playbackClock: PlaybackClock;
  handlePlay: () => void;
  handlePause: () => void;
  handleEnded: () => void;
  handleTimeUpdate: () => void;
  handleLoadedData: () => void;
  handleLoadedMetadata: () => void;
  updatePlaybackClock: () => void;
  nativeFullscreenReentryRef: React.MutableRefObject<boolean>;
}

export type PlaybackControls = ExtendedPlaybackControls;

export function useVideoPlayback({
  videoRef,
  activeFileId,
  autoPlay,
  playbackPosition,
  playbackRate,
  onPlaybackPositionChange,
  onPlaybackStateChange,
  onPlaybackRateChange,
  onPlaybackEnded,
  nativeFullscreenReentryRef: externalReentryRef,
}: UseVideoPlaybackOptions): VideoPlaybackState {
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackClock, setPlaybackClock] = useState<PlaybackClock>({ current: 0, duration: 0 });
  const playbackClockRef = useRef<PlaybackClock>({ current: 0, duration: 0 });
  const internalReentryRef = useRef(false);
  const nativeFullscreenReentryRef = externalReentryRef ?? internalReentryRef;

  // Reset clock on file change
  useEffect(() => {
    playbackClockRef.current = { current: 0, duration: 0 };
    setPlaybackClock({ current: 0, duration: 0 });
    setIsPlaying(false);
  }, [activeFileId]);

  const updatePlaybackClock = useCallback(() => {
    const element = videoRef.current;
    if (!element) {
      return;
    }
    const nextCurrent = Number.isFinite(element.currentTime) ? Math.max(0, Math.floor(element.currentTime)) : 0;
    const nextDuration = Number.isFinite(element.duration) ? Math.max(0, Math.floor(element.duration)) : 0;
    const last = playbackClockRef.current;
    if (last.current === nextCurrent && last.duration === nextDuration) {
      return;
    }
    playbackClockRef.current = { current: nextCurrent, duration: nextDuration };
    setPlaybackClock({ current: nextCurrent, duration: nextDuration });
  }, [videoRef]);

  const attemptAutoplay = useCallback(() => {
    if (!autoPlay) {
      return;
    }

    const element = videoRef.current;
    if (!element) {
      return;
    }

    try {
      const playResult = element.play();
      if (playResult && typeof playResult.then === 'function') {
        playResult.catch(() => {
          // Ignore autoplay rejections triggered by browser or test environments.
        });
      }
    } catch (error) {
      // Ignore autoplay errors that stem from user gesture requirements.
    }
  }, [autoPlay, videoRef]);

  const handlePlay = useCallback(() => {
    setIsPlaying(true);
    onPlaybackStateChange?.('playing');
  }, [onPlaybackStateChange]);

  const handlePause = useCallback(() => {
    setIsPlaying(false);
    onPlaybackStateChange?.('paused');
  }, [onPlaybackStateChange]);

  const handleEnded = useCallback(() => {
    const element = videoRef.current;
    const isNativeFullscreen = Boolean(element && (element as unknown as { webkitDisplayingFullscreen?: boolean }).webkitDisplayingFullscreen);
    nativeFullscreenReentryRef.current = isNativeFullscreen;
    setIsPlaying(false);
    onPlaybackStateChange?.('paused');
    onPlaybackEnded?.();
  }, [onPlaybackEnded, onPlaybackStateChange, videoRef]);

  const handleTimeUpdate = useCallback(() => {
    const element = videoRef.current;
    if (!element) {
      return;
    }
    updatePlaybackClock();
    onPlaybackPositionChange?.(element.currentTime ?? 0);
  }, [onPlaybackPositionChange, updatePlaybackClock, videoRef]);

  const handleLoadedData = useCallback(() => {
    attemptAutoplay();
    updatePlaybackClock();
  }, [attemptAutoplay, updatePlaybackClock]);

  const handleLoadedMetadata = useCallback(() => {
    updatePlaybackClock();
  }, [updatePlaybackClock]);

  // Attempt autoplay on file change
  useEffect(() => {
    attemptAutoplay();
  }, [attemptAutoplay, activeFileId]);

  // Apply playback position
  useEffect(() => {
    const element = videoRef.current;
    if (!element || playbackPosition === null || playbackPosition === undefined) {
      return;
    }

    const clamped = Number.isFinite(playbackPosition) ? Math.max(playbackPosition, 0) : 0;

    if (Math.abs(element.currentTime - clamped) < 0.25) {
      return;
    }

    try {
      element.currentTime = clamped;
    } catch (error) {
      // Ignore assignment failures that can happen in non-media test environments.
    }
    updatePlaybackClock();
  }, [playbackPosition, activeFileId, updatePlaybackClock, videoRef]);

  // Apply playback rate
  useEffect(() => {
    const element = videoRef.current;
    if (!element) {
      return;
    }
    const safeRate = sanitiseRate(playbackRate);
    if (Math.abs(element.playbackRate - safeRate) < 1e-3) {
      return;
    }
    element.playbackRate = safeRate;
  }, [playbackRate, activeFileId, videoRef]);

  // Listen for rate change events
  useEffect(() => {
    const element = videoRef.current;
    if (!element || !onPlaybackRateChange) {
      return;
    }
    const handleRateChange = () => {
      onPlaybackRateChange(sanitiseRate(element.playbackRate));
    };
    element.addEventListener('ratechange', handleRateChange);
    return () => {
      element.removeEventListener('ratechange', handleRateChange);
    };
  }, [onPlaybackRateChange, activeFileId, videoRef]);

  return {
    isPlaying,
    playbackClock,
    handlePlay,
    handlePause,
    handleEnded,
    handleTimeUpdate,
    handleLoadedData,
    handleLoadedMetadata,
    updatePlaybackClock,
    nativeFullscreenReentryRef,
  };
}

/**
 * Creates playback controls for external registration.
 */
export function createPlaybackControls(
  videoRef: React.RefObject<HTMLVideoElement | null>,
  requestFullscreenPlayback: (force?: boolean) => void,
): PlaybackControls {
  return {
    pause: () => {
      const element = videoRef.current;
      if (!element) {
        return;
      }
      try {
        element.pause();
      } catch (error) {
        // Ignore failures triggered by non-media environments.
      }
    },
    play: () => {
      const element = videoRef.current;
      if (!element) {
        return;
      }
      try {
        const playResult = element.play();
        if (playResult && typeof playResult.catch === 'function') {
          playResult.catch(() => undefined);
        }
      } catch (error) {
        // Swallow play failures caused by autoplay policies.
      }
    },
    ensureFullscreen: () => requestFullscreenPlayback(true),
    seek: (time: number) => {
      const element = videoRef.current;
      if (!element) {
        return;
      }
      const clamped = Number.isFinite(time) ? Math.max(time, 0) : 0;
      try {
        element.currentTime = clamped;
      } catch (error) {
        // Ignore assignment failures that can happen in non-media environments.
      }
    },
  };
}
