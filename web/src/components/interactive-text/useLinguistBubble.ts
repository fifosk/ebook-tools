import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type {
  MouseEvent as ReactMouseEvent,
  MutableRefObject,
  PointerEvent as ReactPointerEvent,
} from 'react';
import { assistantLookup } from '../../api/client';
import type { AssistantLookupResponse } from '../../api/dtos';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import type { TextPlayerSentence, TextPlayerVariantKind } from '../../text-player/TextPlayer';
import { buildMyLinguistSystemPrompt } from '../../utils/myLinguistPrompt';
import { speakText } from '../../utils/ttsPlayback';
import {
  DICTIONARY_LOOKUP_LONG_PRESS_MS,
  MY_LINGUIST_BUBBLE_MAX_CHARS,
  MY_LINGUIST_DEFAULT_LLM_MODEL,
  MY_LINGUIST_DEFAULT_LOOKUP_LANGUAGE,
  MY_LINGUIST_STORAGE_KEYS,
} from './constants';
import type {
  LinguistBubbleFloatingPlacement,
  LinguistBubbleNavigation,
  LinguistBubbleState,
  SentenceFragment,
} from './types';
import {
  loadMyLinguistStored,
  loadMyLinguistStoredBool,
  normaliseTextPlayerVariant,
  sanitizeLookupQuery,
  tokenizeSentenceText,
} from './utils';

type TimelineDisplay = {
  sentences: TextPlayerSentence[];
  activeIndex: number;
  effectiveTime: number;
};

export type UseLinguistBubbleArgs = {
  containerRef: MutableRefObject<HTMLDivElement | null>;
  audioRef: MutableRefObject<HTMLAudioElement | null>;
  inlineAudioPlayingRef: MutableRefObject<boolean>;
  dictionarySuppressSeekRef: MutableRefObject<boolean>;
  enabled?: boolean;
  activeSentenceIndex: number;
  setActiveSentenceIndex: (value: number) => void;
  timelineDisplay: TimelineDisplay | null;
  rawSentences: SentenceFragment[];
  chunk: LiveMediaChunk | null;
  jobId?: string | null;
  globalInputLanguage: string;
  resolvedJobOriginalLanguage: string | null;
  resolvedJobTranslationLanguage: string | null;
  onRequestAdvanceChunk?: () => void;
  onInlineAudioPlaybackStateChange?: (state: 'playing' | 'paused') => void;
  seekInlineAudioToTime: (time: number) => void;
};

export type UseLinguistBubbleResult = {
  bubble: LinguistBubbleState | null;
  bubblePinned: boolean;
  bubbleDocked: boolean;
  bubbleDragging: boolean;
  bubbleResizing: boolean;
  bubbleRef: MutableRefObject<HTMLDivElement | null>;
  floatingPlacement: LinguistBubbleFloatingPlacement;
  floatingPosition: { top: number; left: number } | null;
  floatingSize: { width: number; height: number } | null;
  canNavigatePrev: boolean;
  canNavigateNext: boolean;
  onTogglePinned: () => void;
  onToggleDocked: () => void;
  onClose: () => void;
  onSpeak: () => void;
  onSpeakSlow: () => void;
  onNavigateWord: (delta: -1 | 1) => void;
  onBubblePointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onBubblePointerMove: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onBubblePointerUp: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onBubblePointerCancel: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onResizeHandlePointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onResizeHandlePointerMove: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onResizeHandlePointerUp: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onResizeHandlePointerCancel: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onTokenClickCapture: (event: ReactMouseEvent<HTMLDivElement>) => void;
  onPointerDownCapture: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onPointerMoveCapture: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onPointerUpCaptureWithSelection: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onPointerCancelCapture: (event: ReactPointerEvent<HTMLDivElement>) => void;
  onBackgroundClick: (event: ReactMouseEvent<HTMLDivElement>) => void;
  requestPositionUpdate: () => void;
};

