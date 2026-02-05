/**
 * Manages sequence playback logic — segment lookup, sync, advance, skip, seek, dwell.
 *
 * Extracted from useInteractiveAudioPlayback to reduce its size.
 * All refs are passed by identity from the parent; this hook owns no audio element state.
 */

import { useCallback, useEffect, useMemo, useRef } from 'react';
import { timingStore } from '../../stores/timingStore';
import type { TextPlayerVariantKind } from '../../text-player/TextPlayer';
import type {
  SelectedAudioTrack,
  SequenceSegment,
  SequenceTrack,
} from './useInteractiveAudioSequence';
import type { WordSyncController } from './types';

// ─── Constants ──────────────────────────────────────────────────────
const SEQUENCE_SEGMENT_DWELL_MS = 250;

// ─── Types ──────────────────────────────────────────────────────────

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

type TrackRefs = {
  originalTrackRef: string | null;
  translationTrackRef: string | null;
  combinedTrackRef: string | null;
  effectiveAudioRef: string | null;
};

export type UseSequencePlaybackControllerArgs = {
  // From useInteractiveAudioSequence
  sequenceEnabled: boolean;
  sequenceEnabledRef: React.MutableRefObject<boolean>;
  sequencePlan: SequenceSegment[];
  sequenceTrack: SequenceTrack | null;
  setSequenceTrack: (track: SequenceTrack | null) => void;
  sequenceDefaultTrack: SequenceTrack;
  sequenceTrackRef: React.MutableRefObject<SequenceTrack | null>;
  sequenceIndexRef: React.MutableRefObject<number>;
  pendingSequenceSeekRef: React.MutableRefObject<{ time: number; autoPlay: boolean; targetSentenceIndex?: number } | null>;
  sequenceAutoPlayRef: React.MutableRefObject<boolean>;
  lastSequenceEndedRef: React.MutableRefObject<number | null>;

  // Audio element
  audioRef: React.MutableRefObject<HTMLAudioElement | null>;
  inlineAudioPlayingRef: React.MutableRefObject<boolean>;

  // Sentence state
  activeSentenceIndex: number;
  activeSentenceIndexRef: React.MutableRefObject<number>;
  setActiveSentenceIndex: (value: number) => void;
  setChunkTime: React.Dispatch<React.SetStateAction<number>>;

  // Callbacks from parent
  updateSentenceForTime: (time: number, duration: number) => void;
  updateActiveGateFromTime: (time: number) => void;
  emitAudioProgress: (position: number) => void;
  hasTimeline: boolean;

  // Word sync
  wordSyncControllerRef: React.MutableRefObject<WordSyncController | null>;

  // Manual seek tracking
  lastManualSeekTimeRef: React.MutableRefObject<number>;

  // Cue visibility for skip logic
  resolvedCueVisibility: CueVisibility;

  // Track URLs
  trackRefs: TrackRefs;

  // Debug
  sequenceDebugEnabled: boolean;
  originalAudioEnabled: boolean;
  translationAudioEnabled: boolean;
  originalTrackUrl: string | null;
  translationTrackUrl: string | null;
  resolvedAudioUrl: string | null;
  chunkTime: number;
};

export type UseSequencePlaybackControllerResult = {
  // Consumed by useInlineAudioHandlers (interface unchanged)
  getSequenceIndexForPlayback: () => number;
  advanceSequenceSegment: (options?: { autoPlay?: boolean }) => boolean;
  syncSequenceIndexToTime: (mediaTime: number) => void;
  maybeAdvanceSequence: (mediaTime: number) => boolean;
  isDwellPauseRef: React.MutableRefObject<boolean>;

  // Consumed by parent for external API
  skipSequenceSentence: (direction: 1 | -1) => boolean;
  handleSequenceAwareTokenSeek: (time: number, info?: { variantKind: TextPlayerVariantKind; sentenceIndex: number }) => void;
  selectedTracks: SelectedAudioTrack[];
  sequenceDebugInfo: SequenceDebugInfo | null;

  // Needed by transition effect (stays in parent)
  findSequenceIndexForSentence: (sentenceIndex: number, preferredTrack?: SequenceTrack | null) => number;
  applySequenceSegment: (segment: SequenceSegment, options?: { autoPlay?: boolean }) => void;

  // Refs owned by this hook, needed by parent
  sequenceSegmentDwellRef: React.MutableRefObject<number | null>;
  sequenceOperationInProgressRef: React.MutableRefObject<boolean>;
};

