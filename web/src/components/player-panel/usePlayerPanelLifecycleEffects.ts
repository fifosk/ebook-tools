import { useEffect, type Dispatch, type SetStateAction } from 'react';
import type { MediaSelectionRequest } from '../../types/player';
import type { PendingChunkSelection } from './usePlayerPanelSelectionState';

type UsePlayerPanelLifecycleEffectsArgs = {
  normalisedJobId: string;
  selectionRequest: MediaSelectionRequest | null;
  isInlineAudioPlaying: boolean;
  isInteractiveFullscreen: boolean;
  onVideoPlaybackStateChange?: (isPlaying: boolean) => void;
  onPlaybackStateChange?: (isPlaying: boolean) => void;
  onFullscreenChange?: (isFullscreen: boolean) => void;
  requestAutoPlay: () => void;
  resetInteractiveFullscreen: () => void;
  setPendingSelection: Dispatch<SetStateAction<MediaSelectionRequest | null>>;
  setPendingChunkSelection: Dispatch<SetStateAction<PendingChunkSelection | null>>;
  setPendingTextScrollRatio: Dispatch<SetStateAction<number | null>>;
};

export function usePlayerPanelLifecycleEffects({
  normalisedJobId,
  selectionRequest,
  isInlineAudioPlaying,
  isInteractiveFullscreen,
  onVideoPlaybackStateChange,
  onPlaybackStateChange,
  onFullscreenChange,
  requestAutoPlay,
  resetInteractiveFullscreen,
  setPendingSelection,
  setPendingChunkSelection,
  setPendingTextScrollRatio,
}: UsePlayerPanelLifecycleEffectsArgs) {
  useEffect(() => {
    onVideoPlaybackStateChange?.(false);
  }, [onVideoPlaybackStateChange]);

  useEffect(() => {
    onPlaybackStateChange?.(isInlineAudioPlaying);
  }, [isInlineAudioPlaying, onPlaybackStateChange]);

  useEffect(() => {
    if (!selectionRequest?.autoPlay) {
      return;
    }
    requestAutoPlay();
  }, [requestAutoPlay, selectionRequest?.autoPlay, selectionRequest?.token]);

  useEffect(() => {
    resetInteractiveFullscreen();
    setPendingSelection(null);
    setPendingChunkSelection(null);
    setPendingTextScrollRatio(null);
  }, [
    normalisedJobId,
    resetInteractiveFullscreen,
    setPendingChunkSelection,
    setPendingSelection,
    setPendingTextScrollRatio,
  ]);

  useEffect(() => {
    onFullscreenChange?.(isInteractiveFullscreen);
  }, [isInteractiveFullscreen, onFullscreenChange]);
}
