import { useEffect, useMemo, useRef, useState } from 'react';
import { buildStorageUrl } from '../api/client';

type TextSection = {
  path: string;
  content: string;
  error?: string;
};

type TextViewerProps = {
  files: string[];
  isLoading?: boolean;
  isGenerating?: boolean;
};

function formatDisplayName(path: string): string {
  const segments = path.split(/[/\\]+/).filter((segment) => segment.length > 0);
  return segments.length > 0 ? segments[segments.length - 1] : path;
}

export default function TextViewer({ files, isLoading = false, isGenerating = false }: TextViewerProps) {
  const [sections, setSections] = useState<TextSection[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const loadedRef = useRef<Set<string>>(new Set());
  const filesRef = useRef<string[]>(files);

  useEffect(() => {
    filesRef.current = files;
  }, [files]);

  useEffect(() => {
    for (const path of files) {
      if (loadedRef.current.has(path)) {
        continue;
      }
      loadedRef.current.add(path);
      setPendingCount((previous) => previous + 1);
      const url = buildStorageUrl(path);
      fetch(url)
        .then(async (response) => {
          if (!response.ok) {
            throw new Error(`Request failed with status ${response.status}`);
          }
          return response.text();
        })
        .then((content) => {
          setSections((previous) => {
            const next = [...previous, { path, content }];
            const order = filesRef.current;
            next.sort((a, b) => order.indexOf(a.path) - order.indexOf(b.path));
            return next;
          });
        })
        .catch((error: unknown) => {
          const message = error instanceof Error ? error.message : 'Unable to load section.';
          setSections((previous) => {
            const next = [...previous, { path, content: '', error: message }];
            const order = filesRef.current;
            next.sort((a, b) => order.indexOf(a.path) - order.indexOf(b.path));
            return next;
          });
        })
        .finally(() => {
          setPendingCount((previous) => Math.max(previous - 1, 0));
        });
    }
  }, [files]);

  const hasContent = sections.length > 0;
  const isUpdating = pendingCount > 0;

  const pendingMessage = useMemo(() => {
    if (isLoading) {
      return 'Loading media details…';
    }
    if (isUpdating) {
      return 'Fetching latest text sections…';
    }
    if (isGenerating && !hasContent) {
      return 'Text will appear here as it is generated.';
    }
    return null;
  }, [hasContent, isGenerating, isLoading, isUpdating]);

  return (
    <div className="text-viewer">
      {pendingMessage ? <p className="text-viewer__status">{pendingMessage}</p> : null}
      {hasContent ? (
        <div className="text-viewer__sections">
          {sections.map((section) => (
            <article key={section.path} className="text-viewer__section">
              <header className="text-viewer__section-header">
                <strong>{formatDisplayName(section.path)}</strong>
              </header>
              {section.error ? (
                <p className="alert" role="status">
                  {section.error}
                </p>
              ) : (
                <div
                  className="text-viewer__section-content"
                  dangerouslySetInnerHTML={{ __html: section.content }}
                />
              )}
            </article>
          ))}
        </div>
      ) : null}
      {!hasContent && !pendingMessage ? (
        <p className="text-viewer__status">No text files are available for this job yet.</p>
      ) : null}
    </div>
  );
}
