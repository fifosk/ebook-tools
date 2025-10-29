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
  onPlaybackStateChange?: (state: 'playing' | 'paused') => void;
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
  onPlaybackStateChange,
}: VideoPlayerProps) {
  const elementRef = useRef<HTMLVideoElement | null>(null);
  const labels = files.map((file, index) => ({
    id: file.id,
    label: file.name ?? `Video ${index + 1}`
  }));

  const activeFile = activeId ? files.find((file) => file.id === activeId) ?? null : null;

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

  const handlePlay = useCallback(() => {
    onPlaybackStateChange?.('playing');
  }, [onPlaybackStateChange]);

  const handlePause = useCallback(() => {
    onPlaybackStateChange?.('paused');
  }, [onPlaybackStateChange]);

  const handleEnded = useCallback(() => {
    onPlaybackStateChange?.('paused');
    onPlaybackEnded?.();
  }, [onPlaybackEnded, onPlaybackStateChange]);

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
        onPlay={handlePlay}
        onPause={handlePause}
        onEnded={handleEnded}
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
            onClick={() => onSelectFile(file.id)}
          >
            {file.label}
          </button>
        ))}
      </div>
    </div>
  );
}
