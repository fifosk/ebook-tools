import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type {
  MouseEvent as ReactMouseEvent,
  MutableRefObject,
  PointerEvent as ReactPointerEvent,
} from 'react';
import { fetchLlmModels, fetchVoiceInventory } from '../../api/client';
import type { VoiceInventoryResponse } from '../../api/dtos';
import { resolveLanguageCode } from '../../constants/languageCodes';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import {
  MY_LINGUIST_BUBBLE_MAX_CHARS,
  MY_LINGUIST_DEFAULT_LLM_MODEL,
  MY_LINGUIST_DEFAULT_LOOKUP_LANGUAGE,
  MY_LINGUIST_STORAGE_KEYS,
} from './constants';
import type {
  LinguistBubbleFloatingPlacement,
  LinguistBubbleState,
  LinguistBubbleNavigation,
  SentenceFragment,
  TimelineDisplay,
} from './types';
import type { TextPlayerVariantKind } from '../../text-player/TextPlayer';
import { useLinguistBubbleInteractions } from './useLinguistBubbleInteractions';
import { useLinguistBubbleLayout } from './useLinguistBubbleLayout';
import { useLinguistBubbleLookup } from './useLinguistBubbleLookup';
import { useLinguistBubbleNavigation } from './useLinguistBubbleNavigation';
import {
  buildMyLinguistLanguageOptions,
  buildMyLinguistModelOptions,
  storeMyLinguistStored,
} from './utils';

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
  onPlayFromNarration: (() => void) | undefined;
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
  openTokenLookup: (
    query: string,
    variantKind: TextPlayerVariantKind | null,
    anchorElement: HTMLElement | null,
    navigationOverride?: LinguistBubbleNavigation | null,
  ) => void;
  lookupLanguageOptions: string[];
  llmModelOptions: string[];
  ttsVoiceOptions: string[];
  onLookupLanguageChange: (value: string) => void;
  onLlmModelChange: (value: string | null) => void;
  onTtsVoiceChange: (value: string | null) => void;
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
  const [linguistBubble, setLinguistBubble] = useState<LinguistBubbleState | null>(null);
  const linguistRequestCounterRef = useRef(0);
  const linguistAnchorRectRef = useRef<DOMRect | null>(null);
  const linguistAnchorElementRef = useRef<HTMLElement | null>(null);
  const llmModelsLoadedRef = useRef(false);
  const voiceInventoryLoadedRef = useRef(false);
  const [availableLlmModels, setAvailableLlmModels] = useState<string[]>([]);
  const [voiceInventory, setVoiceInventory] = useState<VoiceInventoryResponse | null>(null);
  const lookupLanguageOptions = useMemo(
    () =>
      buildMyLinguistLanguageOptions(
        [
          linguistBubble?.lookupLanguage,
          resolvedJobTranslationLanguage,
          resolvedJobOriginalLanguage,
          globalInputLanguage,
          MY_LINGUIST_DEFAULT_LOOKUP_LANGUAGE,
        ],
        MY_LINGUIST_DEFAULT_LOOKUP_LANGUAGE,
      ),
    [
      globalInputLanguage,
      linguistBubble?.lookupLanguage,
      resolvedJobOriginalLanguage,
      resolvedJobTranslationLanguage,
    ],
  );
  const llmModelOptions = useMemo(
    () =>
      buildMyLinguistModelOptions(
        linguistBubble?.llmModel,
        availableLlmModels,
        MY_LINGUIST_DEFAULT_LLM_MODEL,
      ),
    [availableLlmModels, linguistBubble?.llmModel],
  );

  const ttsVoiceOptions = useMemo(() => {
    if (!voiceInventory) {
      return [];
    }
    const ttsLanguage = linguistBubble?.ttsLanguage ?? '';
    // Convert language name (e.g., "English") to code (e.g., "en") if needed
    const resolvedCode = resolveLanguageCode(ttsLanguage) ?? ttsLanguage;
    const normalizedLang = resolvedCode.toLowerCase().split(/[-_]/)[0];
    const options: string[] = [];
    const seen = new Set<string>();

    // Add auto options at the top (priority order: gTTS -> Piper -> macOS)
    const autoOptions = ['gTTS', 'piper-auto', 'macOS-auto'];
    for (const opt of autoOptions) {
      seen.add(opt.toLowerCase());
      options.push(opt);
    }

    // Add current voice if set and not an auto option
    if (linguistBubble?.ttsVoice) {
      const current = linguistBubble.ttsVoice.trim();
      if (current && !seen.has(current.toLowerCase())) {
        seen.add(current.toLowerCase());
        options.push(current);
      }
    }

    // Add gTTS option for the language (specific language variant)
    for (const entry of voiceInventory.gtts ?? []) {
      const entryLang = entry.code.toLowerCase().split(/[-_]/)[0];
      if (entryLang === normalizedLang) {
        const identifier = `gTTS-${entryLang}`;
        if (!seen.has(identifier.toLowerCase())) {
          seen.add(identifier.toLowerCase());
          options.push(identifier);
        }
        break;
      }
    }

    // Add Piper voices matching the language
    for (const voice of voiceInventory.piper ?? []) {
      const voiceLang = voice.lang.toLowerCase().split(/[-_]/)[0];
      if (voiceLang === normalizedLang && !seen.has(voice.name.toLowerCase())) {
        seen.add(voice.name.toLowerCase());
        options.push(voice.name);
      }
    }

    // Add macOS voices matching the language
    for (const voice of voiceInventory.macos ?? []) {
      const voiceLang = voice.lang.toLowerCase().split(/[-_]/)[0];
      if (voiceLang === normalizedLang) {
        const identifier = `${voice.name} - ${voice.lang}`;
        if (!seen.has(identifier.toLowerCase())) {
          seen.add(identifier.toLowerCase());
          options.push(identifier);
        }
      }
    }

    return options;
  }, [voiceInventory, linguistBubble?.ttsLanguage, linguistBubble?.ttsVoice]);

  const layout = useLinguistBubbleLayout({
    anchorRectRef: linguistAnchorRectRef,
    anchorElementRef: linguistAnchorElementRef,
    bubble: linguistBubble,
  });

  const lookup = useLinguistBubbleLookup({
    isEnabled,
    audioRef,
    requestCounterRef: linguistRequestCounterRef,
    bubble: linguistBubble,
    setBubble: setLinguistBubble,
    anchorRectRef: linguistAnchorRectRef,
    anchorElementRef: linguistAnchorElementRef,
    jobId,
    chunk,
    globalInputLanguage,
    resolvedJobOriginalLanguage,
    resolvedJobTranslationLanguage,
    applyOpenLayout: layout.applyOpenLayout,
    maxQueryChars: MY_LINGUIST_BUBBLE_MAX_CHARS,
    loadingAnswer: 'Lookup in progress…',
    truncationSuffix: '…',
  });

  const navigation = useLinguistBubbleNavigation({
    containerRef,
    anchorRectRef: linguistAnchorRectRef,
    anchorElementRef: linguistAnchorElementRef,
    bubble: linguistBubble,
    bubblePinned: layout.bubblePinned,
    bubbleDocked: layout.bubbleDocked,
    activeSentenceIndex,
    setActiveSentenceIndex,
    timelineDisplay,
    rawSentences,
    chunk,
    onRequestAdvanceChunk,
    seekInlineAudioToTime,
    openLinguistBubbleForRect: lookup.openLinguistBubbleForRect,
    requestPositionUpdate: layout.requestPositionUpdate,
  });

  const interactions = useLinguistBubbleInteractions({
    containerRef,
    bubbleRef: layout.bubbleRef,
    audioRef,
    inlineAudioPlayingRef,
    dictionarySuppressSeekRef,
    isEnabled,
    onInlineAudioPlaybackStateChange,
    openLinguistBubbleForRect: lookup.openLinguistBubbleForRect,
  });

  const handleLookupLanguageChange = useCallback((value: string) => {
    const trimmed = value.trim();
    if (!trimmed) {
      return;
    }
    storeMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.lookupLanguage, trimmed);
    setLinguistBubble((previous) => {
      if (!previous) {
        return previous;
      }
      return { ...previous, lookupLanguage: trimmed };
    });
  }, []);

  const handleLlmModelChange = useCallback((value: string | null) => {
    const trimmed = (value ?? '').trim();
    storeMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.llmModel, trimmed, { allowEmpty: true });
    setLinguistBubble((previous) => {
      if (!previous) {
        return previous;
      }
      return { ...previous, llmModel: trimmed ? trimmed : null };
    });
  }, []);

  const handleTtsVoiceChange = useCallback((value: string | null) => {
    const trimmed = (value ?? '').trim();
    storeMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.ttsVoice, trimmed, { allowEmpty: true });
    setLinguistBubble((previous) => {
      if (!previous) {
        return previous;
      }
      return { ...previous, ttsVoice: trimmed ? trimmed : null };
    });
  }, []);

  const closeLinguistBubble = useCallback(() => {
    lookup.resetBubbleState();
    navigation.resetNavigation();
    layout.resetLayout();
  }, [layout.resetLayout, lookup.resetBubbleState, navigation.resetNavigation]);

  // Play word from narration audio using cached audio reference
  const handlePlayFromNarration = useCallback(() => {
    const audioRefData = linguistBubble?.cachedAudioRef;
    if (!audioRefData) {
      return;
    }
    // Seek to the start of the word in the narration audio
    seekInlineAudioToTime(audioRefData.t0);
    // Start playback
    const element = audioRef.current;
    if (element && element.paused) {
      void element.play().catch(() => {
        // Ignore autoplay policy errors
      });
    }
  }, [audioRef, linguistBubble?.cachedAudioRef, seekInlineAudioToTime]);

  const openTokenLookup = useCallback(
    (
      query: string,
      variantKind: TextPlayerVariantKind | null,
      anchorElement: HTMLElement | null,
      navigationOverride: LinguistBubbleNavigation | null = null,
    ) => {
      if (!isEnabled) {
        return;
      }
      const trimmed = query.trim();
      if (!trimmed) {
        return;
      }
      const rect =
        anchorElement?.getBoundingClientRect() ?? containerRef.current?.getBoundingClientRect();
      if (!rect) {
        return;
      }
      lookup.openLinguistBubbleForRect(
        trimmed,
        rect,
        'click',
        variantKind,
        anchorElement,
        navigationOverride,
      );
    },
    [containerRef, isEnabled, lookup],
  );

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
      const bubbleEl = layout.bubbleRef.current;
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
  }, [closeLinguistBubble, linguistBubble, layout.bubbleRef]);

  useEffect(() => {
    if (!isEnabled || !linguistBubble || llmModelsLoadedRef.current) {
      return;
    }
    llmModelsLoadedRef.current = true;
    void fetchLlmModels()
      .then((models) => {
        setAvailableLlmModels(models ?? []);
      })
      .catch(() => {
        setAvailableLlmModels([]);
      });
  }, [isEnabled, linguistBubble]);

  useEffect(() => {
    if (!isEnabled || !linguistBubble || voiceInventoryLoadedRef.current) {
      return;
    }
    voiceInventoryLoadedRef.current = true;
    void fetchVoiceInventory()
      .then((inventory) => {
        setVoiceInventory(inventory);
      })
      .catch(() => {
        setVoiceInventory(null);
      });
  }, [isEnabled, linguistBubble]);

  const noop = useCallback(() => {}, []);
  const noopNavigate = useCallback((_delta: -1 | 1) => {}, []);
  const noopMouse = useCallback((_event: ReactMouseEvent<HTMLDivElement>) => {}, []);
  const noopPointer = useCallback((_event: ReactPointerEvent<HTMLDivElement>) => {}, []);
  const noopLookup = useCallback((_value: string) => {}, []);
  const noopModel = useCallback((_value: string | null) => {}, []);
  const noopVoice = useCallback((_value: string | null) => {}, []);

  if (!isEnabled) {
    return {
      bubble: null,
      bubblePinned: false,
      bubbleDocked: false,
      bubbleDragging: false,
      bubbleResizing: false,
      bubbleRef: layout.bubbleRef,
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
      onPlayFromNarration: undefined,
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
      onBackgroundClick: interactions.onBackgroundClick,
      requestPositionUpdate: noop,
      openTokenLookup: noop as UseLinguistBubbleResult['openTokenLookup'],
      lookupLanguageOptions: [],
      llmModelOptions: [],
      ttsVoiceOptions: [],
      onLookupLanguageChange: noopLookup,
      onLlmModelChange: noopModel,
      onTtsVoiceChange: noopVoice,
    };
  }

  return {
    bubble: linguistBubble,
    bubblePinned: layout.bubblePinned,
    bubbleDocked: layout.bubbleDocked,
    bubbleDragging: layout.bubbleDragging,
    bubbleResizing: layout.bubbleResizing,
    bubbleRef: layout.bubbleRef,
    floatingPlacement: layout.floatingPlacement,
    floatingPosition: layout.floatingPosition,
    floatingSize: layout.floatingSize,
    canNavigatePrev: navigation.canNavigatePrev,
    canNavigateNext: navigation.canNavigateNext,
    onTogglePinned: layout.onTogglePinned,
    onToggleDocked: layout.onToggleDocked,
    onClose: closeLinguistBubble,
    onSpeak: lookup.onSpeak,
    onSpeakSlow: lookup.onSpeakSlow,
    onPlayFromNarration: linguistBubble?.cachedAudioRef ? handlePlayFromNarration : undefined,
    onNavigateWord: navigation.onNavigateWord,
    onBubblePointerDown: layout.onBubblePointerDown,
    onBubblePointerMove: layout.onBubblePointerMove,
    onBubblePointerUp: layout.onBubblePointerUp,
    onBubblePointerCancel: layout.onBubblePointerCancel,
    onResizeHandlePointerDown: layout.onResizeHandlePointerDown,
    onResizeHandlePointerMove: layout.onResizeHandlePointerMove,
    onResizeHandlePointerUp: layout.onResizeHandlePointerUp,
    onResizeHandlePointerCancel: layout.onResizeHandlePointerCancel,
    onTokenClickCapture: interactions.onTokenClickCapture,
    onPointerDownCapture: interactions.onPointerDownCapture,
    onPointerMoveCapture: interactions.onPointerMoveCapture,
    onPointerUpCaptureWithSelection: interactions.onPointerUpCaptureWithSelection,
    onPointerCancelCapture: interactions.onPointerCancelCapture,
    onBackgroundClick: interactions.onBackgroundClick,
    requestPositionUpdate: layout.requestPositionUpdate,
    openTokenLookup,
    lookupLanguageOptions,
    llmModelOptions,
    ttsVoiceOptions,
    onLookupLanguageChange: handleLookupLanguageChange,
    onLlmModelChange: handleLlmModelChange,
    onTtsVoiceChange: handleTtsVoiceChange,
  };
}
