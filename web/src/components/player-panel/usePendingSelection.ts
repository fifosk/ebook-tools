import { useEffect } from 'react';
import type { LiveMediaChunk, LiveMediaItem, LiveMediaState } from '../../hooks/useLiveMedia';
import type { MediaSelectionRequest } from '../../types/player';
import { MEDIA_CATEGORIES, type MediaCategory } from './constants';
import { findChunkIndexForBaseId } from './helpers';
import type { InlineAudioOption } from './useInlineAudioOptions';

type UsePendingSelectionArgs = {
  pendingSelection: MediaSelectionRequest | null;
  setPendingSelection: (next: MediaSelectionRequest | null) => void;
  chunks: LiveMediaChunk[];
  media: LiveMediaState;
  findMatchingMediaId: (baseId: string | null, type: MediaCategory, available: LiveMediaItem[]) => string | null;
  getMediaItem: (category: MediaCategory, id: string | null | undefined) => LiveMediaItem | null;
  deriveBaseId: (item: LiveMediaItem) => string | null;
  rememberPosition: (args: {
    mediaId: string;
    mediaType: MediaCategory;
    baseId: string | null;
    position: number;
  }) => void;
  visibleInlineAudioOptions: InlineAudioOption[];
  setSelectedItemIds: React.Dispatch<React.SetStateAction<Record<MediaCategory, string | null>>>;
  setPendingChunkSelection: React.Dispatch<React.SetStateAction<{ index: number; token: number } | null>>;
  setPendingTextScrollRatio: React.Dispatch<React.SetStateAction<number | null>>;
  setInlineAudioSelection: React.Dispatch<React.SetStateAction<string | null>>;
};

export function usePendingSelection({
  pendingSelection,
  setPendingSelection,
  chunks,
  media,
  findMatchingMediaId,
  getMediaItem,
  deriveBaseId,
  rememberPosition,
  visibleInlineAudioOptions,
  setSelectedItemIds,
  setPendingChunkSelection,
  setPendingTextScrollRatio,
  setInlineAudioSelection,
}: UsePendingSelectionArgs) {
  useEffect(() => {
    if (!pendingSelection) {
      return;
    }

    const hasLoadedMedia = MEDIA_CATEGORIES.some((category) => media[category].length > 0);
    if (!hasLoadedMedia) {
      return;
    }

    const { baseId, preferredType, offsetRatio = null, approximateTime = null } = pendingSelection;
    const selectionToken = pendingSelection.token ?? Date.now();
    const chunkMatchIndex = findChunkIndexForBaseId(baseId, chunks);

    const candidateOrder: MediaCategory[] = [];
    if (preferredType) {
      candidateOrder.push(preferredType);
    }
    MEDIA_CATEGORIES.forEach((category) => {
      if (!candidateOrder.includes(category)) {
        candidateOrder.push(category);
      }
    });

    const matchByCategory: Record<MediaCategory, string | null> = {
      text: baseId ? findMatchingMediaId(baseId, 'text', media.text) : null,
      audio: baseId ? findMatchingMediaId(baseId, 'audio', media.audio) : null,
      video: baseId ? findMatchingMediaId(baseId, 'video', media.video) : null,
    };

    if (matchByCategory.audio) {
      setSelectedItemIds((current) =>
        current.audio === matchByCategory.audio ? current : { ...current, audio: matchByCategory.audio },
      );
    }

    const tabCandidates = candidateOrder.filter(
      (category): category is Extract<MediaCategory, 'text' | 'video'> =>
        category === 'text' || category === 'video',
    );

    let appliedCategory: MediaCategory | null = null;

    for (const category of tabCandidates) {
      if (category === 'text' && !matchByCategory.text && chunkMatchIndex >= 0) {
        setPendingChunkSelection({ index: chunkMatchIndex, token: selectionToken });
        appliedCategory = 'text';
        break;
      }

      const matchId = matchByCategory[category];
      if (!matchId) {
        continue;
      }

      setSelectedItemIds((current) => {
        if (current[category] === matchId) {
          return current;
        }
        return { ...current, [category]: matchId };
      });
      appliedCategory = category;
      break;
    }

    if (!appliedCategory && preferredType) {
      if (preferredType === 'audio') {
        setSelectedItemIds((current) => {
          if (current.audio !== null) {
            return current;
          }
          const firstAudio = media.audio.find((item) => item.url);
          if (!firstAudio?.url) {
            return current;
          }
          return { ...current, audio: firstAudio.url };
        });

        if (chunkMatchIndex >= 0) {
          setPendingChunkSelection({ index: chunkMatchIndex, token: selectionToken });
          appliedCategory = 'text';
        } else if (media.text.length > 0) {
          setSelectedItemIds((current) => {
            if (current.text) {
              return current;
            }
            const firstText = media.text.find((item) => item.url);
            if (!firstText?.url) {
              return current;
            }
            return { ...current, text: firstText.url };
          });
          appliedCategory = 'text';
        } else if (media.video.length > 0) {
          setSelectedItemIds((current) => {
            if (current.video) {
              return current;
            }
            const firstVideo = media.video.find((item) => item.url);
            if (!firstVideo?.url) {
              return current;
            }
            return { ...current, video: firstVideo.url };
          });
          appliedCategory = 'video';
        }
      } else {
        const category = preferredType;
        if (category === 'text' && chunkMatchIndex >= 0) {
          setPendingChunkSelection({ index: chunkMatchIndex, token: selectionToken });
          appliedCategory = 'text';
        } else {
          setSelectedItemIds((current) => {
            const hasCurrent = current[category] !== null;
            if (hasCurrent) {
              return current;
            }
            const firstItem = media[category].find((item) => item.url);
            if (!firstItem?.url) {
              return current;
            }
            return { ...current, [category]: firstItem.url };
          });
          appliedCategory = media[category].length > 0 ? category : null;
        }
      }
    }

    if (matchByCategory.audio && approximateTime != null && Number.isFinite(approximateTime)) {
      const audioItem = getMediaItem('audio', matchByCategory.audio);
      const audioBaseId = audioItem ? deriveBaseId(audioItem) : null;
      rememberPosition({
        mediaId: matchByCategory.audio,
        mediaType: 'audio',
        baseId: audioBaseId,
        position: Math.max(approximateTime, 0),
      });
    }

    if (matchByCategory.video && approximateTime != null && Number.isFinite(approximateTime)) {
      const videoItem = getMediaItem('video', matchByCategory.video);
      const videoBaseId = videoItem ? deriveBaseId(videoItem) : null;
      rememberPosition({
        mediaId: matchByCategory.video,
        mediaType: 'video',
        baseId: videoBaseId,
        position: Math.max(approximateTime, 0),
      });
    }

    if ((matchByCategory.text || chunkMatchIndex >= 0) && offsetRatio != null && Number.isFinite(offsetRatio)) {
      setPendingTextScrollRatio(Math.max(Math.min(offsetRatio, 1), 0));
    } else {
      setPendingTextScrollRatio(null);
    }

    if (matchByCategory.audio && visibleInlineAudioOptions.some((option) => option.url === matchByCategory.audio)) {
      setInlineAudioSelection((current) => (current === matchByCategory.audio ? current : matchByCategory.audio));
    }

    setPendingSelection(null);
  }, [
    chunks,
    deriveBaseId,
    findMatchingMediaId,
    getMediaItem,
    media,
    pendingSelection,
    rememberPosition,
    setInlineAudioSelection,
    setPendingChunkSelection,
    setPendingSelection,
    setPendingTextScrollRatio,
    setSelectedItemIds,
    visibleInlineAudioOptions,
  ]);
}
