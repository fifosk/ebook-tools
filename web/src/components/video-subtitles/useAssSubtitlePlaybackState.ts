import { useCallback, useEffect, useRef, useState } from 'react';
import type { MutableRefObject } from 'react';
import type { AssSubtitleCue } from '../../lib/subtitles';
import { findActiveCueIndex } from './subtitleTrackOverlayUtils';

type UseAssSubtitlePlaybackStateOptions = {
  videoRef: MutableRefObject<HTMLVideoElement | null>;
  cues: AssSubtitleCue[];
  overlayActive: boolean;
};

type UseAssSubtitlePlaybackStateResult = {
  activeCueIndex: number;
  activeCueIndexRef: MutableRefObject<number>;
  isPlaying: boolean;
  commitActiveCueIndex: (index: number) => void;
};

export function useAssSubtitlePlaybackState({
  videoRef,
  cues,
  overlayActive,
}: UseAssSubtitlePlaybackStateOptions): UseAssSubtitlePlaybackStateResult {
  const [activeCueIndex, setActiveCueIndex] = useState(-1);
  const activeCueIndexRef = useRef(-1);
  const [isPlaying, setIsPlaying] = useState(false);

  const commitActiveCueIndex = useCallback((index: number) => {
    activeCueIndexRef.current = index;
    setActiveCueIndex(index);
  }, []);

  useEffect(() => {
    if (!overlayActive) {
      commitActiveCueIndex(-1);
      setIsPlaying(false);
      return;
    }
    const video = videoRef.current;
    if (!video) {
      return;
    }
    const updatePlaybackState = () => {
      setIsPlaying(!video.paused);
    };
    const updateActiveCue = () => {
      const time = video.currentTime ?? 0;
      const nextIndex = findActiveCueIndex(cues, time, activeCueIndexRef.current);
      if (nextIndex !== activeCueIndexRef.current) {
        commitActiveCueIndex(nextIndex);
      }
    };
    let rafId: number | null = null;
    const tick = () => {
      updateActiveCue();
      if (!video.paused) {
        rafId = window.requestAnimationFrame(tick);
      } else {
        rafId = null;
      }
    };
    const handlePlay = () => {
      updatePlaybackState();
      if (rafId === null) {
        rafId = window.requestAnimationFrame(tick);
      }
    };
    const handlePause = () => {
      updatePlaybackState();
      if (rafId !== null) {
        window.cancelAnimationFrame(rafId);
        rafId = null;
      }
      updateActiveCue();
    };
    const handleSeeked = () => {
      updateActiveCue();
    };
    const handleTimeUpdate = () => {
      if (video.paused) {
        updateActiveCue();
      }
    };

    updatePlaybackState();
    updateActiveCue();
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('seeked', handleSeeked);
    video.addEventListener('timeupdate', handleTimeUpdate);
    return () => {
      if (rafId !== null) {
        window.cancelAnimationFrame(rafId);
      }
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('seeked', handleSeeked);
      video.removeEventListener('timeupdate', handleTimeUpdate);
    };
  }, [commitActiveCueIndex, cues, overlayActive, videoRef]);

  return { activeCueIndex, activeCueIndexRef, isPlaying, commitActiveCueIndex };
}
