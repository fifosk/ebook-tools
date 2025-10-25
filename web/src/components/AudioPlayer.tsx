export interface AudioFile {
  id: string;
  url: string;
  name?: string;
}

interface AudioPlayerProps {
  file: AudioFile | null;
  isLoading?: boolean;
}

export default function AudioPlayer({ file, isLoading = false }: AudioPlayerProps) {
  if (isLoading) {
    return (
      <div className="audio-player" role="status">
        Loading audio…
      </div>
    );
  }

  if (!file) {
    return (
      <div className="audio-player" role="status">
        Waiting for audio files…
      </div>
    );
  }

  return (
    <div className="audio-player">
      <div className="audio-player__metadata" aria-live="polite">
        <span className="audio-player__title">{file.name ?? 'Latest audio track'}</span>
      </div>
      <audio
        key={file.id}
        className="audio-player__element"
        data-testid="audio-player"
        controls
        src={file.url}
      >
        Your browser does not support the audio element.
      </audio>
    </div>
  );
}
