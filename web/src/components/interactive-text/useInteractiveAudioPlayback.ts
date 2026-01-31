import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { AudioTrackMetadata } from '../../api/dtos';
import type { LiveMediaChunk, MediaClock } from '../../hooks/useLiveMedia';
import { useMediaClock } from '../../hooks/useLiveMedia';
import { usePlayerCore } from '../../hooks/usePlayerCore';
import { timingStore } from '../../stores/timingStore';
import type { TextPlayerVariantKind, TextPlayerSeekInfo } from '../../text-player/TextPlayer';
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

  const pendingInitialSeek = useRef<number | null>(null);
  const lastReportedPosition = useRef(0);
  // Track previous audioResetKey to detect sequence mode transitions
  const prevAudioResetKeyRef = useRef<string | null>(null);
  // Store the target sentence index when transitioning from sequence mode
  const pendingSequenceExitSeekRef = useRef<{ sentenceIndex: number } | null>(null);

  useEffect(() => {
    const prevKey = prevAudioResetKeyRef.current;
    prevAudioResetKeyRef.current = audioResetKey;

    if (!effectiveAudioUrl) {
      // No audio URL - clear pending seeks but PRESERVE the sentence position
      // so that when audio is re-enabled, we can continue from where we were
      pendingInitialSeek.current = null;
      lastReportedPosition.current = 0;
      pendingSequenceExitSeekRef.current = null;
      // DON'T reset activeSentenceIndex - preserve position for when audio is re-enabled
      setAudioDuration(null);
      // DON'T reset chunkTime - preserve position
      return;
    }

    // If the key hasn't changed, don't do anything
    // This handles React re-renders that don't actually change the audio source
    if (prevKey === audioResetKey) {
      return;
    }

    // Detect transitions between sequence mode and single-track mode
    const wasSequenceMode = prevKey?.startsWith('sequence:') ?? false;
    const isSequenceMode = audioResetKey.startsWith('sequence:');
    const isTransitioningFromSequence = wasSequenceMode && !isSequenceMode;
    const isStayingInSequenceMode = wasSequenceMode && isSequenceMode;
    const isEnteringSequenceMode = !wasSequenceMode && isSequenceMode;

    if (isEnteringSequenceMode) {
      // Entering sequence mode from single-track mode
      // Find the correct segment for the current sentence and set up a pending seek
      // This prevents timelineDisplay effect from resetting to 0 when the audio loads
      const currentSentence = activeSentenceIndexRef.current ?? 0;
      const preferredTrack = sequenceTrackRef.current ?? sequenceDefaultTrack;

      // Find the segment for this sentence, preferring the current track
      let targetSegmentIndex = -1;
      if (sequencePlan.length > 0) {
        targetSegmentIndex = sequencePlan.findIndex(
          (seg) => seg.sentenceIndex === currentSentence && seg.track === preferredTrack,
        );
        if (targetSegmentIndex < 0) {
          targetSegmentIndex = sequencePlan.findIndex(
            (seg) => seg.sentenceIndex === currentSentence,
          );
        }
        if (targetSegmentIndex < 0) {
          targetSegmentIndex = 0;
        }
      }

      const targetSegment = sequencePlan[targetSegmentIndex] ?? null;

      if (import.meta.env.DEV) {
        console.debug('[audioResetKey] Entering sequence mode', {
          prevKey,
          newKey: audioResetKey,
          activeSentenceIndex: currentSentence,
          targetSegmentIndex,
          targetSegment,
          currentEffectiveUrl: effectiveAudioUrl,
          originalTrackUrl,
          translationTrackUrl,
        });
      }

      pendingInitialSeek.current = null;
      lastReportedPosition.current = 0;
      // Clear any pending sequence exit seek - we're re-entering sequence mode now
      pendingSequenceExitSeekRef.current = null;
      // Synchronously update sequenceEnabledRef so guards in timelineDisplay effect work immediately
      sequenceEnabledRef.current = true;

      // Begin a transition to guard against timelineDisplay effect resetting position
      timingStore.beginTransition({
        type: 'transitioning',
        targetSentenceIndex: currentSentence,
      });

      // Set up the pending sequence seek so handleLoadedMetadata and timelineDisplay
      // effect will preserve the current position
      if (targetSegment) {
        sequenceIndexRef.current = targetSegmentIndex;
        const shouldPlay = inlineAudioPlayingRef.current;

        // Determine what the new effective audio URL will be after setting the sequence track
        const newEffectiveUrl = targetSegment.track === 'original' ? originalTrackUrl : translationTrackUrl;
        const urlWillChange = newEffectiveUrl !== effectiveAudioUrl;

        if (import.meta.env.DEV) {
          console.debug('[audioResetKey] URL change check', {
            currentUrl: effectiveAudioUrl,
            newUrl: newEffectiveUrl,
            urlWillChange,
            targetTrack: targetSegment.track,
            currentTrack: sequenceTrackRef.current,
          });
        }

        // Check if we need to switch tracks AND the URL will actually change
        // If the URL won't change (already playing the same track), handleLoadedMetadata
        // won't fire, so we need to handle the seek directly
        if (urlWillChange) {
          // Set pending seek - will be consumed by handleLoadedMetadata after audio loads
          pendingSequenceSeekRef.current = {
            time: targetSegment.start,
            autoPlay: shouldPlay,
          };
          sequenceTrackRef.current = targetSegment.track;
          setSequenceTrack(targetSegment.track);
        } else {
          // URL won't change - seek directly without waiting for handleLoadedMetadata
          // This handles the case where sequence mode is enabled but we're already on the right track
          const element = audioRef.current;
          if (element) {
            // Set a brief pending seek to prevent timelineDisplay from overriding
            // Include the target sentence index so we can verify when to clear
            pendingSequenceSeekRef.current = {
              time: targetSegment.start,
              autoPlay: shouldPlay,
              targetSentenceIndex: targetSegment.sentenceIndex,
            };
            // Update the track ref even if URL doesn't change
            sequenceTrackRef.current = targetSegment.track;
            setSequenceTrack(targetSegment.track);
            element.currentTime = targetSegment.start;
            setChunkTime(targetSegment.start);
            setActiveSentenceIndex(targetSegment.sentenceIndex);
            // Clear the pending seek ref after a brief delay to allow the seek to take effect.
            // For same-URL seeks, handleLoadedMetadata won't fire, so we need to clear here.
            const targetSeekTime = targetSegment.start;
            requestAnimationFrame(() => {
              requestAnimationFrame(() => {
                // Only clear if we're still at the same pending seek
                if (pendingSequenceSeekRef.current?.time === targetSeekTime) {
                  if (import.meta.env.DEV) {
                    console.debug('[audioResetKey] Clearing pendingSequenceSeekRef after same-URL seek', {
                      targetSeekTime,
                      currentTime: element.currentTime,
                    });
                  }
                  pendingSequenceSeekRef.current = null;
                  timingStore.completeTransition();
                }
              });
            });
            if (shouldPlay && element.paused) {
              const result = element.play?.();
              if (result && typeof result.catch === 'function') {
                result.catch(() => undefined);
              }
            }
          } else {
            // No element yet - just update state, sequence system will handle seek when element is ready
            sequenceTrackRef.current = targetSegment.track;
            setSequenceTrack(targetSegment.track);
            setActiveSentenceIndex(targetSegment.sentenceIndex);
            // Don't set pendingSequenceSeekRef since there's no element to seek
            // Complete the transition since we've updated the state
            timingStore.completeTransition();
          }
        }
      } else {
        // No target segment found - complete the transition anyway
        timingStore.completeTransition();
      }

      // Don't reset activeSentenceIndex - sequence system will manage it
      setAudioDuration(null);
      return;
    }

    if (isTransitioningFromSequence) {
      // Preserve the current sentence position when exiting sequence mode
      // Store the target sentence for seeking after the new audio loads
      const targetSentence = activeSentenceIndexRef.current;

      // Check if the URL will actually change - if not, we need to handle the seek directly
      // The previous URL was based on sequenceTrack, the new URL is effectiveAudioUrl (from audioResetKey)
      const sequenceTrackUrl = sequenceTrackRef.current === 'original' ? originalTrackUrl : translationTrackUrl;
      const urlWillChange = sequenceTrackUrl !== effectiveAudioUrl;

      if (import.meta.env.DEV) {
        console.debug('[audioResetKey] Transitioning from sequence mode, preserving position', {
          prevKey,
          newKey: audioResetKey,
          targetSentence,
          urlWillChange,
          sequenceTrackUrl,
          effectiveAudioUrl,
        });
      }

      pendingInitialSeek.current = null;
      lastReportedPosition.current = 0;

      if (urlWillChange) {
        // URL will change, so handleLoadedMetadata will fire and can handle the seek
        pendingSequenceExitSeekRef.current = { sentenceIndex: targetSentence };
      } else {
        // URL won't change - need to seek directly
        // The timelineSentences won't be available yet in this effect, so we set the ref
        // and let the timelineDisplay effect handle clearing it with a timeout
        pendingSequenceExitSeekRef.current = { sentenceIndex: targetSentence };
        // Clear the ref after a delay since handleLoadedMetadata won't fire
        setTimeout(() => {
          if (import.meta.env.DEV) {
            console.debug('[audioResetKey] Clearing pendingSequenceExitSeekRef after timeout (URL unchanged)');
          }
          pendingSequenceExitSeekRef.current = null;
        }, 100);
      }
      // Don't reset activeSentenceIndex - keep current position
      // Don't reset chunkTime - will be updated when seeking to the correct position
      setAudioDuration(null);
      return;
    }

    if (isStayingInSequenceMode) {
      // Switching tracks within sequence mode (e.g., original → translation)
      // The activeSentenceIndex is managed by applySequenceSegment, so don't reset it
      if (import.meta.env.DEV) {
        console.debug('[audioResetKey] Track switch within sequence mode, not resetting', {
          prevKey,
          newKey: audioResetKey,
          activeSentenceIndex: activeSentenceIndexRef.current,
        });
      }
      pendingInitialSeek.current = null;
      lastReportedPosition.current = 0;
      // Don't reset activeSentenceIndex or chunkTime - managed by applySequenceSegment
      setAudioDuration(null);
      return;
    }

    // Check if we're switching between single-track modes (e.g., translation-only → original-only)
    // In this case, we want to preserve position and seek to the corresponding time
    // This happens when neither the old nor new key is in sequence mode
    const isSwitchingSingleTracks = prevKey && !wasSequenceMode && !isSequenceMode && prevKey !== audioResetKey;
    if (isSwitchingSingleTracks) {
      const targetSentence = activeSentenceIndexRef.current;
      if (import.meta.env.DEV) {
        console.debug('[audioResetKey] Switching single tracks, preserving position', {
          prevKey,
          newKey: audioResetKey,
          targetSentence,
        });
      }
      pendingInitialSeek.current = null;
      lastReportedPosition.current = 0;
      // Set up a pending seek - handleLoadedMetadata will seek to the correct position
      // for this sentence in the new track's timeline
      pendingSequenceExitSeekRef.current = { sentenceIndex: targetSentence };
      setAudioDuration(null);
      return;
    }

    pendingInitialSeek.current = null;
    lastReportedPosition.current = 0;
    pendingSequenceExitSeekRef.current = null;
    setActiveSentenceIndex(0);
    setAudioDuration(null);
    setChunkTime(0);
  }, [audioResetKey, effectiveAudioUrl, getStoredAudioPosition, originalTrackUrl, sequenceDefaultTrack, sequencePlan, setActiveSentenceIndex, setChunkTime, setSequenceTrack, translationTrackUrl]);

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

  // Track if we're in the middle of a programmatic sequence operation
  const sequenceOperationInProgressRef = useRef(false);

  // Track previous sequenceEnabled state to detect transitions
  const prevSequenceEnabledRef = useRef(sequenceEnabled);
  useEffect(() => {
    const wasEnabled = prevSequenceEnabledRef.current;
    prevSequenceEnabledRef.current = sequenceEnabled;

    if (!sequenceEnabled || sequencePlan.length === 0) {
      // Clear any pending sequence operations when disabled
      pendingSequenceSeekRef.current = null;
      setSequenceTrack(null);

      // If we're transitioning from enabled to disabled, preserve the current sentence
      // by NOT resetting sequenceIndexRef - the activeSentenceIndex is already correct
      if (wasEnabled && !sequenceEnabled) {
        if (import.meta.env.DEV) {
          console.debug('[SequenceSync] Sequence disabled, preserving sentence position', {
            activeSentenceIndex: activeSentenceIndexRef.current,
          });
        }
        // Don't reset sequenceIndexRef - the sentence position is preserved in activeSentenceIndex
      } else {
        if (import.meta.env.DEV) {
          console.debug('[SequenceSync] Disabled or empty plan, resetting index');
        }
        sequenceIndexRef.current = 0;
      }
      return;
    }
    // Check if there's a pending sequence seek - if so, the advanceSequenceSegment
    // or applySequenceSegment has already set up the next segment, don't interfere
    if (pendingSequenceSeekRef.current) {
      if (import.meta.env.DEV) {
        console.debug('[SequenceSync] Pending seek exists, skipping', pendingSequenceSeekRef.current);
      }
      return;
    }
    // Check if the current sequenceIndexRef points to a valid segment
    // Don't check track match - just verify the index is in range
    const currentIndex = sequenceIndexRef.current;
    if (currentIndex >= 0 && currentIndex < sequencePlan.length) {
      // The current index is valid - don't reset it
      // The track will be updated by applySequenceSegment when needed
      if (import.meta.env.DEV) {
        console.debug('[SequenceSync] Index valid, not resetting', { currentIndex, planLength: sequencePlan.length });
      }
      return;
    }
    // Only initialize if the index is invalid (first load or plan changed)
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
    if (import.meta.env.DEV) {
      console.debug('[SequenceSync] Initializing index', { nextIndex, segment, preferredSentence, preferredTrack });
    }
    sequenceIndexRef.current = nextIndex;
    if (!sequenceTrackRef.current) {
      setSequenceTrack(segment.track);
    }
  }, [findSequenceIndexForSentence, sequenceDefaultTrack, sequenceEnabled, sequencePlan, setSequenceTrack]);

  const syncSequenceIndexToTime = useCallback(
    (mediaTime: number) => {
      if (!sequenceEnabled || sequencePlan.length === 0) {
        return;
      }
      // Don't re-sync during a pending sequence seek - advanceSequenceSegment already set the index
      if (pendingSequenceSeekRef.current) {
        return;
      }
      const currentTrack = sequenceTrackRef.current;
      if (!currentTrack) {
        return;
      }
      const epsilon = 0.05;

      // First check if the current index is still valid for the given time
      // This prevents resetting during track switches where the time is at a segment boundary
      const currentIndex = sequenceIndexRef.current;
      if (currentIndex >= 0 && currentIndex < sequencePlan.length) {
        const currentSegment = sequencePlan[currentIndex];
        if (
          currentSegment.track === currentTrack &&
          mediaTime >= currentSegment.start - epsilon &&
          mediaTime <= currentSegment.end + epsilon
        ) {
          // Current index is still valid, don't change it
          return;
        }
      }

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
        if (import.meta.env.DEV) {
          console.debug('[applySequenceSegment] Switching track', {
            from: sequenceTrackRef.current,
            to: segment.track,
            segment,
            pendingSeek: { time: segment.start, autoPlay: shouldPlay },
          });
        }
        // Begin transition using store state - primary guard for timeline effects
        timingStore.beginTransition({
          type: 'transitioning',
          fromTrack: sequenceTrackRef.current ?? undefined,
          toTrack: segment.track,
          targetSentenceIndex: segment.sentenceIndex,
          targetTime: segment.start,
          autoPlay: shouldPlay,
        });
        sequenceTrackRef.current = segment.track;
        pendingSequenceSeekRef.current = { time: segment.start, autoPlay: shouldPlay };
        // Clear word highlight immediately when switching tracks to prevent flickering
        // The AudioSyncController will recalculate once the new timeline is loaded
        timingStore.setLast(null);
        // Update chunkTime and activeSentenceIndex immediately when switching tracks
        // This prevents flickering by ensuring the timeline calculations use correct values
        // before the new audio loads
        setChunkTime(segment.start);
        setActiveSentenceIndex(segment.sentenceIndex);
        if (import.meta.env.DEV) {
          console.debug('[applySequenceSegment] Set activeSentenceIndex', {
            sentenceIndex: segment.sentenceIndex,
            refValue: activeSentenceIndexRef.current,
          });
        }
        setSequenceTrack(segment.track);
        return;
      }
      if (!element) {
        if (import.meta.env.DEV) {
          console.debug('[applySequenceSegment] No element, returning');
        }
        return;
      }
      if (import.meta.env.DEV) {
        console.debug('[applySequenceSegment] Same track, seeking to', {
          segment,
          shouldPlay,
        });
      }
      // Begin transition for same-track seeks
      timingStore.beginTransition({
        type: 'seeking',
        targetSentenceIndex: segment.sentenceIndex,
        targetTime: segment.start,
        autoPlay: shouldPlay,
      });
      // Set pendingSequenceSeekRef to prevent timelineDisplay effect from overriding
      // the activeSentenceIndex during the seek
      pendingSequenceSeekRef.current = { time: segment.start, autoPlay: shouldPlay };
      wordSyncControllerRef.current?.handleSeeking();
      element.currentTime = Math.max(0, segment.start);
      setChunkTime(segment.start);
      setActiveSentenceIndex(segment.sentenceIndex);
      if (!hasTimeline && Number.isFinite(element.duration) && element.duration > 0) {
        updateSentenceForTime(segment.start, element.duration);
      }
      updateActiveGateFromTime(segment.start);
      emitAudioProgress(segment.start);
      // Mark this as a manual seek to prevent backward index movement due to timeline scaling
      // This protects against the timelineDisplay effect resetting sentence index after same-track seek
      lastManualSeekTimeRef.current = Date.now();
      // Clear the pending seek ref and transition state after a brief delay to allow the seek to take effect.
      // For same-track seeks, handleLoadedMetadata won't fire, so we need to clear here.
      // We use requestAnimationFrame to ensure the seek has been processed.
      const targetSeekTime = segment.start;
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          // Only clear if we're still at the same pending seek
          if (pendingSequenceSeekRef.current?.time === targetSeekTime) {
            if (import.meta.env.DEV) {
              console.debug('[applySequenceSegment] Clearing pendingSequenceSeekRef after same-track seek', {
                targetSeekTime,
                currentTime: element.currentTime,
              });
            }
            pendingSequenceSeekRef.current = null;
            timingStore.completeTransition();
          }
        });
      });
      if (shouldPlay) {
        const result = element.play?.();
        if (result && typeof result.catch === 'function') {
          result.catch(() => undefined);
        }
      }
    },
    [emitAudioProgress, hasTimeline, setActiveSentenceIndex, setChunkTime, updateActiveGateFromTime, updateSentenceForTime],
  );

  const advanceSequenceSegment = useCallback(
    (options?: { autoPlay?: boolean }) => {
      if (!sequenceEnabled || sequencePlan.length === 0) {
        return false;
      }
      // Use sequenceIndexRef directly to advance to the next segment
      // Don't use getSequenceIndexForPlayback which can re-compute based on sentence index
      const currentIndex = sequenceIndexRef.current;
      if (currentIndex < 0 || currentIndex >= sequencePlan.length) {
        return false;
      }
      const nextIndex = currentIndex + 1;
      if (nextIndex >= sequencePlan.length) {
        if (import.meta.env.DEV) {
          console.debug('[advanceSequenceSegment] No more segments', { currentIndex, planLength: sequencePlan.length });
        }
        return false;
      }
      const nextSegment = sequencePlan[nextIndex];
      if (!nextSegment) {
        return false;
      }
      if (import.meta.env.DEV) {
        console.debug('[advanceSequenceSegment] Advancing', {
          from: currentIndex,
          to: nextIndex,
          segment: nextSegment,
          currentTrack: sequenceTrackRef.current,
          nextTrack: nextSegment.track,
        });
      }
      sequenceIndexRef.current = nextIndex;
      applySequenceSegment(nextSegment, options);
      return true;
    },
    [applySequenceSegment, sequenceEnabled, sequencePlan],
  );

  // Skip to a different sentence within the sequence (direction: 1 for next, -1 for previous)
  // Respects cue visibility: if only one track is visible, skip to that track
  const skipSequenceSentence = useCallback(
    (direction: 1 | -1): boolean => {
      if (!sequenceEnabled || sequencePlan.length === 0) {
        return false;
      }
      const currentIndex = sequenceIndexRef.current;
      if (currentIndex < 0 || currentIndex >= sequencePlan.length) {
        return false;
      }
      const currentSegment = sequencePlan[currentIndex];
      if (!currentSegment) {
        return false;
      }
      const currentSentenceIndex = currentSegment.sentenceIndex;
      const targetSentenceIndex = currentSentenceIndex + direction;

      // Determine preferred track based on cue visibility
      // This controls which track to start at when skipping to a different sentence
      const origVisible = resolvedCueVisibility.original;
      const transVisible = resolvedCueVisibility.translation || resolvedCueVisibility.transliteration;
      let preferredTrack: SequenceTrack | null = null;
      if (origVisible && transVisible) {
        // Both visible: start at beginning of sentence (original comes first)
        preferredTrack = 'original';
      } else if (origVisible) {
        preferredTrack = 'original';
      } else if (transVisible) {
        preferredTrack = 'translation';
      } else {
        // Neither visible: fallback to original (start at beginning)
        preferredTrack = 'original';
      }

      // Find the first segment for the target sentence (prefer visibility-based track)
      let targetIndex = sequencePlan.findIndex(
        (seg) => seg.sentenceIndex === targetSentenceIndex && seg.track === preferredTrack,
      );
      // If not found with preferred track, try any segment for that sentence
      if (targetIndex < 0) {
        targetIndex = sequencePlan.findIndex((seg) => seg.sentenceIndex === targetSentenceIndex);
      }
      if (targetIndex < 0) {
        return false;
      }
      const targetSegment = sequencePlan[targetIndex];
      if (!targetSegment) {
        return false;
      }
      sequenceIndexRef.current = targetIndex;
      applySequenceSegment(targetSegment, { autoPlay: inlineAudioPlayingRef.current });
      return true;
    },
    [applySequenceSegment, resolvedCueVisibility, sequenceDefaultTrack, sequenceEnabled, sequencePlan],
  );

  // Seek to a specific token position, handling sequence mode track switching
  // When in sequence mode and clicking a token from a different track, switch to that track
  const handleSequenceAwareTokenSeek = useCallback(
    (time: number, info?: { variantKind: TextPlayerVariantKind; sentenceIndex: number }) => {
      if (import.meta.env.DEV) {
        console.debug('[handleSequenceAwareTokenSeek]', {
          time,
          info,
          sequenceEnabled,
          currentTrack: sequenceTrackRef.current,
        });
      }

      // If not in sequence mode or no info provided, just do a simple seek
      if (!sequenceEnabled || !info) {
        const element = audioRef.current;
        if (!element || !Number.isFinite(time)) {
          return;
        }
        const target = Math.max(
          0,
          Math.min(time, Number.isFinite(element.duration) ? element.duration : time),
        );
        element.currentTime = target;
        setChunkTime(target);
        const maybePlay = element.play?.();
        if (maybePlay && typeof maybePlay.catch === 'function') {
          maybePlay.catch(() => undefined);
        }
        return;
      }

      // Map variant kind to sequence track
      const targetTrack: SequenceTrack | null =
        info.variantKind === 'original'
          ? 'original'
          : info.variantKind === 'translation'
            ? 'translation'
            : null;

      if (!targetTrack) {
        // Transliteration or unknown variant - no dedicated audio track
        // Just seek in the current track
        const element = audioRef.current;
        if (!element || !Number.isFinite(time)) {
          return;
        }
        const target = Math.max(
          0,
          Math.min(time, Number.isFinite(element.duration) ? element.duration : time),
        );
        element.currentTime = target;
        setChunkTime(target);
        const maybePlay = element.play?.();
        if (maybePlay && typeof maybePlay.catch === 'function') {
          maybePlay.catch(() => undefined);
        }
        return;
      }

      // Find the segment in the sequence plan for this sentence and track
      const targetIndex = sequencePlan.findIndex(
        (seg) => seg.sentenceIndex === info.sentenceIndex && seg.track === targetTrack,
      );

      if (targetIndex < 0) {
        // No segment found for this sentence/track combo - fall back to simple seek
        if (import.meta.env.DEV) {
          console.debug('[handleSequenceAwareTokenSeek] No segment found for sentence/track', {
            sentenceIndex: info.sentenceIndex,
            targetTrack,
          });
        }
        const element = audioRef.current;
        if (!element || !Number.isFinite(time)) {
          return;
        }
        const target = Math.max(
          0,
          Math.min(time, Number.isFinite(element.duration) ? element.duration : time),
        );
        element.currentTime = target;
        setChunkTime(target);
        const maybePlay = element.play?.();
        if (maybePlay && typeof maybePlay.catch === 'function') {
          maybePlay.catch(() => undefined);
        }
        return;
      }

      const targetSegment = sequencePlan[targetIndex];
      if (!targetSegment) {
        return;
      }

      // Update the sequence index
      sequenceIndexRef.current = targetIndex;

      // If we're already on the correct track, just seek within the current audio
      if (sequenceTrackRef.current === targetTrack) {
        if (import.meta.env.DEV) {
          console.debug('[handleSequenceAwareTokenSeek] Same track, seeking directly', {
            targetTrack,
            time,
          });
        }
        const element = audioRef.current;
        if (!element || !Number.isFinite(time)) {
          return;
        }
        // Use the time from the token, not the segment start
        const target = Math.max(
          0,
          Math.min(time, Number.isFinite(element.duration) ? element.duration : time),
        );
        element.currentTime = target;
        setChunkTime(target);
        setActiveSentenceIndex(info.sentenceIndex);
        const maybePlay = element.play?.();
        if (maybePlay && typeof maybePlay.catch === 'function') {
          maybePlay.catch(() => undefined);
        }
        return;
      }

      // Different track - need to switch tracks and seek to the token time
      if (import.meta.env.DEV) {
        console.debug('[handleSequenceAwareTokenSeek] Switching track', {
          from: sequenceTrackRef.current,
          to: targetTrack,
          sentenceIndex: info.sentenceIndex,
          seekTime: time,
        });
      }

      // Create a modified segment with the token's seek time instead of segment start
      const modifiedSegment: SequenceSegment = {
        ...targetSegment,
        start: time, // Use token time instead of segment start
      };

      applySequenceSegment(modifiedSegment, { autoPlay: inlineAudioPlayingRef.current });
    },
    [applySequenceSegment, audioRef, sequenceEnabled, sequencePlan, setActiveSentenceIndex, setChunkTime],
  );

  const maybeAdvanceSequence = useCallback(
    (mediaTime: number) => {
      // Use ref to get current value - prevents stale closure issues during state transitions
      if (!sequenceEnabledRef.current || sequencePlan.length === 0) {
        return false;
      }
      if (!inlineAudioPlayingRef.current) {
        return false;
      }
      if (pendingSequenceSeekRef.current) {
        if (import.meta.env.DEV) {
          console.debug('[maybeAdvanceSequence] Skipping due to pending seek', pendingSequenceSeekRef.current);
        }
        return false;
      }
      // Use sequenceIndexRef directly - don't recalculate based on sentence index
      // as that can find the wrong segment when multiple segments exist for same sentence
      const currentIndex = sequenceIndexRef.current;
      if (currentIndex < 0 || currentIndex >= sequencePlan.length) {
        return false;
      }
      const segment = sequencePlan[currentIndex];
      if (!segment) {
        return false;
      }
      // Only advance if we're past the current segment's end time
      if (mediaTime < segment.end - 0.03) {
        return false;
      }
      // Check if this is the last segment - if so, don't try to advance
      // The handleAudioEnded will handle transitioning to the next chunk
      if (currentIndex >= sequencePlan.length - 1) {
        if (import.meta.env.DEV) {
          console.debug('[maybeAdvanceSequence] At last segment, waiting for audio end', {
            mediaTime,
            segmentEnd: segment.end,
            currentIndex,
          });
        }
        return false;
      }
      if (import.meta.env.DEV) {
        console.debug('[maybeAdvanceSequence] Time exceeded segment end', {
          mediaTime,
          segmentEnd: segment.end,
          currentIndex,
          segment,
        });
      }
      return advanceSequenceSegment({ autoPlay: true });
    },
    [advanceSequenceSegment, sequenceEnabled, sequencePlan],
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
    pendingSequenceExitSeekRef,
    timelineSentences,
    isSeekingRef,
    lastManualSeekTimeRef,
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
