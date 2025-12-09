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
  subtitleScale?: number;
}

import { useCallback, useEffect, useRef } from 'react';
import type { CSSProperties } from 'react';

const DEFAULT_PLAYBACK_RATE = 1;

function sanitiseRate(value: number | null | undefined): number {
  if (!Number.isFinite(value) || !value) {
    return DEFAULT_PLAYBACK_RATE;
  }
  return Math.max(0.25, Math.min(4, value));
}

function filterCueTextByVisibility(
  rawText: string,
  visibility: { original: boolean; transliteration: boolean; translation: boolean }
): string {
  if (!rawText) {
    return rawText;
  }
  const lines = rawText.split(/\r?\n/);
  const filtered: string[] = [];

  for (const line of lines) {
    const classMatch = line.match(/<c\.([^>]+)>/i);
    if (classMatch) {
      const classes = classMatch[1]
        .split(/\s+/)
        .map((value) => value.trim())
        .filter(Boolean);
      if (classes.some((value) => value === 'original') && !visibility.original) {
        continue;
      }
      if (classes.some((value) => value === 'transliteration') && !visibility.transliteration) {
        continue;
      }
      if (classes.some((value) => value === 'translation') && !visibility.translation) {
        continue;
      }
    }
    filtered.push(line);
  }

  if (filtered.length === lines.length) {
    return rawText;
  }
  return filtered.join('\n');
}

function extractMediaName(file: VideoFile, fallbackLabel?: string): string {
  const raw = file.name || file.url || fallbackLabel || "";
  if (!raw) {
    return "";
  }
  const withoutQuery = raw.split(/[?#]/)[0];
  const afterSlash = withoutQuery.replace(/\\/g, "/");
  const leaf = afterSlash.substring(afterSlash.lastIndexOf("/") + 1) || afterSlash;
  const trimmedLeaf = leaf.endsWith("/") ? leaf.slice(0, -1) : leaf;
  const dotIndex = trimmedLeaf.lastIndexOf(".");
  if (dotIndex > 0) {
    return trimmedLeaf.slice(0, dotIndex) || trimmedLeaf;
  }
  return trimmedLeaf || raw;
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
  subtitleScale = 1,
}: VideoPlayerProps) {
  const elementRef = useRef<HTMLVideoElement | null>(null);
  const fullscreenRef = useRef<HTMLDivElement | null>(null);
  const fullscreenRequestedRef = useRef(false);
  const cueTextCacheRef = useRef<WeakMap<TextTrackCue, string>>(new WeakMap());
  const labels = files.map((file, index) => ({
    id: file.id,
    label: file.name ?? `Video ${index + 1}`
  }));

  const activeFile = activeId ? files.find((file) => file.id === activeId) ?? null : null;
  const activeIndex = activeFile ? labels.findIndex((file) => file.id === activeFile.id) : -1;
  const fallbackLabel = activeIndex >= 0 ? labels[activeIndex]?.label : undefined;
  const displayName = activeFile ? extractMediaName(activeFile, fallbackLabel) : '';
  const labelText =
    displayName && activeIndex >= 0
      ? `Now playing \u2022 ${displayName} (Video ${activeIndex + 1} of ${labels.length})`
      : displayName
        ? `Now playing \u2022 ${displayName}`
        : activeIndex >= 0
          ? `Now playing \u2022 Video ${activeIndex + 1} of ${labels.length}`
          : 'Now playing';

  const getFullscreenTarget = useCallback(() => fullscreenRef.current ?? elementRef.current, []);

  const requestFullscreenPlayback = useCallback(() => {
    const target = getFullscreenTarget();
    if (typeof document === 'undefined' || !target || !isTheaterMode) {
      return;
    }
    if (document.fullscreenElement === target) {
      return;
    }
    if (typeof target.requestFullscreen === 'function') {
      const result = target.requestFullscreen();
      if (result && typeof (result as Promise<unknown>).catch === 'function') {
        (result as Promise<unknown>).catch(() => {
          /* Ignore request rejections (e.g. lacking user gesture). */
        });
      }
      fullscreenRequestedRef.current = true;
    }
  }, [getFullscreenTarget, isTheaterMode]);

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
        fullscreenRequestedRef.current = false;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isTheaterMode, onExitTheaterMode]);

  useEffect(() => {
    const element = elementRef.current;
    const target = getFullscreenTarget();
    if (typeof document === 'undefined' || !target) {
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
      if (document.fullscreenElement === target || fullscreenRequestedRef.current) {
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
        (document.fullscreenElement === target || fullscreenRequestedRef.current)
      ) {
        releaseFullscreen();
      }
    };
  }, [getFullscreenTarget, isTheaterMode, activeFile?.id, requestFullscreenPlayback]);

  useEffect(() => {
    const target = getFullscreenTarget();
    if (!isTheaterMode || typeof document === 'undefined' || !target) {
      return;
    }

    const handleFullscreenChange = () => {
      if (document.fullscreenElement === target) {
        fullscreenRequestedRef.current = true;
        return;
      }
      // If we expected fullscreen but lost it (e.g. source change), try to re-request.
      if (isTheaterMode && fullscreenRequestedRef.current) {
        requestFullscreenPlayback();
        return;
      }
      fullscreenRequestedRef.current = false;
      onExitTheaterMode?.('lost');
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, [getFullscreenTarget, isTheaterMode, onExitTheaterMode, requestFullscreenPlayback]);

  useEffect(() => {
    const element = elementRef.current;
    if (!element || !isTheaterMode) {
      return;
    }
    const handleLoadedData = () => {
      requestFullscreenPlayback();
    };
    element.addEventListener('loadeddata', handleLoadedData);
    return () => {
      element.removeEventListener('loadeddata', handleLoadedData);
    };
  }, [isTheaterMode, activeFile?.id, requestFullscreenPlayback]);

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

  useEffect(() => {
    if (!subtitlesEnabled) {
      return;
    }
    const element = elementRef.current;
    if (!element || !element.textTracks) {
      return;
    }
    const track =
      Array.from(element.textTracks).find((item) => item.mode === 'showing' || item.mode === 'hidden') ??
      element.textTracks[0] ??
      null;
    if (!track) {
      return;
    }

    const cache = cueTextCacheRef.current;

    const applyCueVisibility = () => {
      const cues = track.cues;
      if (!cues) {
        return;
      }
      for (let index = 0; index < cues.length; index += 1) {
        const cue = cues[index];
        const cueWithText = cue as VTTCue & { text?: string };
        const baseText = cache.get(cue) ?? cueWithText.text ?? '';
        if (!cache.has(cue)) {
          cache.set(cue, baseText);
        }
        const filteredText = filterCueTextByVisibility(baseText, cueVisibility);
        if (cueWithText.text !== filteredText && typeof cueWithText.text === 'string') {
          cueWithText.text = filteredText;
        }
      }
    };

    applyCueVisibility();
    track.addEventListener('cuechange', applyCueVisibility);
    return () => {
      track.removeEventListener('cuechange', applyCueVisibility);
    };
  }, [cueVisibility, subtitlesEnabled, activeFile?.id, tracks]);

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
        <div className="video-player__stage" ref={fullscreenRef}>
          <div
            className="video-player__active-label"
            title={activeFile.name ?? activeFile.url ?? 'Active video'}
            data-testid="video-player-active-label"
          >
            {labelText}
          </div>
          <div className="video-player__canvas">
            <video
              ref={elementRef}
              className="video-player__element"
              style={{ '--subtitle-scale': subtitleScale } as CSSProperties}
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
