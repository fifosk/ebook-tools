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
  onPlaybackStateChange?: (state: 'playing' | 'paused') => void;
}

import { useCallback, useEffect, useId, useMemo, useRef } from 'react';
import PlayerCore from '../player/PlayerCore';
import { usePlayerCore } from '../hooks/usePlayerCore';
import { formatMediaDropdownLabel } from '../utils/mediaLabels';
import { appendAccessTokenToStorageUrl, getAuthToken } from '../api/client';

export default function AudioPlayer({
  files,
  activeId,
  onSelectFile,
  autoPlay = false,
  onPlaybackEnded,
  playbackPosition = null,
  onPlaybackPositionChange,
  onRegisterControls,
  onPlaybackStateChange,
}: AudioPlayerProps) {
  const { ref: attachCore, core } = usePlayerCore();
  const lastReportedTime = useRef<number | null>(null);
  const playlistSelectId = useId();
  const authToken = getAuthToken();
  const resolvedFiles = useMemo(
    () =>
      files.map((file) => ({
        ...file,
        url: appendAccessTokenToStorageUrl(file.url),
      })),
    [files, authToken],
  );
  const labels = resolvedFiles.map((file, index) => ({
    id: file.id,
    label: formatMediaDropdownLabel(file.name ?? file.url, `Track ${index + 1}`),
  }));

  const activeFile = activeId ? resolvedFiles.find((file) => file.id === activeId) ?? null : null;

  useEffect(() => {
    if (!onRegisterControls) {
      return;
    }
    if (!core) {
      onRegisterControls(null);
      return;
    }
    const controls = {
      pause: () => {
        core.pause();
        onPlaybackStateChange?.('paused');
      },
      play: () => {
        try {
          const result = core.play();
          onPlaybackStateChange?.('playing');
          if (result && typeof result.catch === 'function') {
            result.catch(() => {
              onPlaybackStateChange?.('paused');
            });
          }
        } catch {
          onPlaybackStateChange?.('paused');
        }
      },
    };
    onRegisterControls(controls);
    return () => {
      onRegisterControls(null);
    };
  }, [core, onPlaybackStateChange, onRegisterControls]);

  useEffect(() => {
    onPlaybackStateChange?.('paused');
  }, [activeFile?.id, onPlaybackStateChange]);

  const attemptAutoplay = useCallback(() => {
    if (!autoPlay || !core) {
      return;
    }
    try {
      const playResult = core.play();
      if (playResult && typeof playResult.catch === 'function') {
        playResult.catch(() => undefined);
      }
    } catch {
      // Ignore autoplay rejections in restricted environments.
    }
  }, [autoPlay, core]);

  useEffect(() => {
    attemptAutoplay();
  }, [attemptAutoplay, activeFile?.id]);

  useEffect(() => {
    lastReportedTime.current = null;
  }, [activeFile?.id]);

  useEffect(() => {
    if (!core || playbackPosition === null || playbackPosition === undefined) {
      return;
    }
    const clamped = Number.isFinite(playbackPosition) ? Math.max(playbackPosition, 0) : 0;
    if (Math.abs(core.getCurrentTime() - clamped) < 0.25) {
      return;
    }
    core.seek(clamped);
  }, [core, playbackPosition, activeFile?.id]);

  useEffect(() => {
    if (!core || !onPlaybackPositionChange) {
      return;
    }
    return core.on('time', (time) => {
      if (lastReportedTime.current !== null && Math.abs(lastReportedTime.current - time) < 0.01) {
        return;
      }
      lastReportedTime.current = time;
      onPlaybackPositionChange(time);
    });
  }, [core, onPlaybackPositionChange]);

  useEffect(() => {
    if (!core || !onPlaybackStateChange) {
      return;
    }
    const unsubscribePlaying = core.on('playing', () => {
      onPlaybackStateChange('playing');
    });
    const unsubscribePaused = core.on('paused', () => {
      onPlaybackStateChange('paused');
    });
    return () => {
      unsubscribePlaying();
      unsubscribePaused();
    };
  }, [core, onPlaybackStateChange]);

  const handleEnded = useCallback(() => {
    onPlaybackStateChange?.('paused');
    onPlaybackEnded?.();
  }, [onPlaybackEnded, onPlaybackStateChange]);

  if (resolvedFiles.length === 0) {
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
      <PlayerCore
        key={activeFile.id}
        ref={attachCore}
        className="audio-player__element"
        data-testid="audio-player"
        controls
        src={activeFile.url}
        autoPlay={autoPlay}
        onEnded={handleEnded}
        onLoadedData={attemptAutoplay}
      >
        Your browser does not support the audio element.
      </PlayerCore>
      <div className="audio-player__selector">
        <label className="audio-player__selector-label" htmlFor={playlistSelectId}>
          Audio
        </label>
        <select
          id={playlistSelectId}
          className="audio-player__select"
          value={activeFile.id}
          onChange={(event) => {
            const next = event.target.value;
            if (next) {
              onSelectFile(next);
            }
          }}
        >
          {labels.map((file) => (
            <option key={file.id} value={file.id}>
              {file.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
