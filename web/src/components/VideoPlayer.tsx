export interface VideoFile {
  id: string;
  url: string;
  name?: string;
  poster?: string;
}

interface VideoPlayerProps {
  files: VideoFile[];
  activeId: string | null;
  onSelectFile: (fileId: string) => void;
  autoPlay?: boolean;
  onPlaybackEnded?: () => void;
  playbackPosition?: number | null;
  onPlaybackPositionChange?: (position: number) => void;
}

import { useCallback, useEffect, useRef } from 'react';

export default function VideoPlayer({
  files,
  activeId,
  onSelectFile,
  autoPlay = false,
  onPlaybackEnded,
  playbackPosition = null,
  onPlaybackPositionChange,
}: VideoPlayerProps) {
  const elementRef = useRef<HTMLVideoElement | null>(null);
  const labels = files.map((file, index) => ({
    id: file.id,
    label: file.name ?? `Video ${index + 1}`
  }));

  const activeFile = activeId ? files.find((file) => file.id === activeId) ?? null : null;
  const shouldRestoreFullscreenRef = useRef(false);

  const getFullscreenElement = useCallback(() => {
    if (typeof document === 'undefined') {
      return null;
    }

    const standardElement = document.fullscreenElement;
    if (standardElement) {
      return standardElement;
    }

    const webkitElement = (document as unknown as { webkitFullscreenElement?: Element | null })
      .webkitFullscreenElement;
    if (webkitElement) {
      return webkitElement;
    }

    const mozElement = (document as unknown as { mozFullScreenElement?: Element | null }).mozFullScreenElement;
    if (mozElement) {
      return mozElement;
    }

    const msElement = (document as unknown as { msFullscreenElement?: Element | null }).msFullscreenElement;
    if (msElement) {
      return msElement;
    }

    return null;
  }, []);

  const markFullscreenRestoreIfNeeded = useCallback(() => {
    const element = elementRef.current;
    if (!element) {
      shouldRestoreFullscreenRef.current = false;
      return;
    }

    const fullscreenElement = getFullscreenElement();

    shouldRestoreFullscreenRef.current = fullscreenElement === element;
  }, [getFullscreenElement]);

  const restoreFullscreenIfNeeded = useCallback(() => {
    const element = elementRef.current;
    if (!element || !shouldRestoreFullscreenRef.current) {
      return;
    }

    shouldRestoreFullscreenRef.current = false;

    const requestFullscreen =
      element.requestFullscreen?.bind(element) ??
      (element as unknown as { webkitRequestFullscreen?: () => Promise<void> | void }).webkitRequestFullscreen?.bind(element) ??
      (element as unknown as { mozRequestFullScreen?: () => Promise<void> | void }).mozRequestFullScreen?.bind(element) ??
      (element as unknown as { msRequestFullscreen?: () => Promise<void> | void }).msRequestFullscreen?.bind(element);

    if (!requestFullscreen) {
      return;
    }

    try {
      const result = requestFullscreen();
      if (result && typeof (result as Promise<void>).then === 'function') {
        (result as Promise<void>).catch(() => {
          // Ignore fullscreen restoration rejections that stem from browser policies.
        });
      }
    } catch (error) {
      // Ignore fullscreen restoration failures triggered by browser restrictions.
    }
  }, []);

  const attemptAutoplay = useCallback(() => {
    if (!autoPlay) {
      return;
    }

    const element = elementRef.current;
    if (!element) {
      return;
    }

    try {
      const playResult = element.play();
      if (playResult && typeof playResult.then === 'function') {
        playResult.catch(() => {
          // Ignore autoplay rejections triggered by browser or test environments.
        });
      }
    } catch (error) {
      // Ignore autoplay errors that stem from user gesture requirements.
    }
  }, [autoPlay]);

  useEffect(() => {
    attemptAutoplay();
  }, [attemptAutoplay, activeFile?.id]);

  useEffect(() => {
    restoreFullscreenIfNeeded();
  }, [restoreFullscreenIfNeeded, activeFile?.id]);

  useEffect(() => {
    const element = elementRef.current;
    if (!element || playbackPosition === null || playbackPosition === undefined) {
      return;
    }

    const clamped = Number.isFinite(playbackPosition) ? Math.max(playbackPosition, 0) : 0;

    if (Math.abs(element.currentTime - clamped) < 0.25) {
      return;
    }

    try {
      element.currentTime = clamped;
    } catch (error) {
      // Ignore assignment failures that can happen in non-media test environments.
    }
  }, [playbackPosition, activeFile?.id]);

  const handleTimeUpdate = useCallback(() => {
    const element = elementRef.current;
    if (!element) {
      return;
    }

    onPlaybackPositionChange?.(element.currentTime ?? 0);
  }, [onPlaybackPositionChange]);

  const handleSelectPlaylistItem = useCallback(
    (fileId: string) => {
      markFullscreenRestoreIfNeeded();
      onSelectFile(fileId);
    },
    [markFullscreenRestoreIfNeeded, onSelectFile]
  );

  const handlePlaybackEnded = useCallback(() => {
    markFullscreenRestoreIfNeeded();
    onPlaybackEnded?.();
  }, [markFullscreenRestoreIfNeeded, onPlaybackEnded]);

  if (files.length === 0) {
    return (
      <div className="video-player" role="status">
        Waiting for video files…
      </div>
    );
  }

  if (!activeFile) {
    return (
      <div className="video-player" role="status">
        Preparing the latest video…
      </div>
    );
  }

  return (
    <div className="video-player">
      <video
        key={activeFile.id}
        ref={elementRef}
        className="video-player__element"
        data-testid="video-player"
        controls
        src={activeFile.url}
        poster={activeFile.poster}
        autoPlay={autoPlay}
        playsInline
        onEnded={handlePlaybackEnded}
        onLoadedData={attemptAutoplay}
        onTimeUpdate={handleTimeUpdate}
      >
        Your browser does not support the video element.
      </video>
      <div className="video-player__playlist" role="group" aria-label="Video playlist">
        {labels.map((file) => (
          <button
            key={file.id}
            type="button"
            className="video-player__item"
            aria-pressed={file.id === activeId}
            onClick={() => handleSelectPlaylistItem(file.id)}
          >
            {file.label}
          </button>
        ))}
      </div>
    </div>
  );
}
