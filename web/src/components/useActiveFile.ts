import { useCallback, useEffect, useState } from 'react';

export interface IdentifiableFile {
  id: string;
}

export interface ActiveFileState<T extends IdentifiableFile> {
  activeFile: T | null;
  activeId: string | null;
  selectFile: (fileId: string) => void;
}

export function useActiveFile<T extends IdentifiableFile>(files: T[]): ActiveFileState<T> {
  const [activeId, setActiveId] = useState<string | null>(() =>
    files.length > 0 ? files[files.length - 1].id : null
  );

  useEffect(() => {
    if (files.length === 0) {
      if (activeId !== null) {
        setActiveId(null);
      }
      return;
    }

    const hasActive = activeId !== null && files.some((file) => file.id === activeId);

    if (!hasActive) {
      setActiveId(files[files.length - 1].id);
    }
  }, [files, activeId]);

  const selectFile = useCallback((fileId: string) => {
    setActiveId(fileId);
  }, []);

  const activeFile = activeId ? files.find((file) => file.id === activeId) ?? null : null;

  return {
    activeFile,
    activeId,
    selectFile
  };
}
