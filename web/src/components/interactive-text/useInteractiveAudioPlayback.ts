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
  type SelectedAudioTrack,
  type SequenceSegment,
  type SequenceTrack,
} from './useInteractiveAudioSequence';
import { useInteractiveAudioTimeline } from './useInteractiveAudioTimeline';
import { useInlineAudioHandlers } from './useInlineAudioHandlers';
import { useInteractiveTextTiming } from './useInteractiveTextTiming';
import { useInteractiveWordSync } from './useInteractiveWordSync';

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
  const isVariantVisible = useCallback(
    (variant: TextPlayerVariantKind) => {
      if (variant === 'translit') {
        return resolvedCueVisibility.transliteration;
      }
      return resolvedCueVisibility[variant];
    },
    [resolvedCueVisibility],
  );
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
  const [activeSentenceIndex, setActiveSentenceIndex] = useState(0);

  const activeSentenceIndexRef = useRef(0);
  useEffect(() => {
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
    isVariantVisible,
    revealMemoryRef,
  });

  const { rawSentences, textPlayerSentences, sentenceWeightSummary } = useTextPlayerSentences({
    paragraphs,
    timelineDisplay,
    chunk,
    activeSentenceIndex,
    cueVisibility: resolvedCueVisibility,
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
    setChunkTime(0);
    setActiveSentenceIndex(0);
  }, [hasTimeline, chunk?.chunkId, chunk?.rangeFragment, chunk?.startSentence, chunk?.endSentence]);

  useEffect(() => {
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

  useEffect(() => {
    if (!timelineDisplay) {
      return;
    }
    const { activeIndex: candidateIndex, effectiveTime } = timelineDisplay;
    if (candidateIndex === activeSentenceIndex) {
      return;
    }
    if (!timelineSentences || timelineSentences.length === 0) {
      setActiveSentenceIndex(candidateIndex);
      return;
    }
    const epsilon = 0.05;
    const clampedIndex = Math.max(0, Math.min(candidateIndex, timelineSentences.length - 1));
    const candidateRuntime = timelineSentences[clampedIndex];
    if (!candidateRuntime) {
      setActiveSentenceIndex(clampedIndex);
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
    setActiveSentenceIndex(clampedIndex);
  }, [timelineDisplay, activeSentenceIndex, timelineSentences]);

  const pendingInitialSeek = useRef<number | null>(null);
  const lastReportedPosition = useRef(0);

  useEffect(() => {
    if (!effectiveAudioUrl) {
      pendingInitialSeek.current = null;
      lastReportedPosition.current = 0;
      setActiveSentenceIndex(0);
      setAudioDuration(null);
      setChunkTime(0);
      return;
    }
    pendingInitialSeek.current = null;
    lastReportedPosition.current = 0;
    setActiveSentenceIndex(0);
    setAudioDuration(null);
    setChunkTime(0);
  }, [audioResetKey, getStoredAudioPosition]);

  const findSequenceIndexForSentence = useCallback(
    (sentenceIndex: number, preferredTrack?: SequenceTrack | null) => {
      if (!sequencePlan.length || sentenceIndex < 0) {
        return -1;
      }
      if (preferredTrack) {
        const matched = sequencePlan.findIndex(
          (segment) => segment.sentenceIndex === sentenceIndex && segment.track === preferredTrack,
        );
        if (matched >= 0) {
          return matched;
        }
      }
      return sequencePlan.findIndex((segment) => segment.sentenceIndex === sentenceIndex);
    },
    [sequencePlan],
  );

  useEffect(() => {
    if (!sequenceEnabled || sequencePlan.length === 0) {
      sequenceIndexRef.current = 0;
      setSequenceTrack(null);
      pendingSequenceSeekRef.current = null;
      return;
    }
    const preferredSentence = activeSentenceIndexRef.current ?? 0;
    const preferredTrack = sequenceTrackRef.current ?? sequenceDefaultTrack;
    let nextIndex = findSequenceIndexForSentence(preferredSentence, preferredTrack);
    if (nextIndex < 0) {
      nextIndex = findSequenceIndexForSentence(preferredSentence, null);
    }
    if (nextIndex < 0) {
      nextIndex = 0;
    }
    const segment = sequencePlan[nextIndex];
    if (!segment) {
      return;
    }
    sequenceIndexRef.current = nextIndex;
    if (sequenceTrackRef.current && sequenceTrackRef.current === segment.track) {
      pendingSequenceSeekRef.current = null;
      return;
    }
    if (!sequenceTrackRef.current) {
      setSequenceTrack(segment.track);
      return;
    }
    pendingSequenceSeekRef.current = {
      time: segment.start,
      autoPlay: inlineAudioPlayingRef.current,
    };
    setSequenceTrack(segment.track);
  }, [findSequenceIndexForSentence, sequenceDefaultTrack, sequenceEnabled, sequencePlan, setSequenceTrack]);

  const syncSequenceIndexToTime = useCallback(
    (mediaTime: number) => {
      if (!sequenceEnabled || sequencePlan.length === 0) {
        return;
      }
      const currentTrack = sequenceTrackRef.current;
      if (!currentTrack) {
        return;
      }
      const epsilon = 0.05;
      let matchIndex = sequencePlan.findIndex(
        (segment) =>
          segment.track === currentTrack &&
          mediaTime >= segment.start - epsilon &&
          mediaTime <= segment.end + epsilon,
      );
      if (matchIndex < 0) {
        matchIndex = sequencePlan.findIndex(
          (segment) => segment.track === currentTrack && mediaTime < segment.start,
        );
        if (matchIndex < 0) {
          matchIndex = sequencePlan.length - 1;
        }
      }
      if (matchIndex >= 0) {
        sequenceIndexRef.current = matchIndex;
      }
    },
    [sequenceEnabled, sequencePlan],
  );

  const getSequenceIndexForPlayback = useCallback(() => {
    if (!sequencePlan.length) {
      return -1;
    }
    const currentTrack = sequenceTrackRef.current ?? sequenceDefaultTrack;
    const sentenceIndex = activeSentenceIndexRef.current ?? 0;
    const resolvedIndex = findSequenceIndexForSentence(sentenceIndex, currentTrack);
    if (resolvedIndex >= 0) {
      return resolvedIndex;
    }
    return sequenceIndexRef.current >= 0 ? sequenceIndexRef.current : 0;
  }, [findSequenceIndexForSentence, sequenceDefaultTrack, sequencePlan]);

  const emitAudioProgress = useCallback(
    (position: number) => {
      if (!effectiveAudioUrl || !onAudioProgress) {
        return;
      }
      if (Math.abs(position - lastReportedPosition.current) < 0.25) {
        return;
      }
      lastReportedPosition.current = position;
      onAudioProgress(effectiveAudioUrl, position);
    },
    [effectiveAudioUrl, onAudioProgress],
  );

  const applySequenceSegment = useCallback(
    (segment: SequenceSegment, options?: { autoPlay?: boolean }) => {
      if (!segment) {
        return;
      }
      const element = audioRef.current;
      const shouldPlay = options?.autoPlay ?? inlineAudioPlayingRef.current;
      sequenceAutoPlayRef.current = shouldPlay;
      if (sequenceTrackRef.current !== segment.track) {
        sequenceTrackRef.current = segment.track;
        pendingSequenceSeekRef.current = { time: segment.start, autoPlay: shouldPlay };
        setSequenceTrack(segment.track);
        return;
      }
      if (!element) {
        return;
      }
      wordSyncControllerRef.current?.handleSeeking();
      element.currentTime = Math.max(0, segment.start);
      setChunkTime(segment.start);
      if (!hasTimeline && Number.isFinite(element.duration) && element.duration > 0) {
        updateSentenceForTime(segment.start, element.duration);
      }
      updateActiveGateFromTime(segment.start);
      emitAudioProgress(segment.start);
      if (shouldPlay) {
        const result = element.play?.();
        if (result && typeof result.catch === 'function') {
          result.catch(() => undefined);
        }
      }
    },
    [emitAudioProgress, hasTimeline, updateActiveGateFromTime, updateSentenceForTime],
  );

  const advanceSequenceSegment = useCallback(
    (options?: { autoPlay?: boolean }) => {
      if (!sequenceEnabled || sequencePlan.length === 0) {
        return false;
      }
      const currentIndex = getSequenceIndexForPlayback();
      if (currentIndex < 0) {
        return false;
      }
      const nextIndex = currentIndex + 1;
      if (nextIndex >= sequencePlan.length) {
        return false;
      }
      const nextSegment = sequencePlan[nextIndex];
      if (!nextSegment) {
        return false;
      }
      sequenceIndexRef.current = nextIndex;
      applySequenceSegment(nextSegment, options);
      return true;
    },
    [applySequenceSegment, getSequenceIndexForPlayback, sequenceEnabled, sequencePlan],
  );

  const maybeAdvanceSequence = useCallback(
    (mediaTime: number) => {
      if (!sequenceEnabled || sequencePlan.length === 0) {
        return false;
      }
      if (!inlineAudioPlayingRef.current) {
        return false;
      }
      if (pendingSequenceSeekRef.current) {
        return false;
      }
      syncSequenceIndexToTime(mediaTime);
      const currentIndex = getSequenceIndexForPlayback();
      const segment = currentIndex >= 0 ? sequencePlan[currentIndex] : null;
      if (!segment) {
        return false;
      }
      if (mediaTime < segment.end - 0.03) {
        return false;
      }
      return advanceSequenceSegment({ autoPlay: true });
    },
    [advanceSequenceSegment, getSequenceIndexForPlayback, sequenceEnabled, sequencePlan, syncSequenceIndexToTime],
  );

  const selectedTracks = useMemo<SelectedAudioTrack[]>(() => {
    if (sequenceEnabled) {
      return ['original', 'translation'];
    }
    if (trackRefs.effectiveAudioRef && trackRefs.effectiveAudioRef === trackRefs.originalTrackRef) {
      return ['original'];
    }
    if (
      trackRefs.effectiveAudioRef &&
      trackRefs.effectiveAudioRef === trackRefs.translationTrackRef
    ) {
      return ['translation'];
    }
    if (trackRefs.effectiveAudioRef && trackRefs.effectiveAudioRef === trackRefs.combinedTrackRef) {
      return ['combined'];
    }
    return [];
  }, [sequenceEnabled, trackRefs]);
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

  const formatSequenceDebugUrl = useCallback((value: string | null) => {
    if (!value) {
      return '—';
    }
    const trimmed = value.trim().replace(/[?#].*$/, '');
    if (!trimmed) {
      return '—';
    }
    const parts = trimmed.split('/');
    return parts[parts.length - 1] || trimmed;
  }, []);

  const sequenceDebugInfo = sequenceDebugEnabled
    ? {
        enabled: sequenceEnabled,
        origEnabled: originalAudioEnabled,
        transEnabled: translationAudioEnabled,
        hasOrigSeg: sequencePlan.some((segment) => segment.track === 'original'),
        hasTransSeg: sequencePlan.some((segment) => segment.track === 'translation'),
        hasOrigTrack: Boolean(originalTrackUrl),
        hasTransTrack: Boolean(translationTrackUrl),
        track: sequenceTrackRef.current ?? sequenceTrack ?? sequenceDefaultTrack,
        index: sequenceIndexRef.current,
        lastEnded: lastSequenceEndedRef.current
          ? lastSequenceEndedRef.current.toFixed(3)
          : 'none',
        autoPlay: sequenceAutoPlayRef.current ? 'true' : 'false',
        plan: sequencePlan.length,
        sentence: activeSentenceIndex,
        time: chunkTime,
        pending: pendingSequenceSeekRef.current
          ? `${pendingSequenceSeekRef.current.time.toFixed(3)}:${
              pendingSequenceSeekRef.current.autoPlay ? 'auto' : 'manual'
            }`
          : 'none',
        playing: audioRef.current ? !audioRef.current.paused : inlineAudioPlayingRef.current,
        audio: formatSequenceDebugUrl(resolvedAudioUrl),
        original: formatSequenceDebugUrl(originalTrackUrl),
        translation: formatSequenceDebugUrl(translationTrackUrl),
      }
    : null;
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
    isSeekingRef,
    wordSyncControllerRef,
    effectivePlaybackRate,
    chunkTime,
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
    handleTokenSeek,
    wordSync: {
      legacyWordSyncEnabled,
      shouldUseWordSync,
      wordSyncSentences,
    },
  };
}
