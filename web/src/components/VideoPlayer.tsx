export interface VideoFile {
  id: string;
  url: string;
  name?: string;
  poster?: string;
}

interface VideoPlayerProps {
  file: VideoFile | null;
  isLoading?: boolean;
}

export default function VideoPlayer({ file, isLoading = false }: VideoPlayerProps) {
  if (isLoading) {
    return (
      <div className="video-player" role="status">
        Loading video…
      </div>
    );
  }

  if (!file) {
    return (
      <div className="video-player" role="status">
        Waiting for video files…
      </div>
    );
  }

  return (
    <div className="video-player">
      <div className="video-player__metadata" aria-live="polite">
        <span className="video-player__title">{file.name ?? 'Latest video'}</span>
      </div>
      <video
        key={file.id}
        className="video-player__element"
        data-testid="video-player"
        controls
        src={file.url}
        poster={file.poster}
      >
        Your browser does not support the video element.
      </video>
    </div>
  );
}
