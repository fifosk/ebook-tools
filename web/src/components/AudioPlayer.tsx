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
}

export default function AudioPlayer({
  files,
  activeId,
  onSelectFile,
  autoPlay = false,
  onPlaybackEnded,
}: AudioPlayerProps) {
  const labels = files.map((file, index) => ({
    id: file.id,
    label: file.name ?? `Track ${index + 1}`
  }));

  const activeFile = activeId ? files.find((file) => file.id === activeId) ?? null : null;

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
        autoPlay={autoPlay}
        onEnded={onPlaybackEnded}
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
