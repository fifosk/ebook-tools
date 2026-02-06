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
import type { CSSProperties, ReactNode, UIEvent } from 'react';
import type { AudioTrackMetadata } from '../api/dtos';
import type { LiveMediaChunk } from '../hooks/useLiveMedia';
import { DebugOverlay } from '../player/DebugOverlay';
import '../styles/debug-overlay.css';
import TextPlayer, {
  type TextPlayerVariantKind,
} from '../text-player/TextPlayer';
import { useLanguagePreferences } from '../context/LanguageProvider';
import { useMyPainter } from '../context/MyPainterProvider';
import type { InteractiveTextTheme } from '../types/interactiveTextTheme';
import type { PlayerFeatureFlags, PlayerMode } from '../types/player';
import { HEADER_COLLAPSE_KEY, loadHeaderCollapsed, storeHeaderCollapsed } from '../utils/playerHeader';
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
import { useChunkPrefetch, resolveActiveSentenceNumber } from './interactive-text/useChunkPrefetch';
import { useInteractiveFullscreen } from './interactive-text/useInteractiveFullscreen';
import { useTextPlayerKeyboard } from './interactive-text/useTextPlayerKeyboard';

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
  onToggleCueVisibility?: (key: 'original' | 'transliteration' | 'translation') => void;
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
  onRegisterSequenceSkip?: (skipFn: ((direction: 1 | -1) => boolean) | null) => void;
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
    onRegisterSequenceSkip,
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
    onToggleCueVisibility,
  },
  forwardedRef,
) {
  const { inputLanguage: globalInputLanguage } = useLanguagePreferences();
  const { setPlayerSentence, imageRefreshToken } = useMyPainter();
  const featureFlags = playerFeatures ?? {};
  const linguistEnabled = featureFlags.linguist !== false;
  const painterEnabled = featureFlags.painter !== false;
  const sequenceDebugEnabled = useSequenceDebug();
  const [isHeaderCollapsed, setIsHeaderCollapsed] = useState(loadHeaderCollapsed);
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== HEADER_COLLAPSE_KEY) {
        return;
      }
      setIsHeaderCollapsed(loadHeaderCollapsed());
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);
  const toggleHeaderCollapsed = useCallback(() => {
    setIsHeaderCollapsed((previous) => {
      const next = !previous;
      storeHeaderCollapsed(next);
      return next;
    });
  }, []);
  const resolvedJobOriginalLanguage = useMemo(() => {
    const trimmed = typeof jobOriginalLanguage === 'string' ? jobOriginalLanguage.trim() : '';
    return trimmed.length > 0 ? trimmed : null;
  }, [jobOriginalLanguage]);
  const resolvedJobTranslationLanguage = useMemo(() => {
    const trimmed = typeof jobTranslationLanguage === 'string' ? jobTranslationLanguage.trim() : '';
    return trimmed.length > 0 ? trimmed : null;
  }, [jobTranslationLanguage]);
  const resolvedVariantVisibility = useMemo(
    () => ({
      original: cueVisibility?.original ?? true,
      translation: cueVisibility?.translation ?? true,
      translit: cueVisibility?.transliteration ?? true,
    }),
    [cueVisibility],
  );
  const isVariantVisible = useCallback(
    (kind: TextPlayerVariantKind) => resolvedVariantVisibility[kind] ?? true,
    [resolvedVariantVisibility],
  );
  const handleToggleVariant = useCallback(
    (kind: TextPlayerVariantKind) => {
      if (!onToggleCueVisibility) {
        return;
      }
      const key = kind === 'translit' ? 'transliteration' : kind;
      onToggleCueVisibility(key);
    },
    [onToggleCueVisibility],
  );
  const rootRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const dictionarySuppressSeekRef = useRef(false);
  const {
    bodyStyle,
    safeInfoGlyph,
    hasChannelBug,
    safeInfoTitle,
    safeInfoMeta,
    showInfoHeader: hasInfoHeader,
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
  const showHeaderContent = hasInfoHeader && !isHeaderCollapsed;
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

  // Bridging state: synced from audio playback hook via effects below
  const [prefetchSentenceIndex, setPrefetchSentenceIndex] = useState(0);
  const [prefetchIsPlaying, setPrefetchIsPlaying] = useState(false);
  const [prefetchSequenceEnabled, setPrefetchSequenceEnabled] = useState(false);

  // Chunk prefetching via hook
  const { resolvedChunk, resolvedChunks } = useChunkPrefetch({
    jobId,
    playerMode,
    chunk,
    chunks,
    activeSentenceIndex: prefetchSentenceIndex,
    originalAudioEnabled,
    translationAudioEnabled,
    isPlaying: prefetchIsPlaying,
    sequenceEnabled: prefetchSequenceEnabled,
  });
  const activeChunk = resolvedChunk ?? chunk;
  const activeChunks = resolvedChunks ?? chunks;
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
    sequencePlayback,
  } = useInteractiveAudioPlayback({
    content,
    chunk: activeChunk,
    chunks: activeChunks,
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
  const activeTextSentence =
    textPlayerSentences && textPlayerSentences.length > 0 ? textPlayerSentences[0] : null;

  // Sync real playback state into prefetch bridging state
  useEffect(() => { setPrefetchSentenceIndex(activeSentenceIndex); }, [activeSentenceIndex]);
  useEffect(() => { setPrefetchIsPlaying(isInlineAudioPlaying); }, [isInlineAudioPlaying]);
  useEffect(() => { setPrefetchSequenceEnabled(sequencePlayback.enabled); }, [sequencePlayback.enabled]);

  // Track the skip function in a ref so registration effect doesn't re-run when it changes
  const skipSentenceRef = useRef(sequencePlayback.skipSentence);
  useEffect(() => {
    skipSentenceRef.current = sequencePlayback.skipSentence;
  }, [sequencePlayback.skipSentence]);

  // Create a stable wrapper function that delegates to the ref
  const stableSkipSentence = useMemo(() => {
    const fn = (direction: 1 | -1): boolean => {
      return skipSentenceRef.current(direction);
    };
    return fn;
  }, []);

  // Track the callback in a ref so we don't depend on it in the effect
  const onRegisterSequenceSkipRef = useRef(onRegisterSequenceSkip);
  useEffect(() => {
    onRegisterSequenceSkipRef.current = onRegisterSequenceSkip;
  }, [onRegisterSequenceSkip]);

  // Track whether we've registered so we only clear on actual unmount or disable
  const isRegisteredRef = useRef(false);

  // Register sequence skip function with parent component
  // Only re-run when enabled state changes
  useEffect(() => {
    const register = onRegisterSequenceSkipRef.current;
    if (!register) {
      return;
    }
    if (sequencePlayback.enabled) {
      if (import.meta.env.DEV) {
        console.debug('[InteractiveTextViewer] Registering sequence skip function');
      }
      register(stableSkipSentence);
      isRegisteredRef.current = true;
    } else if (isRegisteredRef.current) {
      if (import.meta.env.DEV) {
        console.debug('[InteractiveTextViewer] Clearing sequence skip function (sequence disabled)');
      }
      register(null);
      isRegisteredRef.current = false;
    }
  }, [sequencePlayback.enabled, stableSkipSentence]);

  // Separate cleanup effect that only runs on unmount
  useEffect(() => {
    return () => {
      if (isRegisteredRef.current) {
        const register = onRegisterSequenceSkipRef.current;
        if (register) {
          if (import.meta.env.DEV) {
            console.debug('[InteractiveTextViewer] Cleanup: clearing sequence skip function on unmount');
          }
          register(null);
        }
        isRegisteredRef.current = false;
      }
    };
  }, []);

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
    chunk: activeChunk,
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
    onPlayFromNarration: handleLinguistPlayFromNarration,
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
    lookupLanguageOptions: linguistLookupLanguageOptions,
    llmModelOptions: linguistLlmModelOptions,
    ttsVoiceOptions: linguistTtsVoiceOptions,
    onLookupLanguageChange: handleLookupLanguageChange,
    onLlmModelChange: handleLlmModelChange,
    onTtsVoiceChange: handleTtsVoiceChange,
  } = linguist;

  // Keyboard navigation and selection state via hook
  const {
    manualSelection,
    multiSelection,
    textPlayerSelection,
    textPlayerShadowSelection,
    textPlayerSelectionRange,
    handleTextPlayerKeyDown,
  } = useTextPlayerKeyboard({
    containerRef,
    activeTextSentence,
    isInlineAudioPlaying,
    linguistBubble,
    isVariantVisible,
    openLinguistTokenLookup,
  });

  // Fullscreen state management via hook
  const {
    fullscreenControlsCollapsed,
    handleAdvancedControlsToggle,
  } = useInteractiveFullscreen({
    rootRef,
    isFullscreen,
    chunk,
    content,
    rawContent,
    activeAudioUrl,
    onRequestExitFullscreen,
  });

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

  const activeSentenceNumber = useMemo(
    () => resolveActiveSentenceNumber(activeChunk, activeSentenceIndex),
    [activeChunk, activeSentenceIndex],
  );

  const isLibraryMediaOrigin = useLibraryMediaOrigin(activeChunk);

  const { sentenceImageReelNode, activeSentenceImagePath, reelScale } = useSentenceImageReel({
    jobId,
    playerMode,
    chunk: activeChunk,
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
    chunk: activeChunk,
    activeSentenceIndex,
    activeSentenceNumber,
    activeSentenceImagePath,
    isLibraryMediaOrigin,
    setPlayerSentence: painterEnabled ? setPlayerSentence : null,
  });

  const overlayAudioEl = playerCore?.getElement() ?? audioRef.current ?? null;

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
        onPlayFromNarration={handleLinguistPlayFromNarration}
        onClose={closeLinguistBubble}
        lookupLanguageOptions={linguistLookupLanguageOptions}
        onLookupLanguageChange={handleLookupLanguageChange}
        llmModelOptions={linguistLlmModelOptions}
        onLlmModelChange={handleLlmModelChange}
        ttsVoiceOptions={linguistTtsVoiceOptions}
        onTtsVoiceChange={handleTtsVoiceChange}
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
    chunk: activeChunk,
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
          showControls={false}
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
          {hasInfoHeader && showHeaderContent ? (
            <div className="player-panel__player-info-header">
              <div className="player-panel__player-info-header-content" aria-hidden="true">
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
            </div>
          ) : null}
          {hasInfoHeader ? (
            <button
              type="button"
              className="player-panel__player-info-toggle player-panel__player-info-toggle--interactive"
              data-collapsed={isHeaderCollapsed ? 'true' : 'false'}
              onClick={toggleHeaderCollapsed}
              onPointerDown={(event) => event.stopPropagation()}
              aria-label={isHeaderCollapsed ? 'Show info header' : 'Hide info header'}
            >
              <svg viewBox="0 0 24 24" role="img" focusable="false" aria-hidden="true">
                <path d="M6 9l6 6 6-6Z" fill="currentColor" />
              </svg>
            </button>
          ) : null}
          <div
            className="player-panel__interactive-body"
            data-has-badge={showHeaderContent ? 'true' : undefined}
          >
            {showHeaderContent && (slideIndicator || audioTimelineText) ? (
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
                  selectionRange={textPlayerSelectionRange}
                  shadowSelection={textPlayerShadowSelection}
                  variantVisibility={resolvedVariantVisibility}
                  onToggleVariant={onToggleCueVisibility ? handleToggleVariant : undefined}
                  footer={pinnedLinguistBubbleNode}
                />
              ) : rawSentences.length > 0 ? (
                <pre className="player-panel__document-text">{content}</pre>
              ) : activeChunk ? (
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
                onPlayFromNarration={handleLinguistPlayFromNarration}
                onClose={closeLinguistBubble}
                lookupLanguageOptions={linguistLookupLanguageOptions}
                onLookupLanguageChange={handleLookupLanguageChange}
                llmModelOptions={linguistLlmModelOptions}
                onLlmModelChange={handleLlmModelChange}
                ttsVoiceOptions={linguistTtsVoiceOptions}
                onTtsVoiceChange={handleTtsVoiceChange}
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
