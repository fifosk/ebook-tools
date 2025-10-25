import { useEffect, useMemo, useState } from 'react';
import { buildStorageUrl } from '../api/client';

type AudioPlayerProps = {
  files: string[];
  showUpdatingIndicator?: boolean;
};

function formatDisplayName(path: string): string {
  const segments = path.split(/[/\\]+/).filter((segment) => segment.length > 0);
  return segments.length > 0 ? segments[segments.length - 1] : path;
}

export default function AudioPlayer({ files, showUpdatingIndicator = false }: AudioPlayerProps) {
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
    return <p>No audio segments are available yet.</p>;
  }

  return (
    <div className="audio-player">
      <div className="audio-player__controls">
        <audio key={active.path} controls preload="auto" style={{ width: '100%' }}>
          <source src={active.url} />
          Your browser does not support HTML audio.
        </audio>
        {showUpdatingIndicator ? (
          <div className="player-indicator" role="status">
            Loading additional audio…
          </div>
        ) : null}
      </div>
      <ul className="audio-player__playlist">
        {sources.map((source, index) => (
          <li key={source.path} className={index === activeIndex ? 'active' : undefined}>
            <button
              type="button"
              onClick={() => setActiveIndex(index)}
              className="link-button"
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
