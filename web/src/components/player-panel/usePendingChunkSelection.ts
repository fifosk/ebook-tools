import { useEffect } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import type { PendingChunkSelection } from './usePlayerPanelSelectionState';

type UsePendingChunkSelectionArgs = {
  chunks: LiveMediaChunk[];
  pendingChunkSelection: PendingChunkSelection | null;
  setPendingChunkSelection: Dispatch<SetStateAction<PendingChunkSelection | null>>;
  activateChunk: (chunk: LiveMediaChunk | null | undefined, options?: { scrollRatio?: number }) => boolean;
};

export function usePendingChunkSelection({
  chunks,
  pendingChunkSelection,
  setPendingChunkSelection,
  activateChunk,
}: UsePendingChunkSelectionArgs) {
  useEffect(() => {
    if (!pendingChunkSelection) {
      return;
    }

    const { index } = pendingChunkSelection;
    if (index < 0 || index >= chunks.length) {
      setPendingChunkSelection(null);
      return;
    }

    activateChunk(chunks[index], { scrollRatio: 0 });
    setPendingChunkSelection(null);
  }, [activateChunk, chunks, pendingChunkSelection, setPendingChunkSelection]);
}
