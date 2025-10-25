export interface TextFile {
  id: string;
  name?: string;
  content?: string;
  url?: string;
}

interface TextViewerProps {
  file: TextFile | null;
  isLoading?: boolean;
}

function openDocument(url: string) {
  if (typeof window === 'undefined') {
    return;
  }

  window.open(url, '_blank', 'noopener');
}

export default function TextViewer({ file, isLoading = false }: TextViewerProps) {
  if (isLoading) {
    return (
      <div className="text-viewer" role="status">
        Loading text files…
      </div>
    );
  }

  if (!file) {
    return (
      <div className="text-viewer" role="status">
        Waiting for text files…
      </div>
    );
  }

  return (
    <div className="text-viewer" data-testid="text-viewer-content" aria-live="polite">
      <header className="text-viewer__header">
        <h3>{file.name ?? 'Latest text output'}</h3>
      </header>
      <div className="text-viewer__body">
        {file.content ? (
          <pre>{file.content}</pre>
        ) : file.url ? (
          <button
            type="button"
            className="text-viewer__open"
            onClick={() => openDocument(file.url!)}
          >
            Open document in a new tab
          </button>
        ) : (
          <p>No preview available.</p>
        )}
      </div>
    </div>
  );
}
