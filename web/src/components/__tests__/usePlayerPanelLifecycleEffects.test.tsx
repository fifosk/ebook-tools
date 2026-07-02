import { renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { MediaSelectionRequest } from '../../types/player';
import { usePlayerPanelLifecycleEffects } from '../player-panel/usePlayerPanelLifecycleEffects';

type HookArgs = Parameters<typeof usePlayerPanelLifecycleEffects>[0];

function args(overrides: Partial<HookArgs> = {}): HookArgs {
  return {
    normalisedJobId: 'job-1',
    selectionRequest: null,
    isInlineAudioPlaying: false,
    isInteractiveFullscreen: false,
    onVideoPlaybackStateChange: vi.fn(),
    onPlaybackStateChange: vi.fn(),
    onFullscreenChange: vi.fn(),
    requestAutoPlay: vi.fn(),
    resetInteractiveFullscreen: vi.fn(),
    setPendingSelection: vi.fn(),
    setPendingChunkSelection: vi.fn(),
    setPendingTextScrollRatio: vi.fn(),
    ...overrides,
  };
}

describe('usePlayerPanelLifecycleEffects', () => {
  it('publishes playback and fullscreen state changes to shell callbacks', () => {
    const onVideoPlaybackStateChange = vi.fn();
    const onPlaybackStateChange = vi.fn();
    const onFullscreenChange = vi.fn();
    const initial = args({
      onVideoPlaybackStateChange,
      onPlaybackStateChange,
      onFullscreenChange,
    });
    const { rerender } = renderHook((props: HookArgs) => usePlayerPanelLifecycleEffects(props), {
      initialProps: initial,
    });

    expect(onVideoPlaybackStateChange).toHaveBeenCalledWith(false);
    expect(onPlaybackStateChange).toHaveBeenLastCalledWith(false);
    expect(onFullscreenChange).toHaveBeenLastCalledWith(false);

    rerender({
      ...initial,
      isInlineAudioPlaying: true,
      isInteractiveFullscreen: true,
    });

    expect(onPlaybackStateChange).toHaveBeenLastCalledWith(true);
    expect(onFullscreenChange).toHaveBeenLastCalledWith(true);
  });

  it('requests autoplay when a new autoplay selection token arrives', () => {
    const requestAutoPlay = vi.fn();
    const selectionRequest: MediaSelectionRequest = {
      baseId: 'chapter-1',
      autoPlay: true,
      token: 1,
    };
    const initial = args({
      requestAutoPlay,
      selectionRequest,
    });
    const { rerender } = renderHook((props: HookArgs) => usePlayerPanelLifecycleEffects(props), {
      initialProps: initial,
    });

    expect(requestAutoPlay).toHaveBeenCalledTimes(1);

    rerender({
      ...initial,
      selectionRequest: {
        ...selectionRequest,
        token: 2,
      },
    });

    expect(requestAutoPlay).toHaveBeenCalledTimes(2);

    rerender({
      ...initial,
      selectionRequest: {
        ...selectionRequest,
        autoPlay: false,
        token: 3,
      },
    });

    expect(requestAutoPlay).toHaveBeenCalledTimes(2);
  });

  it('clears pending reader state when the active job changes', () => {
    const resetInteractiveFullscreen = vi.fn();
    const setPendingSelection = vi.fn();
    const setPendingChunkSelection = vi.fn();
    const setPendingTextScrollRatio = vi.fn();
    const initial = args({
      resetInteractiveFullscreen,
      setPendingSelection,
      setPendingChunkSelection,
      setPendingTextScrollRatio,
    });
    const { rerender } = renderHook((props: HookArgs) => usePlayerPanelLifecycleEffects(props), {
      initialProps: initial,
    });

    expect(resetInteractiveFullscreen).toHaveBeenCalledTimes(1);
    expect(setPendingSelection).toHaveBeenLastCalledWith(null);
    expect(setPendingChunkSelection).toHaveBeenLastCalledWith(null);
    expect(setPendingTextScrollRatio).toHaveBeenLastCalledWith(null);

    rerender({
      ...initial,
      normalisedJobId: 'job-2',
    });

    expect(resetInteractiveFullscreen).toHaveBeenCalledTimes(2);
    expect(setPendingSelection).toHaveBeenCalledTimes(2);
    expect(setPendingChunkSelection).toHaveBeenCalledTimes(2);
    expect(setPendingTextScrollRatio).toHaveBeenCalledTimes(2);
  });
});
