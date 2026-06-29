import { useCallback } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { LiveMediaChunk, LiveMediaItem } from '../../hooks/useLiveMedia';
import type { MediaCategory } from './constants';
import {
  deriveBaseIdFromReference,
  findChunkIndexForBaseId,
} from './helpers';

type ActivateTextItemOptions = {
  scrollRatio?: number;
  autoPlay?: boolean;
};

type UsePlayerPanelTextActivationArgs = {
  chunks: LiveMediaChunk[];
  deriveBaseId: (item: LiveMediaItem) => string | null;
  activateChunk: (chunk: LiveMediaChunk | null | undefined, options?: ActivateTextItemOptions) => boolean;
  setSelectedItemIds: Dispatch<SetStateAction<Record<MediaCategory, string | null>>>;
  setPendingTextScrollRatio: Dispatch<SetStateAction<number | null>>;
  requestAutoPlay: () => void;
};

export function usePlayerPanelTextActivation({
  chunks,
  deriveBaseId,
  activateChunk,
  setSelectedItemIds,
  setPendingTextScrollRatio,
  requestAutoPlay,
}: UsePlayerPanelTextActivationArgs) {
  return useCallback(
    (item: LiveMediaItem | null | undefined, options?: ActivateTextItemOptions) => {
      if (!item?.url) {
        return false;
      }
      const baseId = deriveBaseId(item) ?? deriveBaseIdFromReference(item.url);
      const chunkIndex = baseId ? findChunkIndexForBaseId(baseId, chunks) : -1;
      if (chunkIndex >= 0) {
        return activateChunk(chunks[chunkIndex], options);
      }
      setSelectedItemIds((current) =>
        current.text === item.url ? current : { ...current, text: item.url },
      );
      if (typeof options?.scrollRatio === 'number') {
        setPendingTextScrollRatio(Math.min(Math.max(options.scrollRatio, 0), 1));
      }
      if (options?.autoPlay) {
        requestAutoPlay();
      }
      return false;
    },
    [activateChunk, chunks, deriveBaseId, requestAutoPlay, setPendingTextScrollRatio, setSelectedItemIds],
  );
}
