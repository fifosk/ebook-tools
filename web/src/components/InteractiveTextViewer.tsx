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
import type { AudioTrackMetadata, ChunkSentenceMetadata } from '../api/dtos';
import { appendAccessTokenToStorageUrl, buildStorageUrl } from '../api/client';
import type { LiveMediaChunk } from '../hooks/useLiveMedia';
import { DebugOverlay } from '../player/DebugOverlay';
import '../styles/debug-overlay.css';
import TextPlayer, {
  type TextPlayerTokenRange,
  type TextPlayerTokenSelection,
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

type InlineAudioControls = {
  pause: () => void;
  play: () => void;
};

type TextPlayerMultiSelection = {
  sentenceIndex: number;
  variantKind: TextPlayerVariantKind;
  anchorIndex: number;
  focusIndex: number;
};

const PREFETCH_RADIUS = 2;
const METADATA_PREFETCH_RETRY_MS = 6000;
const AUDIO_PREFETCH_RETRY_MS = 12000;
const PREFETCH_TIMEOUT_MS = 4000;
const AUDIO_PREFETCH_RANGE = 'bytes=0-2047';

function resolveChunkKey(chunk: LiveMediaChunk | null): string | null {
  if (!chunk) {
    return null;
  }
  return (
    chunk.chunkId ??
    chunk.rangeFragment ??
    chunk.metadataPath ??
    chunk.metadataUrl ??
    (chunk.startSentence !== null || chunk.endSentence !== null
      ? `${chunk.startSentence ?? 'na'}-${chunk.endSentence ?? 'na'}`
      : null)
  );
}

function resolveStorageUrl(value: string | null, jobId: string | null): string | null {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (/^[a-z]+:\/\//i.test(trimmed) || trimmed.startsWith('data:') || trimmed.startsWith('blob:')) {
    return appendAccessTokenToStorageUrl(trimmed);
  }
  return buildStorageUrl(trimmed, jobId ?? null);
}

function resolveChunkMetadataUrl(chunk: LiveMediaChunk, jobId: string | null): string | null {
  if (chunk.metadataUrl) {
    return resolveStorageUrl(chunk.metadataUrl, jobId);
  }
  if (chunk.metadataPath) {
    return resolveStorageUrl(chunk.metadataPath, jobId);
  }
  return null;
}

function resolveChunkAudioUrl(
  chunk: LiveMediaChunk,
  jobId: string | null,
  originalAudioEnabled: boolean,
  translationAudioEnabled: boolean,
): string | null {
  const tracks = chunk.audioTracks ?? null;
  const translationUrl =
    tracks?.translation?.url ??
    tracks?.translation?.path ??
    tracks?.trans?.url ??
    tracks?.trans?.path ??
    null;
  const originalUrl =
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.orig?.url ??
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.orig?.path ??
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.original?.url ??
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.original?.path ??
    null;
  const combinedUrl =
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.orig_trans?.url ??
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.orig_trans?.path ??
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.combined?.url ??
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.combined?.path ??
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.mix?.url ??
    (tracks as Record<string, AudioTrackMetadata | null | undefined>)?.mix?.path ??
    null;

  const candidate =
    (translationAudioEnabled ? translationUrl : null) ??
    (originalAudioEnabled ? originalUrl : null) ??
    (translationAudioEnabled ? combinedUrl : null) ??
    (originalAudioEnabled ? combinedUrl : null) ??
    translationUrl ??
    originalUrl ??
    combinedUrl;

  return resolveStorageUrl(candidate, jobId);
}

function resolveActiveSentenceNumber(chunk: LiveMediaChunk | null, activeSentenceIndex: number): number {
  if (chunk?.sentences && chunk.sentences.length > 0) {
    const entry = chunk.sentences[Math.max(0, Math.min(activeSentenceIndex, chunk.sentences.length - 1))];
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
}

function findChunkForSentence(chunks: LiveMediaChunk[], sentenceNumber: number): LiveMediaChunk | null {
  for (const chunk of chunks) {
    const start = typeof chunk.startSentence === 'number' ? Math.trunc(chunk.startSentence) : null;
    const end = typeof chunk.endSentence === 'number' ? Math.trunc(chunk.endSentence) : null;
    if (start !== null && end !== null && sentenceNumber >= start && sentenceNumber <= end) {
      return chunk;
    }
    const sentenceCount = typeof chunk.sentenceCount === 'number' ? Math.trunc(chunk.sentenceCount) : null;
    if (start !== null && sentenceCount !== null) {
      const inferredEnd = start + Math.max(sentenceCount - 1, 0);
      if (sentenceNumber >= start && sentenceNumber <= inferredEnd) {
        return chunk;
      }
    }
    if (chunk.sentences && chunk.sentences.length > 0) {
      if (chunk.sentences.some((entry) => Math.trunc(entry?.sentence_number ?? -1) === sentenceNumber)) {
        return chunk;
      }
    }
  }
  return null;
}

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
  const [prefetchedSentences, setPrefetchedSentences] = useState<Record<string, ChunkSentenceMetadata[]>>({});
  const prefetchedSentencesRef = useRef(prefetchedSentences);
  const metadataAttemptRef = useRef<Map<string, number>>(new Map());
  const metadataInFlightRef = useRef<Set<string>>(new Set());
  const audioAttemptRef = useRef<Map<string, number>>(new Map());
  const audioInFlightRef = useRef<Set<string>>(new Set());
  const prefetchedAudioRef = useRef<Set<string>>(new Set());
  const lastPrefetchSentenceRef = useRef<number | null>(null);

  useEffect(() => {
    prefetchedSentencesRef.current = prefetchedSentences;
  }, [prefetchedSentences]);

  useEffect(() => {
    setPrefetchedSentences({});
    prefetchedSentencesRef.current = {};
    metadataAttemptRef.current.clear();
    metadataInFlightRef.current.clear();
    audioAttemptRef.current.clear();
    audioInFlightRef.current.clear();
    prefetchedAudioRef.current.clear();
    lastPrefetchSentenceRef.current = null;
  }, [jobId, playerMode]);

  const hydrateChunk = useCallback(
    (target: LiveMediaChunk): LiveMediaChunk => {
      if (target.sentences && target.sentences.length > 0) {
        return target;
      }
      const key = resolveChunkKey(target);
      if (!key) {
        return target;
      }
      const cached = prefetchedSentences[key];
      if (!cached || cached.length === 0) {
        return target;
      }
      return {
        ...target,
        sentences: cached,
        sentenceCount:
          typeof target.sentenceCount === 'number' && Number.isFinite(target.sentenceCount)
            ? target.sentenceCount
            : cached.length,
      };
    },
    [prefetchedSentences],
  );
  const resolvedChunk = useMemo(() => (chunk ? hydrateChunk(chunk) : null), [chunk, hydrateChunk]);
  const resolvedChunks = useMemo(() => {
    if (!Array.isArray(chunks)) {
      return null;
    }
    const hydrated = chunks.map((entry) => (entry ? hydrateChunk(entry) : null));
    return hydrated.filter((entry): entry is LiveMediaChunk => Boolean(entry));
  }, [chunks, hydrateChunk]);
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
  const [manualSelection, setManualSelection] = useState<TextPlayerTokenSelection | null>(null);
  const [multiSelection, setMultiSelection] = useState<TextPlayerMultiSelection | null>(null);
  const activeTextSentence =
    textPlayerSentences && textPlayerSentences.length > 0 ? textPlayerSentences[0] : null;
  const prefetchChunkMetadata = useCallback(
    async (target: LiveMediaChunk) => {
      if (playerMode !== 'online') {
        return;
      }
      if (target.sentences && target.sentences.length > 0) {
        return;
      }
      const key = resolveChunkKey(target);
      if (!key || prefetchedSentencesRef.current[key]) {
        return;
      }
      if (metadataInFlightRef.current.has(key)) {
        return;
      }
      const lastAttempt = metadataAttemptRef.current.get(key);
      const now = Date.now();
      if (lastAttempt && now - lastAttempt < METADATA_PREFETCH_RETRY_MS) {
        return;
      }
      const metadataUrl = resolveChunkMetadataUrl(target, jobId);
      if (!metadataUrl) {
        return;
      }
      metadataAttemptRef.current.set(key, now);
      metadataInFlightRef.current.add(key);
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), PREFETCH_TIMEOUT_MS);
      try {
        const response = await fetch(metadataUrl, {
          method: 'GET',
          cache: 'no-store',
          signal: controller.signal,
        });
        if (!response.ok) {
          return;
        }
        const payload = (await response.json()) as unknown;
        const sentences = Array.isArray(payload)
          ? (payload as ChunkSentenceMetadata[])
          : Array.isArray((payload as { sentences?: ChunkSentenceMetadata[] })?.sentences)
            ? (payload as { sentences?: ChunkSentenceMetadata[] }).sentences ?? null
            : null;
        if (!sentences || sentences.length === 0) {
          return;
        }
        setPrefetchedSentences((current) => {
          if (current[key]) {
            return current;
          }
          return { ...current, [key]: sentences };
        });
      } catch {
        return;
      } finally {
        window.clearTimeout(timeout);
        metadataInFlightRef.current.delete(key);
      }
    },
    [jobId, playerMode],
  );

  const prefetchChunkAudio = useCallback(
    async (target: LiveMediaChunk) => {
      if (playerMode !== 'online') {
        return;
      }
      const audioUrl = resolveChunkAudioUrl(target, jobId, originalAudioEnabled, translationAudioEnabled);
      if (!audioUrl) {
        return;
      }
      if (prefetchedAudioRef.current.has(audioUrl)) {
        return;
      }
      if (audioInFlightRef.current.has(audioUrl)) {
        return;
      }
      const lastAttempt = audioAttemptRef.current.get(audioUrl);
      const now = Date.now();
      if (lastAttempt && now - lastAttempt < AUDIO_PREFETCH_RETRY_MS) {
        return;
      }
      audioAttemptRef.current.set(audioUrl, now);
      audioInFlightRef.current.add(audioUrl);
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), PREFETCH_TIMEOUT_MS);
      try {
        const response = await fetch(audioUrl, {
          method: 'GET',
          headers: {
            Range: AUDIO_PREFETCH_RANGE,
          },
          signal: controller.signal,
        });
        if (response.ok) {
          prefetchedAudioRef.current.add(audioUrl);
        }
      } catch {
        return;
      } finally {
        window.clearTimeout(timeout);
        audioInFlightRef.current.delete(audioUrl);
      }
    },
    [jobId, originalAudioEnabled, playerMode, translationAudioEnabled],
  );

  useEffect(() => {
    if (playerMode !== 'online') {
      return;
    }
    const chunkList = Array.isArray(activeChunks) ? activeChunks : [];
    if (!activeChunk || chunkList.length === 0) {
      return;
    }
    const activeSentenceNumber = resolveActiveSentenceNumber(activeChunk, activeSentenceIndex);
    const hasActiveSentences = Boolean(activeChunk.sentences && activeChunk.sentences.length > 0);
    if (hasActiveSentences) {
      if (lastPrefetchSentenceRef.current === activeSentenceNumber) {
        return;
      }
      lastPrefetchSentenceRef.current = activeSentenceNumber;
    }
    const targetMap = new Map<string, LiveMediaChunk>();
    for (let offset = -PREFETCH_RADIUS; offset <= PREFETCH_RADIUS; offset += 1) {
      const candidate = activeSentenceNumber + offset;
      if (candidate <= 0) {
        continue;
      }
      const match = findChunkForSentence(chunkList, candidate);
      if (match) {
        const key = resolveChunkKey(match) ?? `sentence:${candidate}`;
        targetMap.set(key, match);
      }
    }
    if (targetMap.size === 0) {
      const activeKey = resolveChunkKey(activeChunk);
      const activeIndex = activeKey
        ? chunkList.findIndex((entry) => resolveChunkKey(entry) === activeKey)
        : -1;
      if (activeIndex >= 0) {
        for (let offset = -PREFETCH_RADIUS; offset <= PREFETCH_RADIUS; offset += 1) {
          const index = activeIndex + offset;
          if (index < 0 || index >= chunkList.length) {
            continue;
          }
          const entry = chunkList[index];
          const key = resolveChunkKey(entry) ?? `chunk:${index}`;
          targetMap.set(key, entry);
        }
      } else {
        const key = resolveChunkKey(activeChunk) ?? 'chunk:active';
        targetMap.set(key, activeChunk);
      }
    }
    targetMap.forEach((target) => {
      void prefetchChunkMetadata(target);
      void prefetchChunkAudio(target);
    });
  }, [
    activeChunk,
    activeChunks,
    activeSentenceIndex,
    playerMode,
    prefetchChunkAudio,
    prefetchChunkMetadata,
  ]);

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
    onLookupLanguageChange: handleLookupLanguageChange,
    onLlmModelChange: handleLlmModelChange,
  } = linguist;

  useEffect(() => {
    setManualSelection(null);
    setMultiSelection(null);
  }, [activeTextSentence?.id]);

  useEffect(() => {
    if (isInlineAudioPlaying) {
      setManualSelection(null);
      setMultiSelection(null);
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
    if (!isVariantVisible(navigation.variantKind)) {
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
    setMultiSelection(null);
  }, [activeTextSentence, isInlineAudioPlaying, isVariantVisible, linguistBubble?.navigation]);

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
  const { selection: textPlayerSelection, shadowSelection: textPlayerShadowSelection } = useMemo(() => {
    if (!activeTextSentence) {
      return { selection: null, shadowSelection: null };
    }

    const variantForKind = (kind: TextPlayerVariantKind) => {
      if (!isVariantVisible(kind)) {
        return null;
      }
      return activeTextSentence.variants.find((variant) => variant.baseClass === kind) ?? null;
    };

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
  }, [activeTextSentence, isInlineAudioPlaying, isVariantVisible, linguistBubble?.navigation, manualSelection]);

  const textPlayerSelectionRange = useMemo<TextPlayerTokenRange | null>(() => {
    if (!activeTextSentence || isInlineAudioPlaying || !multiSelection) {
      return null;
    }
    if (multiSelection.sentenceIndex !== activeTextSentence.index) {
      return null;
    }
    if (!isVariantVisible(multiSelection.variantKind)) {
      return null;
    }
    const variant = activeTextSentence.variants.find(
      (entry) => entry.baseClass === multiSelection.variantKind,
    );
    if (!variant || variant.tokens.length === 0) {
      return null;
    }
    const maxIndex = variant.tokens.length - 1;
    const anchorIndex = Math.max(0, Math.min(multiSelection.anchorIndex, maxIndex));
    const focusIndex = Math.max(0, Math.min(multiSelection.focusIndex, maxIndex));
    return {
      sentenceIndex: activeTextSentence.index,
      variantKind: variant.baseClass,
      startIndex: Math.min(anchorIndex, focusIndex),
      endIndex: Math.max(anchorIndex, focusIndex),
    };
  }, [activeTextSentence, isInlineAudioPlaying, isVariantVisible, multiSelection]);
  const handleTextPlayerKeyDown = useCallback(
    (event: ReactKeyboardEvent<HTMLDivElement>) => {
      if (isInlineAudioPlaying || !activeTextSentence) {
        return;
      }
      const key = event.key;
      const isArrow =
        key === 'ArrowLeft' || key === 'ArrowRight' || key === 'ArrowUp' || key === 'ArrowDown';
      const isShift = event.shiftKey;
      const isHorizontal = key === 'ArrowLeft' || key === 'ArrowRight';
      if (key !== 'Enter' && !isArrow) {
        return;
      }
      const variants = activeTextSentence.variants.filter(
        (variant) => variant.tokens.length > 0 && isVariantVisible(variant.baseClass),
      );
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
      const clampIndex = (value: number) => Math.max(0, Math.min(value, tokenCount - 1));
      const activeMultiSelection =
        multiSelection &&
        multiSelection.sentenceIndex === activeTextSentence.index &&
        multiSelection.variantKind === currentVariant.baseClass
          ? multiSelection
          : null;

      if (key === 'Enter') {
        const anchorIndex = activeMultiSelection
          ? clampIndex(activeMultiSelection.anchorIndex)
          : clampIndex(current.tokenIndex);
        const focusIndex = activeMultiSelection
          ? clampIndex(activeMultiSelection.focusIndex)
          : clampIndex(current.tokenIndex);
        const rangeStart = Math.min(anchorIndex, focusIndex);
        const rangeEnd = Math.max(anchorIndex, focusIndex);
        const selectedTokens = activeMultiSelection
          ? currentVariant.tokens.slice(rangeStart, rangeEnd + 1)
          : [currentVariant.tokens[focusIndex]];
        const tokenText = selectedTokens.join(' ').trim();
        if (!tokenText) {
          return;
        }
        const selector = [
          `[data-sentence-index="${current.sentenceIndex}"]`,
          `[data-text-player-token="true"][data-text-player-variant="${currentVariant.baseClass}"][data-text-player-token-index="${focusIndex}"]`,
        ].join(' ');
        const candidate = containerRef.current?.querySelector(selector);
        const anchorElement = candidate instanceof HTMLElement ? candidate : null;
        openLinguistTokenLookup(tokenText, currentVariant.baseClass, anchorElement, {
          sentenceIndex: activeTextSentence.index,
          tokenIndex: focusIndex,
          variantKind: currentVariant.baseClass,
        });
        event.preventDefault();
        event.stopPropagation();
        return;
      }

      if (!isShift || !isHorizontal) {
        setMultiSelection(null);
      }

      let nextSelection: TextPlayerTokenSelection | null = null;
      if (isHorizontal) {
        const delta = key === 'ArrowRight' ? 1 : -1;
        const baseFocusIndex = activeMultiSelection
          ? clampIndex(activeMultiSelection.focusIndex)
          : clampIndex(current.tokenIndex);
        const anchorIndex = activeMultiSelection
          ? clampIndex(activeMultiSelection.anchorIndex)
          : clampIndex(current.tokenIndex);
        let nextIndex = baseFocusIndex + delta;
        if (isShift) {
          if (nextIndex < 0) {
            nextIndex = 0;
          } else if (nextIndex >= tokenCount) {
            nextIndex = tokenCount - 1;
          }
        } else {
          if (nextIndex < 0) {
            nextIndex = tokenCount - 1;
          } else if (nextIndex >= tokenCount) {
            nextIndex = 0;
          }
        }
        nextSelection = {
          sentenceIndex: activeTextSentence.index,
          variantKind: currentVariant.baseClass,
          tokenIndex: nextIndex,
        };
        if (isShift) {
          setMultiSelection({
            sentenceIndex: activeTextSentence.index,
            variantKind: currentVariant.baseClass,
            anchorIndex,
            focusIndex: nextIndex,
          });
        }
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
    [
      activeTextSentence,
      isInlineAudioPlaying,
      isVariantVisible,
      multiSelection,
      openLinguistTokenLookup,
      textPlayerSelection,
    ],
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
        lookupLanguageOptions={linguistLookupLanguageOptions}
        onLookupLanguageChange={handleLookupLanguageChange}
        llmModelOptions={linguistLlmModelOptions}
        onLlmModelChange={handleLlmModelChange}
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
                onClose={closeLinguistBubble}
                lookupLanguageOptions={linguistLookupLanguageOptions}
                onLookupLanguageChange={handleLookupLanguageChange}
                llmModelOptions={linguistLlmModelOptions}
                onLlmModelChange={handleLlmModelChange}
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
