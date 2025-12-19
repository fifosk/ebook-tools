import { useMemo } from 'react';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';

export function useLibraryMediaOrigin(chunk: LiveMediaChunk | null): boolean {
  return useMemo(() => {
    const metadataUrl = chunk?.metadataUrl ?? null;
    if (typeof metadataUrl !== 'string' || !metadataUrl.trim()) {
      return false;
    }
    return metadataUrl.includes('/api/library/media/');
  }, [chunk?.metadataUrl]);
}
