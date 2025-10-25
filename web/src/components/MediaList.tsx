import { buildStorageUrl } from '../api/client';

type MediaListProps = {
  mediaType: string;
  files: string[];
};

function formatDisplayName(path: string): string {
  const segments = path.split(/[/\\]+/).filter((segment) => segment.length > 0);
  return segments.length > 0 ? segments[segments.length - 1] : path;
}

export default function MediaList({ mediaType, files }: MediaListProps) {
  if (files.length === 0) {
    return <p>No {mediaType} files have been generated yet.</p>;
  }
  return (
    <ul className="media-list">
      {files.map((path) => (
        <li key={path}>
          <a href={buildStorageUrl(path)} target="_blank" rel="noreferrer">
            {formatDisplayName(path)}
          </a>
        </li>
      ))}
    </ul>
  );
}
