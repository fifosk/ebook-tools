import { useCallback, useMemo } from 'react';
import type { MutableRefObject } from 'react';
import type { LiveMediaChunk, LiveMediaItem } from '../../hooks/useLiveMedia';
import type { MediaCategory, NavigationIntent } from './constants';

type UsePlayerPanelNavigationArgs = {
  mediaText: LiveMediaItem[];
  selectedTextId: string | null;
  chunks: LiveMediaChunk[];
  activeTextChunkIndex: number;
  activateTextItem: (item: LiveMediaItem | null | undefined, options?: { scrollRatio?: number; autoPlay?: boolean }) => boolean;
  activateChunk: (chunk: LiveMediaChunk | null | undefined, options?: { scrollRatio?: number; autoPlay?: boolean }) => boolean;
  updateSelection: (category: MediaCategory, intent: NavigationIntent) => void;
  inlineAudioPlayingRef: MutableRefObject<boolean>;
};

type DerivedNavigation = {
  mode: 'media' | 'chunks' | 'none';
  count: number;
  index: number;
};

type UsePlayerPanelNavigationResult = {
  derivedNavigation: DerivedNavigation;
  isFirstDisabled: boolean;
  isPreviousDisabled: boolean;
  isNextDisabled: boolean;
  isLastDisabled: boolean;
  handleNavigate: (intent: NavigationIntent, options?: { autoPlay?: boolean }) => void;
  handleNavigatePreservingPlayback: (intent: NavigationIntent) => void;
};

export function usePlayerPanelNavigation({
  mediaText,
  selectedTextId,
  chunks,
  activeTextChunkIndex,
  activateTextItem,
  activateChunk,
  updateSelection,
  inlineAudioPlayingRef,
}: UsePlayerPanelNavigationArgs): UsePlayerPanelNavigationResult {
  const navigableItems = useMemo(
    () => mediaText.filter((item) => typeof item.url === 'string' && item.url.length > 0),
    [mediaText],
  );
  const activeNavigableIndex = useMemo(() => {
    const currentId = selectedTextId;
    if (!currentId) {
      return navigableItems.length > 0 ? 0 : -1;
    }

    const matchIndex = navigableItems.findIndex((item) => item.url === currentId);
    if (matchIndex >= 0) {
      return matchIndex;
    }

    return navigableItems.length > 0 ? 0 : -1;
  }, [navigableItems, selectedTextId]);
  const derivedNavigation = useMemo<DerivedNavigation>(() => {
    if (navigableItems.length > 0) {
      return {
        mode: 'media',
        count: navigableItems.length,
        index: Math.max(0, activeNavigableIndex),
      };
    }
    if (chunks.length > 0) {
      const index = activeTextChunkIndex >= 0 ? activeTextChunkIndex : 0;
      return {
        mode: 'chunks',
        count: chunks.length,
        index: Math.max(0, Math.min(index, Math.max(chunks.length - 1, 0))),
      };
    }
    return { mode: 'none', count: 0, index: -1 };
  }, [activeNavigableIndex, activeTextChunkIndex, chunks.length, navigableItems.length]);
  const isFirstDisabled = derivedNavigation.count === 0 || derivedNavigation.index <= 0;
  const isPreviousDisabled = derivedNavigation.count === 0 || derivedNavigation.index <= 0;
  const isNextDisabled =
    derivedNavigation.count === 0 || derivedNavigation.index >= derivedNavigation.count - 1;
  const isLastDisabled =
    derivedNavigation.count === 0 || derivedNavigation.index >= derivedNavigation.count - 1;

  const handleNavigate = useCallback(
    (intent: NavigationIntent, options?: { autoPlay?: boolean }) => {
      const autoPlay = options?.autoPlay ?? true;
      if (navigableItems.length > 0) {
        const currentId = selectedTextId;
        const currentIndex = currentId
          ? navigableItems.findIndex((item) => item.url === currentId)
          : -1;
        const lastIndex = navigableItems.length - 1;
        let nextIndex = currentIndex;
        switch (intent) {
          case 'first':
            nextIndex = 0;
            break;
          case 'last':
            nextIndex = lastIndex;
            break;
          case 'previous':
            nextIndex = currentIndex <= 0 ? 0 : currentIndex - 1;
            break;
          case 'next':
            nextIndex = currentIndex < 0 ? 0 : Math.min(currentIndex + 1, lastIndex);
            break;
          default:
            nextIndex = currentIndex;
        }
        if (nextIndex === currentIndex) {
          return;
        }
        const nextItem = navigableItems[nextIndex];
        if (!nextItem) {
          return;
        }
        activateTextItem(nextItem, { autoPlay, scrollRatio: 0 });
        return;
      }

      if (chunks.length > 0) {
        const currentIndex = activeTextChunkIndex >= 0 ? activeTextChunkIndex : 0;
        const lastIndex = chunks.length - 1;
        let nextIndex = currentIndex;
        switch (intent) {
          case 'first':
            nextIndex = 0;
            break;
          case 'last':
            nextIndex = lastIndex;
            break;
          case 'previous':
            nextIndex = currentIndex <= 0 ? 0 : currentIndex - 1;
            break;
          case 'next':
            nextIndex = currentIndex < 0 ? 0 : Math.min(currentIndex + 1, lastIndex);
            break;
          default:
            nextIndex = currentIndex;
        }
        if (nextIndex === currentIndex) {
          return;
        }
        const targetChunk = chunks[nextIndex];
        if (!targetChunk) {
          return;
        }
        activateChunk(targetChunk, { autoPlay, scrollRatio: 0 });
        return;
      }

      updateSelection('text', intent);
    },
    [
      activateChunk,
      activateTextItem,
      activeTextChunkIndex,
      chunks,
      navigableItems,
      selectedTextId,
      updateSelection,
    ],
  );

  const handleNavigatePreservingPlayback = useCallback(
    (intent: NavigationIntent) => {
      handleNavigate(intent, { autoPlay: inlineAudioPlayingRef.current });
    },
    [handleNavigate, inlineAudioPlayingRef],
  );

  return {
    derivedNavigation,
    isFirstDisabled,
    isPreviousDisabled,
    isNextDisabled,
    isLastDisabled,
    handleNavigate,
    handleNavigatePreservingPlayback,
  };
}
