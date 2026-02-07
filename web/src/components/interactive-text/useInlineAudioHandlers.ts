import { useCallback, useEffect, useRef } from 'react';
import { timingStore } from '../../stores/timingStore';
import type { WordSyncController, TimelineSentenceRuntime } from './types';

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
  pendingSequenceSeekRef: React.MutableRefObject<{ time: number; autoPlay: boolean; targetSentenceIndex?: number } | null>;
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
  pendingSequenceExitSeekRef: React.MutableRefObject<{ sentenceIndex: number } | null>;
  timelineSentences: TimelineSentenceRuntime[] | null;
  isSeekingRef: React.MutableRefObject<boolean>;
  lastManualSeekTimeRef: React.MutableRefObject<number>;
  wordSyncControllerRef: React.MutableRefObject<WordSyncController | null>;
  effectivePlaybackRate: number;
  chunkTime: number;
  isDwellPauseRef?: React.MutableRefObject<boolean>;
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
  pendingSequenceExitSeekRef,
  timelineSentences,
  isSeekingRef,
  lastManualSeekTimeRef,
  wordSyncControllerRef,
  effectivePlaybackRate,
  chunkTime,
  isDwellPauseRef,
}: UseInlineAudioHandlersArgs): UseInlineAudioHandlersResult {
  const progressTimerRef = useRef<number | null>(null);
  // Keep a ref to the latest maybeAdvanceSequence so the progress-timer interval
  // (which is never recreated) always calls the freshest version.  Without this,
  // the interval closure captures a stale maybeAdvanceSequence whose inner
  // sequencePlan may be from a previous render.
  const maybeAdvanceSequenceRef = useRef(maybeAdvanceSequence);
  maybeAdvanceSequenceRef.current = maybeAdvanceSequence;

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
          // Skip progress updates while a pending sequence seek is in progress
          // This prevents overwriting chunkTime with stale values before the seek completes
          // The pending seek will be cleared by handleLoadedMetadata after the audio loads
          if (pendingSequenceSeekRef.current) {
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
          maybeAdvanceSequenceRef.current(currentTime);
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
    // Skip state updates if this is a dwell pause (pause at segment end before advancing)
    // The playback will resume automatically after the dwell period
    if (isDwellPauseRef?.current) {
      if (import.meta.env.DEV) {
        console.debug('[handleInlineAudioPause] Skipping due to dwell pause');
      }
      return;
    }
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
    isDwellPauseRef,
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
    const pendingSequenceSeek = pendingSequenceSeekRef.current;
    // If there's a pending sequence seek, set chunkTime to the target time, not initialTime
    // This prevents the timelineDisplay effect from calculating wrong sentence indices
    if (pendingSequenceSeek) {
      setChunkTime(pendingSequenceSeek.time);
    } else {
      setChunkTime(initialTime);
    }
    if (import.meta.env.DEV) {
      console.debug('[handleLoadedMetadata]', {
        duration,
        initialTime,
        pendingSequenceSeek,
        sequenceEnabled,
        sequencePlanLength,
      });
    }
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
      // Mark this as a manual seek to prevent backward index movement due to timeline scaling
      // This protects against the timelineDisplay effect resetting sentence index after track switch
      lastManualSeekTimeRef.current = Date.now();
      // Clear the pending seek ref after a brief delay to allow the seek to take effect.
      // We use requestAnimationFrame to ensure the audio element has processed the seek
      // before we allow progress updates to resume.
      // The guard in syncSequenceIndexToTime (checking if current segment is valid for time)
      // prevents recalculation when handleAudioSeeked fires.
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          // Only clear if we're still at the same pending seek
          // (avoid clearing a newer pending seek set by a subsequent operation)
          if (pendingSequenceSeekRef.current?.time === targetSeek) {
            if (import.meta.env.DEV) {
              console.debug('[handleLoadedMetadata] Clearing pendingSequenceSeekRef after seek', {
                targetSeek,
                currentTime: element.currentTime,
              });
            }
            pendingSequenceSeekRef.current = null;
            // Complete the transition in the store
            timingStore.completeTransition();
          }
        });
      });
      wordSyncControllerRef.current?.snap();
      return;
    }
    // Handle pending seek when transitioning from sequence mode to single-track mode
    const pendingSequenceExitSeek = pendingSequenceExitSeekRef.current;
    if (pendingSequenceExitSeek && timelineSentences && timelineSentences.length > 0) {
      const safeDuration = Number.isFinite(duration) && duration > 0 ? duration : null;
      const targetSentenceIndex = Math.min(
        pendingSequenceExitSeek.sentenceIndex,
        timelineSentences.length - 1,
      );
      const targetSentence = timelineSentences[targetSentenceIndex];
      if (targetSentence) {
        // Add a small offset (0.1s) after sentence start to ensure the timeline
        // agrees this time is within the target sentence, not at the boundary
        // which might be considered part of the previous sentence
        let targetSeek = targetSentence.startTime + 0.1;
        // Clamp to valid range (within the sentence)
        const sentenceDuration = targetSentence.endTime - targetSentence.startTime;
        if (sentenceDuration > 0.2) {
          // If sentence is long enough, keep the offset
          targetSeek = Math.min(targetSeek, targetSentence.endTime - 0.1);
        } else {
          // For very short sentences, seek to the middle
          targetSeek = (targetSentence.startTime + targetSentence.endTime) / 2;
        }
        if (safeDuration !== null) {
          targetSeek = Math.min(targetSeek, Math.max(safeDuration - 0.1, 0));
        }
        if (targetSeek < 0 || !Number.isFinite(targetSeek)) {
          targetSeek = 0;
        }
        if (import.meta.env.DEV) {
          console.debug('[handleLoadedMetadata] Sequence exit seek', {
            targetSentenceIndex,
            targetSeek,
            sentenceStartTime: targetSentence.startTime,
          });
        }
        element.currentTime = targetSeek;
        setChunkTime(targetSeek);
        setActiveSentenceIndex(targetSentenceIndex);
        // Mark this as a manual seek to prevent backward index movement due to timeline scaling
        lastManualSeekTimeRef.current = Date.now();
        if (safeDuration !== null && !hasTimeline) {
          updateSentenceForTime(targetSeek, safeDuration);
        }
        updateActiveGateFromTime(targetSeek);
        emitAudioProgress(targetSeek);
        // Delay clearing the ref to allow timelineDisplay effect to see it and skip
        // Use a longer timeout to ensure React has re-rendered with the new timeline
        // and the audio element has stabilized at the seek position
        setTimeout(() => {
          // Only clear if the current pendingSequenceExitSeekRef matches what we set
          if (pendingSequenceExitSeekRef.current?.sentenceIndex === targetSentenceIndex) {
            if (import.meta.env.DEV) {
              console.debug('[handleLoadedMetadata] Clearing pendingSequenceExitSeekRef', {
                targetSentenceIndex,
              });
            }
            pendingSequenceExitSeekRef.current = null;
            // Complete any transition in progress
            timingStore.completeTransition();
          }
        }, 200);
        wordSyncControllerRef.current?.snap();
        return;
      }
      // Clear pending seek if no target sentence found
      setTimeout(() => {
        if (pendingSequenceExitSeekRef.current?.sentenceIndex === pendingSequenceExitSeek.sentenceIndex) {
          pendingSequenceExitSeekRef.current = null;
        }
      }, 200);
    } else if (pendingSequenceExitSeek) {
      // Clear pending seek if no timeline sentences available
      setTimeout(() => {
        if (pendingSequenceExitSeekRef.current?.sentenceIndex === pendingSequenceExitSeek.sentenceIndex) {
          pendingSequenceExitSeekRef.current = null;
        }
      });
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
    pendingSequenceExitSeekRef,
    lastManualSeekTimeRef,
    pendingSequenceSeekRef,
    sequenceAutoPlayRef,
    setActiveSentenceIndex,
    setAudioDuration,
    setChunkTime,
    timelineSentences,
    updateActiveGateFromTime,
    updateSentenceForTime,
    wordSyncControllerRef,
  ]);

  const handleTimeUpdate = useCallback(() => {
    const element = audioRef.current;
    if (!element) {
      return;
    }
    // Skip time updates while a pending sequence seek is in progress
    // This prevents overwriting chunkTime with stale values (e.g., 0) before the seek completes
    if (pendingSequenceSeekRef.current) {
      // Still waiting for audio to seek - skip this update
      // The pending seek will be cleared by handleLoadedMetadata after the audio loads
      // and seeks to the correct position
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
    maybeAdvanceSequenceRef.current(currentTime);
    if (element.paused) {
      wordSyncControllerRef.current?.snap();
    }
  }, [
    audioRef,
    emitAudioProgress,
    hasTimeline,
    pendingSequenceSeekRef,
    setAudioDuration,
    setChunkTime,
    updateActiveGateFromTime,
    updateSentenceForTime,
    wordSyncControllerRef,
  ]);

  const handleAudioEnded = useCallback(() => {
    if (import.meta.env.DEV) {
      console.debug('[handleAudioEnded]', {
        sequenceEnabled,
        sequencePlanLength,
        pendingSequenceSeek: pendingSequenceSeekRef.current,
      });
    }
    if (sequenceEnabled) {
      const element = audioRef.current;
      if (element && Number.isFinite(element.currentTime)) {
        lastSequenceEndedRef.current = element.currentTime;
      }
    }
    if (sequenceEnabled && pendingSequenceSeekRef.current) {
      if (import.meta.env.DEV) {
        console.debug('[handleAudioEnded] Skipping - pending seek exists');
      }
      return;
    }
    if (sequenceEnabled && advanceSequenceSegment({ autoPlay: true })) {
      if (import.meta.env.DEV) {
        console.debug('[handleAudioEnded] Advanced to next segment');
      }
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
