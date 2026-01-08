import { useCallback, useEffect, useRef } from 'react';
import { timingStore } from '../../stores/timingStore';
import type { WordSyncController } from './types';

type InlineAudioControls = {
  pause: () => void;
  play: () => void;
};

type UseInlineAudioHandlersArgs = {
  audioRef: React.MutableRefObject<HTMLAudioElement | null>;
  effectiveAudioUrl: string | null;
  resolvedAudioUrl: string | null;
  audioResetKey: string;
  inlineAudioPlayingRef: React.MutableRefObject<boolean>;
  setIsInlineAudioPlaying: React.Dispatch<React.SetStateAction<boolean>>;
  sequenceEnabled: boolean;
  sequencePlanLength: number;
  sequenceAutoPlayRef: React.MutableRefObject<boolean>;
  pendingSequenceSeekRef: React.MutableRefObject<{ time: number; autoPlay: boolean } | null>;
  pendingChunkAutoPlayRef: React.MutableRefObject<boolean>;
  pendingChunkAutoPlayKeyRef: React.MutableRefObject<string | null>;
  lastSequenceEndedRef: React.MutableRefObject<number | null>;
  getSequenceIndexForPlayback: () => number;
  advanceSequenceSegment: (options?: { autoPlay?: boolean }) => boolean;
  syncSequenceIndexToTime: (mediaTime: number) => void;
  maybeAdvanceSequence: (mediaTime: number) => boolean;
  updateSentenceForTime: (time: number, duration: number) => void;
  updateActiveGateFromTime: (time: number) => void;
  emitAudioProgress: (position: number) => void;
  hasTimeline: boolean;
  timelineDisplay: { activeIndex: number } | null;
  audioDuration: number | null;
  totalSentences: number;
  setAudioDuration: React.Dispatch<React.SetStateAction<number | null>>;
  setChunkTime: React.Dispatch<React.SetStateAction<number>>;
  setActiveSentenceIndex: React.Dispatch<React.SetStateAction<number>>;
  onInlineAudioPlaybackStateChange?: (state: 'playing' | 'paused') => void;
  onRegisterInlineAudioControls?: (controls: InlineAudioControls | null) => void;
  onRequestAdvanceChunk?: () => void;
  dictionarySuppressSeekRef: React.MutableRefObject<boolean>;
  pendingInitialSeekRef: React.MutableRefObject<number | null>;
  isSeekingRef: React.MutableRefObject<boolean>;
  wordSyncControllerRef: React.MutableRefObject<WordSyncController | null>;
  effectivePlaybackRate: number;
  chunkTime: number;
};

type UseInlineAudioHandlersResult = {
  handleInlineAudioPlay: () => void;
  handleInlineAudioPause: () => void;
  handleLoadedMetadata: () => void;
  handleTimeUpdate: () => void;
  handleAudioEnded: () => void;
  handleAudioSeeked: () => void;
  handleAudioSeeking: () => void;
  handleAudioWaiting: () => void;
  handleAudioStalled: () => void;
  handleAudioPlaying: () => void;
  handleAudioRateChange: () => void;
  seekInlineAudioToTime: (time: number) => void;
  handleTokenSeek: (time: number) => void;
};

