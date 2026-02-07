/**
 * Manages audio mode transitions — entering/exiting sequence mode, single-track switches.
 *
 * Extracted from useInteractiveAudioPlayback to reduce its size.
 * All refs are passed by identity from the parent; this hook owns only transition-related refs.
 */

import { useCallback, useEffect, useRef } from 'react';
import { timingStore } from '../../stores/timingStore';
import type { SequenceSegment, SequenceTrack } from './useInteractiveAudioSequence';

// ─── Types ──────────────────────────────────────────────────────────

export type UseAudioModeTransitionArgs = {
  // Trigger
  audioResetKey: string;
  effectiveAudioUrl: string | null;

  // Sequence state (from useInteractiveAudioSequence)
  sequenceEnabledRef: React.MutableRefObject<boolean>;
  sequencePlan: SequenceSegment[];
  sequenceDefaultTrack: SequenceTrack;
  sequenceTrackRef: React.MutableRefObject<SequenceTrack | null>;
  sequenceIndexRef: React.MutableRefObject<number>;
  pendingSequenceSeekRef: React.MutableRefObject<{
    time: number;
    autoPlay: boolean;
    targetSentenceIndex?: number;
  } | null>;
  setSequenceTrack: (track: SequenceTrack | null) => void;

  // Audio element
  audioRef: React.MutableRefObject<HTMLAudioElement | null>;
  inlineAudioPlayingRef: React.MutableRefObject<boolean>;

  // Track URLs
  originalTrackUrl: string | null;
  translationTrackUrl: string | null;

  // State setters
  activeSentenceIndexRef: React.MutableRefObject<number>;
  setActiveSentenceIndex: (value: number) => void;
  setChunkTime: React.Dispatch<React.SetStateAction<number>>;
  setAudioDuration: React.Dispatch<React.SetStateAction<number | null>>;

  // Manual seek tracking (for backward-movement guard in timelineDisplay effect)
  lastManualSeekTimeRef: React.MutableRefObject<number>;

  // Callbacks
  onAudioProgress?: (audioUrl: string, position: number) => void;
};

export type UseAudioModeTransitionResult = {
  pendingInitialSeekRef: React.MutableRefObject<number | null>;
  pendingSequenceExitSeekRef: React.MutableRefObject<{ sentenceIndex: number } | null>;
  emitAudioProgress: (position: number) => void;
};

// ─── Hook ───────────────────────────────────────────────────────────

