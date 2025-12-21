import { useCallback, useEffect, useRef } from 'react';
import type { LiveMediaChunk, LiveMediaItem } from '../../hooks/useLiveMedia';
import { isAudioFileType } from './utils';
import { deriveBaseIdFromReference } from './helpers';
import type { MediaCategory, NavigationIntent } from './constants';
import type { InlineAudioOption } from './useInlineAudioOptions';

type ActivateChunkOptions = {
  scrollRatio?: number;
  autoPlay?: boolean;
};

type UseInlineAudioSelectionArgs = {
  chunks: LiveMediaChunk[];
  audioChunkIndexMap: Map<string, number>;
  activeTextChunkIndex: number;
  inlineAudioSelection: string | null;
  setInlineAudioSelection: React.Dispatch<React.SetStateAction<string | null>>;
  visibleInlineAudioOptions: InlineAudioOption[];
  mediaAudio: LiveMediaItem[];
  getMediaItem: (category: MediaCategory, id: string | null | undefined) => LiveMediaItem | null;
  deriveBaseId: (item: LiveMediaItem) => string | null;
  setSelectedItemIds: React.Dispatch<React.SetStateAction<Record<MediaCategory, string | null>>>;
  setPendingTextScrollRatio: React.Dispatch<React.SetStateAction<number | null>>;
  rememberPosition: (args: {
    mediaId: string;
    mediaType: MediaCategory;
    baseId: string | null;
    position: number;
  }) => void;
  requestAutoPlay: () => void;
  updateSelection: (category: MediaCategory, intent: NavigationIntent) => void;
};

type UseInlineAudioSelectionResult = {
  activateChunk: (chunk: LiveMediaChunk | null | undefined, options?: ActivateChunkOptions) => boolean;
  handleInlineAudioEnded: () => void;
};

