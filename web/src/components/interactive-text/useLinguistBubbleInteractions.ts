import { useCallback, useEffect, useRef } from 'react';
import type {
  MouseEvent as ReactMouseEvent,
  MutableRefObject,
  PointerEvent as ReactPointerEvent,
} from 'react';
import type { TextPlayerVariantKind } from '../../text-player/TextPlayer';
import { DICTIONARY_LOOKUP_LONG_PRESS_MS } from './constants';
import type { LinguistBubbleNavigation } from './types';
import { normaliseTextPlayerVariant } from './utils';

export type UseLinguistBubbleInteractionsArgs = {
  containerRef: MutableRefObject<HTMLDivElement | null>;
  bubbleRef: MutableRefObject<HTMLDivElement | null>;
  audioRef: MutableRefObject<HTMLAudioElement | null>;
  inlineAudioPlayingRef: MutableRefObject<boolean>;
  dictionarySuppressSeekRef: MutableRefObject<boolean>;
  isEnabled: boolean;
  onInlineAudioPlaybackStateChange?: (state: 'playing' | 'paused') => void;
  openLinguistBubbleForRect: (
    query: string,
    rect: DOMRect,
    trigger: 'click' | 'selection',
    variantKind: TextPlayerVariantKind | null,
    anchorElement: HTMLElement | null,
    navigationOverride?: LinguistBubbleNavigation | null,
  ) => void;
};

export type UseLinguistBubbleInteractionsResult = {
  onTokenClickCapture: (event: ReactMouseEvent<HTMLDivElement>) => void;
  onPointerDownCapture: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onPointerMoveCapture: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onPointerUpCaptureWithSelection: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onPointerCancelCapture: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onBackgroundClick: (event: ReactMouseEvent<HTMLDivElement>) => void;
};

