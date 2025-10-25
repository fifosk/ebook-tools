import { useEffect, useMemo, useState } from 'react';
import { buildStorageUrl } from '../api/client';

type VideoPlayerProps = {
  files: string[];
  showUpdatingIndicator?: boolean;
};

function formatDisplayName(path: string): string {
  const segments = path.split(/[/\\]+/).filter((segment) => segment.length > 0);
  return segments.length > 0 ? segments[segments.length - 1] : path;
}

export default function VideoPlayer({ files, showUpdatingIndicator = false }: VideoPlayerProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (files.length === 0) {
      setActiveIndex(0);
      return;
    }
    setActiveIndex((previous) => {
      if (previous < files.length) {
        return previous;
      }
      return Math.max(files.length - 1, 0);
    });
  }, [files]);

  const sources = useMemo(() => files.map((path) => ({ path, url: buildStorageUrl(path) })), [files]);
  const active = sources[activeIndex];

  if (sources.length === 0) {
    return <p>No video segments are available yet.</p>;
  }

  return (
    <div className="video-player">
      <div className="video-player__canvas">
        <video key={active.path} controls preload="auto" style={{ width: '100%', maxHeight: '360px' }}>
          <source src={active.url} />
          Your browser does not support HTML video.
        </video>
        {showUpdatingIndicator ? (
          <div className="player-indicator" role="status">
            Loading additional video…
          </div>
        ) : null}
      </div>
      <ul className="video-player__playlist">
        {sources.map((source, index) => (
          <li key={source.path} className={index === activeIndex ? 'active' : undefined}>
            <button
              type="button"
              className="link-button"
              onClick={() => setActiveIndex(index)}
              disabled={index === activeIndex}
            >
              {formatDisplayName(source.path)}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
