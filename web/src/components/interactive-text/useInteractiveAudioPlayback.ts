import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { AudioTrackMetadata } from '../../api/dtos';
import type { LiveMediaChunk, MediaClock } from '../../hooks/useLiveMedia';
import { useMediaClock } from '../../hooks/useLiveMedia';
import { usePlayerCore } from '../../hooks/usePlayerCore';
import { timingStore } from '../../stores/timingStore';
import type { TextPlayerVariantKind } from '../../text-player/TextPlayer';
import { normaliseTranslationSpeed } from '../player-panel/constants';
import { buildParagraphs } from './utils';
import { useTimelineDisplay } from './useTimelineDisplay';
import { useTextPlayerSentences } from './useTextPlayerSentences';
import {
  useInteractiveAudioSequence,
  type SequenceTrack,
} from './useInteractiveAudioSequence';
import { useInteractiveAudioTimeline } from './useInteractiveAudioTimeline';
import { useInlineAudioHandlers } from './useInlineAudioHandlers';
import { useInteractiveTextTiming } from './useInteractiveTextTiming';
import { useInteractiveWordSync } from './useInteractiveWordSync';
import { useSequencePlaybackController } from './useSequencePlaybackController';
import { useAudioModeTransition } from './useAudioModeTransition';

type InlineAudioControls = {
  pause: () => void;
  play: () => void;
};

type CueVisibility = {
  original: boolean;
  transliteration: boolean;
  translation: boolean;
};

type SequenceDebugInfo = {
  enabled: boolean;
  origEnabled: boolean;
  transEnabled: boolean;
  hasOrigSeg: boolean;
  hasTransSeg: boolean;
  hasOrigTrack: boolean;
  hasTransTrack: boolean;
  track: SequenceTrack;
  index: number;
  lastEnded: string;
  autoPlay: string;
  plan: number;
  sentence: number;
  time: number;
  pending: string;
  playing: boolean;
  audio: string;
  original: string;
  translation: string;
};

type RevealMemoryRef = React.MutableRefObject<{
  sentenceIdx: number | null;
  counts: Record<TextPlayerVariantKind, number>;
}>;

type UseInteractiveAudioPlaybackArgs = {
  content: string;
  chunk: LiveMediaChunk | null;
  chunks: LiveMediaChunk[] | null;
  activeChunkIndex: number | null;
  audioTracks: Record<string, AudioTrackMetadata> | null;
  activeAudioUrl: string | null;
  jobId: string | null;
  playerMode: 'online' | 'export';
  originalAudioEnabled: boolean;
  translationAudioEnabled: boolean;
  translationSpeed: number;
  activeTimingTrack: 'mix' | 'translation' | 'original';
  cueVisibility?: CueVisibility;
  onAudioProgress?: (audioUrl: string, position: number) => void;
  getStoredAudioPosition?: (audioUrl: string) => number;
  onRegisterInlineAudioControls?: (controls: InlineAudioControls | null) => void;
  onInlineAudioPlaybackStateChange?: (state: 'playing' | 'paused') => void;
  onRequestAdvanceChunk?: () => void;
  onActiveSentenceChange?: (sentenceNumber: number | null) => void;
  dictionarySuppressSeekRef: React.MutableRefObject<boolean>;
  containerRef: React.MutableRefObject<HTMLDivElement | null>;
  revealMemoryRef: RevealMemoryRef;
  sequenceDebugEnabled: boolean;
};

