import { useMemo } from 'react';
import type { LiveMediaChunk, LiveMediaItem } from '../../hooks/useLiveMedia';
import {
  buildInteractiveAudioCatalog,
  resolveActiveTextChunk,
  resolveChunkForSelectedItem,
  resolveSelectedTextItem,
} from './activeTextSelection';

type UsePlayerPanelActiveTextArgs = {
  textItems: LiveMediaItem[];
  audioItems: LiveMediaItem[];
  chunks: LiveMediaChunk[];
  selectedTextId: string | null;
  selectedAudioId: string | null;
  inlineAudioSelection: string | null;
};

export function usePlayerPanelActiveText({
  textItems,
  audioItems,
  chunks,
  selectedTextId,
  selectedAudioId,
  inlineAudioSelection,
}: UsePlayerPanelActiveTextArgs) {
  const selectedItem = useMemo(
    () => resolveSelectedTextItem(textItems, selectedTextId),
    [textItems, selectedTextId],
  );
  const selectedChunk = useMemo(
    () => resolveChunkForSelectedItem(chunks, selectedItem),
    [chunks, selectedItem],
  );
  const {
    playlist: interactiveAudioPlaylist,
    nameMap: interactiveAudioNameMap,
    chunkIndexMap: audioChunkIndexMap,
  } = useMemo(() => buildInteractiveAudioCatalog(chunks, audioItems), [chunks, audioItems]);
  const activeTextChunk = useMemo(
    () =>
      resolveActiveTextChunk({
        chunks,
        selectedChunk,
        inlineAudioSelection,
        audioChunkIndexMap,
        selectedAudioId,
      }),
    [audioChunkIndexMap, chunks, inlineAudioSelection, selectedAudioId, selectedChunk],
  );
  const activeTextChunkIndex = useMemo(
    () => (activeTextChunk ? chunks.findIndex((chunk) => chunk === activeTextChunk) : -1),
    [activeTextChunk, chunks],
  );

  return {
    selectedItem,
    selectedChunk,
    interactiveAudioPlaylist,
    interactiveAudioNameMap,
    audioChunkIndexMap,
    activeTextChunk,
    activeTextChunkIndex,
  };
}
