import { useMemo } from 'react';
import { useActiveFile } from './useActiveFile';

export interface TextFile {
  id: string;
  name?: string;
  content?: string;
  url?: string;
}

interface TextViewerProps {
  files: TextFile[];
}

export default function TextViewer({ files }: TextViewerProps) {
  const { activeFile, activeId, selectFile } = useActiveFile(files);

  const labels = useMemo(
    () =>
      files.map((file, index) => ({
        id: file.id,
        label: file.name ?? `Text ${index + 1}`
      })),
    [files]
  );

  if (files.length === 0) {
    return (
      <div className="text-viewer" role="status">
        Loading text files…
      </div>
    );
  }

  if (!activeFile) {
    return (
      <div className="text-viewer" role="status">
        Preparing the latest text file…
      </div>
    );
  }

  return (
    <div className="text-viewer">
      <div className="text-viewer__tabs" role="tablist" aria-label="Text files">
        {labels.map((file) => (
          <button
            key={file.id}
            type="button"
            role="tab"
            className="text-viewer__tab"
            aria-selected={file.id === activeId}
            aria-controls={`text-viewer-panel-${file.id}`}
            onClick={() => selectFile(file.id)}
          >
            {file.label}
          </button>
        ))}
      </div>
      <div
        className="text-viewer__content"
        role="tabpanel"
        id={`text-viewer-panel-${activeFile.id}`}
        aria-live="polite"
        data-testid="text-viewer-content"
      >
        {activeFile.content ? (
          <pre>{activeFile.content}</pre>
        ) : activeFile.url ? (
          <a href={activeFile.url} target="_blank" rel="noreferrer">
            Open {activeFile.name ?? 'document'}
          </a>
        ) : (
          <p>No preview available.</p>
        )}
      </div>
    </div>
  );
}
