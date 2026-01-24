/**
 * Hook for handling touch/pointer scrubbing gestures on the video player.
 */

import { useCallback, useEffect, useRef } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';

interface ScrubState {
  pointerId: number | null;
  active: boolean;
  startX: number;
  startY: number;
  startTime: number;
  width: number;
}

export interface UseVideoScrubbingOptions {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  canvasRef: React.RefObject<HTMLDivElement | null>;
  activeFileId: string | null;
  onPlaybackPositionChange?: (position: number) => void;
  updatePlaybackClock: () => void;
}

export interface VideoScrubbingHandlers {
  handleScrubPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
  handleScrubPointerMove: (event: ReactPointerEvent<HTMLDivElement>) => void;
  handleScrubPointerEnd: (event: ReactPointerEvent<HTMLDivElement>) => void;
}

export function useVideoScrubbing({
  videoRef,
  canvasRef,
  activeFileId,
  onPlaybackPositionChange,
  updatePlaybackClock,
}: UseVideoScrubbingOptions): VideoScrubbingHandlers {
  const scrubStateRef = useRef<ScrubState>({
    pointerId: null,
    active: false,
    startX: 0,
    startY: 0,
    startTime: 0,
    width: 0,
  });

  const shouldIgnoreScrubTarget = useCallback((target: EventTarget | null): boolean => {
    if (!target || !(target instanceof HTMLElement)) {
      return false;
    }
    return Boolean(target.closest('.player-panel__my-linguist-bubble'));
  }, []);

  const clearScrubState = useCallback(() => {
    scrubStateRef.current.pointerId = null;
    scrubStateRef.current.active = false;
  }, []);

  // Reset scrub state on file change
  useEffect(() => {
    clearScrubState();
  }, [activeFileId, clearScrubState]);

  const handleScrubPointerDown = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (event.button !== 0 || !event.isPrimary) {
        return;
      }
      if (shouldIgnoreScrubTarget(event.target)) {
        return;
      }
      const element = videoRef.current;
      if (!element) {
        return;
      }
      const rect = canvasRef.current?.getBoundingClientRect() ?? element.getBoundingClientRect();
      const width = Math.max(rect.width || 0, element.clientWidth || 0, 1);
      scrubStateRef.current = {
        pointerId: event.pointerId,
        active: false,
        startX: event.clientX,
        startY: event.clientY,
        startTime: Number.isFinite(element.currentTime) ? element.currentTime : 0,
        width,
      };
    },
    [canvasRef, shouldIgnoreScrubTarget, videoRef],
  );

  const handleScrubPointerMove = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      const state = scrubStateRef.current;
      if (state.pointerId === null || event.pointerId !== state.pointerId) {
        return;
      }
      const element = videoRef.current;
      if (!element) {
        return;
      }
      const deltaX = event.clientX - state.startX;
      const deltaY = event.clientY - state.startY;
      const threshold = 12;
      if (!state.active) {
        if (Math.abs(deltaX) < threshold || Math.abs(deltaX) < Math.abs(deltaY)) {
          return;
        }
        state.active = true;
        try {
          (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
        } catch {
          /* Ignore pointer capture failures. */
        }
      }
      const duration = element.duration;
      if (!Number.isFinite(duration) || duration <= 0) {
        return;
      }
      const width = state.width > 0 ? state.width : 1;
      const deltaSeconds = (deltaX / width) * duration;
      const nextTime = Math.max(0, Math.min(state.startTime + deltaSeconds, duration));
      if (Math.abs(element.currentTime - nextTime) < 0.02) {
        return;
      }
      try {
        element.currentTime = nextTime;
      } catch {
        return;
      }
      updatePlaybackClock();
      onPlaybackPositionChange?.(nextTime);
      event.preventDefault();
    },
    [onPlaybackPositionChange, updatePlaybackClock, videoRef],
  );

  const handleScrubPointerEnd = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      const state = scrubStateRef.current;
      if (state.pointerId === null || event.pointerId !== state.pointerId) {
        return;
      }
      if (state.active) {
        event.preventDefault();
      }
      try {
        (event.currentTarget as HTMLElement).releasePointerCapture(event.pointerId);
      } catch {
        /* Ignore pointer capture failures. */
      }
      clearScrubState();
    },
    [clearScrubState],
  );

  return {
    handleScrubPointerDown,
    handleScrubPointerMove,
    handleScrubPointerEnd,
  };
}
