import { useMemo } from 'react';
import { useActiveFile } from './useActiveFile';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/Tabs';

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
      <Tabs value={activeId ?? undefined} onValueChange={selectFile} className="text-viewer__tabs-container">
        <TabsList className="text-viewer__tabs" aria-label="Text files">
          {labels.map((file) => (
            <TabsTrigger key={file.id} value={file.id} className="text-viewer__tab">
              {file.label}
            </TabsTrigger>
          ))}
        </TabsList>
        {files.map((file) => {
          const isActive = file.id === activeFile.id;
          return (
            <TabsContent
              key={file.id}
              value={file.id}
              className="text-viewer__content"
              aria-live={isActive ? 'polite' : undefined}
              data-testid={isActive ? 'text-viewer-content' : undefined}
            >
              {file.content ? (
                <pre>{file.content}</pre>
              ) : file.url ? (
                <a href={file.url} target="_blank" rel="noreferrer">
                  Open {file.name ?? 'document'}
                </a>
              ) : (
                <p>No preview available.</p>
              )}
            </TabsContent>
          );
        })}
      </Tabs>
    </div>
  );
}