export function useInteractiveAudioPlayback({
  content,
  chunk,
  chunks,
  activeChunkIndex,
  audioTracks,
  activeAudioUrl,
  jobId,
  playerMode,
  originalAudioEnabled,
  translationAudioEnabled,
  translationSpeed,
  activeTimingTrack,
  cueVisibility,
  onAudioProgress,
  getStoredAudioPosition,
  onRegisterInlineAudioControls,
  onInlineAudioPlaybackStateChange,
  onRequestAdvanceChunk,
  onActiveSentenceChange,
  dictionarySuppressSeekRef,
  containerRef,
  revealMemoryRef,
  sequenceDebugEnabled,
}: UseInteractiveAudioPlaybackArgs) {
  const isExportMode = playerMode === 'export';
  const resolvedCueVisibility = useMemo(() => {
    return (
      cueVisibility ?? {
        original: true,
        transliteration: true,
        translation: true,
      }
    );
  }, [cueVisibility]);
  const resolvedTranslationSpeed = useMemo(
    () => normaliseTranslationSpeed(translationSpeed),
    [translationSpeed],
  );

  const {
    ref: attachPlayerCore,
    core: playerCore,
    elementRef: audioRef,
    mediaRef: rawAttachMediaElement,
  } = usePlayerCore();
  const attachMediaElement = useCallback(
    (element: HTMLAudioElement | null) => {
      rawAttachMediaElement(element);
      timingStore.setAudioEl(element);
    },
    [rawAttachMediaElement],
  );

  const inlineAudioPlayingRef = useRef(false);
  const isSeekingRef = useRef(false);
  const [isInlineAudioPlaying, setIsInlineAudioPlaying] = useState(false);

  const [chunkTime, setChunkTime] = useState(0);
  const [audioDuration, setAudioDuration] = useState<number | null>(null);
  const [activeSentenceIndex, setActiveSentenceIndexState] = useState(0);

  const activeSentenceIndexRef = useRef(0);
  // Create a setter that updates both the state AND the ref synchronously
  // This is critical for sequence playback where we need the ref to be accurate immediately
  const setActiveSentenceIndex = useCallback((value: number | ((prev: number) => number)) => {
    if (typeof value === 'function') {
      setActiveSentenceIndexState((prev) => {
        const next = value(prev);
        if (import.meta.env.DEV) {
          console.debug('[setActiveSentenceIndex] Function setter', { prev, next, oldRef: activeSentenceIndexRef.current });
        }
        activeSentenceIndexRef.current = next;
        return next;
      });
    } else {
      if (import.meta.env.DEV) {
        // Log stack trace when setting to 0 to find the culprit
        if (value === 0 && activeSentenceIndexRef.current !== 0) {
          console.debug('[setActiveSentenceIndex] RESET TO 0', { oldRef: activeSentenceIndexRef.current });
          console.trace('[setActiveSentenceIndex] Stack trace for reset to 0');
        } else {
          console.debug('[setActiveSentenceIndex] Direct setter', { value, oldRef: activeSentenceIndexRef.current });
        }
      }
      activeSentenceIndexRef.current = value;
      setActiveSentenceIndexState(value);
    }
  }, []);
  // Also sync from state in case something else sets it (like effects)
  useEffect(() => {
    if (import.meta.env.DEV && activeSentenceIndexRef.current !== activeSentenceIndex) {
      console.debug('[activeSentenceIndex sync effect] Syncing ref from state', {
        oldRef: activeSentenceIndexRef.current,
        newState: activeSentenceIndex,
      });
    }
    activeSentenceIndexRef.current = activeSentenceIndex;
  }, [activeSentenceIndex]);

  const clock = useMediaClock(audioRef);
  const clockRef = useRef<MediaClock>(clock);
  useEffect(() => {
    clockRef.current = clock;
  }, [clock]);

  useEffect(() => {
    const element = playerCore?.getElement() ?? audioRef.current ?? null;
    timingStore.setAudioEl(element);
    return () => {
      if (timingStore.get().audioEl === element) {
        timingStore.setAudioEl(null);
      }
    };
  }, [playerCore]);

  const [prefersReducedMotion, setPrefersReducedMotion] = useState<boolean>(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return false;
    }
    try {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch {
      return false;
    }
  });
  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return;
    }
    let mounted = true;
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => {
      if (!mounted) {
        return;
      }
      setPrefersReducedMotion(media.matches);
    };
    update();
    try {
      if (typeof media.addEventListener === 'function') {
        media.addEventListener('change', update);
        return () => {
          mounted = false;
          media.removeEventListener('change', update);
        };
      }
      if (typeof media.addListener === 'function') {
        media.addListener(update);
        return () => {
          mounted = false;
          media.removeListener(update);
        };
      }
    } catch {
      // Ignore listener registration errors.
    }
    return () => {
      mounted = false;
    };
  }, []);
  const followHighlightEnabled = !prefersReducedMotion;

  const {
    sequence: {
      enabled: sequenceEnabled,
      enabledRef: sequenceEnabledRef,
      plan: sequencePlan,
      track: sequenceTrack,
      setTrack: setSequenceTrack,
      defaultTrack: sequenceDefaultTrack,
      trackRef: sequenceTrackRef,
      indexRef: sequenceIndexRef,
      pendingSeekRef: pendingSequenceSeekRef,
      autoPlayRef: sequenceAutoPlayRef,
      pendingChunkAutoPlayRef,
      pendingChunkAutoPlayKeyRef,
      lastSequenceEndedRef,
    },
    effectiveAudioUrl,
    resolvedAudioUrl,
    audioResetKey,
    originalTrackUrl,
    translationTrackUrl,
    trackRefs,
    resolvedTimingTrack,
    useCombinedPhases,
  } = useInteractiveAudioSequence({
    chunk,
    audioTracks,
    activeAudioUrl,
    originalAudioEnabled,
    translationAudioEnabled,
    activeTimingTrack,
    isExportMode,
    jobId,
  });

  // Debug: log when sequenceEnabled changes
  useEffect(() => {
    if (import.meta.env.DEV) {
      console.debug('[useInteractiveAudioPlayback] sequenceEnabled changed:', sequenceEnabled, {
        originalAudioEnabled,
        translationAudioEnabled,
        chunkId: chunk?.chunkId ?? null,
      });
    }
  }, [chunk?.chunkId, originalAudioEnabled, sequenceEnabled, translationAudioEnabled]);

  const {
    timingPayload,
    timingDiagnostics,
    effectivePlaybackRate,
    shouldUseWordSync,
    legacyWordSyncEnabled,
    wordSyncSentences,
    activeWordSyncTrack,
    activeWordIndex,
    jobTimingResponse,
  } = useInteractiveTextTiming({
    jobId,
    chunk,
    isExportMode,
    resolvedTimingTrack,
    resolvedTranslationSpeed,
  });
  const { wordSyncControllerRef, updateActiveGateFromTime } = useInteractiveWordSync({
    audioRef,
    playerCore,
    containerRef,
    clockRef,
    followHighlightEnabled,
    timingPayload,
    timingDiagnostics,
    effectivePlaybackRate,
    shouldUseWordSync,
    legacyWordSyncEnabled,
    activeWordSyncTrack,
    activeWordIndex,
    jobId,
    resolvedTimingTrack,
    jobTimingResponse,
    wordSyncSentences,
  });

  const hasTimeline = Boolean(chunk?.sentences && chunk.sentences.length > 0);
  const paragraphs = useMemo(() => buildParagraphs(content), [content]);
  const totalSentences = useMemo(
    () => paragraphs.reduce((count, paragraph) => count + paragraph.sentences.length, 0),
    [paragraphs],
  );

  const { timelineSentences, timelineDisplay } = useTimelineDisplay({
    chunk,
    hasTimeline,
    useCombinedPhases,
    activeTimingTrack: resolvedTimingTrack,
    audioDuration,
    chunkTime,
    activeSentenceIndex,
    revealMemoryRef,
  });

  // Debug: track when timelineDisplay.activeIndex differs from activeSentenceIndex
  useEffect(() => {
    if (import.meta.env.DEV && timelineDisplay && timelineDisplay.activeIndex !== activeSentenceIndex) {
      console.debug('[timelineDisplay mismatch]', {
        displayActiveIndex: timelineDisplay.activeIndex,
        activeSentenceIndex,
        effectiveTime: timelineDisplay.effectiveTime,
        chunkTime,
        resolvedTimingTrack,
        sequenceEnabled,
        pendingSeek: pendingSequenceSeekRef.current,
      });
    }
  }, [timelineDisplay, activeSentenceIndex, chunkTime, resolvedTimingTrack, sequenceEnabled]);

  const { rawSentences, textPlayerSentences, sentenceWeightSummary } = useTextPlayerSentences({
    paragraphs,
    timelineDisplay,
    chunk,
    activeSentenceIndex,
  });

  const updateSentenceForTime = useCallback(
    (time: number, duration: number) => {
      const totalWeight = sentenceWeightSummary.total;
      if (totalWeight <= 0 || duration <= 0 || rawSentences.length === 0) {
        setActiveSentenceIndex(0);
        return;
      }

      const ratio = time / duration;
      const progress = ratio >= 0.995 ? 1 : Math.max(0, Math.min(ratio, 1));
      const targetUnits = progress * totalWeight;
      const cumulative = sentenceWeightSummary.cumulative;

      let sentencePosition = cumulative.findIndex((value) => targetUnits < value);
      if (sentencePosition === -1) {
        sentencePosition = rawSentences.length - 1;
      }

      const sentence = rawSentences[sentencePosition];
      const sentenceStartUnits = sentencePosition === 0 ? 0 : cumulative[sentencePosition - 1];
      const sentenceWeight = Math.max(sentence.weight, 1);
      const intraUnits = targetUnits - sentenceStartUnits;
      const intra = Math.max(0, Math.min(intraUnits / sentenceWeight, 1));

      setActiveSentenceIndex(sentence.index);
      if (Number.isFinite(intra)) {
        // Reserved for future sentence-progress UI.
      }
    },
    [rawSentences, sentenceWeightSummary],
  );

  useEffect(() => {
    if (!hasTimeline) {
      return;
    }
    if (import.meta.env.DEV) {
      console.debug('[chunk change effect] Resetting to 0', {
        chunkId: chunk?.chunkId,
        rangeFragment: chunk?.rangeFragment,
      });
    }
    setChunkTime(0);
    setActiveSentenceIndex(0);
  }, [hasTimeline, chunk?.chunkId, chunk?.rangeFragment, chunk?.startSentence, chunk?.endSentence]);

  useEffect(() => {
    if (import.meta.env.DEV) {
      console.debug('[content/sentences effect] Resetting to 0', {
        contentLength: content?.length,
        totalSentences,
      });
    }
    setActiveSentenceIndex(0);
  }, [content, totalSentences]);

  useEffect(() => {
    if (!onActiveSentenceChange) {
      return;
    }
    if (!totalSentences || totalSentences <= 0) {
      onActiveSentenceChange(null);
      return;
    }
    const activeSentenceNumber = (() => {
      const rawSentenceNumber = chunk?.sentences?.[activeSentenceIndex]?.sentence_number ?? null;
      const chunkSentenceNumber =
        typeof rawSentenceNumber === 'number' && Number.isFinite(rawSentenceNumber)
          ? Math.trunc(rawSentenceNumber)
          : null;
      if (chunkSentenceNumber !== null) {
        return chunkSentenceNumber;
      }
      const start =
        typeof chunk?.startSentence === 'number' && Number.isFinite(chunk.startSentence)
          ? Math.trunc(chunk.startSentence)
          : null;
      if (start !== null) {
        return start + Math.max(0, Math.trunc(activeSentenceIndex));
      }
      return Math.max(1, Math.trunc(activeSentenceIndex) + 1);
    })();
    onActiveSentenceChange(activeSentenceNumber);
  }, [activeSentenceIndex, chunk?.sentences, chunk?.startSentence, onActiveSentenceChange, totalSentences]);

  // Track when a manual seek was performed to prevent backward index movement
  // due to timeline scaling mismatches
  const lastManualSeekTimeRef = useRef<number>(0);

  useEffect(() => {
    if (!timelineDisplay) {
      return;
    }
    // Skip this effect during any playback transition - use store state as primary check
    // This provides a unified guard that covers all transition types
    if (timingStore.isTransitioning()) {
      if (import.meta.env.DEV) {
        console.debug('[timelineDisplay effect] Skipping due to transition in progress', timingStore.getTransition());
      }
      return;
    }
    // Legacy guards for backward compatibility during migration
    // Skip this effect during pending sequence seeks - the correct sentence index
    // has already been set by applySequenceSegment
    if (pendingSequenceSeekRef.current) {
      if (import.meta.env.DEV) {
        console.debug('[timelineDisplay effect] Skipping due to pendingSequenceSeek');
      }
      return;
    }
    // Skip this effect during sequence exit transitions - the correct sentence index
    // has been set by handleLoadedMetadata and we don't want to override it
    if (pendingSequenceExitSeekRef.current) {
      if (import.meta.env.DEV) {
        console.debug('[timelineDisplay effect] Skipping due to pendingSequenceExitSeek');
      }
      return;
    }
    const { activeIndex: candidateIndex, effectiveTime } = timelineDisplay;

    // Guard against resetting to sentence 0 when effectiveTime is 0 but we have a valid position
    // This happens during mode transitions (entering/exiting sequence mode) when audio is reloading
    // and chunkTime temporarily becomes 0. The activeSentenceIndex is more trustworthy in this case.
    if (candidateIndex === 0 && effectiveTime === 0 && activeSentenceIndex > 0) {
      if (import.meta.env.DEV) {
        console.debug('[timelineDisplay effect] Skipping reset to 0 - preserving activeSentenceIndex during mode transition', {
          candidateIndex,
          effectiveTime,
          activeSentenceIndex,
          sequenceEnabled: sequenceEnabledRef.current,
        });
      }
      return;
    }
    if (candidateIndex === activeSentenceIndex) {
      return;
    }
    if (!timelineSentences || timelineSentences.length === 0) {
      if (import.meta.env.DEV) {
        console.debug('[timelineDisplay effect] No timeline sentences, setting to', candidateIndex);
      }
      setActiveSentenceIndex(candidateIndex);
      return;
    }
    const epsilon = 0.05;
    const clampedIndex = Math.max(0, Math.min(candidateIndex, timelineSentences.length - 1));
    const candidateRuntime = timelineSentences[clampedIndex];
    if (!candidateRuntime) {
      if (import.meta.env.DEV) {
        console.debug('[timelineDisplay effect] No candidateRuntime, setting to', clampedIndex);
      }
      setActiveSentenceIndex(clampedIndex);
      return;
    }
    // In sequence mode, the segment times may not align with timeline times due to different
    // audio durations between original and translation tracks causing different scaling factors.
    // The sequence system is the source of truth for sentence progression - don't allow backward
    // movement based on timeline calculations which may be wrong due to scaling mismatches.
    if (sequenceEnabledRef.current && clampedIndex < activeSentenceIndex) {
      // In sequence mode, never allow backward movement from timeline calculations alone.
      // The sequence system will handle backward navigation through skipSequenceSentence.
      // This prevents the scaled timeline from incorrectly resetting the sentence index
      // after track switches where the scaling factor changes (e.g., original: 1.11x, translation: 0.77x).
      return;
    }
    // Prevent backward movement shortly after a manual seek (track switch)
    // This handles timeline scaling mismatches when audioDuration changes
    const timeSinceManualSeek = Date.now() - lastManualSeekTimeRef.current;
    if (clampedIndex < activeSentenceIndex && timeSinceManualSeek < 500) {
      if (import.meta.env.DEV) {
        console.debug('[timelineDisplay effect] Skipping backward movement after recent manual seek', {
          from: activeSentenceIndex,
          candidate: clampedIndex,
          timeSinceManualSeek,
        });
      }
      return;
    }
    if (clampedIndex > activeSentenceIndex) {
      if (effectiveTime < candidateRuntime.startTime + epsilon) {
        return;
      }
    } else if (clampedIndex < activeSentenceIndex) {
      if (effectiveTime > candidateRuntime.endTime - epsilon) {
        return;
      }
    }
    if (import.meta.env.DEV) {
      console.debug('[timelineDisplay effect] Setting activeSentenceIndex', {
        from: activeSentenceIndex,
        to: clampedIndex,
        effectiveTime,
        candidateRuntime: { start: candidateRuntime.startTime, end: candidateRuntime.endTime },
      });
    }
    setActiveSentenceIndex(clampedIndex);
  }, [timelineDisplay, activeSentenceIndex, timelineSentences]);

  const {
    pendingInitialSeekRef: pendingInitialSeek,
    pendingSequenceExitSeekRef,
    emitAudioProgress,
  } = useAudioModeTransition({
    audioResetKey,
    effectiveAudioUrl,
    sequenceEnabledRef,
    sequencePlan,
    sequenceDefaultTrack,
    sequenceTrackRef,
    sequenceIndexRef,
    pendingSequenceSeekRef,
    setSequenceTrack,
    audioRef,
    inlineAudioPlayingRef,
    originalTrackUrl,
    translationTrackUrl,
    activeSentenceIndexRef,
    setActiveSentenceIndex,
    setChunkTime,
    setAudioDuration,
    onAudioProgress,
  });

  const {
    getSequenceIndexForPlayback,
    advanceSequenceSegment,
    syncSequenceIndexToTime,
    maybeAdvanceSequence,
    isDwellPauseRef,
    skipSequenceSentence,
    handleSequenceAwareTokenSeek,
    selectedTracks,
    sequenceDebugInfo,
  } = useSequencePlaybackController({
    sequenceEnabled,
    sequenceEnabledRef,
    sequencePlan,
    sequenceTrack,
    setSequenceTrack,
    sequenceDefaultTrack,
    sequenceTrackRef,
    sequenceIndexRef,
    pendingSequenceSeekRef,
    sequenceAutoPlayRef,
    lastSequenceEndedRef,
    audioRef,
    inlineAudioPlayingRef,
    activeSentenceIndex,
    activeSentenceIndexRef,
    setActiveSentenceIndex,
    setChunkTime,
    updateSentenceForTime,
    updateActiveGateFromTime,
    emitAudioProgress,
    hasTimeline,
    wordSyncControllerRef,
    lastManualSeekTimeRef,
    resolvedCueVisibility,
    trackRefs,
    sequenceDebugEnabled,
    originalAudioEnabled,
    translationAudioEnabled,
    originalTrackUrl,
    translationTrackUrl,
    resolvedAudioUrl,
    chunkTime,
  });

  const { audioTimelineText, audioTimelineTitle } = useInteractiveAudioTimeline({
    chunk,
    chunks,
    activeChunkIndex,
    selectedTracks,
    chunkTime,
    sequenceEnabled,
    sequencePlan,
    sequenceIndexRef,
    jobId,
    isInlineAudioPlaying,
    isSeekingRef,
  });

  const {
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
  } = useInlineAudioHandlers({
    audioRef,
    effectiveAudioUrl,
    resolvedAudioUrl,
    audioResetKey,
    inlineAudioPlayingRef,
    setIsInlineAudioPlaying,
    sequenceEnabled,
    sequencePlanLength: sequencePlan.length,
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
    pendingInitialSeekRef: pendingInitialSeek,
    pendingSequenceExitSeekRef,
    timelineSentences,
    isSeekingRef,
    lastManualSeekTimeRef,
    wordSyncControllerRef,
    effectivePlaybackRate,
    chunkTime,
    isDwellPauseRef,
  });

  const hasVisibleCues =
    resolvedCueVisibility.original ||
    resolvedCueVisibility.transliteration ||
    resolvedCueVisibility.translation;

  return {
    attachPlayerCore,
    attachMediaElement,
    audioRef,
    playerCore,
    chunkTime,
    audioDuration,
    activeSentenceIndex,
    setActiveSentenceIndex,
    resolvedAudioUrl,
    effectiveAudioUrl,
    audioResetKey,
    inlineAudioPlayingRef,
    isInlineAudioPlaying,
    audioTimelineText,
    audioTimelineTitle,
    sequenceDebugInfo,
    resolvedTimingTrack,
    useCombinedPhases,
    resolvedCueVisibility,
    hasVisibleCues,
    timelineSentences,
    timelineDisplay,
    rawSentences,
    textPlayerSentences,
    totalSentences,
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
    handleTokenSeek: handleSequenceAwareTokenSeek,
    wordSync: {
      legacyWordSyncEnabled,
      shouldUseWordSync,
      wordSyncSentences,
    },
    sequencePlayback: {
      enabled: sequenceEnabled,
      skipSentence: skipSequenceSentence,
    },
  };
}
