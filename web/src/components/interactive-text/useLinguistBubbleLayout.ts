import { useCallback, useEffect, useRef, useState } from 'react';
import type { MutableRefObject, PointerEvent as ReactPointerEvent } from 'react';
import { MY_LINGUIST_STORAGE_KEYS } from './constants';
import type { LinguistBubbleFloatingPlacement, LinguistBubbleState } from './types';
import { loadMyLinguistStored, loadMyLinguistStoredBool } from './utils';

type BubbleDragState = {
  pointerId: number;
  startX: number;
  startY: number;
  startTop: number;
  startLeft: number;
  width: number;
  height: number;
  containerRect: DOMRect;
};

type BubbleResizeState = {
  pointerId: number;
  startX: number;
  startY: number;
  startWidth: number;
  startHeight: number;
  position: { top: number; left: number };
  containerRect: DOMRect;
};

export type UseLinguistBubbleLayoutArgs = {
  anchorRectRef: MutableRefObject<DOMRect | null>;
  anchorElementRef: MutableRefObject<HTMLElement | null>;
  bubble: LinguistBubbleState | null;
};

export type UseLinguistBubbleLayoutResult = {
  bubbleRef: MutableRefObject<HTMLDivElement | null>;
  bubblePinned: boolean;
  bubbleDocked: boolean;
  bubbleDragging: boolean;
  bubbleResizing: boolean;
  floatingPlacement: LinguistBubbleFloatingPlacement;
  floatingPosition: { top: number; left: number } | null;
  floatingSize: { width: number; height: number } | null;
  onTogglePinned: () => void;
  onToggleDocked: () => void;
  onBubblePointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onBubblePointerMove: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onBubblePointerUp: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onBubblePointerCancel: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onResizeHandlePointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onResizeHandlePointerMove: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onResizeHandlePointerUp: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onResizeHandlePointerCancel: (event: ReactPointerEvent<HTMLDivElement>) => void;
  requestPositionUpdate: () => void;
  applyOpenLayout: () => void;
  resetLayout: () => void;
};

