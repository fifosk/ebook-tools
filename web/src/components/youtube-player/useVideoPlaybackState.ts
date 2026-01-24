/**
 * Hook for managing video playback state, navigation, and position memory.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { LiveMediaItem } from '../../hooks/useLiveMedia';
import type { NavigationIntent } from '../player-panel/constants';
import {
  DEFAULT_TRANSLATION_SPEED,
  TRANSLATION_SPEED_STEP,
  normaliseTranslationSpeed,
} from '../player-panel/constants';

type MediaCategory = 'text' | 'audio' | 'video';

type PlaybackControls = {
  pause: () => void;
  play: () => void;
  ensureFullscreen?: () => void;
  seek?: (time: number) => void;
};

interface VideoFile {
  id: string;
  url: string;
  name?: string;
}

export interface UseVideoPlaybackStateOptions {
  videoFiles: VideoFile[];
  videoLookup: Map<string, LiveMediaItem>;
  memoryState: {
    currentMediaType: string | null;
    currentMediaId: string | null;
  };
  rememberSelection: (selection: { media: LiveMediaItem & { url: string } }) => void;
  rememberPosition: (position: {
    mediaId: string;
    mediaType: MediaCategory;
    baseId: string | null;
    position: number;
  }) => void;
  getPosition: (mediaId: string) => number;
  deriveBaseId: (item: LiveMediaItem) => string | null;
  onFullscreenChange?: (isFullscreen: boolean) => void;
  onPlaybackStateChange?: (isPlaying: boolean) => void;
  onVideoPlaybackStateChange?: (isPlaying: boolean) => void;
}

export interface VideoPlaybackState {
  /** Currently active video ID */
  activeVideoId: string | null;
  /** Set active video ID */
  setActiveVideoId: React.Dispatch<React.SetStateAction<string | null>>;
  /** Whether video is currently playing */
  isPlaying: boolean;
  /** Whether fullscreen mode is active */
  isFullscreen: boolean;
  /** Current playback speed */
  playbackSpeed: number;
  /** Ref to playback controls */
  controlsRef: React.MutableRefObject<PlaybackControls | null>;
  /** Current playback position */
  playbackPosition: number;
  /** Local position ref for tracking */
  localPositionRef: React.MutableRefObject<number>;
  /** Pending bookmark seek ref */
  pendingBookmarkSeekRef: React.MutableRefObject<{ videoId: string; time: number } | null>;
  /** Navigation state */
  navigationState: {
    disableFirst: boolean;
    disablePrevious: boolean;
    disableNext: boolean;
    disableLast: boolean;
    disablePlayback: boolean;
    disableFullscreen: boolean;
    currentIndex: number;
    videoCount: number;
  };
  /** Handle navigation */
  handleNavigate: (intent: NavigationIntent) => void;
  /** Toggle playback */
  handleTogglePlayback: () => void;
  /** Handle playback state change */
  handlePlaybackStateChange: (state: 'playing' | 'paused') => void;
  /** Handle playback ended */
  handlePlaybackEnded: () => void;
  /** Toggle fullscreen */
  handleToggleFullscreen: () => void;
  /** Handle exit fullscreen */
  handleExitFullscreen: (reason?: 'user' | 'lost') => void;
  /** Register playback controls */
  handleRegisterControls: (controls: PlaybackControls | null) => void;
  /** Handle playback rate change */
  handlePlaybackRateChange: (rate: number) => void;
  /** Adjust playback speed */
  adjustPlaybackSpeed: (direction: 'faster' | 'slower') => void;
  /** Handle playback position change */
  handlePlaybackPositionChange: (position: number) => void;
  /** Reset playback position for a video */
  resetPlaybackPosition: (videoId: string | null) => void;
  /** Apply bookmark seek */
  applyBookmarkSeek: (videoId: string, time: number) => void;
}

