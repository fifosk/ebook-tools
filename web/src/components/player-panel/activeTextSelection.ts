import type { LiveMediaChunk, LiveMediaItem } from '../../hooks/useLiveMedia';
import { formatChunkLabel, isAudioFileType } from './utils';

export function buildInteractiveAudioCatalog(
  chunks: LiveMediaChunk[],
  audioMedia: LiveMediaItem[],
): {
  playlist: LiveMediaItem[];
  nameMap: Map<string, string>;
  chunkIndexMap: Map<string, number>;
} {
  const playlist: LiveMediaItem[] = [];
  const nameMap = new Map<string, string>();
  const chunkIndexMap = new Map<string, number>();
  const seen = new Set<string>();

  const register = (
    item: LiveMediaItem | null | undefined,
    chunkIndex: number | null,
    fallbackLabel?: string,
  ) => {
    if (!item || !item.url) {
      return;
    }
    const url = item.url;
    if (seen.has(url)) {
      return;
    }
    seen.add(url);
    const trimmedName = typeof item.name === 'string' ? item.name.trim() : '';
    const trimmedFallback = typeof fallbackLabel === 'string' ? fallbackLabel.trim() : '';
    const label = trimmedName || trimmedFallback || `Audio ${playlist.length + 1}`;
    const enriched = trimmedName ? item : { ...item, name: label };
    playlist.push(enriched);
    nameMap.set(url, label);
    if (typeof chunkIndex === 'number' && chunkIndex >= 0) {
      chunkIndexMap.set(url, chunkIndex);
    }
  };

  chunks.forEach((chunk, index) => {
    const chunkLabel = formatChunkLabel(chunk, index);
    chunk.files.forEach((file) => {
      if (isAudioFileType(file.type)) {
        register(file, index, chunkLabel);
      }
    });
    const audioTracks = chunk.audioTracks;
    if (audioTracks && typeof audioTracks === 'object') {
      Object.entries(audioTracks).forEach(([, trackMeta]) => {
        if (!trackMeta || typeof trackMeta !== 'object') {
          return;
        }
        const trackUrl =
          (trackMeta as { url?: string; path?: string }).url ??
          (trackMeta as { url?: string; path?: string }).path;
        if (typeof trackUrl === 'string' && trackUrl.trim()) {
          register(
            {
              type: 'audio',
              url: trackUrl.trim(),
              name: chunkLabel,
              source: 'completed',
            },
            index,
            chunkLabel,
          );
        }
      });
    }
  });

  audioMedia.forEach((item) => {
    if (!item.url) {
      return;
    }
    const existingIndex = chunkIndexMap.get(item.url);
    register(item, typeof existingIndex === 'number' ? existingIndex : null, item.name);
  });

  return { playlist, nameMap, chunkIndexMap };
}

export function resolveSelectedTextItem(
  textItems: LiveMediaItem[],
  selectedItemId: string | null | undefined,
): LiveMediaItem | null {
  if (textItems.length === 0) {
    return null;
  }
  if (!selectedItemId) {
    return textItems[0] ?? null;
  }
  return textItems.find((item) => item.url === selectedItemId) ?? textItems[0] ?? null;
}

export function resolveChunkForSelectedItem(
  chunks: LiveMediaChunk[],
  selectedItem: LiveMediaItem | null | undefined,
): LiveMediaChunk | null {
  if (!selectedItem) {
    return null;
  }
  return (
    chunks.find((chunk) => {
      if (selectedItem.chunk_id && chunk.chunkId) {
        return chunk.chunkId === selectedItem.chunk_id;
      }
      if (selectedItem.range_fragment && chunk.rangeFragment) {
        return chunk.rangeFragment === selectedItem.range_fragment;
      }
      if (selectedItem.url) {
        return chunk.files.some((file) => file.url === selectedItem.url);
      }
      return false;
    }) ?? null
  );
}

function chunkMatchesInlineAudioTrack(chunk: LiveMediaChunk, inlineAudioSelection: string): boolean {
  const tracks = chunk.audioTracks;
  if (!tracks || typeof tracks !== 'object') {
    return false;
  }
  const selectionBase = inlineAudioSelection.split('?')[0];
  return Object.values(tracks).some((trackMeta) => {
    if (!trackMeta || typeof trackMeta !== 'object') {
      return false;
    }
    const trackUrl =
      (trackMeta as { url?: string; path?: string }).url ??
      (trackMeta as { url?: string; path?: string }).path;
    if (!trackUrl) {
      return false;
    }
    return inlineAudioSelection.includes(trackUrl) || trackUrl.includes(selectionBase);
  });
}

export function resolveActiveTextChunk(args: {
  chunks: LiveMediaChunk[];
  selectedChunk: LiveMediaChunk | null;
  inlineAudioSelection: string | null;
  audioChunkIndexMap: Map<string, number>;
  selectedAudioId: string | null | undefined;
}): LiveMediaChunk | null {
  const { chunks, selectedChunk, inlineAudioSelection, audioChunkIndexMap, selectedAudioId } = args;
  if (selectedChunk) {
    return selectedChunk;
  }
  if (!chunks.length) {
    return null;
  }
  if (inlineAudioSelection) {
    const mappedIndex = audioChunkIndexMap.get(inlineAudioSelection);
    if (typeof mappedIndex === 'number' && mappedIndex >= 0 && mappedIndex < chunks.length) {
      return chunks[mappedIndex];
    }
    const matchedByAudioTracks = chunks.find((chunk) =>
      chunkMatchesInlineAudioTrack(chunk, inlineAudioSelection),
    );
    if (matchedByAudioTracks) {
      return matchedByAudioTracks;
    }
  }
  if (selectedAudioId) {
    const mappedIndex = audioChunkIndexMap.get(selectedAudioId);
    if (typeof mappedIndex === 'number' && mappedIndex >= 0 && mappedIndex < chunks.length) {
      return chunks[mappedIndex];
    }
    const matchedByAudio = chunks.find((chunk) =>
      chunk.files.some((file) => isAudioFileType(file.type) && file.url === selectedAudioId),
    );
    if (matchedByAudio) {
      return matchedByAudio;
    }
  }
  const firstWithSentences = chunks.find(
    (chunk) => Array.isArray(chunk.sentences) && chunk.sentences.length > 0,
  );
  return firstWithSentences ?? chunks[0];
}