export function useInlineAudioHandlers({
  audioRef,
  effectiveAudioUrl,
  resolvedAudioUrl,
  audioResetKey,
  inlineAudioPlayingRef,
  setIsInlineAudioPlaying,
  sequenceEnabled,
  sequencePlanLength,
  sequenceAutoPlayRef,
  pendingSequenceSeekRef,
  pendingChunkAutoPlayRef,
  pendingChunkAutoPlayKeyRef,
  lastSequenceEndedRef,
  getSequenceIndexForPlayback,
  advanceSequenceSegment,
  syncSequenceIndexToTime,
  maybeAdvanceSequence,
  updateSentenceForTime,
  updateActiveGateFromTime,
  emitAudioProgress,
  hasTimeline,
  timelineDisplay,
  audioDuration,
  totalSentences,
  setAudioDuration,
  setChunkTime,
  setActiveSentenceIndex,
  onInlineAudioPlaybackStateChange,
  onRegisterInlineAudioControls,
  onRequestAdvanceChunk,
  dictionarySuppressSeekRef,
  pendingInitialSeekRef,
  isSeekingRef,
  wordSyncControllerRef,
  effectivePlaybackRate,
  chunkTime,
}: UseInlineAudioHandlersArgs): UseInlineAudioHandlersResult {
  const progressTimerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!onRegisterInlineAudioControls) {
      if (!effectiveAudioUrl) {
        onInlineAudioPlaybackStateChange?.('paused');
      }
      return;
    }
    if (!effectiveAudioUrl) {
      onRegisterInlineAudioControls(null);
      onInlineAudioPlaybackStateChange?.('paused');
      return () => {
        onRegisterInlineAudioControls(null);
      };
    }
    const pauseHandler = () => {
      const element = audioRef.current;
      if (!element) {
        return;
      }
      try {
        element.pause();
      } catch (error) {
        // Ignore pause failures triggered by browsers blocking programmatic control.
      }
      onInlineAudioPlaybackStateChange?.('paused');
    };
    const playHandler = () => {
      const element = audioRef.current;
      if (!element) {
        return;
      }
      try {
        const result = element.play();
        onInlineAudioPlaybackStateChange?.('playing');
        if (result && typeof result.catch === 'function') {
          result.catch(() => {
            onInlineAudioPlaybackStateChange?.('paused');
          });
        }
      } catch (error) {
        // Swallow play failures caused by autoplay restrictions.
        onInlineAudioPlaybackStateChange?.('paused');
      }
    };
    onRegisterInlineAudioControls({ pause: pauseHandler, play: playHandler });
    return () => {
      onRegisterInlineAudioControls(null);
    };
  }, [audioRef, effectiveAudioUrl, onInlineAudioPlaybackStateChange, onRegisterInlineAudioControls]);

  const seekInlineAudioToTime = useCallback(
    (time: number) => {
      if (dictionarySuppressSeekRef.current) {
        return;
      }
      const element = audioRef.current;
      if (!element || !Number.isFinite(time)) {
        return;
      }
      try {
        wordSyncControllerRef.current?.handleSeeking();
        const target = Math.max(
          0,
          Math.min(time, Number.isFinite(element.duration) ? element.duration : time),
        );
        element.currentTime = target;
        setChunkTime(target);
        // Keep playback paused while stepping between words.
        wordSyncControllerRef.current?.snap();
      } catch {
        // Ignore seek/play failures.
      }
    },
    [audioRef, dictionarySuppressSeekRef, setChunkTime, wordSyncControllerRef],
  );

  const handleInlineAudioPlay = useCallback(() => {
    inlineAudioPlayingRef.current = true;
    setIsInlineAudioPlaying(true);
    sequenceAutoPlayRef.current = true;
    pendingChunkAutoPlayRef.current = false;
    pendingChunkAutoPlayKeyRef.current = null;
    timingStore.setLast(null);
    const startPlayback = () => {
      wordSyncControllerRef.current?.handlePlay();
      onInlineAudioPlaybackStateChange?.('playing');
      const element = audioRef.current;
      if (element && element.ended) {
        element.currentTime = 0;
        setChunkTime(0);
        setActiveSentenceIndex(0);
        updateActiveGateFromTime(0);
      }
      if (progressTimerRef.current === null) {
        progressTimerRef.current = window.setInterval(() => {
          const mediaEl = audioRef.current;
          if (!mediaEl) {
            return;
          }
          const { currentTime, duration } = mediaEl;
          if (!Number.isFinite(currentTime) || !Number.isFinite(duration) || duration <= 0) {
            return;
          }
          setAudioDuration((existing) =>
            existing && Math.abs(existing - duration) < 0.01 ? existing : duration,
          );
          setChunkTime(currentTime);
          if (!hasTimeline) {
            updateSentenceForTime(currentTime, duration);
          }
          updateActiveGateFromTime(currentTime);
          maybeAdvanceSequence(currentTime);
        }, 120);
      }
    };
    const element = audioRef.current;
    if (!element) {
      startPlayback();
      return;
    }
    const scheduleStart = () => {
      if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
        window.requestAnimationFrame(startPlayback);
      } else {
        startPlayback();
      }
    };
    if (element.readyState >= element.HAVE_CURRENT_DATA) {
      scheduleStart();
      return;
    }
    const handleCanPlay = () => {
      element.removeEventListener('canplay', handleCanPlay);
      scheduleStart();
    };
    element.addEventListener('canplay', handleCanPlay, { once: true });
  }, [
    audioRef,
    hasTimeline,
    inlineAudioPlayingRef,
    maybeAdvanceSequence,
    onInlineAudioPlaybackStateChange,
    pendingChunkAutoPlayKeyRef,
    pendingChunkAutoPlayRef,
    sequenceAutoPlayRef,
    setActiveSentenceIndex,
    setAudioDuration,
    setChunkTime,
    setIsInlineAudioPlaying,
    updateActiveGateFromTime,
    updateSentenceForTime,
    wordSyncControllerRef,
  ]);

  const handleInlineAudioPause = useCallback(() => {
    const element = audioRef.current;
    if (element?.ended && onRequestAdvanceChunk) {
      const hasNextSegment = sequenceEnabled
        ? (() => {
            const currentIndex = getSequenceIndexForPlayback();
            return currentIndex >= 0 && currentIndex < sequencePlanLength - 1;
          })()
        : false;
      if (!sequenceEnabled || !hasNextSegment) {
        pendingChunkAutoPlayRef.current = true;
        pendingChunkAutoPlayKeyRef.current = audioResetKey;
        return;
      }
    }
    if (sequenceEnabled) {
      if (pendingSequenceSeekRef.current) {
        return;
      }
      if (
        pendingChunkAutoPlayRef.current &&
        pendingChunkAutoPlayKeyRef.current === audioResetKey
      ) {
        return;
      }
      if (element?.ended) {
        if (sequenceAutoPlayRef.current || inlineAudioPlayingRef.current) {
          pendingChunkAutoPlayRef.current = true;
          pendingChunkAutoPlayKeyRef.current = audioResetKey;
          return;
        }
        const currentIndex = getSequenceIndexForPlayback();
        const hasNextSegment = currentIndex >= 0 && currentIndex < sequencePlanLength - 1;
        if (hasNextSegment) {
          return;
        }
      }
    }
    inlineAudioPlayingRef.current = false;
    setIsInlineAudioPlaying(false);
    sequenceAutoPlayRef.current = false;
    pendingChunkAutoPlayRef.current = false;
    pendingChunkAutoPlayKeyRef.current = null;
    if (progressTimerRef.current !== null) {
      window.clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
    wordSyncControllerRef.current?.handlePause();
    onInlineAudioPlaybackStateChange?.('paused');
  }, [
    audioRef,
    audioResetKey,
    getSequenceIndexForPlayback,
    inlineAudioPlayingRef,
    onInlineAudioPlaybackStateChange,
    onRequestAdvanceChunk,
    pendingChunkAutoPlayKeyRef,
    pendingChunkAutoPlayRef,
    pendingSequenceSeekRef,
    sequenceAutoPlayRef,
    sequenceEnabled,
    sequencePlanLength,
    setIsInlineAudioPlaying,
    wordSyncControllerRef,
  ]);

  const handleAudioSeeking = useCallback(() => {
    isSeekingRef.current = true;
    wordSyncControllerRef.current?.handleSeeking();
  }, [isSeekingRef, wordSyncControllerRef]);

  const handleAudioWaiting = useCallback(() => {
    wordSyncControllerRef.current?.handleWaiting();
  }, [wordSyncControllerRef]);

  const handleAudioStalled = useCallback(() => {
    wordSyncControllerRef.current?.handleWaiting();
  }, [wordSyncControllerRef]);

  const handleAudioPlaying = useCallback(() => {
    wordSyncControllerRef.current?.handlePlaying();
  }, [wordSyncControllerRef]);

  const handleAudioRateChange = useCallback(() => {
    wordSyncControllerRef.current?.handleRateChange();
  }, [wordSyncControllerRef]);

  const handleLoadedMetadata = useCallback(() => {
    const element = audioRef.current;
    if (!element) {
      return;
    }
    const duration = element.duration;
    if (Number.isFinite(duration) && duration > 0) {
      setAudioDuration(duration);
    } else {
      setAudioDuration(null);
    }
    const initialTime = (() => {
      const current = element.currentTime ?? 0;
      if (Number.isFinite(duration) && duration > 0 && current >= duration - 0.25) {
        return 0;
      }
      return current;
    })();
    if (initialTime !== (element.currentTime ?? 0)) {
      element.currentTime = initialTime;
    }
    setChunkTime(initialTime);
    const pendingSequenceSeek = pendingSequenceSeekRef.current;
    if (pendingSequenceSeek) {
      const safeDuration = Number.isFinite(duration) && duration > 0 ? duration : null;
      const nearEndThreshold =
        safeDuration !== null ? Math.max(safeDuration * 0.9, safeDuration - 3) : null;
      let targetSeek = pendingSequenceSeek.time;
      if (nearEndThreshold !== null && targetSeek >= nearEndThreshold) {
        targetSeek = 0;
      }
      if (safeDuration !== null) {
        targetSeek = Math.min(targetSeek, Math.max(safeDuration - 0.1, 0));
      }
      if (targetSeek < 0 || !Number.isFinite(targetSeek)) {
        targetSeek = 0;
      }
      element.currentTime = targetSeek;
      if (safeDuration !== null && !hasTimeline) {
        updateSentenceForTime(targetSeek, safeDuration);
      }
      updateActiveGateFromTime(targetSeek);
      emitAudioProgress(targetSeek);
      if (pendingSequenceSeek.autoPlay) {
        sequenceAutoPlayRef.current = true;
        const maybePlay = element.play?.();
        if (maybePlay && typeof maybePlay.catch === 'function') {
          maybePlay.catch(() => undefined);
        }
      }
      pendingSequenceSeekRef.current = null;
      wordSyncControllerRef.current?.snap();
      return;
    }
    const seek = pendingInitialSeekRef.current;
    if (typeof seek === 'number' && seek > 0 && Number.isFinite(duration) && duration > 0) {
      const nearEndThreshold = Math.max(duration * 0.9, duration - 3);
      let targetSeek = seek >= nearEndThreshold ? 0 : Math.min(seek, duration - 0.1);
      if (targetSeek < 0 || !Number.isFinite(targetSeek)) {
        targetSeek = 0;
      }
      element.currentTime = targetSeek;
      if (!hasTimeline) {
        updateSentenceForTime(targetSeek, duration);
      }
      updateActiveGateFromTime(targetSeek);
      emitAudioProgress(targetSeek);
      if (targetSeek > 0.1) {
        const maybePlay = element.play?.();
        if (maybePlay && typeof maybePlay.catch === 'function') {
          maybePlay.catch(() => undefined);
        }
      }
      pendingInitialSeekRef.current = null;
      wordSyncControllerRef.current?.snap();
      return;
    }
    pendingInitialSeekRef.current = null;
    updateActiveGateFromTime(element.currentTime ?? 0);
    wordSyncControllerRef.current?.snap();
  }, [
    audioRef,
    emitAudioProgress,
    hasTimeline,
    pendingInitialSeekRef,
    pendingSequenceSeekRef,
    sequenceAutoPlayRef,
    setAudioDuration,
    setChunkTime,
    updateActiveGateFromTime,
    updateSentenceForTime,
    wordSyncControllerRef,
  ]);

  const handleTimeUpdate = useCallback(() => {
    const element = audioRef.current;
    if (!element) {
      return;
    }
    const { currentTime, duration } = element;
    if (!Number.isFinite(currentTime) || !Number.isFinite(duration) || duration <= 0) {
      return;
    }
    setAudioDuration((existing) =>
      existing && Math.abs(existing - duration) < 0.01 ? existing : duration,
    );
    setChunkTime(currentTime);
    if (!hasTimeline) {
      updateSentenceForTime(currentTime, duration);
    }
    emitAudioProgress(currentTime);
    updateActiveGateFromTime(currentTime);
    maybeAdvanceSequence(currentTime);
    if (element.paused) {
      wordSyncControllerRef.current?.snap();
    }
  }, [
    audioRef,
    emitAudioProgress,
    hasTimeline,
    maybeAdvanceSequence,
    setAudioDuration,
    setChunkTime,
    updateActiveGateFromTime,
    updateSentenceForTime,
    wordSyncControllerRef,
  ]);

  const handleAudioEnded = useCallback(() => {
    if (sequenceEnabled) {
      const element = audioRef.current;
      if (element && Number.isFinite(element.currentTime)) {
        lastSequenceEndedRef.current = element.currentTime;
      }
    }
    if (sequenceEnabled && pendingSequenceSeekRef.current) {
      return;
    }
    if (sequenceEnabled && advanceSequenceSegment({ autoPlay: true })) {
      return;
    }
    if (onRequestAdvanceChunk) {
      pendingChunkAutoPlayRef.current = true;
      pendingChunkAutoPlayKeyRef.current = audioResetKey;
    }
    inlineAudioPlayingRef.current = false;
    setIsInlineAudioPlaying(false);
    if (progressTimerRef.current !== null) {
      window.clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
    wordSyncControllerRef.current?.stop();
    onInlineAudioPlaybackStateChange?.('paused');
    if (hasTimeline && timelineDisplay) {
      setChunkTime((prev) => (audioDuration ? audioDuration : prev));
      setActiveSentenceIndex(timelineDisplay.activeIndex);
    } else {
      if (totalSentences > 0) {
        setActiveSentenceIndex(totalSentences - 1);
      }
    }
    emitAudioProgress(0);
    onRequestAdvanceChunk?.();
  }, [
    advanceSequenceSegment,
    audioDuration,
    audioRef,
    audioResetKey,
    emitAudioProgress,
    hasTimeline,
    inlineAudioPlayingRef,
    lastSequenceEndedRef,
    onInlineAudioPlaybackStateChange,
    onRequestAdvanceChunk,
    pendingChunkAutoPlayKeyRef,
    pendingChunkAutoPlayRef,
    pendingSequenceSeekRef,
    sequenceEnabled,
    setActiveSentenceIndex,
    setChunkTime,
    setIsInlineAudioPlaying,
    timelineDisplay,
    totalSentences,
    wordSyncControllerRef,
  ]);

  useEffect(() => {
    if (!sequenceAutoPlayRef.current) {
      return;
    }
    const element = audioRef.current;
    if (!element) {
      return;
    }
    let active = true;
    const attemptPlay = () => {
      if (!active || !sequenceAutoPlayRef.current) {
        return;
      }
      const result = element.play?.();
      if (result && typeof result.catch === 'function') {
        result.catch(() => undefined);
      }
    };
    if (element.readyState >= element.HAVE_FUTURE_DATA) {
      attemptPlay();
      return;
    }
    element.addEventListener('canplay', attemptPlay, { once: true });
    return () => {
      active = false;
      element.removeEventListener('canplay', attemptPlay);
    };
  }, [audioRef, resolvedAudioUrl, sequenceAutoPlayRef]);

  useEffect(() => {
    if (!pendingChunkAutoPlayRef.current) {
      return;
    }
    if (pendingChunkAutoPlayKeyRef.current === audioResetKey) {
      return;
    }
    pendingChunkAutoPlayRef.current = false;
    pendingChunkAutoPlayKeyRef.current = null;
    const element = audioRef.current;
    if (!element) {
      return;
    }
    let active = true;
    const attemptPlay = () => {
      if (!active) {
        return;
      }
      const result = element.play?.();
      if (result && typeof result.catch === 'function') {
        result.catch(() => undefined);
      }
    };
    if (element.readyState >= element.HAVE_CURRENT_DATA) {
      attemptPlay();
      return;
    }
    element.addEventListener('canplay', attemptPlay, { once: true });
    return () => {
      active = false;
      element.removeEventListener('canplay', attemptPlay);
    };
  }, [audioRef, audioResetKey, pendingChunkAutoPlayKeyRef, pendingChunkAutoPlayRef, resolvedAudioUrl]);

  const handleAudioSeeked = useCallback(() => {
    isSeekingRef.current = false;
    wordSyncControllerRef.current?.handleSeeked();
    const element = audioRef.current;
    if (!element || !Number.isFinite(element.duration) || element.duration <= 0) {
      return;
    }
    setChunkTime(element.currentTime ?? 0);
    syncSequenceIndexToTime(element.currentTime ?? 0);
    if (!hasTimeline) {
      updateSentenceForTime(element.currentTime, element.duration);
    }
    emitAudioProgress(element.currentTime);
  }, [
    audioRef,
    emitAudioProgress,
    hasTimeline,
    isSeekingRef,
    setChunkTime,
    syncSequenceIndexToTime,
    updateSentenceForTime,
    wordSyncControllerRef,
  ]);

  const handleTokenSeek = useCallback(
    (time: number) => {
      if (dictionarySuppressSeekRef.current) {
        return;
      }
      const element = audioRef.current;
      if (!element || !Number.isFinite(time)) {
        return;
      }
      try {
        wordSyncControllerRef.current?.handleSeeking();
        const target = Math.max(
          0,
          Math.min(time, Number.isFinite(element.duration) ? element.duration : time),
        );
        element.currentTime = target;
        const maybePlay = element.play?.();
        if (maybePlay && typeof maybePlay.catch === 'function') {
          maybePlay.catch(() => undefined);
        }
      } catch (error) {
        // Ignore seek failures in restricted environments.
      }
    },
    [audioRef, dictionarySuppressSeekRef, wordSyncControllerRef],
  );

  useEffect(() => {
    if (typeof navigator === 'undefined') {
      return;
    }
    const session = navigator.mediaSession;
    if (!session || typeof session.setPositionState !== 'function') {
      return;
    }
    const duration =
      typeof audioDuration === 'number' && Number.isFinite(audioDuration) && audioDuration > 0
        ? audioDuration
        : null;
    if (!resolvedAudioUrl || duration === null) {
      return;
    }
    const safePosition = Number.isFinite(chunkTime)
      ? Math.min(Math.max(chunkTime, 0), duration)
      : 0;
    try {
      session.setPositionState({
        duration,
        position: safePosition,
        playbackRate: effectivePlaybackRate,
      });
    } catch {
      // Ignore unsupported position state updates.
    }
  }, [audioDuration, chunkTime, effectivePlaybackRate, resolvedAudioUrl]);

  useEffect(() => {
    return () => {
      if (progressTimerRef.current !== null) {
        window.clearInterval(progressTimerRef.current);
        progressTimerRef.current = null;
      }
    };
  }, []);

  return {
    handleInlineAudioPlay,
    handleInlineAudioPause,
    handleLoadedMetadata,
    handleTimeUpdate,
    handleAudioEnded,
    handleAudioSeeked,
    handleAudioSeeking,
    handleAudioWaiting,
    handleAudioStalled,
    handleAudioPlaying,
    handleAudioRateChange,
    seekInlineAudioToTime,
    handleTokenSeek,
  };
}