export function useLinguistBubble({
  containerRef,
  audioRef,
  inlineAudioPlayingRef,
  dictionarySuppressSeekRef,
  enabled,
  activeSentenceIndex,
  setActiveSentenceIndex,
  timelineDisplay,
  rawSentences,
  chunk,
  jobId,
  globalInputLanguage,
  resolvedJobOriginalLanguage,
  resolvedJobTranslationLanguage,
  onRequestAdvanceChunk,
  onInlineAudioPlaybackStateChange,
  seekInlineAudioToTime,
}: UseLinguistBubbleArgs): UseLinguistBubbleResult {
  const isEnabled = enabled !== false;
  const linguistBubbleRef = useRef<HTMLDivElement | null>(null);
  const linguistAnchorRectRef = useRef<DOMRect | null>(null);
  const linguistAnchorElementRef = useRef<HTMLElement | null>(null);
  const linguistNavigationPendingRef = useRef<LinguistBubbleNavigation | null>(null);
  const linguistChunkAdvancePendingRef = useRef<{ variantKind: TextPlayerVariantKind } | null>(null);
  const linguistSelectionArmedRef = useRef(false);
  const linguistSelectionLookupPendingRef = useRef(false);
  const linguistRequestCounterRef = useRef(0);
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
  const linguistManualPositionRef = useRef(false);
  const linguistPinnedPositionRef = useRef<{ top: number; left: number } | null>(loadPinnedPosition());
  const linguistPinnedSizeRef = useRef<{ width: number; height: number } | null>(loadPinnedSize());
  const linguistBubbleDragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    startTop: number;
    startLeft: number;
    width: number;
    height: number;
    containerRect: DOMRect;
  } | null>(null);
  const linguistBubbleResizeRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    startWidth: number;
    startHeight: number;
    position: { top: number; left: number };
    containerRect: DOMRect;
  } | null>(null);
  const [linguistBubble, setLinguistBubble] = useState<LinguistBubbleState | null>(null);
  const legacyDockedDefault = loadMyLinguistStoredBool(MY_LINGUIST_STORAGE_KEYS.bubblePinned, true);
  const [linguistBubbleDocked, setLinguistBubbleDocked] = useState<boolean>(() =>
    loadMyLinguistStoredBool(MY_LINGUIST_STORAGE_KEYS.bubbleDocked, legacyDockedDefault),
  );
  const [linguistBubblePinned, setLinguistBubblePinned] = useState<boolean>(() =>
    loadMyLinguistStoredBool(MY_LINGUIST_STORAGE_KEYS.bubbleLocked, false),
  );
  const [linguistBubbleFloatingPlacement, setLinguistBubbleFloatingPlacement] =
    useState<LinguistBubbleFloatingPlacement>('above');
  const [linguistBubbleFloatingPosition, setLinguistBubbleFloatingPosition] = useState<{
    top: number;
    left: number;
  } | null>(null);
  const [linguistBubbleFloatingSize, setLinguistBubbleFloatingSize] = useState<{
    width: number;
    height: number;
  } | null>(null);
  const [linguistBubbleDragging, setLinguistBubbleDragging] = useState(false);
  const [linguistBubbleResizing, setLinguistBubbleResizing] = useState(false);
  const linguistBubblePositionRafRef = useRef<number | null>(null);

  useEffect(() => {
    if (!isEnabled) {
      setLinguistBubble(null);
    }
  }, [isEnabled]);

 

  const dictionaryPressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dictionaryPointerIdRef = useRef<number | null>(null);
  const dictionaryAwaitingResumeRef = useRef(false);
  const dictionaryWasPlayingRef = useRef(false);

  const resolveBubbleContainer = useCallback(() => {
    const bubbleEl = linguistBubbleRef.current;
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
    (position: { top: number; left: number }, size: { width: number; height: number }, containerRect: DOMRect) => {
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
    (size: { width: number; height: number }, position: { top: number; left: number }, containerRect: DOMRect) => {
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
      linguistPinnedPositionRef.current = position;
      linguistPinnedSizeRef.current = size;
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
    linguistPinnedSizeRef.current = size;
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
    const bubbleEl = linguistBubbleRef.current;
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
      /* Ignore resume failures triggered by autoplay policies. */
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
      /* Ignore pause failures triggered by autoplay policies. */
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
      const bubbleEl = linguistBubbleRef.current;
      const pointerInsideBubble =
        bubbleEl !== null && event.target instanceof Node && bubbleEl.contains(event.target);
      if (
        event.pointerType === 'mouse' &&
        event.button === 0 &&
        event.isPrimary &&
        !pointerInsideBubble
      ) {
        linguistSelectionArmedRef.current = true;
      } else {
        linguistSelectionArmedRef.current = false;
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
    [clearDictionaryTimer, isDictionaryTokenTarget, requestDictionaryPause, resumeDictionaryInteraction],
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
      linguistSelectionArmedRef.current = false;
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

  const closeLinguistBubble = useCallback(() => {
    linguistRequestCounterRef.current += 1;
    linguistAnchorRectRef.current = null;
    linguistAnchorElementRef.current = null;
    linguistNavigationPendingRef.current = null;
    linguistChunkAdvancePendingRef.current = null;
    linguistBubbleDragRef.current = null;
    linguistBubbleResizeRef.current = null;
    linguistManualPositionRef.current = false;
    setLinguistBubble(null);
    setLinguistBubbleDragging(false);
    setLinguistBubbleResizing(false);
    setLinguistBubbleFloatingPosition(null);
    setLinguistBubbleFloatingSize(null);
  }, []);

  const extractLinguistNavigation = useCallback(
    (
      anchorElement: HTMLElement | null,
      fallbackVariant: TextPlayerVariantKind | null,
    ): LinguistBubbleNavigation | null => {
      if (!anchorElement) {
        return null;
      }
      const variantKind =
        fallbackVariant ?? normaliseTextPlayerVariant(anchorElement.dataset.textPlayerVariant);
      if (!variantKind) {
        return null;
      }
      const rawTokenIndex = anchorElement.dataset.textPlayerTokenIndex;
      const rawSentenceIndex =
        anchorElement.dataset.textPlayerSentenceIndex ??
        anchorElement.closest('[data-sentence-index]')?.getAttribute('data-sentence-index') ??
        null;
      const tokenIndex = rawTokenIndex ? Number(rawTokenIndex) : Number.NaN;
      const sentenceIndex = rawSentenceIndex ? Number(rawSentenceIndex) : Number.NaN;
      if (!Number.isFinite(tokenIndex) || !Number.isFinite(sentenceIndex)) {
        return null;
      }
      return {
        sentenceIndex,
        tokenIndex,
        variantKind,
      };
    },
    [],
  );

  const openLinguistBubbleForRect = useCallback(
    (
      query: string,
      rect: DOMRect,
      trigger: 'click' | 'selection',
      variantKind: TextPlayerVariantKind | null,
      anchorElement: HTMLElement | null,
      navigationOverride: LinguistBubbleNavigation | null = null,
    ) => {
      if (!isEnabled) {
        return;
      }
      const cleanedQuery = sanitizeLookupQuery(query);
      if (!cleanedQuery) {
        return;
      }
      linguistAnchorRectRef.current = rect;
      linguistAnchorElementRef.current = anchorElement;
      const inlineAudioEl = audioRef.current;
      if (inlineAudioEl && !inlineAudioEl.paused) {
        try {
          inlineAudioEl.pause();
        } catch {
          // Ignore pause failures triggered by autoplay policies.
        }
      }
      const slicedQuery =
        cleanedQuery.length > MY_LINGUIST_BUBBLE_MAX_CHARS
          ? `${cleanedQuery.slice(0, MY_LINGUIST_BUBBLE_MAX_CHARS)}…`
          : cleanedQuery;

      const storedInputLanguage =
        loadMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.inputLanguage) ?? globalInputLanguage;
      const storedLookupLanguage =
        loadMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.lookupLanguage) ?? MY_LINGUIST_DEFAULT_LOOKUP_LANGUAGE;
      const storedModel = loadMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.llmModel, { allowEmpty: true });
      const storedPrompt = loadMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.systemPrompt, { allowEmpty: true });

      const jobPreferredInputLanguage =
        variantKind === 'translation'
          ? resolvedJobTranslationLanguage
          : variantKind === 'original' || variantKind === 'translit'
            ? resolvedJobOriginalLanguage
            : null;
      const resolvedInputLanguage = (jobPreferredInputLanguage ?? storedInputLanguage).trim() || globalInputLanguage;
      const resolvedLookupLanguage = storedLookupLanguage.trim() || MY_LINGUIST_DEFAULT_LOOKUP_LANGUAGE;
      const resolvedModel =
        storedModel === null ? MY_LINGUIST_DEFAULT_LLM_MODEL : storedModel.trim() ? storedModel.trim() : null;
      const modelLabel = resolvedModel ?? 'Auto';
      const resolvedPrompt =
        storedPrompt && storedPrompt.trim()
          ? storedPrompt.trim()
          : buildMyLinguistSystemPrompt(resolvedInputLanguage, resolvedLookupLanguage);

      const requestId = (linguistRequestCounterRef.current += 1);
      const navigation =
        navigationOverride ?? extractLinguistNavigation(anchorElement, variantKind);
      setLinguistBubble({
        query: slicedQuery,
        fullQuery: cleanedQuery,
        status: 'loading',
        answer: 'Lookup in progress…',
        modelLabel,
        ttsLanguage: resolvedInputLanguage,
        ttsStatus: 'idle',
        navigation,
      });

      if (linguistBubbleDocked) {
        linguistManualPositionRef.current = false;
        setLinguistBubbleFloatingPosition(null);
        setLinguistBubbleFloatingSize(null);
        setLinguistBubbleFloatingPlacement('above');
      } else if (linguistBubblePinned && linguistPinnedPositionRef.current) {
        linguistManualPositionRef.current = true;
        setLinguistBubbleFloatingPlacement('free');
        setLinguistBubbleFloatingPosition(linguistPinnedPositionRef.current);
        setLinguistBubbleFloatingSize(linguistPinnedSizeRef.current ?? null);
      } else if (linguistBubblePinned) {
        linguistManualPositionRef.current = false;
        setLinguistBubbleFloatingSize(linguistPinnedSizeRef.current ?? null);
        setLinguistBubbleFloatingPlacement('above');
      } else {
        linguistManualPositionRef.current = false;
        setLinguistBubbleFloatingSize(linguistPinnedSizeRef.current ?? null);
        setLinguistBubbleFloatingPlacement('above');
      }

      const page = typeof window !== 'undefined' ? window.location.pathname : null;
      void assistantLookup({
        query: slicedQuery,
        input_language: resolvedInputLanguage,
        lookup_language: resolvedLookupLanguage,
        llm_model: resolvedModel,
        system_prompt: resolvedPrompt,
        context: {
          source: 'my_linguist',
          page,
          job_id: jobId,
          selection_text: trigger === 'selection' ? slicedQuery : null,
          metadata: {
            ui: 'interactive_bubble',
            trigger,
            chunk_id: chunk?.chunkId ?? null,
          },
        },
      })
        .then((response: AssistantLookupResponse) => {
          if (linguistRequestCounterRef.current !== requestId) {
            return;
          }
          setLinguistBubble((previous) => {
            if (!previous) {
              return previous;
            }
            return {
              ...previous,
              status: 'ready',
              answer: response.answer,
              ttsStatus: 'loading',
            };
          });
          void speakText({ text: cleanedQuery, language: resolvedInputLanguage })
            .then(() => {
              if (linguistRequestCounterRef.current !== requestId) {
                return;
              }
              setLinguistBubble((previous) => {
                if (!previous) {
                  return previous;
                }
                return { ...previous, ttsStatus: 'ready' };
              });
            })
            .catch(() => {
              if (linguistRequestCounterRef.current !== requestId) {
                return;
              }
              setLinguistBubble((previous) => {
                if (!previous) {
                  return previous;
                }
                return { ...previous, ttsStatus: 'error' };
              });
            });
        })
        .catch((error: unknown) => {
          if (linguistRequestCounterRef.current !== requestId) {
            return;
          }
          const message = error instanceof Error ? error.message : 'Unable to reach MyLinguist.';
          setLinguistBubble((previous) => {
            if (!previous) {
              return previous;
            }
            return {
              ...previous,
              status: 'error',
              answer: `Error: ${message}`,
              ttsStatus: 'idle',
            };
          });
        });
    },
    [
      audioRef,
      chunk?.chunkId,
      extractLinguistNavigation,
      globalInputLanguage,
      isEnabled,
      jobId,
      linguistBubbleDocked,
      linguistBubblePinned,
      resolvedJobOriginalLanguage,
      resolvedJobTranslationLanguage,
    ],
  );

  const handleLinguistSpeak = useCallback(() => {
    const bubble = linguistBubble;
    if (!bubble) {
      return;
    }
    const text = bubble.fullQuery.trim();
    if (!text || bubble.ttsStatus === 'loading') {
      return;
    }
    const requestId = linguistRequestCounterRef.current;
    setLinguistBubble((previous) => {
      if (!previous) {
        return previous;
      }
      return { ...previous, ttsStatus: 'loading' };
    });
    void speakText({ text, language: bubble.ttsLanguage })
      .then(() => {
        if (linguistRequestCounterRef.current !== requestId) {
          return;
        }
        setLinguistBubble((previous) => {
          if (!previous) {
            return previous;
          }
          return { ...previous, ttsStatus: 'ready' };
        });
      })
      .catch(() => {
        if (linguistRequestCounterRef.current !== requestId) {
          return;
        }
        setLinguistBubble((previous) => {
          if (!previous) {
            return previous;
          }
          return { ...previous, ttsStatus: 'error' };
        });
      });
  }, [linguistBubble]);

  const handleLinguistSpeakSlow = useCallback(() => {
    const bubble = linguistBubble;
    if (!bubble) {
      return;
    }
    const text = bubble.fullQuery.trim();
    if (!text || bubble.ttsStatus === 'loading') {
      return;
    }
    const requestId = linguistRequestCounterRef.current;
    setLinguistBubble((previous) => {
      if (!previous) {
        return previous;
      }
      return { ...previous, ttsStatus: 'loading' };
    });
    void speakText({ text, language: bubble.ttsLanguage, playbackRate: 0.5 })
      .then(() => {
        if (linguistRequestCounterRef.current !== requestId) {
          return;
        }
        setLinguistBubble((previous) => {
          if (!previous) {
            return previous;
          }
          return { ...previous, ttsStatus: 'ready' };
        });
      })
      .catch(() => {
        if (linguistRequestCounterRef.current !== requestId) {
          return;
        }
        setLinguistBubble((previous) => {
          if (!previous) {
            return previous;
          }
          return { ...previous, ttsStatus: 'error' };
        });
      });
  }, [linguistBubble]);

  const handleLinguistTokenClickCapture = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      if (event.button !== 0) {
        return;
      }
      const container = containerRef.current;
      if (!container) {
        return;
      }
      const bubbleEl = linguistBubbleRef.current;
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
          if (typeof (event.nativeEvent as MouseEvent | undefined)?.stopImmediatePropagation === 'function') {
            (event.nativeEvent as MouseEvent).stopImmediatePropagation();
          }
          if (linguistSelectionLookupPendingRef.current) {
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
      if (typeof (event.nativeEvent as MouseEvent | undefined)?.stopImmediatePropagation === 'function') {
        (event.nativeEvent as MouseEvent).stopImmediatePropagation();
      }
      const tokenText = token.textContent ?? '';
      const variantKind = normaliseTextPlayerVariant((token as HTMLElement).dataset.textPlayerVariant);
      const rect = token.getBoundingClientRect();
      openLinguistBubbleForRect(tokenText, rect, 'click', variantKind, token);
    },
    [containerRef, openLinguistBubbleForRect],
  );

  const handleSelectionLookup = useCallback(() => {
    if (typeof document === 'undefined') {
      return;
    }
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const bubbleEl = linguistBubbleRef.current;
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
      const node = (focusNode instanceof HTMLElement ? focusNode : focusNode?.parentElement) ?? null;
      rect = node ? node.getBoundingClientRect() : null;
    }
    if (!rect) {
      return;
    }
    const anchorCandidate = (focusNode instanceof HTMLElement ? focusNode : focusNode?.parentElement)?.closest?.(
      '[data-text-player-token="true"]',
    );
    const anchorEl = anchorCandidate instanceof HTMLElement ? anchorCandidate : null;
    openLinguistBubbleForRect(trimmed, rect, 'selection', variantKind, anchorEl);
  }, [containerRef, openLinguistBubbleForRect]);

  const handleBubblePointerDown = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (linguistBubbleDocked) {
        return;
      }
      if (linguistBubbleResizing) {
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
      const bubbleEl = linguistBubbleRef.current;
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
      linguistManualPositionRef.current = true;
      setLinguistBubbleDragging(true);
      setLinguistBubbleFloatingPlacement('free');
      setLinguistBubbleFloatingPosition(position);
      setLinguistBubbleFloatingSize({ width: bubbleRect.width, height: bubbleRect.height });
      linguistBubbleDragRef.current = {
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
    [clampBubblePosition, linguistBubbleDocked, linguistBubbleResizing, resolveBubbleContainer],
  );

  const handleBubblePointerMove = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      const drag = linguistBubbleDragRef.current;
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
      setLinguistBubbleFloatingPosition(position);
    },
    [clampBubblePosition],
  );

  const finishBubbleDrag = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      const drag = linguistBubbleDragRef.current;
      if (!drag || drag.pointerId !== event.pointerId) {
        return;
      }
      linguistBubbleDragRef.current = null;
      setLinguistBubbleDragging(false);
      try {
        event.currentTarget.releasePointerCapture(event.pointerId);
      } catch {
        // ignore
      }
      if (!linguistBubblePinned) {
        return;
      }
      const layout = captureBubbleLayout();
      if (layout) {
        persistPinnedLayout(layout.position, layout.size);
      }
    },
    [captureBubbleLayout, linguistBubblePinned, persistPinnedLayout],
  );

  const handleBubblePointerCancel = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (!linguistBubbleDragRef.current || linguistBubbleDragRef.current.pointerId !== event.pointerId) {
        return;
      }
      finishBubbleDrag(event);
    },
    [finishBubbleDrag],
  );

  const handleResizeHandlePointerDown = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (linguistBubbleDocked) {
        return;
      }
      if (event.button !== 0 || !event.isPrimary) {
        return;
      }
      const bubbleEl = linguistBubbleRef.current;
      const container = resolveBubbleContainer();
      if (!bubbleEl || !container) {
        return;
      }
      const layout = captureBubbleLayout();
      if (!layout) {
        return;
      }
      linguistManualPositionRef.current = true;
      linguistBubbleDragRef.current = null;
      setLinguistBubbleDragging(false);
      setLinguistBubbleResizing(true);
      setLinguistBubbleFloatingPlacement('free');
      setLinguistBubbleFloatingPosition(layout.position);
      setLinguistBubbleFloatingSize(layout.size);
      linguistBubbleResizeRef.current = {
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
    [captureBubbleLayout, linguistBubbleDocked, resolveBubbleContainer],
  );

  const handleResizeHandlePointerMove = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      const resize = linguistBubbleResizeRef.current;
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
      setLinguistBubbleFloatingSize(size);
    },
    [clampBubbleSize],
  );

  const finishResize = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      const resize = linguistBubbleResizeRef.current;
      if (!resize || resize.pointerId !== event.pointerId) {
        return;
      }
      linguistBubbleResizeRef.current = null;
      setLinguistBubbleResizing(false);
      try {
        event.currentTarget.releasePointerCapture(event.pointerId);
      } catch {
        // ignore
      }
      const layout = captureBubbleLayout();
      if (!layout) {
        return;
      }
      setLinguistBubbleFloatingPosition(layout.position);
      setLinguistBubbleFloatingSize(layout.size);
      if (linguistBubblePinned) {
        persistPinnedLayout(layout.position, layout.size);
      } else {
        persistPinnedSize(layout.size);
      }
    },
    [captureBubbleLayout, linguistBubblePinned, persistPinnedLayout, persistPinnedSize],
  );

  const handleResizeHandlePointerCancel = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (!linguistBubbleResizeRef.current || linguistBubbleResizeRef.current.pointerId !== event.pointerId) {
        return;
      }
      finishResize(event);
    },
    [finishResize],
  );

  const toggleLinguistBubblePinned = useCallback(() => {
    setLinguistBubblePinned((previous) => {
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
          linguistManualPositionRef.current = true;
          setLinguistBubbleFloatingPlacement('free');
          setLinguistBubbleFloatingPosition(layout.position);
          setLinguistBubbleFloatingSize(layout.size);
          persistPinnedLayout(layout.position, layout.size);
        }
      } else {
        linguistManualPositionRef.current = false;
      }
      return next;
    });
  }, [captureBubbleLayout, persistPinnedLayout]);

  const toggleLinguistBubbleDocked = useCallback(() => {
    setLinguistBubbleDocked((previous) => {
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

  const updateLinguistBubbleFloatingPosition = useCallback(() => {
    if (!linguistBubble || linguistBubbleDocked) {
      setLinguistBubbleFloatingPosition(null);
      setLinguistBubbleFloatingPlacement('above');
      return;
    }
    if (linguistBubblePinned && linguistManualPositionRef.current) {
      return;
    }
    if (!linguistBubblePinned && linguistManualPositionRef.current) {
      return;
    }

    const bubbleEl = linguistBubbleRef.current;
    const container = resolveBubbleContainer();
    if (!container || !bubbleEl) {
      return;
    }

    const anchorEl = linguistAnchorElementRef.current;
    const anchorRect = anchorEl?.getBoundingClientRect?.() ?? linguistAnchorRectRef.current;
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

    if (linguistBubblePinned) {
      const freePosition = clampBubblePosition(
        { top: Math.round(top), left: Math.round(clampedCenter - halfWidth) },
        { width: bubbleRect.width, height: bubbleRect.height },
        containerRect,
      );
      linguistManualPositionRef.current = true;
      setLinguistBubbleFloatingPlacement('free');
      setLinguistBubbleFloatingSize({ width: bubbleRect.width, height: bubbleRect.height });
      setLinguistBubbleFloatingPosition(freePosition);
      persistPinnedLayout(freePosition, { width: bubbleRect.width, height: bubbleRect.height });
      return;
    }

    setLinguistBubbleFloatingPlacement(placement);
    setLinguistBubbleFloatingPosition((previous) => {
      const next = { top: Math.round(top), left: Math.round(clampedCenter) };
      if (!previous || previous.top !== next.top || previous.left !== next.left) {
        return next;
      }
      return previous;
    });
  }, [
    clampBubblePosition,
    linguistBubble,
    linguistBubbleDocked,
    linguistBubblePinned,
    persistPinnedLayout,
    resolveBubbleContainer,
  ]);

  const requestLinguistBubblePositionUpdate = useCallback(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (linguistBubblePositionRafRef.current !== null) {
      return;
    }
    linguistBubblePositionRafRef.current = window.requestAnimationFrame(() => {
      linguistBubblePositionRafRef.current = null;
      updateLinguistBubbleFloatingPosition();
    });
  }, [updateLinguistBubbleFloatingPosition]);

  const handlePointerUpCaptureWithSelection = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      handlePointerUpCapture(event);
      const shouldLookupSelection = linguistSelectionArmedRef.current;
      linguistSelectionArmedRef.current = false;
      if (event.pointerType !== 'mouse' || event.button !== 0 || !event.isPrimary) {
        return;
      }
      if (!shouldLookupSelection) {
        return;
      }
      if (typeof window === 'undefined') {
        return;
      }
      const bubbleEl = linguistBubbleRef.current;
      if (bubbleEl && event.target instanceof Node && bubbleEl.contains(event.target)) {
        return;
      }
      linguistSelectionLookupPendingRef.current = true;
      window.setTimeout(() => {
        handleSelectionLookup();
        linguistSelectionLookupPendingRef.current = false;
      }, 0);
    },
    [handlePointerUpCapture, handleSelectionLookup],
  );

  const handleInteractiveBackgroundClick = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      if (event.button !== 0) {
        return;
      }
      if (event.metaKey || event.altKey || event.ctrlKey || event.shiftKey) {
        return;
      }
      const bubbleEl = linguistBubbleRef.current;
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
    [isRenderedTextTarget, toggleInlinePlayback],
  );

  useEffect(() => {
    if (!linguistBubble || linguistBubbleDocked) {
      linguistManualPositionRef.current = false;
      setLinguistBubbleFloatingPosition(null);
      setLinguistBubbleFloatingSize(null);
      setLinguistBubbleFloatingPlacement('above');
      return;
    }
    if (linguistBubblePinned) {
      const storedPosition = linguistPinnedPositionRef.current;
      const storedSize = linguistPinnedSizeRef.current;
      if (storedPosition) {
        linguistManualPositionRef.current = true;
        setLinguistBubbleFloatingPlacement('free');
        setLinguistBubbleFloatingPosition(storedPosition);
        setLinguistBubbleFloatingSize(storedSize ?? null);
        return;
      }
      linguistManualPositionRef.current = false;
      requestLinguistBubblePositionUpdate();
      return;
    }
    linguistManualPositionRef.current = false;
    setLinguistBubbleFloatingSize(linguistPinnedSizeRef.current ?? null);
    requestLinguistBubblePositionUpdate();
  }, [
    linguistBubble,
    linguistBubbleDocked,
    linguistBubblePinned,
    requestLinguistBubblePositionUpdate,
  ]);

  useEffect(() => {
    if (!linguistBubble || linguistBubbleDocked) {
      return;
    }
    if (typeof window === 'undefined') {
      return;
    }
    const handleResize = () => {
      if (linguistBubblePinned) {
        const layout = captureBubbleLayout();
        if (layout) {
          setLinguistBubbleFloatingPosition(layout.position);
          setLinguistBubbleFloatingSize(layout.size);
          persistPinnedLayout(layout.position, layout.size);
        }
        return;
      }
      requestLinguistBubblePositionUpdate();
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [
    captureBubbleLayout,
    linguistBubble,
    linguistBubbleDocked,
    linguistBubblePinned,
    persistPinnedLayout,
    requestLinguistBubblePositionUpdate,
  ]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    return () => {
      if (linguistBubblePositionRafRef.current !== null) {
        window.cancelAnimationFrame(linguistBubblePositionRafRef.current);
        linguistBubblePositionRafRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!linguistBubble) {
      return;
    }
    if (typeof window === 'undefined') {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' || event.key === 'Esc') {
        closeLinguistBubble();
      }
    };
    const handlePointerDown = (event: PointerEvent) => {
      const bubbleEl = linguistBubbleRef.current;
      if (!bubbleEl) {
        closeLinguistBubble();
        return;
      }
      const target = event.target;
      if (target instanceof Node && bubbleEl.contains(target)) {
        return;
      }
      closeLinguistBubble();
    };
    window.addEventListener('keydown', handleKeyDown, true);
    window.addEventListener('pointerdown', handlePointerDown, true);
    return () => {
      window.removeEventListener('keydown', handleKeyDown, true);
      window.removeEventListener('pointerdown', handlePointerDown, true);
    };
  }, [closeLinguistBubble, linguistBubble]);

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

  const linguistSentenceOrder = useMemo(() => {
    if (timelineDisplay?.sentences && timelineDisplay.sentences.length > 0) {
      return timelineDisplay.sentences.map((sentence) => sentence.index);
    }
    if (chunk?.sentences && chunk.sentences.length > 0) {
      return chunk.sentences.map((_sentence, index) => index);
    }
    return rawSentences.map((sentence) => sentence.index);
  }, [chunk?.sentences, rawSentences, timelineDisplay?.sentences]);

  const linguistSentencePositionByIndex = useMemo(() => {
    const map = new Map<number, number>();
    linguistSentenceOrder.forEach((sentenceIndex, position) => {
      map.set(sentenceIndex, position);
    });
    return map;
  }, [linguistSentenceOrder]);

  const tokensForSentence = useCallback(
    (sentenceIndex: number, variantKind: TextPlayerVariantKind): string[] => {
      if (timelineDisplay?.sentences && timelineDisplay.sentences.length > 0) {
        const sentence = timelineDisplay.sentences.find((entry) => entry.index === sentenceIndex);
        const variant = sentence?.variants?.find((candidate) => candidate.baseClass === variantKind) ?? null;
        return variant?.tokens ?? [];
      }

      if (chunk?.sentences && chunk.sentences.length > 0) {
        const sentence = chunk.sentences[sentenceIndex];
        if (!sentence) {
          return [];
        }
        if (variantKind === 'translation') {
          return tokenizeSentenceText(sentence.translation?.text ?? null);
        }
        if (variantKind === 'translit') {
          return tokenizeSentenceText(sentence.transliteration?.text ?? null);
        }
        return tokenizeSentenceText(sentence.original?.text ?? null);
      }

      const position = linguistSentencePositionByIndex.get(sentenceIndex);
      if (position === undefined) {
        return [];
      }
      const sentence = rawSentences[position];
      if (variantKind === 'translation') {
        return tokenizeSentenceText(sentence.translation);
      }
      if (variantKind === 'translit') {
        return tokenizeSentenceText(sentence.transliteration);
      }
      return tokenizeSentenceText(sentence.text);
    },
    [chunk?.sentences, linguistSentencePositionByIndex, rawSentences, timelineDisplay?.sentences],
  );

  const seekTimeForNavigation = useCallback(
    (navigation: LinguistBubbleNavigation): number | null => {
      if (!timelineDisplay?.sentences || timelineDisplay.sentences.length === 0) {
        return null;
      }
      const sentence = timelineDisplay.sentences.find((entry) => entry.index === navigation.sentenceIndex);
      const variant = sentence?.variants?.find((candidate) => candidate.baseClass === navigation.variantKind) ?? null;
      const times = variant?.seekTimes ?? null;
      if (!times || navigation.tokenIndex < 0 || navigation.tokenIndex >= times.length) {
        return null;
      }
      const time = times[navigation.tokenIndex];
      return typeof time === 'number' && Number.isFinite(time) ? time : null;
    },
    [timelineDisplay?.sentences],
  );

  const resolveRelativeLinguistNavigation = useCallback(
    (current: LinguistBubbleNavigation, delta: -1 | 1): LinguistBubbleNavigation | null => {
      const startPosition = linguistSentencePositionByIndex.get(current.sentenceIndex);
      if (startPosition === undefined) {
        return null;
      }
      const variantKind = current.variantKind;
      const currentTokens = tokensForSentence(current.sentenceIndex, variantKind);
      if (currentTokens.length === 0) {
        return null;
      }

      let sentencePosition = startPosition;
      let tokenIndex = current.tokenIndex + delta;

      if (tokenIndex < 0) {
        sentencePosition -= 1;
        while (sentencePosition >= 0) {
          const nextSentenceIndex = linguistSentenceOrder[sentencePosition];
          const tokens = tokensForSentence(nextSentenceIndex, variantKind);
          if (tokens.length > 0) {
            tokenIndex = tokens.length - 1;
            return { sentenceIndex: nextSentenceIndex, tokenIndex, variantKind };
          }
          sentencePosition -= 1;
        }
        return null;
      }

      if (tokenIndex >= currentTokens.length) {
        sentencePosition += 1;
        while (sentencePosition < linguistSentenceOrder.length) {
          const nextSentenceIndex = linguistSentenceOrder[sentencePosition];
          const tokens = tokensForSentence(nextSentenceIndex, variantKind);
          if (tokens.length > 0) {
            tokenIndex = 0;
            return { sentenceIndex: nextSentenceIndex, tokenIndex, variantKind };
          }
          sentencePosition += 1;
        }
        return null;
      }

      return {
        sentenceIndex: current.sentenceIndex,
        tokenIndex,
        variantKind,
      };
    },
    [linguistSentenceOrder, linguistSentencePositionByIndex, tokensForSentence],
  );

  const findTextPlayerTokenElement = useCallback((navigation: LinguistBubbleNavigation): HTMLElement | null => {
    const container = containerRef.current;
    if (!container) {
      return null;
    }
    const selector = [
      `[data-sentence-index="${navigation.sentenceIndex}"]`,
      `[data-text-player-token="true"][data-text-player-variant="${navigation.variantKind}"][data-text-player-token-index="${navigation.tokenIndex}"]`,
    ].join(' ');
    const match = container.querySelector(selector);
    return match instanceof HTMLElement ? match : null;
  }, [containerRef]);

  const navigateLinguistWord = useCallback(
    (delta: -1 | 1) => {
      const current = linguistBubble?.navigation ?? null;
      if (!linguistBubble || !current) {
        return;
      }
      const target = resolveRelativeLinguistNavigation(current, delta);
      if (!target) {
        if (delta === 1 && onRequestAdvanceChunk) {
          linguistChunkAdvancePendingRef.current = { variantKind: current.variantKind };
          onRequestAdvanceChunk();
        }
        return;
      }

      const targetTokens = tokensForSentence(target.sentenceIndex, target.variantKind);
      const rawWord = targetTokens[target.tokenIndex] ?? '';
      if (!rawWord.trim()) {
        return;
      }

      const seekTime = seekTimeForNavigation(target);

      const tokenEl = findTextPlayerTokenElement(target);
      if (tokenEl) {
        openLinguistBubbleForRect(
          rawWord,
          tokenEl.getBoundingClientRect(),
          'click',
          target.variantKind,
          tokenEl,
        );
        if (seekTime !== null) {
          seekInlineAudioToTime(seekTime);
        }
        return;
      }

      const container = containerRef.current;
      const fallbackRect = linguistAnchorRectRef.current ?? container?.getBoundingClientRect();
      if (!fallbackRect) {
        return;
      }

      // Kick off the lookup now, then move the text player if needed. We'll re-anchor to the token once rendered.
      openLinguistBubbleForRect(rawWord, fallbackRect, 'click', target.variantKind, null, target);
      if (seekTime !== null) {
        seekInlineAudioToTime(seekTime);
      }
      if (target.sentenceIndex !== activeSentenceIndex) {
        linguistNavigationPendingRef.current = target;
        setActiveSentenceIndex(target.sentenceIndex);
      }
    },
    [
      activeSentenceIndex,
      findTextPlayerTokenElement,
      linguistBubble,
      onRequestAdvanceChunk,
      openLinguistBubbleForRect,
      resolveRelativeLinguistNavigation,
      seekInlineAudioToTime,
      seekTimeForNavigation,
      setActiveSentenceIndex,
      tokensForSentence,
    ],
  );

  const linguistCanNavigatePrev = useMemo(() => {
    const current = linguistBubble?.navigation ?? null;
    if (!current) {
      return false;
    }
    return resolveRelativeLinguistNavigation(current, -1) !== null;
  }, [linguistBubble?.navigation, resolveRelativeLinguistNavigation]);

  const linguistCanNavigateNext = useMemo(() => {
    const current = linguistBubble?.navigation ?? null;
    if (!current) {
      return false;
    }
    return resolveRelativeLinguistNavigation(current, 1) !== null;
  }, [linguistBubble?.navigation, resolveRelativeLinguistNavigation]);

  useEffect(() => {
    const pending = linguistNavigationPendingRef.current;
    if (!pending || !linguistBubble || linguistBubblePinned || linguistBubbleDocked) {
      return;
    }
    const tokenEl = findTextPlayerTokenElement(pending);
    if (!tokenEl) {
      return;
    }
    linguistNavigationPendingRef.current = null;
    linguistAnchorElementRef.current = tokenEl;
    linguistAnchorRectRef.current = tokenEl.getBoundingClientRect();
    requestLinguistBubblePositionUpdate();
  }, [
    findTextPlayerTokenElement,
    linguistBubble,
    linguistBubblePinned,
    linguistBubbleDocked,
    requestLinguistBubblePositionUpdate,
  ]);

  useEffect(() => {
    const pendingAdvance = linguistChunkAdvancePendingRef.current;
    if (!pendingAdvance || !linguistBubble) {
      return;
    }

    const variantKind = pendingAdvance.variantKind;
    let sentenceIndex: number | null = null;
    for (const candidate of linguistSentenceOrder) {
      const tokens = tokensForSentence(candidate, variantKind);
      if (tokens.length > 0) {
        sentenceIndex = candidate;
        break;
      }
    }

    linguistChunkAdvancePendingRef.current = null;
    if (sentenceIndex === null) {
      return;
    }

    const tokens = tokensForSentence(sentenceIndex, variantKind);
    const rawWord = tokens[0] ?? '';
    if (!rawWord.trim()) {
      return;
    }

    const navigation: LinguistBubbleNavigation = {
      sentenceIndex,
      tokenIndex: 0,
      variantKind,
    };

    const seekTime = seekTimeForNavigation(navigation);
    if (seekTime !== null) {
      seekInlineAudioToTime(seekTime);
    }

    const container = containerRef.current;
    const fallbackRect = container?.getBoundingClientRect() ?? linguistAnchorRectRef.current;
    if (!fallbackRect) {
      return;
    }

    openLinguistBubbleForRect(rawWord, fallbackRect, 'click', variantKind, null, navigation);
    if (sentenceIndex !== activeSentenceIndex) {
      setActiveSentenceIndex(sentenceIndex);
      if (!linguistBubblePinned && !linguistBubbleDocked) {
        linguistNavigationPendingRef.current = navigation;
      }
    }
  }, [
    activeSentenceIndex,
    containerRef,
    linguistBubble,
    linguistBubblePinned,
    linguistBubbleDocked,
    linguistSentenceOrder,
    openLinguistBubbleForRect,
    seekInlineAudioToTime,
    seekTimeForNavigation,
    setActiveSentenceIndex,
    tokensForSentence,
  ]);

  useEffect(() => {
    if (!linguistBubble) {
      return;
    }
    const isTypingTarget = (target: EventTarget | null): target is HTMLElement => {
      if (!target || !(target instanceof HTMLElement)) {
        return false;
      }
      if (target.isContentEditable) {
        return true;
      }
      const tag = target.tagName;
      return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
    };
    const handleShortcut = (event: KeyboardEvent) => {
      if (
        event.defaultPrevented ||
        event.metaKey ||
        event.ctrlKey ||
        !event.altKey ||
        isTypingTarget(event.target)
      ) {
        return;
      }
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        navigateLinguistWord(-1);
        return;
      }
      if (event.key === 'ArrowRight') {
        event.preventDefault();
        navigateLinguistWord(1);
      }
    };
    window.addEventListener('keydown', handleShortcut);
    return () => {
      window.removeEventListener('keydown', handleShortcut);
    };
  }, [linguistBubble, navigateLinguistWord]);

  const noop = useCallback(() => {}, []);
  const noopNavigate = useCallback((_delta: -1 | 1) => {}, []);
  const noopMouse = useCallback((_event: ReactMouseEvent<HTMLDivElement>) => {}, []);
  const noopPointer = useCallback((_event: ReactPointerEvent<HTMLDivElement>) => {}, []);

  if (!isEnabled) {
    return {
      bubble: null,
      bubblePinned: false,
      bubbleDocked: false,
      bubbleDragging: false,
      bubbleResizing: false,
      bubbleRef: linguistBubbleRef,
      floatingPlacement: 'above',
      floatingPosition: null,
      floatingSize: null,
      canNavigatePrev: false,
      canNavigateNext: false,
      onTogglePinned: noop,
      onToggleDocked: noop,
      onClose: noop,
      onSpeak: noop,
      onSpeakSlow: noop,
      onNavigateWord: noopNavigate,
      onBubblePointerDown: noopPointer,
      onBubblePointerMove: noopPointer,
      onBubblePointerUp: noopPointer,
      onBubblePointerCancel: noopPointer,
      onResizeHandlePointerDown: noopPointer,
      onResizeHandlePointerMove: noopPointer,
      onResizeHandlePointerUp: noopPointer,
      onResizeHandlePointerCancel: noopPointer,
      onTokenClickCapture: noopMouse,
      onPointerDownCapture: noopPointer,
      onPointerMoveCapture: noopPointer,
      onPointerUpCaptureWithSelection: noopPointer,
      onPointerCancelCapture: noopPointer,
      onBackgroundClick: handleInteractiveBackgroundClick,
      requestPositionUpdate: noop,
    };
  }

  return {
    bubble: linguistBubble,
    bubblePinned: linguistBubblePinned,
    bubbleDocked: linguistBubbleDocked,
    bubbleDragging: linguistBubbleDragging,
    bubbleResizing: linguistBubbleResizing,
    bubbleRef: linguistBubbleRef,
    floatingPlacement: linguistBubbleFloatingPlacement,
    floatingPosition: linguistBubbleFloatingPosition,
    floatingSize: linguistBubbleFloatingSize,
    canNavigatePrev: linguistCanNavigatePrev,
    canNavigateNext: linguistCanNavigateNext,
    onTogglePinned: toggleLinguistBubblePinned,
    onToggleDocked: toggleLinguistBubbleDocked,
    onClose: closeLinguistBubble,
    onSpeak: handleLinguistSpeak,
    onSpeakSlow: handleLinguistSpeakSlow,
    onNavigateWord: navigateLinguistWord,
    onBubblePointerDown: handleBubblePointerDown,
    onBubblePointerMove: handleBubblePointerMove,
    onBubblePointerUp: finishBubbleDrag,
    onBubblePointerCancel: handleBubblePointerCancel,
    onResizeHandlePointerDown: handleResizeHandlePointerDown,
    onResizeHandlePointerMove: handleResizeHandlePointerMove,
    onResizeHandlePointerUp: finishResize,
    onResizeHandlePointerCancel: handleResizeHandlePointerCancel,
    onTokenClickCapture: handleLinguistTokenClickCapture,
    onPointerDownCapture: handlePointerDownCapture,
    onPointerMoveCapture: handlePointerMoveCapture,
    onPointerUpCaptureWithSelection: handlePointerUpCaptureWithSelection,
    onPointerCancelCapture: handlePointerCancelCapture,
    onBackgroundClick: handleInteractiveBackgroundClick,
    requestPositionUpdate: requestLinguistBubblePositionUpdate,
  };
}