// ─── Hook ───────────────────────────────────────────────────────────

export function useSequencePlaybackController({
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
}: UseSequencePlaybackControllerArgs): UseSequencePlaybackControllerResult {
  // ── Refs owned by this hook ─────────────────────────────────────
  const sequenceSegmentDwellRef = useRef<number | null>(null);
  const isDwellPauseRef = useRef(false);
  const sequenceOperationInProgressRef = useRef(false);
  const prevSequenceEnabledRef = useRef(sequenceEnabled);

  // ── findSequenceIndexForSentence ────────────────────────────────
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

  // ── Sequence sync effect ────────────────────────────────────────
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

  // ── syncSequenceIndexToTime ─────────────────────────────────────
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

  // ── getSequenceIndexForPlayback ─────────────────────────────────
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

  // ── applySequenceSegment ────────────────────────────────────────
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

  // ── advanceSequenceSegment ──────────────────────────────────────
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
      // Clear dwell timer when advancing
      sequenceSegmentDwellRef.current = null;
      applySequenceSegment(nextSegment, options);
      return true;
    },
    [applySequenceSegment, sequenceEnabled, sequencePlan],
  );

  // ── skipSequenceSentence ────────────────────────────────────────
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
      // Clear dwell timer when skipping to different sentence
      sequenceSegmentDwellRef.current = null;
      applySequenceSegment(targetSegment, { autoPlay: inlineAudioPlayingRef.current });
      return true;
    },
    [applySequenceSegment, resolvedCueVisibility, sequenceEnabled, sequencePlan],
  );

  // ── handleSequenceAwareTokenSeek ────────────────────────────────
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

  // ── maybeAdvanceSequence ────────────────────────────────────────
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
        // Not at segment end - clear any pending dwell
        sequenceSegmentDwellRef.current = null;
        isDwellPauseRef.current = false;
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

      // Use a dwell period to ensure the last word highlight is visible before advancing
      const now = performance.now();
      if (sequenceSegmentDwellRef.current === null) {
        // First time reaching segment end - pause audio and start the dwell timer
        // This prevents audio bleed from the next sentence
        const element = audioRef.current;
        if (element && !element.paused) {
          // Set flag before pausing to prevent handleInlineAudioPause from resetting state
          isDwellPauseRef.current = true;
          element.pause();
        }
        sequenceSegmentDwellRef.current = now;
        if (import.meta.env.DEV) {
          console.debug('[maybeAdvanceSequence] Starting dwell at segment end, paused audio', {
            mediaTime,
            segmentEnd: segment.end,
            currentIndex,
          });
        }
        return false;
      }

      // Check if we've dwelled long enough
      const dwellElapsed = now - sequenceSegmentDwellRef.current;
      if (dwellElapsed < SEQUENCE_SEGMENT_DWELL_MS) {
        // Still dwelling - don't advance yet
        return false;
      }

      // Dwell complete - advance to next segment
      sequenceSegmentDwellRef.current = null;
      isDwellPauseRef.current = false;
      if (import.meta.env.DEV) {
        console.debug('[maybeAdvanceSequence] Dwell complete, advancing', {
          mediaTime,
          segmentEnd: segment.end,
          dwellElapsed,
          currentIndex,
          segment,
        });
      }
      return advanceSequenceSegment({ autoPlay: true });
    },
    [advanceSequenceSegment, sequenceEnabled, sequencePlan],
  );

  // ── selectedTracks ──────────────────────────────────────────────
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

  // ── Debug info ──────────────────────────────────────────────────
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

  return {
    getSequenceIndexForPlayback,
    advanceSequenceSegment,
    syncSequenceIndexToTime,
    maybeAdvanceSequence,
    isDwellPauseRef,
    skipSequenceSentence,
    handleSequenceAwareTokenSeek,
    selectedTracks,
    sequenceDebugInfo,
    findSequenceIndexForSentence,
    applySequenceSegment,
    sequenceSegmentDwellRef,
    sequenceOperationInProgressRef,
  };
}
