import { useMemo } from 'react';
import { useActiveFile } from './useActiveFile';

export interface AudioFile {
  id: string;
  url: string;
  name?: string;
}

interface AudioPlayerProps {
  files: AudioFile[];
}

export default function AudioPlayer({ files }: AudioPlayerProps) {
  const { activeFile, activeId, selectFile } = useActiveFile(files);

  const labels = useMemo(
    () =>
      files.map((file, index) => ({
        id: file.id,
        label: file.name ?? `Track ${index + 1}`
      })),
    [files]
  );

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
        className="audio-player__element"
        data-testid="audio-player"
        controls
        src={activeFile.url}
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
            onClick={() => selectFile(file.id)}
          >
            {file.label}
          </button>
        ))}
      </div>
    </div>
  );
}