export function useInlineAudioSelection({
  chunks,
  audioChunkIndexMap,
  activeTextChunkIndex,
  inlineAudioSelection,
  setInlineAudioSelection,
  visibleInlineAudioOptions,
  mediaAudio,
  getMediaItem,
  deriveBaseId,
  setSelectedItemIds,
  setPendingTextScrollRatio,
  rememberPosition,
  requestAutoPlay,
  updateSelection,
}: UseInlineAudioSelectionArgs): UseInlineAudioSelectionResult {
  const inlineAudioBaseRef = useRef<string | null>(null);

  const syncInteractiveSelection = useCallback(
    (audioUrl: string | null) => {
      if (!audioUrl) {
        return;
      }
      setSelectedItemIds((current) =>
        current.audio === audioUrl ? current : { ...current, audio: audioUrl },
      );
      const chunkIndex = audioChunkIndexMap.get(audioUrl);
      if (typeof chunkIndex === 'number' && chunkIndex >= 0 && chunkIndex < chunks.length) {
        const targetChunk = chunks[chunkIndex];
        const nextTextFile = targetChunk.files.find((file) => file.type === 'text' && file.url);
        if (nextTextFile?.url) {
          setSelectedItemIds((current) =>
            current.text === nextTextFile.url ? current : { ...current, text: nextTextFile.url },
          );
        }
      }
    },
    [audioChunkIndexMap, chunks, setSelectedItemIds],
  );

  const activateChunk = useCallback(
    (chunk: LiveMediaChunk | null | undefined, options?: ActivateChunkOptions) => {
      if (!chunk) {
        return false;
      }
      const hasAudioTracks =
        Boolean(chunk.audioTracks) && Object.keys(chunk.audioTracks ?? {}).length > 0;
      const scrollRatio =
        typeof options?.scrollRatio === 'number' ? Math.min(Math.max(options.scrollRatio, 0), 1) : null;
      if (scrollRatio !== null) {
        setPendingTextScrollRatio(scrollRatio);
      }
      const textFile = chunk.files.find(
        (file) => file.type === 'text' && typeof file.url === 'string' && file.url.length > 0,
      );
      if (textFile?.url) {
        setSelectedItemIds((current) =>
          current.text === textFile.url ? current : { ...current, text: textFile.url },
        );
        const textBaseId = deriveBaseIdFromReference(textFile.url);
        rememberPosition({ mediaId: textFile.url, mediaType: 'text', baseId: textBaseId, position: 0 });
      }
      const audioFile = chunk.files.find(
        (file) => isAudioFileType(file.type) && typeof file.url === 'string' && file.url.length > 0,
      );
      if (audioFile?.url) {
        const audioItem = getMediaItem('audio', audioFile.url);
        const audioBaseId = audioItem ? deriveBaseId(audioItem) : deriveBaseIdFromReference(audioFile.url);
        rememberPosition({ mediaId: audioFile.url, mediaType: 'audio', baseId: audioBaseId, position: 0 });
        setInlineAudioSelection((current) => (current === audioFile.url ? current : audioFile.url));
        syncInteractiveSelection(audioFile.url);
        if (options?.autoPlay) {
          requestAutoPlay();
        }
      } else if (options?.autoPlay && hasAudioTracks) {
        requestAutoPlay();
      }
      return true;
    },
    [
      deriveBaseId,
      getMediaItem,
      rememberPosition,
      requestAutoPlay,
      setInlineAudioSelection,
      setPendingTextScrollRatio,
      setSelectedItemIds,
      syncInteractiveSelection,
    ],
  );

  const advanceInteractiveChunk = useCallback(
    (options?: { autoPlay?: boolean }) => {
      if (chunks.length === 0) {
        return false;
      }
      let currentIndex = activeTextChunkIndex;
      if (currentIndex < 0 && inlineAudioSelection) {
        const mappedIndex = audioChunkIndexMap.get(inlineAudioSelection);
        if (typeof mappedIndex === 'number' && mappedIndex >= 0) {
          currentIndex = mappedIndex;
        }
      }
      const nextIndex = currentIndex >= 0 ? currentIndex + 1 : 0;
      if (nextIndex >= chunks.length) {
        return false;
      }
      const nextChunk = chunks[nextIndex];
      activateChunk(nextChunk, {
        scrollRatio: 0,
        autoPlay: options?.autoPlay ?? false,
      });
      return true;
    },
    [activeTextChunkIndex, audioChunkIndexMap, activateChunk, chunks, inlineAudioSelection],
  );

  const handleInlineAudioEnded = useCallback(() => {
    const advanced = advanceInteractiveChunk({ autoPlay: true });
    if (!advanced) {
      updateSelection('text', 'next');
    }
  }, [advanceInteractiveChunk, updateSelection]);

  useEffect(() => {
    if (visibleInlineAudioOptions.length === 0) {
      if (inlineAudioSelection) {
        const currentAudio = getMediaItem('audio', inlineAudioSelection);
        if (!currentAudio) {
          setInlineAudioSelection(null);
        }
      }
      return;
    }

    if (inlineAudioSelection) {
      const hasExactMatch = visibleInlineAudioOptions.some((option) => option.url === inlineAudioSelection);
      if (hasExactMatch) {
        return;
      }

      const currentAudio = getMediaItem('audio', inlineAudioSelection);
      const currentBaseId =
        currentAudio ? deriveBaseId(currentAudio) : inlineAudioBaseRef.current ?? deriveBaseIdFromReference(inlineAudioSelection);

      if (currentBaseId) {
        const remapped = visibleInlineAudioOptions.find((option) => {
          const optionAudio = getMediaItem('audio', option.url);
          if (optionAudio) {
            return deriveBaseId(optionAudio) === currentBaseId;
          }
          return deriveBaseIdFromReference(option.url) === currentBaseId;
        });

        if (remapped?.url) {
          setInlineAudioSelection((current) => (current === remapped.url ? current : remapped.url));
          if (remapped.url !== inlineAudioSelection) {
            syncInteractiveSelection(remapped.url);
          }
          return;
        }
      }
    }

    const desiredBaseId = inlineAudioBaseRef.current;
    if (!inlineAudioSelection) {
      const fallbackUrl = visibleInlineAudioOptions[0]?.url ?? null;
      if (fallbackUrl) {
        setInlineAudioSelection(fallbackUrl);
        syncInteractiveSelection(fallbackUrl);
      }
      return;
    }

    if (!desiredBaseId) {
      return;
    }

    const preferredOption = visibleInlineAudioOptions.find((option) => {
      const optionAudio = getMediaItem('audio', option.url);
      if (optionAudio) {
        return deriveBaseId(optionAudio) === desiredBaseId;
      }
      return deriveBaseIdFromReference(option.url) === desiredBaseId;
    });

    if (!preferredOption?.url || preferredOption.url === inlineAudioSelection) {
      return;
    }

    setInlineAudioSelection(preferredOption.url);
    syncInteractiveSelection(preferredOption.url);
  }, [
    deriveBaseId,
    getMediaItem,
    inlineAudioSelection,
    setInlineAudioSelection,
    syncInteractiveSelection,
    visibleInlineAudioOptions,
  ]);

  useEffect(() => {
    if (!inlineAudioSelection) {
      inlineAudioBaseRef.current = null;
      return;
    }
    const currentAudio = getMediaItem('audio', inlineAudioSelection);
    const baseId = currentAudio ? deriveBaseId(currentAudio) : deriveBaseIdFromReference(inlineAudioSelection);
    inlineAudioBaseRef.current = baseId;
  }, [deriveBaseId, getMediaItem, inlineAudioSelection]);

  useEffect(() => {
    if (!inlineAudioSelection) {
      return;
    }
    const currentAudio = getMediaItem('audio', inlineAudioSelection);
    if (currentAudio) {
      return;
    }
    const baseId = inlineAudioBaseRef.current ?? deriveBaseIdFromReference(inlineAudioSelection);
    if (!baseId) {
      return;
    }

    const replacement = mediaAudio.find((item) => {
      if (!item.url) {
        return false;
      }
      const optionAudio = getMediaItem('audio', item.url);
      if (optionAudio) {
        return deriveBaseId(optionAudio) === baseId;
      }
      return deriveBaseIdFromReference(item.url) === baseId;
    });

    if (replacement?.url) {
      setInlineAudioSelection(replacement.url);
      syncInteractiveSelection(replacement.url);
    }
  }, [
    deriveBaseId,
    getMediaItem,
    inlineAudioSelection,
    mediaAudio,
    setInlineAudioSelection,
    syncInteractiveSelection,
  ]);

  return {
    activateChunk,
    handleInlineAudioEnded,
  };
}
