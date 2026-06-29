import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type MutableRefObject,
  type PointerEvent as ReactPointerEvent,
} from 'react';
import { clampOffset } from './subtitleTrackOverlayUtils';

const SUBTITLE_VERTICAL_OFFSET_KEY = 'video.subtitle.verticalOffset';

type UseSubtitleOverlayDragOptions = {
  overlayRef: MutableRefObject<HTMLDivElement | null>;
  overlayActive: boolean;
};

type UseSubtitleOverlayDragResult = {
  verticalOffset: number;
  isDraggingSubtitles: boolean;
  handleSubtitlePointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
  handleSubtitlePointerMove: (event: ReactPointerEvent<HTMLDivElement>) => void;
  handleSubtitlePointerEnd: (event: ReactPointerEvent<HTMLDivElement>) => void;
  consumeIgnoredClick: () => boolean;
};

export function useSubtitleOverlayDrag({
  overlayRef,
  overlayActive,
}: UseSubtitleOverlayDragOptions): UseSubtitleOverlayDragResult {
  const [verticalOffset, setVerticalOffset] = useState(0);
  const [isDraggingSubtitles, setIsDraggingSubtitles] = useState(false);
  const dragStateRef = useRef({
    pointerId: null as number | null,
    startX: 0,
    startY: 0,
    startOffset: 0,
    active: false,
    ignoreClick: false,
  });

  const resolveContainerHeight = useCallback(() => {
    if (overlayRef.current?.parentElement) {
      const rect = overlayRef.current.parentElement.getBoundingClientRect();
      if (rect.height > 0) {
        return rect.height;
      }
    }
    if (typeof window !== 'undefined') {
      return window.innerHeight || 0;
    }
    return 0;
  }, [overlayRef]);

  const clampSubtitleOffset = useCallback(
    (value: number) => clampOffset(value, resolveContainerHeight()),
    [resolveContainerHeight],
  );

  useEffect(() => {
    if (typeof window === 'undefined' || !overlayActive) {
      return;
    }
    const raw = window.localStorage.getItem(SUBTITLE_VERTICAL_OFFSET_KEY);
    if (!raw) {
      return;
    }
    const parsed = Number.parseFloat(raw);
    if (!Number.isFinite(parsed)) {
      return;
    }
    setVerticalOffset(clampSubtitleOffset(parsed));
  }, [clampSubtitleOffset, overlayActive]);

  const handleSubtitlePointerDown = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (!overlayActive || event.button !== 0 || !event.isPrimary) {
        return;
      }
      const target = event.target;
      if (target instanceof HTMLElement && target.closest('.player-panel__my-linguist-bubble')) {
        return;
      }
      dragStateRef.current = {
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        startOffset: verticalOffset,
        active: false,
        ignoreClick: false,
      };
    },
    [overlayActive, verticalOffset],
  );

  const handleSubtitlePointerMove = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      const state = dragStateRef.current;
      if (state.pointerId === null || event.pointerId !== state.pointerId) {
        return;
      }
      const deltaX = event.clientX - state.startX;
      const deltaY = event.clientY - state.startY;
      if (!state.active) {
        if (Math.abs(deltaY) < 10 || Math.abs(deltaY) < Math.abs(deltaX)) {
          return;
        }
        state.active = true;
        state.ignoreClick = true;
        setIsDraggingSubtitles(true);
      }
      const nextOffset = clampSubtitleOffset(state.startOffset + deltaY);
      if (Math.abs(nextOffset - verticalOffset) > 0.5) {
        setVerticalOffset(nextOffset);
      }
      event.preventDefault();
    },
    [clampSubtitleOffset, verticalOffset],
  );

  const handleSubtitlePointerEnd = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      const state = dragStateRef.current;
      if (state.pointerId === null || event.pointerId !== state.pointerId) {
        return;
      }
      if (state.active) {
        event.preventDefault();
        setIsDraggingSubtitles(false);
        if (typeof window !== 'undefined') {
          window.localStorage.setItem(SUBTITLE_VERTICAL_OFFSET_KEY, String(verticalOffset));
          window.setTimeout(() => {
            dragStateRef.current.ignoreClick = false;
          }, 0);
        } else {
          dragStateRef.current.ignoreClick = false;
        }
      }
      dragStateRef.current.pointerId = null;
      dragStateRef.current.active = false;
    },
    [verticalOffset],
  );

  const consumeIgnoredClick = useCallback(() => {
    if (!dragStateRef.current.ignoreClick) {
      return false;
    }
    dragStateRef.current.ignoreClick = false;
    return true;
  }, []);

  return {
    verticalOffset,
    isDraggingSubtitles,
    handleSubtitlePointerDown,
    handleSubtitlePointerMove,
    handleSubtitlePointerEnd,
    consumeIgnoredClick,
  };
}
