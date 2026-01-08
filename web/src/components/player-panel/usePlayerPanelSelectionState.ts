import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { LiveMediaItem, LiveMediaState } from '../../hooks/useLiveMedia';
import type { MediaSelectionRequest } from '../../types/player';
import { MEDIA_CATEGORIES, type MediaCategory, type NavigationIntent } from './constants';

type MemoryState = {
  currentMediaId: string | null;
  currentMediaType: MediaCategory | null;
};

type RememberSelection = (args: { media: LiveMediaItem }) => void;

type UsePlayerPanelSelectionStateArgs = {
  media: LiveMediaState;
  selectionRequest: MediaSelectionRequest | null;
  memoryState: MemoryState;
  rememberSelection: RememberSelection;
};

type PendingChunkSelection = { index: number; token: number };

type UsePlayerPanelSelectionStateResult = {
  selectedItemIds: Record<MediaCategory, string | null>;
  setSelectedItemIds: React.Dispatch<React.SetStateAction<Record<MediaCategory, string | null>>>;
  pendingSelection: MediaSelectionRequest | null;
  setPendingSelection: React.Dispatch<React.SetStateAction<MediaSelectionRequest | null>>;
  pendingChunkSelection: PendingChunkSelection | null;
  setPendingChunkSelection: React.Dispatch<React.SetStateAction<PendingChunkSelection | null>>;
  pendingTextScrollRatio: number | null;
  setPendingTextScrollRatio: React.Dispatch<React.SetStateAction<number | null>>;
  getMediaItem: (category: MediaCategory, id: string | null | undefined) => LiveMediaItem | null;
  updateSelection: (category: MediaCategory, intent: NavigationIntent) => void;
};

export function usePlayerPanelSelectionState({
  media,
  selectionRequest,
  memoryState,
  rememberSelection,
}: UsePlayerPanelSelectionStateArgs): UsePlayerPanelSelectionStateResult {
  const [selectedItemIds, setSelectedItemIds] = useState<Record<MediaCategory, string | null>>(() => {
    const initial: Record<MediaCategory, string | null> = {
      text: null,
      audio: null,
      video: null,
    };

    MEDIA_CATEGORIES.forEach((category) => {
      const firstItem = media[category][0];
      initial[category] = firstItem?.url ?? null;
    });

    return initial;
  });
  const [pendingSelection, setPendingSelection] = useState<MediaSelectionRequest | null>(null);
  const [pendingChunkSelection, setPendingChunkSelection] = useState<PendingChunkSelection | null>(null);
  const [pendingTextScrollRatio, setPendingTextScrollRatio] = useState<number | null>(null);
  const hasSkippedInitialRememberRef = useRef(false);

  useEffect(() => {
    if (!selectionRequest) {
      return;
    }
    setPendingSelection({
      baseId: selectionRequest.baseId,
      preferredType: selectionRequest.preferredType ?? null,
      offsetRatio: selectionRequest.offsetRatio ?? null,
      approximateTime: selectionRequest.approximateTime ?? null,
      token: selectionRequest.token ?? Date.now(),
    });
  }, [selectionRequest]);

  const mediaIndex = useMemo(() => {
    const map: Record<MediaCategory, Map<string, LiveMediaItem>> = {
      text: new Map(),
      audio: new Map(),
      video: new Map(),
    };

    MEDIA_CATEGORIES.forEach((category) => {
      media[category].forEach((item) => {
        if (item.url) {
          map[category].set(item.url, item);
        }
      });
    });

    return map;
  }, [media]);

  const getMediaItem = useCallback(
    (category: MediaCategory, id: string | null | undefined) => {
      if (!id) {
        return null;
      }
      return mediaIndex[category].get(id) ?? null;
    },
    [mediaIndex],
  );

  useEffect(() => {
    const rememberedType = memoryState.currentMediaType;
    const rememberedId = memoryState.currentMediaId;
    if (!rememberedType || !rememberedId) {
      return;
    }

    if (!mediaIndex[rememberedType].has(rememberedId)) {
      return;
    }

    setSelectedItemIds((current) => {
      if (current[rememberedType] === rememberedId) {
        return current;
      }
      return { ...current, [rememberedType]: rememberedId };
    });
  }, [memoryState.currentMediaId, memoryState.currentMediaType, mediaIndex]);

  useEffect(() => {
    setSelectedItemIds((current) => {
      let changed = false;
      const next: Record<MediaCategory, string | null> = { ...current };

      MEDIA_CATEGORIES.forEach((category) => {
        const items = media[category];
        const currentId = current[category];

        if (items.length === 0) {
          if (currentId !== null) {
            next[category] = null;
            changed = true;
          }
          return;
        }

        const hasCurrent = currentId !== null && items.some((item) => item.url === currentId);

        if (!hasCurrent) {
          next[category] = items[0].url ?? null;
          if (next[category] !== currentId) {
            changed = true;
          }
        }
      });

      return changed ? next : current;
    });
  }, [media]);

  useEffect(() => {
    const activeItemId = selectedItemIds.text;
    if (!activeItemId) {
      return;
    }

    if (
      !hasSkippedInitialRememberRef.current &&
      memoryState.currentMediaType &&
      memoryState.currentMediaId
    ) {
      hasSkippedInitialRememberRef.current = true;
      return;
    }

    const currentItem = getMediaItem('text', activeItemId);
    if (!currentItem) {
      return;
    }

    rememberSelection({ media: currentItem });
  }, [
    selectedItemIds.text,
    getMediaItem,
    rememberSelection,
    memoryState.currentMediaId,
    memoryState.currentMediaType,
  ]);

  const updateSelection = useCallback(
    (category: MediaCategory, intent: NavigationIntent) => {
      setSelectedItemIds((current) => {
        const navigableItems = media[category].filter(
          (item) => typeof item.url === 'string' && item.url.length > 0,
        );
        if (navigableItems.length === 0) {
          return current;
        }

        const currentId = current[category];
        const currentIndex = currentId
          ? navigableItems.findIndex((item) => item.url === currentId)
          : -1;

        let nextIndex = currentIndex;
        switch (intent) {
          case 'first':
            nextIndex = 0;
            break;
          case 'last':
            nextIndex = navigableItems.length - 1;
            break;
          case 'previous':
            nextIndex = currentIndex <= 0 ? 0 : currentIndex - 1;
            break;
          case 'next':
            nextIndex = currentIndex < 0 ? 0 : Math.min(currentIndex + 1, navigableItems.length - 1);
            break;
          default:
            nextIndex = currentIndex;
        }

        if (nextIndex === currentIndex && currentId !== null) {
          return current;
        }

        const nextItem = navigableItems[nextIndex];
        if (!nextItem?.url) {
          return current;
        }

        if (nextItem.url === currentId) {
          return current;
        }

        return { ...current, [category]: nextItem.url };
      });
    },
    [media],
  );

  return {
    selectedItemIds,
    setSelectedItemIds,
    pendingSelection,
    setPendingSelection,
    pendingChunkSelection,
    setPendingChunkSelection,
    pendingTextScrollRatio,
    setPendingTextScrollRatio,
    getMediaItem,
    updateSelection,
  };
}
