import { useCallback, useEffect, type MutableRefObject } from 'react';
import type { AssSubtitleCue } from '../../lib/subtitles';
import {
  findActiveCueIndex,
  findCueInsertIndex,
} from './subtitleTrackOverlayUtils';

type UseSubtitleCueKeyboardNavigationOptions = {
  videoRef: MutableRefObject<HTMLVideoElement | null>;
  cues: AssSubtitleCue[];
  activeCueIndexRef: MutableRefObject<number>;
  overlayActive: boolean;
  isPlaying: boolean;
  openSelectionLookup: () => boolean;
  commitActiveCueIndex: (index: number) => void;
};

type UseSubtitleCueKeyboardNavigationResult = {
  seekCueByOffset: (direction: -1 | 1) => boolean;
};

function isTypingTarget(target: EventTarget | null): boolean {
  if (!target || !(target instanceof HTMLElement)) {
    return false;
  }
  const tag = target.tagName;
  if (!tag) {
    return false;
  }
  return target.isContentEditable || tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
}

export function useSubtitleCueKeyboardNavigation({
  videoRef,
  cues,
  activeCueIndexRef,
  overlayActive,
  isPlaying,
  openSelectionLookup,
  commitActiveCueIndex,
}: UseSubtitleCueKeyboardNavigationOptions): UseSubtitleCueKeyboardNavigationResult {
  const seekCueByOffset = useCallback(
    (direction: -1 | 1) => {
      const video = videoRef.current;
      if (!video || cues.length === 0) {
        return false;
      }
      const time = video.currentTime ?? 0;
      const activeIndex = findActiveCueIndex(cues, time, activeCueIndexRef.current);
      let baseIndex = activeIndex;
      if (baseIndex < 0) {
        const insertIndex = findCueInsertIndex(cues, time);
        baseIndex = direction > 0 ? insertIndex : insertIndex - 1;
      } else {
        baseIndex += direction;
      }
      if (baseIndex < 0 || baseIndex >= cues.length) {
        return false;
      }
      const targetCue = cues[baseIndex];
      if (!targetCue) {
        return false;
      }
      const nextTime = Math.max(0, targetCue.start + 0.001);
      try {
        video.currentTime = nextTime;
      } catch {
        return false;
      }
      commitActiveCueIndex(baseIndex);
      return true;
    },
    [activeCueIndexRef, commitActiveCueIndex, cues, videoRef],
  );

  useEffect(() => {
    if (!overlayActive || typeof window === 'undefined') {
      return;
    }
    const handleGlobalKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.altKey || event.metaKey || isTypingTarget(event.target)) {
        return;
      }
      const code = event.code;
      const key = event.key;
      const isArrowRight = code === 'ArrowRight' || key === 'ArrowRight';
      const isArrowLeft = code === 'ArrowLeft' || key === 'ArrowLeft';
      if ((key === 'Enter' || code === 'Enter') && !isPlaying) {
        const handled = openSelectionLookup();
        if (handled) {
          event.preventDefault();
          event.stopPropagation();
        }
        return;
      }
      if (!isArrowRight && !isArrowLeft) {
        return;
      }
      const video = videoRef.current;
      if (!video || video.paused) {
        return;
      }
      const handled = seekCueByOffset(isArrowRight ? 1 : -1);
      if (handled) {
        event.preventDefault();
        event.stopPropagation();
      }
    };
    window.addEventListener('keydown', handleGlobalKeyDown, true);
    return () => {
      window.removeEventListener('keydown', handleGlobalKeyDown, true);
    };
  }, [isPlaying, openSelectionLookup, overlayActive, seekCueByOffset, videoRef]);

  return { seekCueByOffset };
}