export function useVideoPlaybackState({
  videoFiles,
  videoLookup,
  memoryState,
  rememberSelection,
  rememberPosition,
  getPosition,
  deriveBaseId,
  onFullscreenChange,
  onPlaybackStateChange,
  onVideoPlaybackStateChange,
}: UseVideoPlaybackStateOptions): VideoPlaybackState {
  const [activeVideoId, setActiveVideoId] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(DEFAULT_TRANSLATION_SPEED);

  const pendingAutoplayRef = useRef(false);
  const previousFileCountRef = useRef<number>(videoFiles.length);
  const controlsRef = useRef<PlaybackControls | null>(null);
  const lastActivatedVideoRef = useRef<string | null>(null);
  const localPositionRef = useRef<number>(0);
  const pendingBookmarkSeekRef = useRef<{ videoId: string; time: number } | null>(null);

  // Initialize active video from available files or memory
  useEffect(() => {
    const availableIds = videoFiles.map((file) => file.id);
    if (availableIds.length === 0) {
      setActiveVideoId(null);
      return;
    }

    const rememberedId = memoryState.currentMediaType === 'video' ? memoryState.currentMediaId : null;
    setActiveVideoId((current) => {
      if (current && availableIds.includes(current)) {
        return current;
      }
      if (rememberedId && availableIds.includes(rememberedId)) {
        return rememberedId;
      }
      return availableIds[0] ?? null;
    });
  }, [videoFiles, memoryState.currentMediaId, memoryState.currentMediaType]);

  // Remember selection when active video changes
  useEffect(() => {
    if (!activeVideoId) {
      return;
    }
    const match = videoLookup.get(activeVideoId);
    if (match) {
      rememberSelection({ media: { ...match, url: activeVideoId } });
    }
  }, [activeVideoId, rememberSelection, videoLookup]);

  // Reset playing state when video changes
  useEffect(() => {
    setIsPlaying(false);
  }, [activeVideoId]);

  // Update local position when active video changes
  useEffect(() => {
    if (!activeVideoId) {
      localPositionRef.current = 0;
      return;
    }
    localPositionRef.current = getPosition(activeVideoId);
    lastActivatedVideoRef.current = activeVideoId;
  }, [activeVideoId, getPosition]);

  // Notify parent of playback state changes
  useEffect(() => {
    onPlaybackStateChange?.(isPlaying);
    onVideoPlaybackStateChange?.(isPlaying);
  }, [isPlaying, onPlaybackStateChange, onVideoPlaybackStateChange]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      onPlaybackStateChange?.(false);
      onVideoPlaybackStateChange?.(false);
    };
  }, [onPlaybackStateChange, onVideoPlaybackStateChange]);

  // Reassert fullscreen when active video changes
  useEffect(() => {
    if (!isFullscreen) {
      return;
    }
    const timer = window.setTimeout(() => {
      controlsRef.current?.ensureFullscreen?.();
    }, 0);
    return () => {
      window.clearTimeout(timer);
    };
  }, [isFullscreen, activeVideoId]);

  // Handle autoplay when new videos are appended
  useEffect(() => {
    const previousCount = previousFileCountRef.current;
    previousFileCountRef.current = videoFiles.length;

    if (videoFiles.length === 0) {
      pendingAutoplayRef.current = false;
      return;
    }

    const appended = videoFiles.length > previousCount;
    const shouldResume = pendingAutoplayRef.current && appended;
    if (shouldResume) {
      const nextId = videoFiles[videoFiles.length - 1]?.id;
      if (nextId) {
        const match = videoLookup.get(nextId) ?? null;
        const baseId = match ? deriveBaseId(match) : null;
        rememberPosition({
          mediaId: nextId,
          mediaType: 'video',
          baseId,
          position: 0,
        });
        lastActivatedVideoRef.current = nextId;
        setActiveVideoId(nextId);
        setTimeout(() => {
          if (isFullscreen) {
            controlsRef.current?.ensureFullscreen?.();
          }
          controlsRef.current?.play();
        }, 0);
      }
      pendingAutoplayRef.current = false;
    }
  }, [deriveBaseId, isFullscreen, rememberPosition, videoFiles, videoLookup]);

  const resetPlaybackPosition = useCallback(
    (videoId: string | null) => {
      if (!videoId) {
        return;
      }
      const match = videoLookup.get(videoId) ?? null;
      const baseId = match ? deriveBaseId(match) : null;
      rememberPosition({
        mediaId: videoId,
        mediaType: 'video',
        baseId,
        position: 0,
      });
      lastActivatedVideoRef.current = videoId;
    },
    [deriveBaseId, rememberPosition, videoLookup],
  );

  const handleNavigate = useCallback(
    (intent: NavigationIntent) => {
      if (videoFiles.length === 0) {
        return;
      }
      const currentIndex = activeVideoId ? videoFiles.findIndex((file) => file.id === activeVideoId) : -1;
      const lastIndex = videoFiles.length - 1;
      let nextIndex = currentIndex;
      switch (intent) {
        case 'first':
          nextIndex = 0;
          break;
        case 'last':
          nextIndex = lastIndex;
          break;
        case 'previous':
          nextIndex = currentIndex <= 0 ? 0 : currentIndex - 1;
          break;
        case 'next':
          nextIndex = currentIndex < 0 ? 0 : Math.min(currentIndex + 1, lastIndex);
          break;
        default:
          nextIndex = currentIndex;
      }
      if (nextIndex === currentIndex || nextIndex < 0 || nextIndex >= videoFiles.length) {
        return;
      }
      const nextId = videoFiles[nextIndex].id;
      resetPlaybackPosition(nextId);
      setActiveVideoId(nextId);
    },
    [activeVideoId, resetPlaybackPosition, videoFiles],
  );

  const handleTogglePlayback = useCallback(() => {
    if (isPlaying) {
      controlsRef.current?.pause();
    } else {
      controlsRef.current?.play();
    }
  }, [isPlaying]);

  const handlePlaybackStateChange = useCallback((state: 'playing' | 'paused') => {
    setIsPlaying(state === 'playing');
  }, []);

  const handlePlaybackEnded = useCallback(() => {
    setIsPlaying(false);
    const isLast =
      videoFiles.length > 0 &&
      activeVideoId !== null &&
      videoFiles.findIndex((file) => file.id === activeVideoId) === videoFiles.length - 1;
    pendingAutoplayRef.current = isLast;
    handleNavigate('next');
  }, [activeVideoId, handleNavigate, videoFiles]);

  const handleToggleFullscreen = useCallback(() => {
    setIsFullscreen((current) => {
      const next = !current;
      onFullscreenChange?.(next);
      if (next) {
        controlsRef.current?.ensureFullscreen?.();
      }
      return next;
    });
  }, [onFullscreenChange]);

  const handleExitFullscreen = useCallback(
    (reason?: 'user' | 'lost') => {
      if (reason === 'user') {
        setIsFullscreen(false);
        onFullscreenChange?.(false);
        return;
      }
      if (isFullscreen) {
        setTimeout(() => {
          controlsRef.current?.ensureFullscreen?.();
        }, 0);
        return;
      }
      onFullscreenChange?.(false);
    },
    [isFullscreen, onFullscreenChange],
  );

  const applyBookmarkSeek = useCallback(
    (videoId: string, time: number) => {
      const clamped = Math.max(time, 0);
      localPositionRef.current = clamped;
      lastActivatedVideoRef.current = videoId;
      const match = videoLookup.get(videoId) ?? null;
      const baseId = match ? deriveBaseId(match) : null;
      rememberPosition({
        mediaId: videoId,
        mediaType: 'video',
        baseId,
        position: clamped,
      });
      controlsRef.current?.seek?.(clamped);
    },
    [deriveBaseId, rememberPosition, videoLookup],
  );

  const handleRegisterControls = useCallback(
    (controls: PlaybackControls | null) => {
      controlsRef.current = controls;
      if (!controls) {
        return;
      }
      const pending = pendingBookmarkSeekRef.current;
      if (!pending || pending.videoId !== activeVideoId) {
        return;
      }
      const clamped = Math.max(pending.time, 0);
      localPositionRef.current = clamped;
      const match = videoLookup.get(pending.videoId) ?? null;
      const baseId = match ? deriveBaseId(match) : null;
      rememberPosition({
        mediaId: pending.videoId,
        mediaType: 'video',
        baseId,
        position: clamped,
      });
      controls.seek?.(clamped);
      pendingBookmarkSeekRef.current = null;
    },
    [activeVideoId, deriveBaseId, rememberPosition, videoLookup],
  );

  const handlePlaybackRateChange = useCallback((rate: number) => {
    setPlaybackSpeed(normaliseTranslationSpeed(rate));
  }, []);

  const adjustPlaybackSpeed = useCallback((direction: 'faster' | 'slower') => {
    setPlaybackSpeed((current) => {
      const delta = direction === 'faster' ? TRANSLATION_SPEED_STEP : -TRANSLATION_SPEED_STEP;
      return normaliseTranslationSpeed(current + delta);
    });
  }, []);

  const handlePlaybackPositionChange = useCallback(
    (position: number) => {
      if (!activeVideoId) {
        return;
      }
      localPositionRef.current = Math.max(position, 0);
      const match = videoLookup.get(activeVideoId) ?? null;
      const baseId = match ? deriveBaseId(match) : null;
      rememberPosition({
        mediaId: activeVideoId,
        mediaType: 'video',
        baseId,
        position: Math.max(position, 0),
      });
    },
    [activeVideoId, deriveBaseId, rememberPosition, videoLookup],
  );

  // Handle pending bookmark seek when controls become available
  useEffect(() => {
    const pending = pendingBookmarkSeekRef.current;
    if (!pending || pending.videoId !== activeVideoId) {
      return;
    }
    if (!controlsRef.current?.seek) {
      return;
    }
    applyBookmarkSeek(pending.videoId, pending.time);
    pendingBookmarkSeekRef.current = null;
  }, [activeVideoId, applyBookmarkSeek]);

  const videoCount = videoFiles.length;
  const currentIndex = activeVideoId ? videoFiles.findIndex((file) => file.id === activeVideoId) : -1;
  const playbackPosition =
    activeVideoId && lastActivatedVideoRef.current === activeVideoId ? localPositionRef.current : 0;

  return {
    activeVideoId,
    setActiveVideoId,
    isPlaying,
    isFullscreen,
    playbackSpeed,
    controlsRef,
    playbackPosition,
    localPositionRef,
    pendingBookmarkSeekRef,
    navigationState: {
      disableFirst: videoCount === 0 || currentIndex <= 0,
      disablePrevious: videoCount === 0 || currentIndex <= 0,
      disableNext: videoCount === 0 || currentIndex >= videoCount - 1,
      disableLast: videoCount === 0 || currentIndex >= videoCount - 1,
      disablePlayback: videoCount === 0 || !controlsRef.current,
      disableFullscreen: videoCount === 0,
      currentIndex,
      videoCount,
    },
    handleNavigate,
    handleTogglePlayback,
    handlePlaybackStateChange,
    handlePlaybackEnded,
    handleToggleFullscreen,
    handleExitFullscreen,
    handleRegisterControls,
    handlePlaybackRateChange,
    adjustPlaybackSpeed,
    handlePlaybackPositionChange,
    resetPlaybackPosition,
    applyBookmarkSeek,
  };
}