export function useAudioModeTransition({
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
  lastManualSeekTimeRef,
  onAudioProgress,
}: UseAudioModeTransitionArgs): UseAudioModeTransitionResult {
  const pendingInitialSeekRef = useRef<number | null>(null);
  const lastReportedPositionRef = useRef(0);
  const prevAudioResetKeyRef = useRef<string | null>(null);
  const pendingSequenceExitSeekRef = useRef<{ sentenceIndex: number } | null>(null);

  // ── Audio mode transition effect ──────────────────────────────────

  useEffect(() => {
    const prevKey = prevAudioResetKeyRef.current;
    prevAudioResetKeyRef.current = audioResetKey;

    if (!effectiveAudioUrl) {
      // No audio URL - clear pending seeks but PRESERVE the sentence position
      // so that when audio is re-enabled, we can continue from where we were
      pendingInitialSeekRef.current = null;
      lastReportedPositionRef.current = 0;
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

      pendingInitialSeekRef.current = null;
      lastReportedPositionRef.current = 0;
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
        const newEffectiveUrl =
          targetSegment.track === 'original' ? originalTrackUrl : translationTrackUrl;
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
                    console.debug(
                      '[audioResetKey] Clearing pendingSequenceSeekRef after same-URL seek',
                      {
                        targetSeekTime,
                        currentTime: element.currentTime,
                      },
                    );
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
      const sequenceTrackUrl =
        sequenceTrackRef.current === 'original' ? originalTrackUrl : translationTrackUrl;
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

      pendingInitialSeekRef.current = null;
      lastReportedPositionRef.current = 0;

      // Determine which single track will be active after exiting sequence mode.
      // When original is toggled OFF, translation stays; when translation is toggled OFF, original stays.
      const destinationTrack: SequenceTrack = effectiveAudioUrl === translationTrackUrl ? 'translation' : 'original';
      // Find the segment for the target sentence on the destination track (from sequence plan).
      // The segment's start time is in the destination track's native audio space.
      const exitSegment = sequencePlan.find(
        (seg) => seg.sentenceIndex === targetSentence && seg.track === destinationTrack,
      ) ?? sequencePlan.find(
        (seg) => seg.sentenceIndex === targetSentence,
      );

      if (urlWillChange) {
        // URL will change, so handleLoadedMetadata will fire.
        // Use pendingSequenceSeekRef (not Exit) so the existing seek logic in
        // handleLoadedMetadata handles it — this avoids the stale-closure issue
        // with timelineSentences.
        if (exitSegment) {
          pendingSequenceSeekRef.current = {
            time: exitSegment.start,
            autoPlay: inlineAudioPlayingRef.current,
            targetSentenceIndex: targetSentence,
          };
          // Begin transition to guard timelineDisplay effect
          timingStore.beginTransition({
            type: 'transitioning',
            targetSentenceIndex: targetSentence,
            targetTime: exitSegment.start,
          });
        } else {
          pendingSequenceExitSeekRef.current = { sentenceIndex: targetSentence };
        }
      } else {
        // URL won't change — handleLoadedMetadata won't fire.
        // Seek the audio element directly to the sentence start using the
        // sequence plan (which has segment times in the track's audio space).
        pendingSequenceExitSeekRef.current = { sentenceIndex: targetSentence };

        const element = audioRef.current;
        // Find the segment for the target sentence on the destination track.
        // Use destinationTrack (computed from effectiveAudioUrl) rather than
        // sequenceTrackRef which may point to the track that was toggled OFF.
        const targetSegment = exitSegment;

        if (element && targetSegment && Number.isFinite(element.duration) && element.duration > 0) {
          const wasPlaying = !element.paused;
          // Seek to the sentence start time (in audio space, from sequence plan)
          const seekTime = Math.max(0, Math.min(targetSegment.start, element.duration - 0.1));
          element.currentTime = seekTime;
          setChunkTime(seekTime);
          setActiveSentenceIndex(targetSentence);
          lastManualSeekTimeRef.current = Date.now();

          if (import.meta.env.DEV) {
            console.debug('[audioResetKey] Sequence exit seek (URL unchanged)', {
              targetSentence,
              seekTime,
              destinationTrack,
              wasPlaying,
            });
          }

          // Guard against timelineDisplay overriding during transition
          setTimeout(() => {
            if (pendingSequenceExitSeekRef.current?.sentenceIndex !== targetSentence) return;
            if (import.meta.env.DEV) {
              console.debug(
                '[audioResetKey] Clearing pendingSequenceExitSeekRef after timeout (URL unchanged)',
              );
            }
            pendingSequenceExitSeekRef.current = null;
            // Refresh manual seek time so the backward-movement guard extends
            lastManualSeekTimeRef.current = Date.now();
          }, 300);

          if (wasPlaying) {
            const maybePlay = element.play?.();
            if (maybePlay && typeof maybePlay.catch === 'function') {
              maybePlay.catch(() => undefined);
            }
          }
        } else {
          // No element or no segment — just clear after brief delay
          if (import.meta.env.DEV) {
            console.debug('[audioResetKey] No element/segment for sequence exit seek', {
              hasElement: Boolean(element),
              targetSegment,
              targetSentence,
            });
          }
          setTimeout(() => {
            if (pendingSequenceExitSeekRef.current?.sentenceIndex === targetSentence) {
              pendingSequenceExitSeekRef.current = null;
            }
          }, 100);
        }
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
      pendingInitialSeekRef.current = null;
      lastReportedPositionRef.current = 0;
      // Don't reset activeSentenceIndex or chunkTime - managed by applySequenceSegment
      setAudioDuration(null);
      return;
    }

    // Check if we're switching between single-track modes (e.g., translation-only → original-only)
    // In this case, we want to preserve position and seek to the corresponding time
    // This happens when neither the old nor new key is in sequence mode
    // Only fire when the user has progressed past sentence 0 — otherwise this is a
    // normal chunk advance and the default reset-to-0 path below handles it correctly.
    const targetSentence = activeSentenceIndexRef.current;
    const isSwitchingSingleTracks =
      prevKey && !wasSequenceMode && !isSequenceMode && prevKey !== audioResetKey && targetSentence > 0;
    if (isSwitchingSingleTracks) {
      if (import.meta.env.DEV) {
        console.debug('[audioResetKey] Switching single tracks, preserving position', {
          prevKey,
          newKey: audioResetKey,
          targetSentence,
        });
      }
      pendingInitialSeekRef.current = null;
      lastReportedPositionRef.current = 0;
      // Set up a pending seek - handleLoadedMetadata will seek to the correct position
      // for this sentence in the new track's timeline
      pendingSequenceExitSeekRef.current = { sentenceIndex: targetSentence };
      setAudioDuration(null);
      return;
    }

    pendingInitialSeekRef.current = null;
    lastReportedPositionRef.current = 0;
    pendingSequenceExitSeekRef.current = null;
    setActiveSentenceIndex(0);
    setAudioDuration(null);
    setChunkTime(0);
  }, [
    audioResetKey,
    effectiveAudioUrl,
    originalTrackUrl,
    sequenceDefaultTrack,
    sequencePlan,
    setActiveSentenceIndex,
    setChunkTime,
    setSequenceTrack,
    translationTrackUrl,
  ]);

  // ── Audio progress emission ───────────────────────────────────────

  const emitAudioProgress = useCallback(
    (position: number) => {
      if (!effectiveAudioUrl || !onAudioProgress) {
        return;
      }
      if (Math.abs(position - lastReportedPositionRef.current) < 0.25) {
        return;
      }
      lastReportedPositionRef.current = position;
      onAudioProgress(effectiveAudioUrl, position);
    },
    [effectiveAudioUrl, onAudioProgress],
  );

  return {
    pendingInitialSeekRef,
    pendingSequenceExitSeekRef,
    emitAudioProgress,
  };
}
