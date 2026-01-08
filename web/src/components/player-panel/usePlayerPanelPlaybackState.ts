import { useCallback, useEffect, useRef, useState } from 'react';
import type { LiveMediaItem } from '../../hooks/useLiveMedia';
import type { MediaCategory } from './constants';
import type { PlaybackControls } from './types';

type RememberPosition = (args: {
  mediaId: string;
  mediaType: MediaCategory;
  baseId: string | null;
  position: number;
}) => void;

type UsePlayerPanelPlaybackStateArgs = {
  inlineAudioSelection: string | null;
  getMediaItem: (category: MediaCategory, id: string | null | undefined) => LiveMediaItem | null;
  deriveBaseId: (item: LiveMediaItem | null | undefined) => string | null;
  rememberPosition: RememberPosition;
  getPosition: (mediaId: string | null | undefined) => number;
  readingBedEnabled: boolean;
  playReadingBed: () => void;
};

type UsePlayerPanelPlaybackStateResult = {
  inlineAudioPlayingRef: React.MutableRefObject<boolean>;
  mediaSessionTimeRef: React.MutableRefObject<number | null>;
  isInlineAudioPlaying: boolean;
  hasInlineAudioControls: boolean;
  requestAutoPlay: () => void;
  handleInlineAudioPlaybackStateChange: (state: 'playing' | 'paused') => void;
  handleInlineAudioControlsRegistration: (controls: PlaybackControls | null) => void;
  handleInlineAudioProgress: (audioUrl: string, position: number) => void;
  getInlineAudioPosition: (audioUrl: string) => number;
  handlePauseActiveMedia: () => void;
  handlePlayActiveMedia: () => void;
  handleToggleActiveMedia: () => void;
};

export function usePlayerPanelPlaybackState({
  inlineAudioSelection,
  getMediaItem,
  deriveBaseId,
  rememberPosition,
  getPosition,
  readingBedEnabled,
  playReadingBed,
}: UsePlayerPanelPlaybackStateArgs): UsePlayerPanelPlaybackStateResult {
  const inlineAudioControlsRef = useRef<PlaybackControls | null>(null);
  const inlineAudioPlayingRef = useRef(false);
  const mediaSessionTimeRef = useRef<number | null>(null);
  const [isInlineAudioPlaying, setIsInlineAudioPlaying] = useState(false);
  const updateInlineAudioPlaying = useCallback((next: boolean) => {
    inlineAudioPlayingRef.current = next;
    setIsInlineAudioPlaying(next);
  }, []);
  const pendingAutoPlayRef = useRef(false);
  const [autoPlayToken, setAutoPlayToken] = useState(0);
  const requestAutoPlay = useCallback(() => {
    pendingAutoPlayRef.current = true;
    setAutoPlayToken((value) => value + 1);
  }, []);
  const [hasInlineAudioControls, setHasInlineAudioControls] = useState(false);

  const handleInlineAudioPlaybackStateChange = useCallback(
    (state: 'playing' | 'paused') => {
      updateInlineAudioPlaying(state === 'playing');
    },
    [updateInlineAudioPlaying],
  );

  const handleInlineAudioControlsRegistration = useCallback(
    (controls: PlaybackControls | null) => {
      inlineAudioControlsRef.current = controls;
      setHasInlineAudioControls(Boolean(controls));
      if (!controls) {
        updateInlineAudioPlaying(false);
      }
    },
    [updateInlineAudioPlaying],
  );

  const handlePauseActiveMedia = useCallback(() => {
    inlineAudioControlsRef.current?.pause();
    updateInlineAudioPlaying(false);
  }, [updateInlineAudioPlaying]);

  const handlePlayActiveMedia = useCallback(() => {
    if (readingBedEnabled) {
      playReadingBed();
    }
    inlineAudioControlsRef.current?.play();
    updateInlineAudioPlaying(true);
  }, [playReadingBed, readingBedEnabled, updateInlineAudioPlaying]);

  const handleToggleActiveMedia = useCallback(() => {
    if (isInlineAudioPlaying) {
      handlePauseActiveMedia();
    } else {
      handlePlayActiveMedia();
    }
  }, [handlePauseActiveMedia, handlePlayActiveMedia, isInlineAudioPlaying]);

  const handleInlineAudioProgress = useCallback(
    (audioUrl: string, position: number) => {
      if (!audioUrl) {
        return;
      }
      if (audioUrl === inlineAudioSelection) {
        mediaSessionTimeRef.current = position;
      }
      const current = getMediaItem('audio', audioUrl);
      const baseId = current ? deriveBaseId(current) : null;
      rememberPosition({ mediaId: audioUrl, mediaType: 'audio', baseId, position });
    },
    [deriveBaseId, getMediaItem, inlineAudioSelection, rememberPosition],
  );

  const getInlineAudioPosition = useCallback(
    (audioUrl: string) => getPosition(audioUrl),
    [getPosition],
  );

  useEffect(() => {
    if (!pendingAutoPlayRef.current) {
      return;
    }
    const controls = inlineAudioControlsRef.current;
    if (!controls) {
      return;
    }
    pendingAutoPlayRef.current = false;
    controls.pause();
    controls.play();
  }, [autoPlayToken, hasInlineAudioControls, inlineAudioSelection]);

  return {
    inlineAudioPlayingRef,
    mediaSessionTimeRef,
    isInlineAudioPlaying,
    hasInlineAudioControls,
    requestAutoPlay,
    handleInlineAudioPlaybackStateChange,
    handleInlineAudioControlsRegistration,
    handleInlineAudioProgress,
    getInlineAudioPosition,
    handlePauseActiveMedia,
    handlePlayActiveMedia,
    handleToggleActiveMedia,
  };
}
