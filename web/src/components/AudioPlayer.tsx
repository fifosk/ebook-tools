export interface AudioFile {
  id: string;
  url: string;
  name?: string;
}

interface AudioPlayerProps {
  files: AudioFile[];
  activeId: string | null;
  onSelectFile: (fileId: string) => void;
  autoPlay?: boolean;
  onPlaybackEnded?: () => void;
  playbackPosition?: number | null;
  onPlaybackPositionChange?: (position: number) => void;
  onRegisterControls?: (controls: { pause: () => void; play: () => void } | null) => void;
}

import { useCallback, useEffect, useRef } from 'react';

export default function AudioPlayer({
  files,
  activeId,
  onSelectFile,
  autoPlay = false,
  onPlaybackEnded,
  playbackPosition = null,
  onPlaybackPositionChange,
  onRegisterControls,
}: AudioPlayerProps) {
  const elementRef = useRef<HTMLAudioElement | null>(null);
  const labels = files.map((file, index) => ({
    id: file.id,
    label: file.name ?? `Track ${index + 1}`
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
          // Ignore failures triggered in environments without media support.
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
          // Ignore play failures triggered by autoplay restrictions.
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
          // Ignore autoplay rejections which can happen in tests or restricted environments.
        });
      }
    } catch (error) {
      // Swallow autoplay errors triggered by browser policies.
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
      // Setting currentTime may fail in certain mocked environments; ignore silently.
    }
  }, [playbackPosition, activeFile?.id]);

  const handleTimeUpdate = useCallback(() => {
    const element = elementRef.current;
    if (!element) {
      return;
    }

    onPlaybackPositionChange?.(element.currentTime ?? 0);
  }, [onPlaybackPositionChange]);

  if (files.length === 0) {
    return (
      <div className="audio-player" role="status">
        Waiting for audio files…
      </div>
    );
  }

  if (!activeFile) {
    return (
      <div className="audio-player" role="status">
        Preparing the latest audio track…
      </div>
    );
  }

  return (
    <div className="audio-player">
      <audio
        key={activeFile.id}
        ref={elementRef}
        className="audio-player__element"
        data-testid="audio-player"
        controls
        src={activeFile.url}
        autoPlay={autoPlay}
        onEnded={onPlaybackEnded}
        onLoadedData={attemptAutoplay}
        onTimeUpdate={handleTimeUpdate}
      >
        Your browser does not support the audio element.
      </audio>
      <div className="audio-player__playlist" role="group" aria-label="Audio tracks">
        {labels.map((file) => (
          <button
            key={file.id}
            type="button"
            className="audio-player__track"
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