export function useLinguistBubbleInteractions({
  containerRef,
  bubbleRef,
  audioRef,
  inlineAudioPlayingRef,
  dictionarySuppressSeekRef,
  isEnabled,
  onInlineAudioPlaybackStateChange,
  openLinguistBubbleForRect,
}: UseLinguistBubbleInteractionsArgs): UseLinguistBubbleInteractionsResult {
  const selectionArmedRef = useRef(false);
  const selectionLookupPendingRef = useRef(false);
  const dictionaryPressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dictionaryPointerIdRef = useRef<number | null>(null);
  const dictionaryAwaitingResumeRef = useRef(false);
  const dictionaryWasPlayingRef = useRef(false);

  const clearDictionaryTimer = useCallback(() => {
    if (dictionaryPressTimerRef.current === null) {
      return;
    }
    clearTimeout(dictionaryPressTimerRef.current);
    dictionaryPressTimerRef.current = null;
  }, []);

  const resumeDictionaryInteraction = useCallback(() => {
    clearDictionaryTimer();
    if (!dictionaryAwaitingResumeRef.current) {
      dictionarySuppressSeekRef.current = false;
      return;
    }
    dictionaryAwaitingResumeRef.current = false;
    dictionaryPointerIdRef.current = null;
    dictionarySuppressSeekRef.current = false;
    const shouldResume = dictionaryWasPlayingRef.current;
    dictionaryWasPlayingRef.current = false;
    if (!shouldResume) {
      return;
    }
    const element = audioRef.current;
    if (!element) {
      return;
    }
    try {
      const attempt = element.play?.();
      if (attempt && typeof attempt.catch === 'function') {
        attempt.catch(() => undefined);
      }
    } catch {
      // Ignore resume failures triggered by autoplay policies.
    }
  }, [audioRef, clearDictionaryTimer, dictionarySuppressSeekRef]);

  const requestDictionaryPause = useCallback(() => {
    if (dictionaryAwaitingResumeRef.current) {
      return;
    }
    dictionarySuppressSeekRef.current = true;
    dictionaryAwaitingResumeRef.current = true;
    const element = audioRef.current;
    dictionaryWasPlayingRef.current = inlineAudioPlayingRef.current;
    if (!element) {
      return;
    }
    try {
      element.pause();
    } catch {
      // Ignore pause failures triggered by autoplay policies.
    }
  }, [audioRef, dictionarySuppressSeekRef, inlineAudioPlayingRef]);

  const isDictionaryTokenTarget = useCallback((target: EventTarget | null) => {
    if (!(target instanceof HTMLElement)) {
      return false;
    }
    return Boolean(target.closest('[data-text-player-token="true"]'));
  }, []);

  const handlePointerDownCapture = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      const bubbleEl = bubbleRef.current;
      const pointerInsideBubble =
        bubbleEl !== null && event.target instanceof Node && bubbleEl.contains(event.target);
      if (
        event.pointerType === 'mouse' &&
        event.button === 0 &&
        event.isPrimary &&
        !pointerInsideBubble
      ) {
        selectionArmedRef.current = true;
      } else {
        selectionArmedRef.current = false;
      }
      if (dictionaryAwaitingResumeRef.current) {
        resumeDictionaryInteraction();
      }
      if (
        event.pointerType !== 'mouse' ||
        event.button !== 0 ||
        !event.isPrimary ||
        !isDictionaryTokenTarget(event.target)
      ) {
        clearDictionaryTimer();
        return;
      }
      dictionaryPointerIdRef.current = event.pointerId;
      clearDictionaryTimer();
      dictionaryPressTimerRef.current = setTimeout(() => {
        dictionaryPressTimerRef.current = null;
        requestDictionaryPause();
      }, DICTIONARY_LOOKUP_LONG_PRESS_MS);
    },
    [
      bubbleRef,
      clearDictionaryTimer,
      isDictionaryTokenTarget,
      requestDictionaryPause,
      resumeDictionaryInteraction,
    ],
  );

  const handlePointerMoveCapture = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (dictionaryPressTimerRef.current === null) {
        return;
      }
      if (event.pointerId !== dictionaryPointerIdRef.current) {
        return;
      }
      if (!isDictionaryTokenTarget(event.target)) {
        clearDictionaryTimer();
      }
    },
    [clearDictionaryTimer, isDictionaryTokenTarget],
  );

  const handlePointerUpCapture = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (event.pointerId === dictionaryPointerIdRef.current) {
        clearDictionaryTimer();
      }
    },
    [clearDictionaryTimer],
  );

  const handlePointerCancelCapture = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (event.pointerId === dictionaryPointerIdRef.current) {
        clearDictionaryTimer();
      }
      selectionArmedRef.current = false;
    },
    [clearDictionaryTimer],
  );

  const toggleInlinePlayback = useCallback(() => {
    const element = audioRef.current;
    if (!element || !(element.currentSrc || element.src)) {
      return;
    }
    try {
      if (element.paused) {
        inlineAudioPlayingRef.current = true;
        onInlineAudioPlaybackStateChange?.('playing');
        const attempt = element.play?.();
        if (attempt && typeof attempt.catch === 'function') {
          attempt.catch(() => {
            inlineAudioPlayingRef.current = false;
            onInlineAudioPlaybackStateChange?.('paused');
          });
        }
      } else {
        element.pause();
        inlineAudioPlayingRef.current = false;
        onInlineAudioPlaybackStateChange?.('paused');
      }
    } catch {
      // Ignore playback toggles blocked by autoplay policies.
    }
  }, [audioRef, inlineAudioPlayingRef, onInlineAudioPlaybackStateChange]);

  const isRenderedTextTarget = useCallback((target: EventTarget | null) => {
    if (!(target instanceof HTMLElement)) {
      return false;
    }
    return Boolean(
      target.closest(
        '[data-text-player-token="true"], .player-panel__document-text, .player-panel__document-status',
      ),
    );
  }, []);

  const handleLinguistTokenClickCapture = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      if (event.button !== 0) {
        return;
      }
      const container = containerRef.current;
      if (!container) {
        return;
      }
      const bubbleEl = bubbleRef.current;
      if (bubbleEl && event.target instanceof Node && bubbleEl.contains(event.target)) {
        return;
      }

      const selection = typeof document !== 'undefined' ? document.getSelection() : null;
      if (selection && !selection.isCollapsed && selection.toString().trim()) {
        const anchorInside =
          selection.anchorNode instanceof Node ? container.contains(selection.anchorNode) : false;
        const focusInside =
          selection.focusNode instanceof Node ? container.contains(selection.focusNode) : false;
        if (anchorInside || focusInside) {
          event.stopPropagation();
          if (
            typeof (event.nativeEvent as MouseEvent | undefined)?.stopImmediatePropagation ===
            'function'
          ) {
            (event.nativeEvent as MouseEvent).stopImmediatePropagation();
          }
          if (selectionLookupPendingRef.current) {
            event.preventDefault();
          }
        }
        return;
      }

      if (event.metaKey || event.altKey || event.ctrlKey || event.shiftKey) {
        return;
      }
      if (!(event.target instanceof HTMLElement)) {
        return;
      }
      const token = event.target.closest('[data-text-player-token="true"]');
      if (!token || !(token instanceof HTMLElement) || !container.contains(token)) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      if (
        typeof (event.nativeEvent as MouseEvent | undefined)?.stopImmediatePropagation ===
        'function'
      ) {
        (event.nativeEvent as MouseEvent).stopImmediatePropagation();
      }
      const tokenText = token.textContent ?? '';
      const variantKind = normaliseTextPlayerVariant(
        (token as HTMLElement).dataset.textPlayerVariant,
      );
      const rect = token.getBoundingClientRect();
      openLinguistBubbleForRect(tokenText, rect, 'click', variantKind, token);
    },
    [bubbleRef, containerRef, openLinguistBubbleForRect],
  );

  const handleSelectionLookup = useCallback(() => {
    if (typeof document === 'undefined') {
      return;
    }
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const bubbleEl = bubbleRef.current;
    const selection = document.getSelection();
    if (!selection || selection.isCollapsed) {
      return;
    }
    const anchorNode = selection.anchorNode;
    const focusNode = selection.focusNode;
    const anchorInside = anchorNode instanceof Node ? container.contains(anchorNode) : false;
    const focusInside = focusNode instanceof Node ? container.contains(focusNode) : false;
    if (!anchorInside && !focusInside) {
      return;
    }
    if (bubbleEl) {
      const anchorInBubble = anchorNode instanceof Node ? bubbleEl.contains(anchorNode) : false;
      const focusInBubble = focusNode instanceof Node ? bubbleEl.contains(focusNode) : false;
      if (anchorInBubble || focusInBubble) {
        return;
      }
    }
    const rawText = selection.toString();
    const trimmed = rawText.trim();
    if (!trimmed) {
      return;
    }
    const variantKind = (() => {
      const candidates: Array<Node | null> = [selection.anchorNode, selection.focusNode];
      for (const node of candidates) {
        const element =
          node instanceof HTMLElement
            ? node
            : node && node.parentElement instanceof HTMLElement
              ? node.parentElement
              : null;
        if (!element) {
          continue;
        }
        const variantEl = element.closest('[data-text-player-variant]');
        if (!(variantEl instanceof HTMLElement)) {
          continue;
        }
        const kind = normaliseTextPlayerVariant(variantEl.dataset.textPlayerVariant);
        if (kind) {
          return kind;
        }
      }
      return null;
    })();
    const range = selection.rangeCount > 0 ? selection.getRangeAt(0) : null;
    let rect: DOMRect | null = null;
    if (range) {
      rect = range.getBoundingClientRect();
    }
    if (!rect || (!rect.width && !rect.height)) {
      const node =
        (focusNode instanceof HTMLElement ? focusNode : focusNode?.parentElement) ?? null;
      rect = node ? node.getBoundingClientRect() : null;
    }
    if (!rect) {
      return;
    }
    const anchorCandidate = (
      focusNode instanceof HTMLElement ? focusNode : focusNode?.parentElement
    )?.closest?.('[data-text-player-token="true"]');
    const anchorEl = anchorCandidate instanceof HTMLElement ? anchorCandidate : null;
    openLinguistBubbleForRect(trimmed, rect, 'selection', variantKind, anchorEl);
  }, [bubbleRef, containerRef, openLinguistBubbleForRect]);

  const handlePointerUpCaptureWithSelection = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      handlePointerUpCapture(event);
      const shouldLookupSelection = selectionArmedRef.current;
      selectionArmedRef.current = false;
      if (event.pointerType !== 'mouse' || event.button !== 0 || !event.isPrimary) {
        return;
      }
      if (!shouldLookupSelection) {
        return;
      }
      if (typeof window === 'undefined') {
        return;
      }
      const bubbleEl = bubbleRef.current;
      if (bubbleEl && event.target instanceof Node && bubbleEl.contains(event.target)) {
        return;
      }
      selectionLookupPendingRef.current = true;
      window.setTimeout(() => {
        handleSelectionLookup();
        selectionLookupPendingRef.current = false;
      }, 0);
    },
    [bubbleRef, handlePointerUpCapture, handleSelectionLookup],
  );

  const handleInteractiveBackgroundClick = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      if (event.button !== 0) {
        return;
      }
      if (event.metaKey || event.altKey || event.ctrlKey || event.shiftKey) {
        return;
      }
      const bubbleEl = bubbleRef.current;
      if (bubbleEl && event.target instanceof Node && bubbleEl.contains(event.target)) {
        return;
      }
      const selection = typeof document !== 'undefined' ? document.getSelection() : null;
      if (selection && !selection.isCollapsed) {
        return;
      }
      if (isRenderedTextTarget(event.target)) {
        return;
      }
      toggleInlinePlayback();
    },
    [bubbleRef, isRenderedTextTarget, toggleInlinePlayback],
  );

  useEffect(() => {
    if (!isEnabled) {
      return;
    }
    if (typeof window === 'undefined') {
      return;
    }
    const handleGlobalPointerDown = (event: PointerEvent) => {
      if (!dictionaryAwaitingResumeRef.current) {
        return;
      }
      if (event.pointerId === dictionaryPointerIdRef.current) {
        return;
      }
      resumeDictionaryInteraction();
    };
    const handleGlobalKeyDown = (event: KeyboardEvent) => {
      if (!dictionaryAwaitingResumeRef.current) {
        return;
      }
      if (event.key === 'Escape' || event.key === 'Esc') {
        resumeDictionaryInteraction();
      }
    };
    window.addEventListener('pointerdown', handleGlobalPointerDown, true);
    window.addEventListener('keydown', handleGlobalKeyDown, true);
    return () => {
      window.removeEventListener('pointerdown', handleGlobalPointerDown, true);
      window.removeEventListener('keydown', handleGlobalKeyDown, true);
    };
  }, [isEnabled, resumeDictionaryInteraction]);

  useEffect(() => {
    if (!isEnabled) {
      return;
    }
    if (typeof document === 'undefined') {
      return;
    }
    const handleSelectionChange = () => {
      if (!dictionaryAwaitingResumeRef.current) {
        return;
      }
      const selection = document.getSelection();
      if (!selection || selection.isCollapsed) {
        resumeDictionaryInteraction();
        return;
      }
      const container = containerRef.current;
      if (!container) {
        return;
      }
      const anchorNode = selection.anchorNode;
      const focusNode = selection.focusNode;
      const anchorInside =
        anchorNode instanceof Node ? container.contains(anchorNode) : false;
      const focusInside =
        focusNode instanceof Node ? container.contains(focusNode) : false;
      if (!anchorInside && !focusInside) {
        resumeDictionaryInteraction();
      }
    };
    document.addEventListener('selectionchange', handleSelectionChange);
    return () => {
      document.removeEventListener('selectionchange', handleSelectionChange);
    };
  }, [containerRef, isEnabled, resumeDictionaryInteraction]);

  useEffect(() => {
    return () => {
      clearDictionaryTimer();
      dictionaryAwaitingResumeRef.current = false;
      dictionaryPointerIdRef.current = null;
      dictionarySuppressSeekRef.current = false;
      dictionaryWasPlayingRef.current = false;
    };
  }, [clearDictionaryTimer, dictionarySuppressSeekRef]);

  return {
    onTokenClickCapture: handleLinguistTokenClickCapture,
    onPointerDownCapture: handlePointerDownCapture,
    onPointerMoveCapture: handlePointerMoveCapture,
    onPointerUpCaptureWithSelection: handlePointerUpCaptureWithSelection,
    onPointerCancelCapture: handlePointerCancelCapture,
    onBackgroundClick: handleInteractiveBackgroundClick,
  };
}
