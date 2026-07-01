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

const PLAYER_PANEL_NAV_DEBUG_STORAGE_KEY = 'ebookTools.playerPanelNavigationDebug';

function isPlayerPanelNavigationDebugEnabled(): boolean {
  if (!import.meta.env.DEV || typeof window === 'undefined') {
    return false;
  }
  try {
    return window.localStorage.getItem(PLAYER_PANEL_NAV_DEBUG_STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

function debugPlayerPanelNavigation(...args: unknown[]) {
  if (isPlayerPanelNavigationDebugEnabled()) {
    console.debug(...args);
  }
}

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
    debugPlayerPanelNavigation(
      '[PlayerPanel] handleRegisterSequenceSkip called, fn is:',
      fn ? 'function' : 'null',
    );
    sequenceSkipFnRef.current = fn;
    setHasRegisteredSequenceSkip(Boolean(fn));
  }, []);

  const handleMediaSessionSentenceSkip = useCallback(
    (direction: -1 | 1) => {
      const sequenceSkipFn = sequenceSkipFnRef.current;
      debugPlayerPanelNavigation(
        '[PlayerPanel] handleMediaSessionSentenceSkip called, direction:',
        direction,
        'sequenceSkipFn:',
        sequenceSkipFn ? 'set' : 'null',
      );
      if (sequenceSkipFn) {
        const result = sequenceSkipFn(direction);
        debugPlayerPanelNavigation('[PlayerPanel] sequenceSkipFn returned:', result);
        if (result) {
          return true;
        }
      }
      if (!canJumpToSentence) {
        debugPlayerPanelNavigation('[PlayerPanel] canJumpToSentence is false, returning false');
        return false;
      }
      const fallback = direction > 0 ? jobStartSentence : null;
      const current = activeSentenceNumber ?? fallback;
      if (!current || !Number.isFinite(current)) {
        debugPlayerPanelNavigation('[PlayerPanel] activeSentenceNumber invalid, returning false');
        return false;
      }
      const target = Math.trunc(current) + direction;
      if (jobStartSentence !== null && target < jobStartSentence) {
        return false;
      }
      if (jobEndSentence !== null && target > jobEndSentence) {
        return false;
      }
      debugPlayerPanelNavigation('[PlayerPanel] Jumping to sentence:', target);
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
