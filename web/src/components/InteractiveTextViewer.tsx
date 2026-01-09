import {
  cloneElement,
  forwardRef,
  isValidElement,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { CSSProperties, KeyboardEvent as ReactKeyboardEvent, ReactNode, UIEvent } from 'react';
import type { AudioTrackMetadata } from '../api/dtos';
import type { LiveMediaChunk } from '../hooks/useLiveMedia';
import { DebugOverlay } from '../player/DebugOverlay';
import '../styles/debug-overlay.css';
import TextPlayer, {
  type TextPlayerTokenSelection,
  type TextPlayerVariantKind,
} from '../text-player/TextPlayer';
import { useLanguagePreferences } from '../context/LanguageProvider';
import { useMyPainter } from '../context/MyPainterProvider';
import type { InteractiveTextTheme } from '../types/interactiveTextTheme';
import type { PlayerFeatureFlags, PlayerMode } from '../types/player';
import PlayerChannelBug from './PlayerChannelBug';
import { InteractiveFullscreenControls } from './interactive-text/InteractiveFullscreenControls';
import { InlineAudioPlayer } from './interactive-text/InlineAudioPlayer';
import { MyLinguistBubble } from './interactive-text/MyLinguistBubble';
import { useInteractiveAudioPlayback } from './interactive-text/useInteractiveAudioPlayback';
import { useInteractiveTextVisuals } from './interactive-text/useInteractiveTextVisuals';
import { useLinguistBubble } from './interactive-text/useLinguistBubble';
import { useLibraryMediaOrigin } from './interactive-text/useLibraryMediaOrigin';
import { useMyPainterSentence } from './interactive-text/useMyPainterSentence';
import { useSlideIndicator } from './interactive-text/useSlideIndicator';
import { useSentenceImageReel } from './interactive-text/useSentenceImageReel';
import { useSequenceDebug } from './interactive-text/useSequenceDebug';

type InlineAudioControls = {
  pause: () => void;
  play: () => void;
};

interface InteractiveTextViewerProps {
  content: string;
  rawContent?: string | null;
  chunk: LiveMediaChunk | null;
  chunks?: LiveMediaChunk[] | null;
  activeChunkIndex?: number | null;
  playerMode?: PlayerMode;
  playerFeatures?: PlayerFeatureFlags | null;
  totalSentencesInBook?: number | null;
  bookTotalSentences?: number | null;
  jobStartSentence?: number | null;
  jobEndSentence?: number | null;
  jobOriginalLanguage?: string | null;
  jobTranslationLanguage?: string | null;
  cueVisibility?: {
    original: boolean;
    transliteration: boolean;
    translation: boolean;
  };
  activeAudioUrl: string | null;
  noAudioAvailable: boolean;
  jobId?: string | null;
  onActiveSentenceChange?: (sentenceNumber: number | null) => void;
  onRequestSentenceJump?: (sentenceNumber: number) => void;
  onScroll?: (event: UIEvent<HTMLDivElement>) => void;
  onAudioProgress?: (audioUrl: string, position: number) => void;
  getStoredAudioPosition?: (audioUrl: string) => number;
  onRegisterInlineAudioControls?: (controls: InlineAudioControls | null) => void;
  onInlineAudioPlaybackStateChange?: (state: 'playing' | 'paused') => void;
  onRequestAdvanceChunk?: () => void;
  isFullscreen?: boolean;
  onRequestExitFullscreen?: () => void;
  fullscreenControls?: ReactNode;
  fullscreenAdvancedControls?: ReactNode;
  audioTracks?: Record<string, AudioTrackMetadata> | null;
  activeTimingTrack?: 'mix' | 'translation' | 'original';
  originalAudioEnabled?: boolean;
  translationAudioEnabled?: boolean;
  translationSpeed?: number;
  fontScale?: number;
  theme?: InteractiveTextTheme | null;
  bookTitle?: string | null;
  bookAuthor?: string | null;
  bookYear?: string | null;
  bookGenre?: string | null;
  backgroundOpacityPercent?: number;
  sentenceCardOpacityPercent?: number;
  infoGlyph?: string | null;
  infoGlyphLabel?: string | null;
  infoTitle?: string | null;
  infoMeta?: string | null;
  infoCoverUrl?: string | null;
  infoCoverSecondaryUrl?: string | null;
  infoCoverAltText?: string | null;
  infoCoverVariant?: 'book' | 'subtitles' | 'video' | 'youtube' | 'nas' | 'dub' | 'job' | null;
  bookCoverUrl?: string | null;
  bookCoverAltText?: string | null;
  shortcutHelpOverlay?: ReactNode;
}

const InteractiveTextViewer = forwardRef<HTMLDivElement | null, InteractiveTextViewerProps>(function InteractiveTextViewer(
  {
    content,
    rawContent = null,
    chunk,
    chunks = null,
    activeChunkIndex = null,
    playerMode = 'online',
    playerFeatures = null,
    totalSentencesInBook = null,
    activeAudioUrl,
    noAudioAvailable,
    jobId = null,
    onScroll,
    onAudioProgress,
    getStoredAudioPosition,
    onRegisterInlineAudioControls,
    onInlineAudioPlaybackStateChange,
    onRequestAdvanceChunk,
    isFullscreen = false,
    onRequestExitFullscreen,
    fullscreenControls,
    fullscreenAdvancedControls,
    audioTracks = null,
    activeTimingTrack = 'translation',
    originalAudioEnabled = false,
    translationAudioEnabled = true,
    translationSpeed = 1,
    fontScale = 1,
    theme = null,
    bookTitle = null,
    bookAuthor = null,
    bookYear = null,
    bookGenre = null,
    backgroundOpacityPercent = 65,
    sentenceCardOpacityPercent = 100,
    infoGlyph = null,
    infoGlyphLabel = null,
    infoTitle = null,
    infoMeta = null,
    infoCoverUrl = null,
    infoCoverSecondaryUrl = null,
    infoCoverAltText = null,
    infoCoverVariant = null,
    bookCoverUrl = null,
    bookCoverAltText = null,
    shortcutHelpOverlay = null,
    onActiveSentenceChange,
    onRequestSentenceJump,
    bookTotalSentences = null,
    jobStartSentence = null,
    jobEndSentence = null,
    jobOriginalLanguage = null,
    jobTranslationLanguage = null,
    cueVisibility,
  },
  forwardedRef,
) {
  const { inputLanguage: globalInputLanguage } = useLanguagePreferences();
  const { setPlayerSentence, imageRefreshToken } = useMyPainter();
  const featureFlags = playerFeatures ?? {};
  const linguistEnabled = featureFlags.linguist !== false;
  const painterEnabled = featureFlags.painter !== false;
  const sequenceDebugEnabled = useSequenceDebug();
  const resolvedJobOriginalLanguage = useMemo(() => {
    const trimmed = typeof jobOriginalLanguage === 'string' ? jobOriginalLanguage.trim() : '';
    return trimmed.length > 0 ? trimmed : null;
  }, [jobOriginalLanguage]);
  const resolvedJobTranslationLanguage = useMemo(() => {
    const trimmed = typeof jobTranslationLanguage === 'string' ? jobTranslationLanguage.trim() : '';
    return trimmed.length > 0 ? trimmed : null;
  }, [jobTranslationLanguage]);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const dictionarySuppressSeekRef = useRef(false);
  const {
    bodyStyle,
    safeInfoGlyph,
    hasChannelBug,
    safeInfoTitle,
    safeInfoMeta,
    showInfoHeader,
    showTextBadge,
    showCoverArt,
    showSecondaryCover,
    resolvedCoverUrl,
    resolvedSecondaryCoverUrl,
    resolvedInfoCoverVariant,
    coverAltText,
    handleCoverError,
    handleSecondaryCoverError,
  } = useInteractiveTextVisuals({
    isFullscreen,
    fontScale,
    theme,
    backgroundOpacityPercent,
    sentenceCardOpacityPercent,
    infoGlyph,
    infoTitle,
    infoMeta,
    infoCoverUrl,
    infoCoverSecondaryUrl,
    infoCoverAltText,
    infoCoverVariant,
    bookTitle,
    bookAuthor,
    bookYear,
    bookGenre,
    bookCoverUrl,
    bookCoverAltText,
  });
  const revealMemoryRef = useRef<{
    sentenceIdx: number | null;
    counts: Record<TextPlayerVariantKind, number>;
  }>({
    sentenceIdx: null,
    counts: {
      original: 0,
      translit: 0,
      translation: 0,
    },
  });
  const lastChunkTimeRef = useRef(0);
  const lastChunkIdRef = useRef<string | null>(null);
  const {
    attachPlayerCore,
    attachMediaElement,
    audioRef,
    playerCore,
    chunkTime,
    audioDuration,
    activeSentenceIndex,
    setActiveSentenceIndex,
    resolvedAudioUrl,
    effectiveAudioUrl,
    inlineAudioPlayingRef,
    isInlineAudioPlaying,
    audioTimelineText,
    audioTimelineTitle,
    sequenceDebugInfo,
    hasVisibleCues,
    timelineSentences,
    timelineDisplay,
    rawSentences,
    textPlayerSentences,
    handleInlineAudioPlay,
    handleInlineAudioPause,
    handleLoadedMetadata,
    handleTimeUpdate,
    handleAudioEnded,
    handleAudioSeeked,
    handleAudioSeeking,
    handleAudioWaiting,
    handleAudioStalled,
    handleAudioPlaying,
    handleAudioRateChange,
    seekInlineAudioToTime,
    handleTokenSeek,
    wordSync,
  } = useInteractiveAudioPlayback({
    content,
    chunk,
    chunks,
    activeChunkIndex,
    audioTracks,
    activeAudioUrl,
    jobId,
    playerMode,
    originalAudioEnabled,
    translationAudioEnabled,
    translationSpeed,
    activeTimingTrack,
    cueVisibility,
    onAudioProgress,
    getStoredAudioPosition,
    onRegisterInlineAudioControls,
    onInlineAudioPlaybackStateChange,
    onRequestAdvanceChunk,
    onActiveSentenceChange,
    dictionarySuppressSeekRef,
    containerRef,
    revealMemoryRef,
    sequenceDebugEnabled,
  });
  const { legacyWordSyncEnabled, shouldUseWordSync, wordSyncSentences } = wordSync;
  const [manualSelection, setManualSelection] = useState<TextPlayerTokenSelection | null>(null);
  const activeTextSentence =
    textPlayerSentences && textPlayerSentences.length > 0 ? textPlayerSentences[0] : null;

  const linguist = useLinguistBubble({
    containerRef,
    audioRef,
    inlineAudioPlayingRef,
    dictionarySuppressSeekRef,
    enabled: linguistEnabled,
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
  });
  const {
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
    onBubblePointerUp: handleBubblePointerUp,
    onBubblePointerCancel: handleBubblePointerCancel,
    onResizeHandlePointerDown: handleResizeHandlePointerDown,
    onResizeHandlePointerMove: handleResizeHandlePointerMove,
    onResizeHandlePointerUp: handleResizeHandlePointerUp,
    onResizeHandlePointerCancel: handleResizeHandlePointerCancel,
    onTokenClickCapture: handleLinguistTokenClickCapture,
    onPointerDownCapture: handlePointerDownCapture,
    onPointerMoveCapture: handlePointerMoveCapture,
    onPointerUpCaptureWithSelection: handlePointerUpCaptureWithSelection,
    onPointerCancelCapture: handlePointerCancelCapture,
    onBackgroundClick: handleInteractiveBackgroundClick,
    requestPositionUpdate: requestLinguistBubblePositionUpdate,
    openTokenLookup: openLinguistTokenLookup,
  } = linguist;

  useEffect(() => {
    setManualSelection(null);
  }, [activeTextSentence?.id]);

  useEffect(() => {
    if (isInlineAudioPlaying) {
      setManualSelection(null);
    }
  }, [isInlineAudioPlaying]);

  useEffect(() => {
    if (isInlineAudioPlaying || !activeTextSentence) {
      return;
    }
    const navigation = linguistBubble?.navigation ?? null;
    if (!navigation || navigation.sentenceIndex !== activeTextSentence.index) {
      return;
    }
    const variant = activeTextSentence.variants.find((entry) => entry.baseClass === navigation.variantKind);
    if (!variant || variant.tokens.length === 0) {
      return;
    }
    const clampedIndex = Math.max(0, Math.min(navigation.tokenIndex, variant.tokens.length - 1));
    setManualSelection({
      sentenceIndex: activeTextSentence.index,
      variantKind: navigation.variantKind,
      tokenIndex: clampedIndex,
    });
  }, [activeTextSentence, isInlineAudioPlaying, linguistBubble?.navigation]);

  const fullscreenRequestedRef = useRef(false);
  const fullscreenResyncPendingRef = useRef(false);
  const fullscreenResyncToken = useMemo(() => {
    const parts: (string | number)[] = [];
    if (chunk) {
      parts.push(
        chunk.chunkId ?? '',
        chunk.rangeFragment ?? '',
        chunk.metadataPath ?? '',
        chunk.metadataUrl ?? '',
        chunk.startSentence ?? '',
        chunk.endSentence ?? '',
      );
    } else {
      parts.push('no-chunk');
    }
    parts.push(content.length, (rawContent ?? '').length, activeAudioUrl ?? 'none');
    return parts.join('|');
  }, [activeAudioUrl, chunk, content, rawContent]);
  const isFullscreenRef = useRef(isFullscreen);
  useEffect(() => {
    isFullscreenRef.current = isFullscreen;
  }, [isFullscreen]);

  const requestFullscreenIfNeeded = useCallback(() => {
    if (!isFullscreenRef.current || typeof document === 'undefined') {
      return;
    }
    const element = rootRef.current;
    if (!element) {
      return;
    }
    if (document.fullscreenElement === element || fullscreenRequestedRef.current) {
      return;
    }
    if (typeof element.requestFullscreen !== 'function') {
      fullscreenResyncPendingRef.current = false;
      onRequestExitFullscreen?.();
      return;
    }
    try {
      const requestResult = element.requestFullscreen();
      fullscreenRequestedRef.current = true;
      if (requestResult && typeof requestResult.catch === 'function') {
        requestResult.catch(() => {
          fullscreenRequestedRef.current = false;
          fullscreenResyncPendingRef.current = false;
          onRequestExitFullscreen?.();
        });
      }
    } catch {
      fullscreenRequestedRef.current = false;
      fullscreenResyncPendingRef.current = false;
      onRequestExitFullscreen?.();
    }
  }, [onRequestExitFullscreen]);
  useImperativeHandle<HTMLDivElement | null, HTMLDivElement | null>(forwardedRef, () => containerRef.current);
  const handleScroll = useCallback(
    (event: UIEvent<HTMLDivElement>) => {
      onScroll?.(event);
      if (linguistBubble && !linguistBubbleDocked) {
        requestLinguistBubblePositionUpdate();
      }
    },
    [linguistBubble, linguistBubbleDocked, onScroll, requestLinguistBubblePositionUpdate],
  );

  const exitFullscreen = useCallback(() => {
    if (typeof document === 'undefined') {
      return;
    }
    if (typeof document.exitFullscreen === 'function') {
      const exitResult = document.exitFullscreen();
      if (exitResult && typeof exitResult.catch === 'function') {
        exitResult.catch(() => undefined);
      }
    }
    fullscreenRequestedRef.current = false;
    fullscreenResyncPendingRef.current = false;
  }, []);

  useEffect(() => {
    if (typeof document === 'undefined') {
      return;
    }
    const element = rootRef.current;
    if (!element) {
      return;
    }

    if (isFullscreen) {
      requestFullscreenIfNeeded();
      return () => {
        exitFullscreen();
      };
    }

    if (document.fullscreenElement === element || fullscreenRequestedRef.current) {
      exitFullscreen();
    } else {
      fullscreenRequestedRef.current = false;
    }
    return;
  }, [exitFullscreen, isFullscreen, requestFullscreenIfNeeded]);

  useEffect(() => {
    if (!isFullscreen) {
      return;
    }
    fullscreenResyncPendingRef.current = true;
    requestFullscreenIfNeeded();
  }, [fullscreenResyncToken, isFullscreen, requestFullscreenIfNeeded]);

  useEffect(() => {
    if (!isFullscreen || typeof document === 'undefined') {
      return;
    }
    const element = rootRef.current;
    if (!element) {
      return;
    }
    const handleFullscreenChange = () => {
      if (document.fullscreenElement === element) {
        fullscreenRequestedRef.current = false;
        fullscreenResyncPendingRef.current = false;
        return;
      }
      fullscreenRequestedRef.current = false;
      if (isFullscreen && fullscreenResyncPendingRef.current) {
        fullscreenResyncPendingRef.current = false;
        requestFullscreenIfNeeded();
        return;
      }
      fullscreenResyncPendingRef.current = false;
      onRequestExitFullscreen?.();
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, [isFullscreen, onRequestExitFullscreen, requestFullscreenIfNeeded]);

  const [fullscreenControlsCollapsed, setFullscreenControlsCollapsed] = useState(false);
  const wasFullscreenRef = useRef<boolean>(false);
  useEffect(() => {
    if (!isFullscreen) {
      setFullscreenControlsCollapsed(false);
      wasFullscreenRef.current = false;
      return;
    }
    if (!wasFullscreenRef.current) {
      setFullscreenControlsCollapsed(true);
      wasFullscreenRef.current = true;
    }
  }, [isFullscreen]);
  useEffect(() => {
    if (!isFullscreen) {
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
        event.altKey ||
        event.metaKey ||
        event.ctrlKey ||
        isTypingTarget(event.target)
      ) {
        return;
      }
      if (event.shiftKey && event.key?.toLowerCase() === 'h') {
        setFullscreenControlsCollapsed((value) => !value);
        event.preventDefault();
      }
    };
    window.addEventListener('keydown', handleShortcut);
    return () => {
      window.removeEventListener('keydown', handleShortcut);
    };
  }, [isFullscreen]);

  useEffect(() => {
    const chunkId = chunk?.chunkId ?? chunk?.rangeFragment ?? null;
    if (lastChunkIdRef.current !== chunkId) {
      revealMemoryRef.current = {
        sentenceIdx: null,
        counts: { original: 0, translit: 0, translation: 0 },
      };
      lastChunkIdRef.current = chunkId;
      lastChunkTimeRef.current = 0;
    }
  }, [chunk?.chunkId, chunk?.rangeFragment]);

  useEffect(() => {
    if (chunkTime + 0.05 < lastChunkTimeRef.current) {
      revealMemoryRef.current = {
        sentenceIdx: null,
        counts: { original: 0, translit: 0, translation: 0 },
      };
    }
    lastChunkTimeRef.current = chunkTime;
  }, [chunkTime]);

  const rootClassName = [
    'player-panel__interactive',
    isFullscreen ? 'player-panel__interactive--fullscreen' : null,
  ]
    .filter(Boolean)
    .join(' ');

  const activeSentenceNumber = useMemo(() => {
    const entries = chunk?.sentences ?? null;
    if (entries && entries.length > 0) {
      const entry = entries[Math.max(0, Math.min(activeSentenceIndex, entries.length - 1))];
      const rawSentenceNumber = entry?.sentence_number ?? null;
      if (typeof rawSentenceNumber === 'number' && Number.isFinite(rawSentenceNumber)) {
        return Math.max(1, Math.trunc(rawSentenceNumber));
      }
    }
    const start = chunk?.startSentence ?? null;
    if (typeof start === 'number' && Number.isFinite(start)) {
      return Math.max(1, Math.trunc(start) + Math.max(0, Math.trunc(activeSentenceIndex)));
    }
    return Math.max(1, Math.trunc(activeSentenceIndex) + 1);
  }, [activeSentenceIndex, chunk?.sentences, chunk?.startSentence]);

  const isLibraryMediaOrigin = useLibraryMediaOrigin(chunk);

  const { sentenceImageReelNode, activeSentenceImagePath, reelScale } = useSentenceImageReel({
    jobId,
    playerMode,
    chunk,
    activeSentenceNumber,
    activeSentenceIndex,
    jobStartSentence,
    jobEndSentence,
    totalSentencesInBook,
    bookTotalSentences,
    isFullscreen,
    imageRefreshToken,
    isLibraryMediaOrigin,
    timelineSentences,
    audioDuration,
    audioTracks,
    activeAudioUrl,
    effectiveAudioUrl,
    onRequestSentenceJump,
    inlineAudioPlayingRef,
    setActiveSentenceIndex,
    handleTokenSeek,
    seekInlineAudioToTime,
  });

  const interactiveFrameStyle = useMemo<CSSProperties>(() => {
    return {
      ...bodyStyle,
      '--reel-size-scale': reelScale,
    } as CSSProperties;
  }, [bodyStyle, reelScale]);

  useMyPainterSentence({
    jobId,
    chunk,
    activeSentenceIndex,
    activeSentenceNumber,
    activeSentenceImagePath,
    isLibraryMediaOrigin,
    setPlayerSentence: painterEnabled ? setPlayerSentence : null,
  });

  const overlayAudioEl = playerCore?.getElement() ?? audioRef.current ?? null;
  const { selection: textPlayerSelection, shadowSelection: textPlayerShadowSelection } = useMemo(() => {
    if (!activeTextSentence) {
      return { selection: null, shadowSelection: null };
    }

    const variantForKind = (kind: TextPlayerVariantKind) =>
      activeTextSentence.variants.find((variant) => variant.baseClass === kind) ?? null;

    const resolveSelection = (
      variant: (typeof activeTextSentence.variants)[number] | null,
    ): TextPlayerTokenSelection | null => {
      if (!variant || variant.tokens.length === 0) {
        return null;
      }
      const rawIndex =
        typeof variant.currentIndex === 'number' && Number.isFinite(variant.currentIndex)
          ? Math.trunc(variant.currentIndex)
          : 0;
      const clampedIndex = Math.max(0, Math.min(rawIndex, variant.tokens.length - 1));
      return {
        sentenceIndex: activeTextSentence.index,
        variantKind: variant.baseClass,
        tokenIndex: clampedIndex,
      };
    };

    const normalizeSelection = (selection: TextPlayerTokenSelection | null): TextPlayerTokenSelection | null => {
      if (!selection || selection.sentenceIndex !== activeTextSentence.index) {
        return null;
      }
      const variant = variantForKind(selection.variantKind);
      if (!variant || variant.tokens.length === 0) {
        return null;
      }
      const clampedIndex = Math.max(0, Math.min(selection.tokenIndex, variant.tokens.length - 1));
      return {
        sentenceIndex: activeTextSentence.index,
        variantKind: variant.baseClass,
        tokenIndex: clampedIndex,
      };
    };

    const defaultSelection =
      resolveSelection(variantForKind('translation')) ??
      resolveSelection(variantForKind('translit')) ??
      resolveSelection(variantForKind('original'));

    const navigation = linguistBubble?.navigation ?? null;
    const bubbleSelection = navigation
      ? normalizeSelection({
          sentenceIndex: navigation.sentenceIndex,
          variantKind: navigation.variantKind,
          tokenIndex: navigation.tokenIndex,
        })
      : null;
    const safeManualSelection = normalizeSelection(manualSelection);

    const selection = isInlineAudioPlaying
      ? defaultSelection
      : safeManualSelection ?? bubbleSelection ?? defaultSelection;
    const translationVariant = variantForKind('translation');
    const translitVariant = variantForKind('translit');
    let shadowSelection: TextPlayerTokenSelection | null = null;
    if (
      selection &&
      translationVariant &&
      translitVariant &&
      translationVariant.tokens.length === translitVariant.tokens.length
    ) {
      const shadowIndex = selection.tokenIndex;
      if (shadowIndex >= 0 && shadowIndex < translationVariant.tokens.length) {
        if (selection.variantKind === 'translation') {
          shadowSelection = {
            sentenceIndex: activeTextSentence.index,
            variantKind: 'translit',
            tokenIndex: shadowIndex,
          };
        } else if (selection.variantKind === 'translit') {
          shadowSelection = {
            sentenceIndex: activeTextSentence.index,
            variantKind: 'translation',
            tokenIndex: shadowIndex,
          };
        }
      }
    }

    return { selection, shadowSelection };
  }, [activeTextSentence, isInlineAudioPlaying, linguistBubble?.navigation, manualSelection]);
  const handleTextPlayerKeyDown = useCallback(
    (event: ReactKeyboardEvent<HTMLDivElement>) => {
      if (isInlineAudioPlaying || !activeTextSentence) {
        return;
      }
      const key = event.key;
      const isArrow =
        key === 'ArrowLeft' || key === 'ArrowRight' || key === 'ArrowUp' || key === 'ArrowDown';
      if (key !== 'Enter' && !isArrow) {
        return;
      }
      const variants = activeTextSentence.variants.filter((variant) => variant.tokens.length > 0);
      if (variants.length === 0) {
        return;
      }
      const fallbackSelection: TextPlayerTokenSelection = {
        sentenceIndex: activeTextSentence.index,
        variantKind: variants[0].baseClass,
        tokenIndex: 0,
      };
      const current = textPlayerSelection ?? fallbackSelection;
      const currentVariant =
        variants.find((variant) => variant.baseClass === current.variantKind) ?? variants[0];
      const tokenCount = currentVariant.tokens.length;
      if (tokenCount === 0) {
        return;
      }

      if (key === 'Enter') {
        const tokenText = currentVariant.tokens[current.tokenIndex] ?? '';
        if (!tokenText.trim()) {
          return;
        }
        const selector = [
          `[data-sentence-index="${current.sentenceIndex}"]`,
          `[data-text-player-token="true"][data-text-player-variant="${current.variantKind}"][data-text-player-token-index="${current.tokenIndex}"]`,
        ].join(' ');
        const candidate = containerRef.current?.querySelector(selector);
        const anchorElement = candidate instanceof HTMLElement ? candidate : null;
        openLinguistTokenLookup(tokenText, current.variantKind, anchorElement, {
          sentenceIndex: current.sentenceIndex,
          tokenIndex: current.tokenIndex,
          variantKind: current.variantKind,
        });
        event.preventDefault();
        event.stopPropagation();
        return;
      }

      let nextSelection: TextPlayerTokenSelection | null = null;
      if (key === 'ArrowLeft' || key === 'ArrowRight') {
        const delta = key === 'ArrowRight' ? 1 : -1;
        let nextIndex = current.tokenIndex + delta;
        if (nextIndex < 0) {
          nextIndex = tokenCount - 1;
        } else if (nextIndex >= tokenCount) {
          nextIndex = 0;
        }
        nextSelection = {
          sentenceIndex: activeTextSentence.index,
          variantKind: currentVariant.baseClass,
          tokenIndex: nextIndex,
        };
      } else {
        const order = variants.map((variant) => variant.baseClass);
        const currentPos = order.indexOf(currentVariant.baseClass);
        const nextPos = key === 'ArrowUp' ? currentPos - 1 : currentPos + 1;
        if (nextPos < 0 || nextPos >= order.length) {
          return;
        }
        const nextVariant = variants[nextPos];
        const clampedIndex = Math.max(0, Math.min(current.tokenIndex, nextVariant.tokens.length - 1));
        nextSelection = {
          sentenceIndex: activeTextSentence.index,
          variantKind: nextVariant.baseClass,
          tokenIndex: clampedIndex,
        };
      }

      setManualSelection(nextSelection);
      event.preventDefault();
      event.stopPropagation();
    },
    [activeTextSentence, isInlineAudioPlaying, openLinguistTokenLookup, textPlayerSelection],
  );
  const showTextPlayer =
    !(legacyWordSyncEnabled && shouldUseWordSync && wordSyncSentences && wordSyncSentences.length > 0) &&
    Boolean(textPlayerSentences && textPlayerSentences.length > 0);
  const pinnedLinguistBubbleNode =
    linguistEnabled && linguistBubble && linguistBubbleDocked && hasVisibleCues ? (
      <MyLinguistBubble
        bubble={linguistBubble}
        isPinned={linguistBubblePinned}
        isDocked={linguistBubbleDocked}
        isDragging={linguistBubbleDragging}
        isResizing={linguistBubbleResizing}
        variant="docked"
        bubbleRef={linguistBubbleRef}
        canNavigatePrev={linguistCanNavigatePrev}
        canNavigateNext={linguistCanNavigateNext}
        onTogglePinned={toggleLinguistBubblePinned}
        onToggleDocked={toggleLinguistBubbleDocked}
        onNavigatePrev={() => navigateLinguistWord(-1)}
        onNavigateNext={() => navigateLinguistWord(1)}
        onSpeak={handleLinguistSpeak}
        onSpeakSlow={handleLinguistSpeakSlow}
        onClose={closeLinguistBubble}
        onBubblePointerDown={handleBubblePointerDown}
        onBubblePointerMove={handleBubblePointerMove}
        onBubblePointerUp={handleBubblePointerUp}
        onBubblePointerCancel={handleBubblePointerCancel}
        onResizeHandlePointerDown={handleResizeHandlePointerDown}
        onResizeHandlePointerMove={handleResizeHandlePointerMove}
        onResizeHandlePointerUp={handleResizeHandlePointerUp}
        onResizeHandlePointerCancel={handleResizeHandlePointerCancel}
      />
    ) : null;

  const inlineAudioAvailable = Boolean(resolvedAudioUrl || noAudioAvailable);

  const hasAdvancedControls = Boolean(fullscreenAdvancedControls || inlineAudioAvailable);
  const hasFullscreenPanelContent = Boolean(fullscreenControls || fullscreenAdvancedControls || inlineAudioAvailable);
  const inlineAudioCollapsed = Boolean(isFullscreen && fullscreenControlsCollapsed);
  const handleAdvancedControlsToggle = useCallback(() => {
    setFullscreenControlsCollapsed((value) => !value);
  }, []);
  const resolvedFullscreenControls = useMemo(() => {
    if (!fullscreenControls) {
      return null;
    }
    if (isValidElement(fullscreenControls)) {
      return cloneElement(fullscreenControls, {
        showAdvancedToggle: hasAdvancedControls,
        advancedControlsOpen: !fullscreenControlsCollapsed,
        onToggleAdvancedControls: handleAdvancedControlsToggle,
      });
    }
    return fullscreenControls;
  }, [fullscreenControls, fullscreenControlsCollapsed, handleAdvancedControlsToggle, hasAdvancedControls]);
  const slideIndicator = useSlideIndicator({
    chunk,
    activeSentenceIndex,
    jobStartSentence,
    jobEndSentence,
    bookTotalSentences,
    totalSentencesInBook,
  });

  return (
    <>
      <div
        ref={rootRef}
        className={rootClassName}
        data-fullscreen={isFullscreen ? 'true' : 'false'}
        data-original-enabled={originalAudioEnabled ? 'true' : 'false'}
        data-cues-visible={hasVisibleCues ? 'true' : 'false'}
      >
      <InteractiveFullscreenControls
        isVisible={isFullscreen && hasFullscreenPanelContent}
        collapsed={fullscreenControlsCollapsed}
        mainControls={resolvedFullscreenControls}
      >
        {fullscreenAdvancedControls}
      </InteractiveFullscreenControls>
        <InlineAudioPlayer
          audioUrl={resolvedAudioUrl}
          noAudioAvailable={noAudioAvailable}
          collapsed={inlineAudioCollapsed}
          playerRef={attachPlayerCore}
          mediaRef={attachMediaElement}
          onPlay={handleInlineAudioPlay}
          onPause={handleInlineAudioPause}
          onLoadedMetadata={handleLoadedMetadata}
          onTimeUpdate={handleTimeUpdate}
          onEnded={handleAudioEnded}
          onSeeked={handleAudioSeeked}
          onSeeking={handleAudioSeeking}
          onWaiting={handleAudioWaiting}
          onStalled={handleAudioStalled}
          onPlaying={handleAudioPlaying}
          onRateChange={handleAudioRateChange}
        />
        {sequenceDebugInfo ? (
          <div className="player-panel__sequence-debug">
            <span>seqEnabled: {sequenceDebugInfo.enabled ? 'true' : 'false'}</span>
            <span>origEnabled: {sequenceDebugInfo.origEnabled ? 'true' : 'false'}</span>
            <span>transEnabled: {sequenceDebugInfo.transEnabled ? 'true' : 'false'}</span>
            <span>hasOrigSeg: {sequenceDebugInfo.hasOrigSeg ? 'true' : 'false'}</span>
            <span>hasTransSeg: {sequenceDebugInfo.hasTransSeg ? 'true' : 'false'}</span>
            <span>hasOrigTrack: {sequenceDebugInfo.hasOrigTrack ? 'true' : 'false'}</span>
            <span>hasTransTrack: {sequenceDebugInfo.hasTransTrack ? 'true' : 'false'}</span>
            <span>track: {sequenceDebugInfo.track}</span>
            <span>plan: {sequenceDebugInfo.plan}</span>
            <span>index: {sequenceDebugInfo.index}</span>
            <span>lastEnded: {sequenceDebugInfo.lastEnded}</span>
            <span>autoPlay: {sequenceDebugInfo.autoPlay}</span>
            <span>sentence: {sequenceDebugInfo.sentence}</span>
            <span>time: {sequenceDebugInfo.time.toFixed(3)}</span>
            <span>pending: {sequenceDebugInfo.pending}</span>
            <span>playing: {sequenceDebugInfo.playing ? 'true' : 'false'}</span>
            <span>audio: {sequenceDebugInfo.audio}</span>
            <span>orig: {sequenceDebugInfo.original}</span>
            <span>trans: {sequenceDebugInfo.translation}</span>
          </div>
        ) : null}
        <div
          key="interactive-body"
          className="player-panel__document-body player-panel__interactive-frame"
          style={interactiveFrameStyle}
        >
          {showInfoHeader ? (
            <div className="player-panel__player-info-header" aria-hidden="true">
              {hasChannelBug ? <PlayerChannelBug glyph={safeInfoGlyph} label={infoGlyphLabel} /> : null}
              {showCoverArt ? (
                <div className="player-panel__player-info-art" data-variant={resolvedInfoCoverVariant}>
                  <img
                    className="player-panel__player-info-art-main"
                    src={resolvedCoverUrl ?? undefined}
                    alt={coverAltText}
                    onError={handleCoverError}
                    loading="lazy"
                  />
                  {showSecondaryCover ? (
                    <img
                      className="player-panel__player-info-art-secondary"
                      src={resolvedSecondaryCoverUrl ?? undefined}
                      alt=""
                      aria-hidden="true"
                      onError={handleSecondaryCoverError}
                      loading="lazy"
                    />
                  ) : null}
                </div>
              ) : null}
              {showTextBadge ? (
                <div className="player-panel__interactive-book-badge player-panel__player-info-badge">
                  <div className="player-panel__interactive-book-badge-text">
                    {safeInfoTitle ? (
                      <span className="player-panel__interactive-book-badge-title">{safeInfoTitle}</span>
                    ) : null}
                    {safeInfoMeta ? (
                      <span className="player-panel__interactive-book-badge-meta">{safeInfoMeta}</span>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}
          <div
            className="player-panel__interactive-body"
            data-has-badge={showInfoHeader ? 'true' : undefined}
          >
            {slideIndicator || audioTimelineText ? (
              <div className="player-panel__interactive-slide-stack">
                {slideIndicator ? (
                  <div className="player-panel__interactive-slide-indicator" title={slideIndicator.label}>
                    {slideIndicator.label}
                  </div>
                ) : null}
                {audioTimelineText ? (
                  <div
                    className="player-panel__interactive-slide-indicator player-panel__interactive-slide-indicator--audio"
                    title={audioTimelineTitle ?? audioTimelineText}
                  >
                    {audioTimelineText}
                  </div>
                ) : null}
              </div>
            ) : null}
            {sentenceImageReelNode}
            <div
              ref={containerRef}
              className="player-panel__interactive-text-scroll"
              data-testid="player-panel-document"
              onScroll={handleScroll}
              onKeyDown={handleTextPlayerKeyDown}
              tabIndex={0}
              onClickCapture={handleLinguistTokenClickCapture}
              onClick={handleInteractiveBackgroundClick}
              onPointerDownCapture={handlePointerDownCapture}
              onPointerMoveCapture={handlePointerMoveCapture}
              onPointerUpCapture={handlePointerUpCaptureWithSelection}
              onPointerCancelCapture={handlePointerCancelCapture}
            >
              {legacyWordSyncEnabled && shouldUseWordSync && wordSyncSentences && wordSyncSentences.length > 0 ? null : showTextPlayer ? (
                <TextPlayer
                  sentences={textPlayerSentences ?? []}
                  onSeek={handleTokenSeek}
                  selection={textPlayerSelection}
                  shadowSelection={textPlayerShadowSelection}
                  footer={pinnedLinguistBubbleNode}
                />
              ) : rawSentences.length > 0 ? (
                <pre className="player-panel__document-text">{content}</pre>
              ) : chunk ? (
                <div className="player-panel__document-status" role="status">
                  Loading interactive chunk…
                </div>
              ) : (
                <div className="player-panel__document-status" role="status">
                  Text preview will appear once generated.
                </div>
              )}
              {pinnedLinguistBubbleNode && !showTextPlayer ? (
                <div className="player-panel__my-linguist-dock" aria-label="MyLinguist lookup dock">
                  {pinnedLinguistBubbleNode}
                </div>
              ) : null}
            </div>
            {linguistEnabled && linguistBubble && !linguistBubbleDocked && hasVisibleCues ? (
              <MyLinguistBubble
                bubble={linguistBubble}
                isPinned={linguistBubblePinned}
                isDocked={linguistBubbleDocked}
                isDragging={linguistBubbleDragging}
                isResizing={linguistBubbleResizing}
                variant="floating"
                bubbleRef={linguistBubbleRef}
                floatingPlacement={linguistBubbleFloatingPlacement}
                floatingPosition={linguistBubbleFloatingPosition}
                floatingSize={linguistBubbleFloatingSize}
                canNavigatePrev={linguistCanNavigatePrev}
                canNavigateNext={linguistCanNavigateNext}
                onTogglePinned={toggleLinguistBubblePinned}
                onToggleDocked={toggleLinguistBubbleDocked}
                onNavigatePrev={() => navigateLinguistWord(-1)}
                onNavigateNext={() => navigateLinguistWord(1)}
                onSpeak={handleLinguistSpeak}
                onSpeakSlow={handleLinguistSpeakSlow}
                onClose={closeLinguistBubble}
                onBubblePointerDown={handleBubblePointerDown}
                onBubblePointerMove={handleBubblePointerMove}
                onBubblePointerUp={handleBubblePointerUp}
                onBubblePointerCancel={handleBubblePointerCancel}
                onResizeHandlePointerDown={handleResizeHandlePointerDown}
                onResizeHandlePointerMove={handleResizeHandlePointerMove}
                onResizeHandlePointerUp={handleResizeHandlePointerUp}
                onResizeHandlePointerCancel={handleResizeHandlePointerCancel}
              />
            ) : null}
          </div>
        </div>
        {shortcutHelpOverlay}
      </div>
      <DebugOverlay audioEl={overlayAudioEl} />
    </>
  );
});

export default InteractiveTextViewer;
