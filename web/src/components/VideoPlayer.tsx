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
  isTheaterMode?: boolean;
  onExitTheaterMode?: () => void;
  onRegisterControls?: (controls: { pause: () => void; play: () => void } | null) => void;
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
  isTheaterMode = false,
  onExitTheaterMode,
  onRegisterControls,
}: VideoPlayerProps) {
  const elementRef = useRef<HTMLVideoElement | null>(null);
  const fullscreenRequestedRef = useRef(false);
  const labels = files.map((file, index) => ({
    id: file.id,
    label: file.name ?? `Video ${index + 1}`
  }));

  const activeFile = activeId ? files.find((file) => file.id === activeId) ?? null : null;

  useEffect(() => {
    if (!onRegisterControls) {
      return;
    }
    const controls = {
      pause: () => {
        const element = elementRef.current;
        if (!element) {
          return;
        }
        try {
          element.pause();
        } catch (error) {
          // Ignore failures triggered by non-media environments.
        }
      },
      play: () => {
        const element = elementRef.current;
        if (!element) {
          return;
        }
        try {
          const playResult = element.play();
          if (playResult && typeof playResult.catch === 'function') {
            playResult.catch(() => undefined);
          }
        } catch (error) {
          // Swallow play failures caused by autoplay policies.
        }
      },
    };
    onRegisterControls(controls);
    return () => {
      onRegisterControls(null);
    };
  }, [onRegisterControls, activeFile?.id]);

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

  useEffect(() => {
    if (!isTheaterMode) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onExitTheaterMode?.();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isTheaterMode, onExitTheaterMode]);

  useEffect(() => {
    const element = elementRef.current;
    if (typeof document === 'undefined' || !element) {
      return;
    }

    const ensureFullscreen = () => {
      if (!isTheaterMode) {
        return;
      }
      if (document.fullscreenElement === element) {
        return;
      }
      if (typeof element.requestFullscreen === 'function') {
        const result = element.requestFullscreen();
        if (result && typeof (result as Promise<unknown>).catch === 'function') {
          (result as Promise<unknown>).catch(() => {
            /* Swallow fullscreen request rejections (e.g. user gesture requirements). */
          });
        }
        fullscreenRequestedRef.current = true;
      }
    };

    const releaseFullscreen = () => {
      if (typeof document.exitFullscreen === 'function') {
        const result = document.exitFullscreen();
        if (result && typeof (result as Promise<unknown>).catch === 'function') {
          (result as Promise<unknown>).catch(() => {
            /* Ignore exit failures in unsupported environments. */
          });
        }
      }
      fullscreenRequestedRef.current = false;
    };

    if (isTheaterMode) {
      ensureFullscreen();
    } else {
      if (document.fullscreenElement === element || fullscreenRequestedRef.current) {
        releaseFullscreen();
      } else {
        fullscreenRequestedRef.current = false;
      }
    }

    return () => {
      if (!isTheaterMode) {
        return;
      }
      if (
        typeof document !== 'undefined' &&
        (document.fullscreenElement === element || fullscreenRequestedRef.current)
      ) {
        releaseFullscreen();
      }
    };
  }, [isTheaterMode, activeFile?.id]);

  useEffect(() => {
    if (!isTheaterMode || typeof document === 'undefined') {
      return;
    }

    const handleFullscreenChange = () => {
      const element = elementRef.current;
      if (!element) {
        return;
      }
      if (document.fullscreenElement !== element) {
        fullscreenRequestedRef.current = false;
        onExitTheaterMode?.();
      }
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, [isTheaterMode, onExitTheaterMode]);

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
    <>
      {isTheaterMode ? (
        <button
          type="button"
          className="video-player__backdrop"
          aria-label="Exit immersive mode"
          onClick={onExitTheaterMode}
        />
      ) : null}
      <div className={['video-player', isTheaterMode ? 'video-player--enlarged' : null].filter(Boolean).join(' ')}>
        <div className="video-player__stage">
          <div className="video-player__canvas">
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
          </div>
        </div>
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
    </>
  );
}
