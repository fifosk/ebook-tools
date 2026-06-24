import { useCallback, useRef, useState } from 'react';
import type { MutableRefObject } from 'react';
import type { NavigationIntent } from './constants';

type UsePlayerPanelMediaNavigationArgs = {
  activeSentenceNumber: number | null;
  canJumpToSentence: boolean;
  jobStartSentence: number | null;
  jobEndSentence: number | null;
  mediaSessionTimeRef: MutableRefObject<number | null>;
  onInteractiveSentenceJump: (sentenceNumber: number) => void;
  onNavigatePreservingPlayback: (intent: NavigationIntent) => void;
};

type SequenceSkipHandler = (direction: 1 | -1) => boolean;

export function usePlayerPanelMediaNavigation({
  activeSentenceNumber,
  canJumpToSentence,
  jobStartSentence,
  jobEndSentence,
  mediaSessionTimeRef,
  onInteractiveSentenceJump,
  onNavigatePreservingPlayback,
}: UsePlayerPanelMediaNavigationArgs) {
  const sequenceSkipFnRef = useRef<SequenceSkipHandler | null>(null);
  const [hasRegisteredSequenceSkip, setHasRegisteredSequenceSkip] = useState(false);

  const handleRegisterSequenceSkip = useCallback((fn: SequenceSkipHandler | null) => {
    if (import.meta.env.DEV) {
      console.debug('[PlayerPanel] handleRegisterSequenceSkip called, fn is:', fn ? 'function' : 'null');
    }
    sequenceSkipFnRef.current = fn;
    setHasRegisteredSequenceSkip(Boolean(fn));
  }, []);

  const handleMediaSessionSentenceSkip = useCallback(
    (direction: -1 | 1) => {
      const sequenceSkipFn = sequenceSkipFnRef.current;
      if (import.meta.env.DEV) {
        console.debug(
          '[PlayerPanel] handleMediaSessionSentenceSkip called, direction:',
          direction,
          'sequenceSkipFn:',
          sequenceSkipFn ? 'set' : 'null'
        );
      }
      if (sequenceSkipFn) {
        const result = sequenceSkipFn(direction);
        if (import.meta.env.DEV) {
          console.debug('[PlayerPanel] sequenceSkipFn returned:', result);
        }
        if (result) {
          return true;
        }
      }
      if (!canJumpToSentence) {
        if (import.meta.env.DEV) {
          console.debug('[PlayerPanel] canJumpToSentence is false, returning false');
        }
        return false;
      }
      const fallback = direction > 0 ? jobStartSentence : null;
      const current = activeSentenceNumber ?? fallback;
      if (!current || !Number.isFinite(current)) {
        if (import.meta.env.DEV) {
          console.debug('[PlayerPanel] activeSentenceNumber invalid, returning false');
        }
        return false;
      }
      const target = Math.trunc(current) + direction;
      if (jobStartSentence !== null && target < jobStartSentence) {
        return false;
      }
      if (jobEndSentence !== null && target > jobEndSentence) {
        return false;
      }
      if (import.meta.env.DEV) {
        console.debug('[PlayerPanel] Jumping to sentence:', target);
      }
      onInteractiveSentenceJump(target);
      return true;
    },
    [
      activeSentenceNumber,
      canJumpToSentence,
      jobEndSentence,
      jobStartSentence,
      onInteractiveSentenceJump,
    ],
  );

  const handleMediaSessionTrackSkip = useCallback(
    (direction: -1 | 1) => {
      if (handleMediaSessionSentenceSkip(direction)) {
        return;
      }
      onNavigatePreservingPlayback(direction > 0 ? 'next' : 'previous');
    },
    [handleMediaSessionSentenceSkip, onNavigatePreservingPlayback],
  );

  const handleKeyboardNavigate = useCallback(
    (intent: NavigationIntent) => {
      if (intent === 'next' || intent === 'previous') {
        const direction = intent === 'next' ? 1 : -1;
        if (handleMediaSessionSentenceSkip(direction)) {
          return;
        }
      }
      onNavigatePreservingPlayback(intent);
    },
    [handleMediaSessionSentenceSkip, onNavigatePreservingPlayback],
  );

  const handleMediaSessionSeekTo = useCallback(
    (details: MediaSessionActionDetails) => {
      const seekTime =
        typeof details.seekTime === 'number' && Number.isFinite(details.seekTime)
          ? details.seekTime
          : null;
      const current = mediaSessionTimeRef.current;
      if (seekTime === null || current === null || !Number.isFinite(current)) {
        return;
      }
      if (Math.abs(seekTime - current) < 0.25) {
        return;
      }
      handleMediaSessionTrackSkip(seekTime > current ? 1 : -1);
    },
    [handleMediaSessionTrackSkip, mediaSessionTimeRef],
  );

  return {
    hasSentenceNav: canJumpToSentence || hasRegisteredSequenceSkip,
    handleRegisterSequenceSkip,
    handleKeyboardNavigate,
    handleMediaSessionTrackSkip,
    handleMediaSessionSeekTo,
  };
}
