import { useCallback, useEffect } from 'react';
import type { RefObject, UIEvent } from 'react';
import type { LiveMediaItem } from '../../hooks/useLiveMedia';

type UsePlayerPanelScrollMemoryArgs = {
  textScrollRef: RefObject<HTMLDivElement | null>;
  activeTextId: string | null;
  pendingTextScrollRatio: number | null;
  setPendingTextScrollRatio: (value: number | null) => void;
  textPlaybackPosition: number;
  textPreviewUrl?: string | null;
  getMediaItem: (category: 'text', id: string | null | undefined) => LiveMediaItem | null;
  deriveBaseId: (item: LiveMediaItem | null | undefined) => string | null;
  rememberPosition: (args: { mediaId: string; mediaType: 'text'; baseId: string | null; position: number }) => void;
};

type UsePlayerPanelScrollMemoryResult = {
  handleTextScroll: (event: UIEvent<HTMLElement>) => void;
};

export function usePlayerPanelScrollMemory({
  textScrollRef,
  activeTextId,
  pendingTextScrollRatio,
  setPendingTextScrollRatio,
  textPlaybackPosition,
  textPreviewUrl,
  getMediaItem,
  deriveBaseId,
  rememberPosition,
}: UsePlayerPanelScrollMemoryArgs): UsePlayerPanelScrollMemoryResult {
  const handleTextScroll = useCallback(
    (event: UIEvent<HTMLElement>) => {
      const mediaId = activeTextId;
      if (!mediaId) {
        return;
      }

      const current = getMediaItem('text', mediaId);
      const baseId = current ? deriveBaseId(current) : null;
      const target = event.currentTarget as HTMLElement;
      rememberPosition({ mediaId, mediaType: 'text', baseId, position: target.scrollTop ?? 0 });
    },
    [activeTextId, deriveBaseId, getMediaItem, rememberPosition],
  );

  useEffect(() => {
    const mediaId = activeTextId;
    if (!mediaId) {
      return;
    }

    const element = textScrollRef.current;
    if (!element) {
      return;
    }

    if (pendingTextScrollRatio !== null) {
      const maxScroll = Math.max(element.scrollHeight - element.clientHeight, 0);
      const target = Math.min(Math.max(pendingTextScrollRatio, 0), 1) * maxScroll;
      try {
        element.scrollTop = target;
        if (typeof element.scrollTo === 'function') {
          element.scrollTo({ top: target });
        }
      } catch (error) {
        // Ignore scroll assignment failures in non-browser environments.
      }

      const current = getMediaItem('text', mediaId);
      const baseId = current ? deriveBaseId(current) : null;
      rememberPosition({ mediaId, mediaType: 'text', baseId, position: target });
      setPendingTextScrollRatio(null);
      return;
    }

    const storedPosition = textPlaybackPosition;
    if (Math.abs(element.scrollTop - storedPosition) < 1) {
      return;
    }

    try {
      element.scrollTop = storedPosition;
      if (typeof element.scrollTo === 'function') {
        element.scrollTo({ top: storedPosition });
      }
    } catch (error) {
      // Swallow assignment errors triggered by unsupported scrolling APIs in tests.
    }
  }, [
    activeTextId,
    textPlaybackPosition,
    textPreviewUrl,
    pendingTextScrollRatio,
    getMediaItem,
    deriveBaseId,
    rememberPosition,
    setPendingTextScrollRatio,
    textScrollRef,
  ]);

  return { handleTextScroll };
}
