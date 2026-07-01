import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { usePlayerPanelMediaNavigation } from '../player-panel/usePlayerPanelMediaNavigation';

type HookArgs = Parameters<typeof usePlayerPanelMediaNavigation>[0];

function renderMediaNavigation(overrides: Partial<HookArgs> = {}) {
  const mediaSessionTimeRef: HookArgs['mediaSessionTimeRef'] = { current: 10 };
  const onInteractiveSentenceJump = vi.fn();
  const onNavigatePreservingPlayback = vi.fn();
  const hook = renderHook((props: HookArgs) => usePlayerPanelMediaNavigation(props), {
    initialProps: {
      activeSentenceNumber: 5,
      canJumpToSentence: true,
      jobStartSentence: 1,
      jobEndSentence: 8,
      mediaSessionTimeRef,
      onInteractiveSentenceJump,
      onNavigatePreservingPlayback,
      ...overrides,
    },
  });

  return {
    ...hook,
    mediaSessionTimeRef,
    onInteractiveSentenceJump,
    onNavigatePreservingPlayback,
  };
}

describe('usePlayerPanelMediaNavigation', () => {
  it('keeps navigation debug output silent by default', () => {
    const debugSpy = vi.spyOn(console, 'debug').mockImplementation(() => undefined);
    const sequenceSkip = vi.fn(() => true);
    const { result } = renderMediaNavigation();

    try {
      act(() => {
        result.current.handleRegisterSequenceSkip(sequenceSkip);
        result.current.handleKeyboardNavigate('next');
        result.current.handleRegisterSequenceSkip(null);
        result.current.handleKeyboardNavigate('previous');
        result.current.handleMediaSessionSeekTo({ seekTime: 14 } as MediaSessionActionDetails);
      });

      expect(debugSpy).not.toHaveBeenCalled();
    } finally {
      debugSpy.mockRestore();
    }
  });

  it('prefers a registered sequence skip handler for keyboard next and previous', () => {
    const sequenceSkip = vi.fn(() => true);
    const { result, onInteractiveSentenceJump, onNavigatePreservingPlayback } = renderMediaNavigation({
      canJumpToSentence: false,
    });

    expect(result.current.hasSentenceNav).toBe(false);

    act(() => {
      result.current.handleRegisterSequenceSkip(sequenceSkip);
    });

    expect(result.current.hasSentenceNav).toBe(true);

    act(() => {
      result.current.handleKeyboardNavigate('next');
      result.current.handleKeyboardNavigate('previous');
    });

    expect(sequenceSkip).toHaveBeenNthCalledWith(1, 1);
    expect(sequenceSkip).toHaveBeenNthCalledWith(2, -1);
    expect(onInteractiveSentenceJump).not.toHaveBeenCalled();
    expect(onNavigatePreservingPlayback).not.toHaveBeenCalled();
  });

  it('falls back to sentence jumps and respects job sentence boundaries', () => {
    const { result, rerender, onInteractiveSentenceJump, onNavigatePreservingPlayback } = renderMediaNavigation();

    act(() => {
      result.current.handleKeyboardNavigate('next');
    });

    expect(onInteractiveSentenceJump).toHaveBeenCalledWith(6);
    expect(onNavigatePreservingPlayback).not.toHaveBeenCalled();

    rerender({
      activeSentenceNumber: 8,
      canJumpToSentence: true,
      jobStartSentence: 1,
      jobEndSentence: 8,
      mediaSessionTimeRef: { current: 10 },
      onInteractiveSentenceJump,
      onNavigatePreservingPlayback,
    });

    act(() => {
      result.current.handleKeyboardNavigate('next');
    });

    expect(onInteractiveSentenceJump).toHaveBeenCalledTimes(1);
    expect(onNavigatePreservingPlayback).toHaveBeenCalledWith('next');
  });

  it('uses chunk navigation when sentence navigation is unavailable', () => {
    const { result, onInteractiveSentenceJump, onNavigatePreservingPlayback } = renderMediaNavigation({
      canJumpToSentence: false,
    });

    act(() => {
      result.current.handleKeyboardNavigate('first');
      result.current.handleKeyboardNavigate('next');
    });

    expect(onInteractiveSentenceJump).not.toHaveBeenCalled();
    expect(onNavigatePreservingPlayback).toHaveBeenNthCalledWith(1, 'first');
    expect(onNavigatePreservingPlayback).toHaveBeenNthCalledWith(2, 'next');
  });

  it('maps media-session seek targets to track skip directions', () => {
    const { result, onInteractiveSentenceJump, onNavigatePreservingPlayback } = renderMediaNavigation();

    act(() => {
      result.current.handleMediaSessionSeekTo({ seekTime: 10.1 } as MediaSessionActionDetails);
      result.current.handleMediaSessionSeekTo({ seekTime: 13 } as MediaSessionActionDetails);
      result.current.handleMediaSessionSeekTo({ seekTime: 7 } as MediaSessionActionDetails);
    });

    expect(onInteractiveSentenceJump).toHaveBeenNthCalledWith(1, 6);
    expect(onInteractiveSentenceJump).toHaveBeenNthCalledWith(2, 4);
    expect(onNavigatePreservingPlayback).not.toHaveBeenCalled();
  });
});