export function useLinguistBubbleLayout({
  anchorRectRef,
  anchorElementRef,
  bubble,
}: UseLinguistBubbleLayoutArgs): UseLinguistBubbleLayoutResult {
  const bubbleRef = useRef<HTMLDivElement | null>(null);
  const manualPositionRef = useRef(false);
  const dragRef = useRef<BubbleDragState | null>(null);
  const resizeRef = useRef<BubbleResizeState | null>(null);
  const positionRafRef = useRef<number | null>(null);

  const loadPinnedPosition = () => {
    const raw = loadMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.bubblePinnedPosition);
    if (!raw) {
      return null;
    }
    try {
      const value = JSON.parse(raw) as { top?: number; left?: number };
      if (
        typeof value.top === 'number' &&
        Number.isFinite(value.top) &&
        typeof value.left === 'number' &&
        Number.isFinite(value.left)
      ) {
        return { top: value.top, left: value.left };
      }
    } catch {
      return null;
    }
    return null;
  };

  const loadPinnedSize = () => {
    const raw = loadMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.bubblePinnedSize);
    if (!raw) {
      return null;
    }
    try {
      const value = JSON.parse(raw) as { width?: number; height?: number };
      if (
        typeof value.width === 'number' &&
        Number.isFinite(value.width) &&
        typeof value.height === 'number' &&
        Number.isFinite(value.height)
      ) {
        return { width: value.width, height: value.height };
      }
    } catch {
      return null;
    }
    return null;
  };

  const pinnedPositionRef = useRef<{ top: number; left: number } | null>(loadPinnedPosition());
  const pinnedSizeRef = useRef<{ width: number; height: number } | null>(loadPinnedSize());
  const legacyDockedDefault = loadMyLinguistStoredBool(
    MY_LINGUIST_STORAGE_KEYS.bubblePinned,
    true,
  );
  const [bubbleDocked, setBubbleDocked] = useState<boolean>(() =>
    loadMyLinguistStoredBool(MY_LINGUIST_STORAGE_KEYS.bubbleDocked, legacyDockedDefault),
  );
  const [bubblePinned, setBubblePinned] = useState<boolean>(() =>
    loadMyLinguistStoredBool(MY_LINGUIST_STORAGE_KEYS.bubbleLocked, false),
  );
  const [bubbleDragging, setBubbleDragging] = useState(false);
  const [bubbleResizing, setBubbleResizing] = useState(false);
  const [floatingPlacement, setFloatingPlacement] =
    useState<LinguistBubbleFloatingPlacement>('above');
  const [floatingPosition, setFloatingPosition] = useState<{
    top: number;
    left: number;
  } | null>(null);
  const [floatingSize, setFloatingSize] = useState<{
    width: number;
    height: number;
  } | null>(null);

  const resolveBubbleContainer = useCallback(() => {
    const bubbleEl = bubbleRef.current;
    if (!bubbleEl) {
      return null;
    }
    const offsetParent = bubbleEl.offsetParent;
    if (offsetParent instanceof HTMLElement) {
      return offsetParent;
    }
    return bubbleEl.parentElement instanceof HTMLElement ? bubbleEl.parentElement : null;
  }, []);

  const clampBubblePosition = useCallback(
    (
      position: { top: number; left: number },
      size: { width: number; height: number },
      containerRect: DOMRect,
    ) => {
      const margin = 12;
      const maxLeft = Math.max(margin, containerRect.width - size.width - margin);
      const maxTop = Math.max(margin, containerRect.height - size.height - margin);
      const clampedLeft = Math.min(Math.max(position.left, margin), maxLeft);
      const clampedTop = Math.min(Math.max(position.top, margin), maxTop);
      return { top: clampedTop, left: clampedLeft };
    },
    [],
  );

  const clampBubbleSize = useCallback(
    (
      size: { width: number; height: number },
      position: { top: number; left: number },
      containerRect: DOMRect,
    ) => {
      const margin = 12;
      const baseMinWidth = 240;
      const baseMinHeight = 160;
      const maxWidth = Math.max(120, containerRect.width - position.left - margin);
      const maxHeight = Math.max(120, containerRect.height - position.top - margin);
      const minWidth = Math.min(baseMinWidth, maxWidth);
      const minHeight = Math.min(baseMinHeight, maxHeight);
      const width = Math.min(Math.max(size.width, minWidth), maxWidth);
      const height = Math.min(Math.max(size.height, minHeight), maxHeight);
      return { width, height };
    },
    [],
  );

  const persistPinnedLayout = useCallback(
    (position: { top: number; left: number }, size: { width: number; height: number } | null) => {
      pinnedPositionRef.current = position;
      pinnedSizeRef.current = size;
      if (typeof window === 'undefined') {
        return;
      }
      try {
        window.localStorage.setItem(
          MY_LINGUIST_STORAGE_KEYS.bubblePinnedPosition,
          JSON.stringify({ top: Math.round(position.top), left: Math.round(position.left) }),
        );
        if (size) {
          window.localStorage.setItem(
            MY_LINGUIST_STORAGE_KEYS.bubblePinnedSize,
            JSON.stringify({ width: Math.round(size.width), height: Math.round(size.height) }),
          );
        }
      } catch {
        // ignore
      }
    },
    [],
  );

  const persistPinnedSize = useCallback((size: { width: number; height: number } | null) => {
    pinnedSizeRef.current = size;
    if (!size || typeof window === 'undefined') {
      return;
    }
    try {
      window.localStorage.setItem(
        MY_LINGUIST_STORAGE_KEYS.bubblePinnedSize,
        JSON.stringify({ width: Math.round(size.width), height: Math.round(size.height) }),
      );
    } catch {
      // ignore
    }
  }, []);

  const captureBubbleLayout = useCallback(() => {
    const bubbleEl = bubbleRef.current;
    const container = resolveBubbleContainer();
    if (!bubbleEl || !container) {
      return null;
    }
    const bubbleRect = bubbleEl.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();
    const width = Number.isFinite(bubbleRect.width) ? bubbleRect.width : null;
    const height = Number.isFinite(bubbleRect.height) ? bubbleRect.height : null;
    if (width === null || height === null) {
      return null;
    }
    const position = clampBubblePosition(
      {
        top: bubbleRect.top - containerRect.top,
        left: bubbleRect.left - containerRect.left,
      },
      { width, height },
      containerRect,
    );
    return {
      position,
      size: { width, height },
    };
  }, [clampBubblePosition, resolveBubbleContainer]);

  const cancelPositionUpdate = useCallback(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (positionRafRef.current === null) {
      return;
    }
    window.cancelAnimationFrame(positionRafRef.current);
    positionRafRef.current = null;
  }, []);

  const updateFloatingPosition = useCallback(() => {
    if (!bubble || bubbleDocked) {
      setFloatingPosition(null);
      setFloatingPlacement('above');
      return;
    }
    if (bubblePinned && manualPositionRef.current) {
      return;
    }
    if (!bubblePinned && manualPositionRef.current) {
      return;
    }

    const bubbleEl = bubbleRef.current;
    const container = resolveBubbleContainer();
    if (!container || !bubbleEl) {
      return;
    }

    const anchorEl = anchorElementRef.current;
    const anchorRect = anchorEl?.getBoundingClientRect?.() ?? anchorRectRef.current;
    if (!anchorRect) {
      return;
    }

    const containerRect = container.getBoundingClientRect();
    const bubbleRect = bubbleEl.getBoundingClientRect();
    if (!Number.isFinite(bubbleRect.width) || !Number.isFinite(bubbleRect.height)) {
      return;
    }

    const margin = 12;
    const centerX = anchorRect.left + anchorRect.width / 2 - containerRect.left;
    const halfWidth = bubbleRect.width / 2;
    const minLeft = halfWidth + margin;
    const maxLeft = Math.max(minLeft, containerRect.width - halfWidth - margin);
    const clampedCenter = Math.min(Math.max(centerX, minLeft), maxLeft);

    let placement: LinguistBubbleFloatingPlacement = 'above';
    let top = anchorRect.top - containerRect.top - bubbleRect.height - margin;
    if (!Number.isFinite(top)) {
      return;
    }
    if (top < margin) {
      placement = 'below';
      top = anchorRect.bottom - containerRect.top + margin;
    }
    top = Math.max(margin, top);

    if (bubblePinned) {
      const freePosition = clampBubblePosition(
        { top: Math.round(top), left: Math.round(clampedCenter - halfWidth) },
        { width: bubbleRect.width, height: bubbleRect.height },
        containerRect,
      );
      manualPositionRef.current = true;
      setFloatingPlacement('free');
      setFloatingSize({ width: bubbleRect.width, height: bubbleRect.height });
      setFloatingPosition(freePosition);
      persistPinnedLayout(freePosition, { width: bubbleRect.width, height: bubbleRect.height });
      return;
    }

    setFloatingPlacement(placement);
    setFloatingPosition((previous) => {
      const next = { top: Math.round(top), left: Math.round(clampedCenter) };
      if (!previous || previous.top !== next.top || previous.left !== next.left) {
        return next;
      }
      return previous;
    });
  }, [
    anchorElementRef,
    anchorRectRef,
    bubble,
    bubbleDocked,
    bubblePinned,
    clampBubblePosition,
    persistPinnedLayout,
    resolveBubbleContainer,
  ]);

  const requestPositionUpdate = useCallback(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (positionRafRef.current !== null) {
      return;
    }
    positionRafRef.current = window.requestAnimationFrame(() => {
      positionRafRef.current = null;
      updateFloatingPosition();
    });
  }, [updateFloatingPosition]);

  const applyOpenLayout = useCallback(() => {
    if (bubbleDocked) {
      manualPositionRef.current = false;
      setFloatingPosition(null);
      setFloatingSize(null);
      setFloatingPlacement('above');
      return;
    }
    if (bubblePinned && pinnedPositionRef.current) {
      manualPositionRef.current = true;
      setFloatingPlacement('free');
      setFloatingPosition(pinnedPositionRef.current);
      setFloatingSize(pinnedSizeRef.current ?? null);
      return;
    }
    manualPositionRef.current = false;
    setFloatingSize(pinnedSizeRef.current ?? null);
    setFloatingPlacement('above');
  }, [bubbleDocked, bubblePinned]);

  const resetLayout = useCallback(() => {
    manualPositionRef.current = false;
    dragRef.current = null;
    resizeRef.current = null;
    setBubbleDragging(false);
    setBubbleResizing(false);
    setFloatingPosition(null);
    setFloatingSize(null);
    setFloatingPlacement('above');
    cancelPositionUpdate();
  }, [cancelPositionUpdate]);

  const handleBubblePointerDown = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (bubbleDocked) {
        return;
      }
      if (bubbleResizing) {
        return;
      }
      if (event.button !== 0 || !event.isPrimary) {
        return;
      }
      if (!(event.target instanceof HTMLElement)) {
        return;
      }
      if (event.target.closest('button')) {
        return;
      }
      const bubbleEl = bubbleRef.current;
      const container = resolveBubbleContainer();
      if (!bubbleEl || !container) {
        return;
      }
      const bubbleRect = bubbleEl.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();
      if (!Number.isFinite(bubbleRect.width) || !Number.isFinite(bubbleRect.height)) {
        return;
      }
      const position = clampBubblePosition(
        {
          top: bubbleRect.top - containerRect.top,
          left: bubbleRect.left - containerRect.left,
        },
        { width: bubbleRect.width, height: bubbleRect.height },
        containerRect,
      );
      manualPositionRef.current = true;
      setBubbleDragging(true);
      setFloatingPlacement('free');
      setFloatingPosition(position);
      setFloatingSize({ width: bubbleRect.width, height: bubbleRect.height });
      dragRef.current = {
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        startTop: position.top,
        startLeft: position.left,
        width: bubbleRect.width,
        height: bubbleRect.height,
        containerRect,
      };
      event.preventDefault();
      event.stopPropagation();
      try {
        event.currentTarget.setPointerCapture(event.pointerId);
      } catch {
        // ignore
      }
    },
    [bubbleDocked, bubbleResizing, clampBubblePosition, resolveBubbleContainer],
  );

  const handleBubblePointerMove = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      const drag = dragRef.current;
      if (!drag || drag.pointerId !== event.pointerId) {
        return;
      }
      const deltaX = event.clientX - drag.startX;
      const deltaY = event.clientY - drag.startY;
      const position = clampBubblePosition(
        {
          top: drag.startTop + deltaY,
          left: drag.startLeft + deltaX,
        },
        { width: drag.width, height: drag.height },
        drag.containerRect,
      );
      setFloatingPosition(position);
    },
    [clampBubblePosition],
  );

  const finishBubbleDrag = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      const drag = dragRef.current;
      if (!drag || drag.pointerId !== event.pointerId) {
        return;
      }
      dragRef.current = null;
      setBubbleDragging(false);
      try {
        event.currentTarget.releasePointerCapture(event.pointerId);
      } catch {
        // ignore
      }
      if (!bubblePinned) {
        return;
      }
      const layout = captureBubbleLayout();
      if (layout) {
        persistPinnedLayout(layout.position, layout.size);
      }
    },
    [bubblePinned, captureBubbleLayout, persistPinnedLayout],
  );

  const handleBubblePointerCancel = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (!dragRef.current || dragRef.current.pointerId !== event.pointerId) {
        return;
      }
      finishBubbleDrag(event);
    },
    [finishBubbleDrag],
  );

  const handleResizeHandlePointerDown = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (bubbleDocked) {
        return;
      }
      if (event.button !== 0 || !event.isPrimary) {
        return;
      }
      const bubbleEl = bubbleRef.current;
      const container = resolveBubbleContainer();
      if (!bubbleEl || !container) {
        return;
      }
      const layout = captureBubbleLayout();
      if (!layout) {
        return;
      }
      manualPositionRef.current = true;
      dragRef.current = null;
      setBubbleDragging(false);
      setBubbleResizing(true);
      setFloatingPlacement('free');
      setFloatingPosition(layout.position);
      setFloatingSize(layout.size);
      resizeRef.current = {
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        startWidth: layout.size.width,
        startHeight: layout.size.height,
        position: layout.position,
        containerRect: container.getBoundingClientRect(),
      };
      event.preventDefault();
      event.stopPropagation();
      try {
        event.currentTarget.setPointerCapture(event.pointerId);
      } catch {
        // ignore
      }
    },
    [bubbleDocked, captureBubbleLayout, resolveBubbleContainer],
  );

  const handleResizeHandlePointerMove = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      const resize = resizeRef.current;
      if (!resize || resize.pointerId !== event.pointerId) {
        return;
      }
      const deltaX = event.clientX - resize.startX;
      const deltaY = event.clientY - resize.startY;
      const size = clampBubbleSize(
        { width: resize.startWidth + deltaX, height: resize.startHeight + deltaY },
        resize.position,
        resize.containerRect,
      );
      setFloatingSize(size);
    },
    [clampBubbleSize],
  );

  const finishResize = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      const resize = resizeRef.current;
      if (!resize || resize.pointerId !== event.pointerId) {
        return;
      }
      resizeRef.current = null;
      setBubbleResizing(false);
      try {
        event.currentTarget.releasePointerCapture(event.pointerId);
      } catch {
        // ignore
      }
      const layout = captureBubbleLayout();
      if (!layout) {
        return;
      }
      setFloatingPosition(layout.position);
      setFloatingSize(layout.size);
      if (bubblePinned) {
        persistPinnedLayout(layout.position, layout.size);
      } else {
        persistPinnedSize(layout.size);
      }
    },
    [bubblePinned, captureBubbleLayout, persistPinnedLayout, persistPinnedSize],
  );

  const handleResizeHandlePointerCancel = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (!resizeRef.current || resizeRef.current.pointerId !== event.pointerId) {
        return;
      }
      finishResize(event);
    },
    [finishResize],
  );

  const togglePinned = useCallback(() => {
    setBubblePinned((previous) => {
      const next = !previous;
      if (typeof window !== 'undefined') {
        try {
          window.localStorage.setItem(MY_LINGUIST_STORAGE_KEYS.bubbleLocked, String(next));
        } catch {
          // ignore
        }
      }
      if (next) {
        const layout = captureBubbleLayout();
        if (layout) {
          manualPositionRef.current = true;
          setFloatingPlacement('free');
          setFloatingPosition(layout.position);
          setFloatingSize(layout.size);
          persistPinnedLayout(layout.position, layout.size);
        }
      } else {
        manualPositionRef.current = false;
      }
      return next;
    });
  }, [captureBubbleLayout, persistPinnedLayout]);

  const toggleDocked = useCallback(() => {
    setBubbleDocked((previous) => {
      const next = !previous;
      if (typeof window !== 'undefined') {
        try {
          window.localStorage.setItem(MY_LINGUIST_STORAGE_KEYS.bubbleDocked, String(next));
        } catch {
          // ignore
        }
      }
      return next;
    });
  }, []);

  useEffect(() => {
    if (!bubble || bubbleDocked) {
      manualPositionRef.current = false;
      setFloatingPosition(null);
      setFloatingSize(null);
      setFloatingPlacement('above');
      return;
    }
    if (bubblePinned) {
      const storedPosition = pinnedPositionRef.current;
      const storedSize = pinnedSizeRef.current;
      if (storedPosition) {
        manualPositionRef.current = true;
        setFloatingPlacement('free');
        setFloatingPosition(storedPosition);
        setFloatingSize(storedSize ?? null);
        return;
      }
      manualPositionRef.current = false;
      requestPositionUpdate();
      return;
    }
    manualPositionRef.current = false;
    setFloatingSize(pinnedSizeRef.current ?? null);
    requestPositionUpdate();
  }, [bubble, bubbleDocked, bubblePinned, requestPositionUpdate]);

  useEffect(() => {
    if (!bubble || bubbleDocked) {
      return;
    }
    if (typeof window === 'undefined') {
      return;
    }
    const handleResize = () => {
      if (bubblePinned) {
        const layout = captureBubbleLayout();
        if (layout) {
          setFloatingPosition(layout.position);
          setFloatingSize(layout.size);
          persistPinnedLayout(layout.position, layout.size);
        }
        return;
      }
      requestPositionUpdate();
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [
    bubble,
    bubbleDocked,
    bubblePinned,
    captureBubbleLayout,
    persistPinnedLayout,
    requestPositionUpdate,
  ]);

  useEffect(() => {
    return () => {
      cancelPositionUpdate();
    };
  }, [cancelPositionUpdate]);

  return {
    bubbleRef,
    bubblePinned,
    bubbleDocked,
    bubbleDragging,
    bubbleResizing,
    floatingPlacement,
    floatingPosition,
    floatingSize,
    onTogglePinned: togglePinned,
    onToggleDocked: toggleDocked,
    onBubblePointerDown: handleBubblePointerDown,
    onBubblePointerMove: handleBubblePointerMove,
    onBubblePointerUp: finishBubbleDrag,
    onBubblePointerCancel: handleBubblePointerCancel,
    onResizeHandlePointerDown: handleResizeHandlePointerDown,
    onResizeHandlePointerMove: handleResizeHandlePointerMove,
    onResizeHandlePointerUp: finishResize,
    onResizeHandlePointerCancel: handleResizeHandlePointerCancel,
    requestPositionUpdate,
    applyOpenLayout,
    resetLayout,
  };
}
