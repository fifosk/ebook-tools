export interface VideoFile {
  id: string;
  url: string;
  name?: string;
  poster?: string;
}

export interface SubtitleTrack {
  url: string;
  label?: string;
  kind?: string;
  language?: string;
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
  playbackRate?: number | null;
  onPlaybackRateChange?: (rate: number) => void;
  isTheaterMode?: boolean;
  onExitTheaterMode?: (reason?: 'user' | 'lost') => void;
  onRegisterControls?: (
    controls:
      | {
          pause: () => void;
          play: () => void;
          ensureFullscreen?: () => void;
        }
      | null
  ) => void;
  subtitlesEnabled?: boolean;
  tracks?: SubtitleTrack[];
  cueVisibility?: {
    original: boolean;
    transliteration: boolean;
    translation: boolean;
  };
}

import { useCallback, useEffect, useRef } from 'react';

const DEFAULT_PLAYBACK_RATE = 1;

function sanitiseRate(value: number | null | undefined): number {
  if (!Number.isFinite(value) || !value) {
    return DEFAULT_PLAYBACK_RATE;
  }
  return Math.max(0.25, Math.min(4, value));
}

export default function VideoPlayer({
  files,
  activeId,
  onSelectFile,
  autoPlay = false,
  onPlaybackEnded,
  playbackPosition = null,
  onPlaybackPositionChange,
  onPlaybackStateChange,
  playbackRate = DEFAULT_PLAYBACK_RATE,
  onPlaybackRateChange,
  isTheaterMode = false,
  onExitTheaterMode,
  onRegisterControls,
  subtitlesEnabled = true,
  tracks = [],
  cueVisibility = { original: true, transliteration: true, translation: true },
}: VideoPlayerProps) {
  const elementRef = useRef<HTMLVideoElement | null>(null);
  const fullscreenRequestedRef = useRef(false);
  const labels = files.map((file, index) => ({
    id: file.id,
    label: file.name ?? `Video ${index + 1}`
  }));

  const activeFile = activeId ? files.find((file) => file.id === activeId) ?? null : null;

  const requestFullscreenPlayback = useCallback(() => {
    const element = elementRef.current;
    if (typeof document === 'undefined' || !element || !isTheaterMode) {
      return;
    }
    if (document.fullscreenElement === element) {
      return;
    }
    if (typeof element.requestFullscreen === 'function') {
      const result = element.requestFullscreen();
      if (result && typeof (result as Promise<unknown>).catch === 'function') {
        (result as Promise<unknown>).catch(() => {
          /* Ignore request rejections (e.g. lacking user gesture). */
        });
      }
      fullscreenRequestedRef.current = true;
    }
  }, [isTheaterMode]);

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
      ensureFullscreen: requestFullscreenPlayback,
    };
    onRegisterControls(controls);
    return () => {
      onRegisterControls(null);
    };
  }, [onRegisterControls, activeFile?.id, requestFullscreenPlayback]);

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

  useEffect(() => {
    const element = elementRef.current;
    if (!element) {
      return;
    }
    const safeRate = sanitiseRate(playbackRate);
    if (Math.abs(element.playbackRate - safeRate) < 1e-3) {
      return;
    }
    element.playbackRate = safeRate;
  }, [playbackRate, activeFile?.id]);

  useEffect(() => {
    const element = elementRef.current;
    if (!element || !onPlaybackRateChange) {
      return;
    }
    const handleRateChange = () => {
      onPlaybackRateChange(sanitiseRate(element.playbackRate));
    };
    element.addEventListener('ratechange', handleRateChange);
    return () => {
      element.removeEventListener('ratechange', handleRateChange);
    };
  }, [onPlaybackRateChange, activeFile?.id]);

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
        onExitTheaterMode?.('user');
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
      requestFullscreenPlayback();
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
  }, [isTheaterMode, activeFile?.id, requestFullscreenPlayback]);

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
        onExitTheaterMode?.('lost');
      }
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, [isTheaterMode, onExitTheaterMode]);

  useEffect(() => {
    const element = elementRef.current;
    if (!element || !element.textTracks) {
      return;
    }
    Array.from(element.textTracks).forEach((track, index) => {
      if (!subtitlesEnabled) {
        track.mode = 'disabled';
        return;
      }
      track.mode = index === 0 ? 'showing' : 'disabled';
    });
  }, [subtitlesEnabled, activeFile?.id, tracks]);

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
          onClick={() => onExitTheaterMode?.('user')}
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
              crossOrigin="use-credentials"
              src={activeFile.url}
              poster={activeFile.poster}
              autoPlay={autoPlay}
              playsInline
              data-cue-original={cueVisibility.original ? 'on' : 'off'}
              data-cue-transliteration={cueVisibility.transliteration ? 'on' : 'off'}
              data-cue-translation={cueVisibility.translation ? 'on' : 'off'}
              onPlay={handlePlay}
              onPause={handlePause}
              onEnded={handleEnded}
              onLoadedData={attemptAutoplay}
              onTimeUpdate={handleTimeUpdate}
            >
              {tracks.map((track, index) => (
                <track
                  key={`${track.url}-${index}`}
                  src={track.url}
                  kind={track.kind ?? 'subtitles'}
                  label={track.label}
                  srcLang={track.language || 'und'}
                  default={index === 0}
                />
              ))}
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
