import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import type {
  CSSProperties,
  ReactNode,
  UIEvent,
} from 'react';
import {
  appendAccessToken,
  fetchJobTiming,
} from '../api/client';
import type {
  AudioTrackMetadata,
  JobTimingResponse,
} from '../api/dtos';
import type { LiveMediaChunk, MediaClock } from '../hooks/useLiveMedia';
import { useMediaClock } from '../hooks/useLiveMedia';
import { usePlayerCore } from '../hooks/usePlayerCore';
import {
  start as startAudioSync,
  stop as stopAudioSync,
} from '../player/AudioSyncController';
import { timingStore } from '../stores/timingStore';
import { DebugOverlay } from '../player/DebugOverlay';
import '../styles/debug-overlay.css';
import type { TimingPayload } from '../types/timing';
import TextPlayer, {
  type TextPlayerVariantKind,
} from '../text-player/TextPlayer';
import type { ChunkSentenceMetadata, TrackTimingPayload } from '../api/dtos';
import { buildWordIndex } from '../lib/timing/wordSync';
import { WORD_SYNC, normaliseTranslationSpeed } from './player-panel/constants';
import { useLanguagePreferences } from '../context/LanguageProvider';
import { useMyPainter } from '../context/MyPainterProvider';
import type { InteractiveTextTheme } from '../types/interactiveTextTheme';
import PlayerChannelBug from './PlayerChannelBug';
import {
  EMPTY_TIMING_PAYLOAD,
} from './interactive-text/constants';
import { InteractiveFullscreenControls } from './interactive-text/InteractiveFullscreenControls';
import { InlineAudioPlayer } from './interactive-text/InlineAudioPlayer';
import { MyLinguistBubble } from './interactive-text/MyLinguistBubble';
import type {
  SentenceGate,
  WordSyncController,
  WordSyncLane,
  WordSyncRenderableToken,
  WordSyncSentence,
} from './interactive-text/types';
import {
  buildParagraphs,
  buildSentenceGateList,
  buildTimingPayloadFromJobTiming,
  buildTimingPayloadFromWordIndex,
  computeTimingMetrics,
  rgbaFromHex,
} from './interactive-text/utils';
import { useLinguistBubble } from './interactive-text/useLinguistBubble';
import { useLibraryMediaOrigin } from './interactive-text/useLibraryMediaOrigin';
import { useMyPainterSentence } from './interactive-text/useMyPainterSentence';
import { useSlideIndicator } from './interactive-text/useSlideIndicator';
import { useSentenceImageReel } from './interactive-text/useSentenceImageReel';
import { createNoopWordSyncController, createWordSyncController } from './interactive-text/wordSyncController';
import { useTextPlayerSentences } from './interactive-text/useTextPlayerSentences';
import { useTimelineDisplay } from './interactive-text/useTimelineDisplay';

type InlineAudioControls = {
  pause: () => void;
  play: () => void;
};

interface InteractiveTextViewerProps {
  content: string;
  rawContent?: string | null;
  chunk: LiveMediaChunk | null;
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
  audioTracks?: Record<string, AudioTrackMetadata> | null;
  activeTimingTrack?: 'mix' | 'translation';
  originalAudioEnabled?: boolean;
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
}

const InteractiveTextViewer = forwardRef<HTMLDivElement | null, InteractiveTextViewerProps>(function InteractiveTextViewer(
  {
    content,
    rawContent = null,
    chunk,
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
    audioTracks = null,
    activeTimingTrack = 'translation',
    originalAudioEnabled = false,
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
  const resolvedJobOriginalLanguage = useMemo(() => {
    const trimmed = typeof jobOriginalLanguage === 'string' ? jobOriginalLanguage.trim() : '';
    return trimmed.length > 0 ? trimmed : null;
  }, [jobOriginalLanguage]);
  const resolvedJobTranslationLanguage = useMemo(() => {
    const trimmed = typeof jobTranslationLanguage === 'string' ? jobTranslationLanguage.trim() : '';
    return trimmed.length > 0 ? trimmed : null;
  }, [jobTranslationLanguage]);
  const resolvedCueVisibility = useMemo(() => {
    return (
      cueVisibility ?? {
        original: true,
        transliteration: true,
        translation: true,
      }
    );
  }, [cueVisibility]);
  const isVariantVisible = useCallback(
    (variant: TextPlayerVariantKind) => {
      if (variant === 'translit') {
        return resolvedCueVisibility.transliteration;
      }
      return resolvedCueVisibility[variant];
    },
    [resolvedCueVisibility],
  );
  const resolvedTranslationSpeed = useMemo(
    () => normaliseTranslationSpeed(translationSpeed),
    [translationSpeed],
  );
  const safeBookTitle = typeof bookTitle === 'string' ? bookTitle.trim() : '';
  const safeBookMeta = useMemo(() => {
    const parts: string[] = [];
    if (typeof bookAuthor === 'string' && bookAuthor.trim()) {
      parts.push(bookAuthor.trim());
    }
    if (typeof bookYear === 'string' && bookYear.trim()) {
      parts.push(bookYear.trim());
    }
    if (typeof bookGenre === 'string' && bookGenre.trim()) {
      parts.push(bookGenre.trim());
    }
    return parts.join(' · ');
  }, [bookAuthor, bookGenre, bookYear]);
  const safeInfoTitle = useMemo(() => {
    const trimmed = typeof infoTitle === 'string' ? infoTitle.trim() : '';
    if (trimmed) {
      return trimmed;
    }
    return safeBookTitle;
  }, [infoTitle, safeBookTitle]);
  const safeInfoMeta = useMemo(() => {
    const trimmed = typeof infoMeta === 'string' ? infoMeta.trim() : '';
    if (trimmed) {
      return trimmed;
    }
    return safeBookMeta;
  }, [infoMeta, safeBookMeta]);
  const safeFontScale = useMemo(() => {
    if (!Number.isFinite(fontScale) || fontScale <= 0) {
      return 1;
    }
    const clamped = Math.min(Math.max(fontScale, 0.5), 3);
    return Math.round(clamped * 100) / 100;
  }, [fontScale]);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const formatRem = useCallback((value: number) => `${Math.round(value * 1000) / 1000}rem`, []);
  const safeBackgroundOpacity = useMemo(() => {
    const raw = Number(backgroundOpacityPercent);
    if (!Number.isFinite(raw)) {
      return 100;
    }
    return Math.round(Math.min(Math.max(raw, 0), 100));
  }, [backgroundOpacityPercent]);
  const safeSentenceCardOpacity = useMemo(() => {
    const raw = Number(sentenceCardOpacityPercent);
    if (!Number.isFinite(raw)) {
      return 100;
    }
    return Math.round(Math.min(Math.max(raw, 0), 100));
  }, [sentenceCardOpacityPercent]);
  const bodyStyle = useMemo<CSSProperties>(() => {
    const baseSentenceFont = (isFullscreen ? 1.32 : 1.08) * safeFontScale;
    const activeSentenceFont = (isFullscreen ? 1.56 : 1.28) * safeFontScale;
    const style: Record<string, string | number> = {
      '--interactive-font-scale': safeFontScale,
      '--tp-sentence-font-size': formatRem(baseSentenceFont),
      '--tp-sentence-active-font-size': formatRem(activeSentenceFont),
    };

    if (theme) {
      const alpha = safeBackgroundOpacity / 100;
      const resolvedBackground = rgbaFromHex(theme.background, alpha) ?? theme.background;
      style['--interactive-bg'] = resolvedBackground;
      style['--interactive-color-original'] = theme.original;
      style['--interactive-color-original-active'] = theme.originalActive;
      style['--interactive-color-translation'] = theme.translation;
      style['--interactive-color-transliteration'] = theme.transliteration;

      const originalMuted = rgbaFromHex(theme.original, 0.75);
      if (originalMuted) {
        style['--interactive-color-original-muted'] = originalMuted;
      }

      const highlightStrong = rgbaFromHex(theme.highlight, 0.85);
      const highlightSoft = rgbaFromHex(theme.highlight, 0.3);
      const highlightVerySoft = rgbaFromHex(theme.highlight, 0.2);
      const highlightSentenceBg = rgbaFromHex(theme.highlight, 0.45);
      const highlightOutline = rgbaFromHex(theme.highlight, 0.35);

      if (highlightStrong) {
        style['--interactive-highlight-strong'] = highlightStrong;
      }
      if (highlightSoft) {
        style['--interactive-highlight-soft'] = highlightSoft;
      }
      if (highlightVerySoft) {
        style['--interactive-highlight-very-soft'] = highlightVerySoft;
      }
      if (highlightSentenceBg) {
        style['--interactive-highlight-sentence-bg'] = highlightSentenceBg;
      }
      if (highlightOutline) {
        style['--interactive-highlight-outline'] = highlightOutline;
      }

      style['--tp-bg'] = resolvedBackground;
      style['--tp-original'] = theme.original;
      style['--tp-translit'] = theme.transliteration;
      style['--tp-translation'] = theme.translation;
      style['--tp-progress'] = theme.highlight;

      const cardScale = safeSentenceCardOpacity / 100;
      const sentenceBg = rgbaFromHex(theme.highlight, 0.06 * cardScale);
      const sentenceActiveBg = rgbaFromHex(theme.highlight, 0.16 * cardScale);
      const sentenceShadowColor = rgbaFromHex(theme.highlight, 0.22 * cardScale);
      if (sentenceBg) {
        style['--tp-sentence-bg'] = sentenceBg;
      }
      if (sentenceActiveBg) {
        style['--tp-sentence-active-bg'] = sentenceActiveBg;
      }
      if (sentenceShadowColor) {
        style['--tp-sentence-active-shadow'] = `0 6px 26px ${sentenceShadowColor}`;
      } else if (cardScale <= 0.01) {
        style['--tp-sentence-active-shadow'] = 'none';
      }
    }

    return style as CSSProperties;
  }, [formatRem, isFullscreen, safeBackgroundOpacity, safeFontScale, safeSentenceCardOpacity, theme]);
  const safeInfoGlyph = useMemo(() => {
    if (typeof infoGlyph !== 'string') {
      return 'JOB';
    }
    const trimmed = infoGlyph.trim();
    return trimmed ? trimmed : 'JOB';
  }, [infoGlyph]);
  const hasChannelBug = typeof infoGlyph === 'string' && infoGlyph.trim().length > 0;
  const resolvedCoverUrlFromProps = useMemo(() => {
    const primary = typeof infoCoverUrl === 'string' ? infoCoverUrl.trim() : '';
    if (primary) {
      return primary;
    }
    const legacy = typeof bookCoverUrl === 'string' ? bookCoverUrl.trim() : '';
    return legacy || null;
  }, [bookCoverUrl, infoCoverUrl]);
  const resolvedSecondaryCoverUrlFromProps = useMemo(() => {
    const secondary = typeof infoCoverSecondaryUrl === 'string' ? infoCoverSecondaryUrl.trim() : '';
    return secondary || null;
  }, [infoCoverSecondaryUrl]);
  const [viewportCoverFailed, setViewportCoverFailed] = useState(false);
  const [viewportSecondaryCoverFailed, setViewportSecondaryCoverFailed] = useState(false);
  useEffect(() => {
    setViewportCoverFailed(false);
  }, [resolvedCoverUrlFromProps]);
  useEffect(() => {
    setViewportSecondaryCoverFailed(false);
  }, [resolvedSecondaryCoverUrlFromProps]);
  const resolvedCoverUrl = viewportCoverFailed ? null : resolvedCoverUrlFromProps;
  const resolvedSecondaryCoverUrl = viewportSecondaryCoverFailed ? null : resolvedSecondaryCoverUrlFromProps;
  const showSecondaryCover =
    Boolean(resolvedCoverUrl) && Boolean(resolvedSecondaryCoverUrl) && resolvedSecondaryCoverUrl !== resolvedCoverUrl;
  const showCoverArt = Boolean(resolvedCoverUrl);
  const showTextBadge = Boolean(safeInfoTitle || safeInfoMeta);
  const showInfoHeader = hasChannelBug || showCoverArt || showTextBadge;

  const resolvedInfoCoverVariant = useMemo(() => {
    const candidate = typeof infoCoverVariant === 'string' ? infoCoverVariant.trim().toLowerCase() : '';
    if (
      candidate === 'book' ||
      candidate === 'subtitles' ||
      candidate === 'video' ||
      candidate === 'youtube' ||
      candidate === 'nas' ||
      candidate === 'dub' ||
      candidate === 'job'
    ) {
      return candidate;
    }

    const glyph = safeInfoGlyph.trim().toLowerCase();
    if (glyph === 'bk' || glyph === 'book') {
      return 'book';
    }
    if (glyph === 'sub' || glyph === 'subtitle' || glyph === 'subtitles' || glyph === 'cc') {
      return 'subtitles';
    }
    if (glyph === 'yt' || glyph === 'youtube') {
      return 'youtube';
    }
    if (glyph === 'nas') {
      return 'nas';
    }
    if (glyph === 'dub') {
      return 'dub';
    }
    if (glyph === 'tv' || glyph === 'vid' || glyph === 'video') {
      return 'video';
    }
    return 'job';
  }, [infoCoverVariant, safeInfoGlyph]);

  const coverAltText =
    (typeof infoCoverAltText === 'string' && infoCoverAltText.trim() ? infoCoverAltText.trim() : null) ??
    (typeof bookCoverAltText === 'string' && bookCoverAltText.trim() ? bookCoverAltText.trim() : null) ??
    (safeInfoTitle ? `Cover for ${safeInfoTitle}` : 'Cover');
  const dictionarySuppressSeekRef = useRef(false);
  const {
    ref: attachPlayerCore,
    core: playerCore,
    elementRef: audioRef,
    mediaRef: rawAttachMediaElement,
  } = usePlayerCore();
  const progressTimerRef = useRef<number | null>(null);
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
  const attachMediaElement = useCallback(
    (element: HTMLAudioElement | null) => {
      rawAttachMediaElement(element);
      timingStore.setAudioEl(element);
    },
    [rawAttachMediaElement],
  );
  const tokenElementsRef = useRef<Map<string, HTMLElement>>(new Map());
  const sentenceElementsRef = useRef<Map<number, HTMLElement>>(new Map());
  const wordSyncControllerRef = useRef<WordSyncController | null>(null);
  const gateListRef = useRef<SentenceGate[]>([]);
  const clock = useMediaClock(audioRef);
  const clockRef = useRef<MediaClock>(clock);
  const diagnosticsSignatureRef = useRef<string | null>(null);
  const highlightPolicyRef = useRef<string | null>(null);
  const inlineAudioPlayingRef = useRef(false);
  const [jobTimingResponse, setJobTimingResponse] = useState<JobTimingResponse | null>(null);
  const [timingDiagnostics, setTimingDiagnostics] = useState<{ policy: string | null; estimated: boolean; punctuation?: boolean } | null>(null);

  useEffect(() => {
    clockRef.current = clock;
  }, [clock]);
  useEffect(() => {
    highlightPolicyRef.current = timingDiagnostics?.policy ?? null;
  }, [timingDiagnostics]);
  useEffect(() => {
    const element = playerCore?.getElement() ?? audioRef.current ?? null;
    timingStore.setAudioEl(element);
    return () => {
      if (timingStore.get().audioEl === element) {
        timingStore.setAudioEl(null);
      }
    };
  }, [playerCore]);

  const [prefersReducedMotion, setPrefersReducedMotion] = useState<boolean>(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return false;
    }
    try {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch {
      return false;
    }
  });
  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return;
    }
    let mounted = true;
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => {
      if (!mounted) {
        return;
      }
      setPrefersReducedMotion(media.matches);
    };
    update();
    try {
      if (typeof media.addEventListener === 'function') {
        media.addEventListener('change', update);
        return () => {
          mounted = false;
          media.removeEventListener('change', update);
        };
      }
      if (typeof media.addListener === 'function') {
        media.addListener(update);
        return () => {
          mounted = false;
          media.removeListener(update);
        };
      }
    } catch {
      // Ignore listener registration errors.
    }
    return () => {
      mounted = false;
    };
  }, []);
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
  const [chunkTime, setChunkTime] = useState(0);
  const hasTimeline = Boolean(chunk?.sentences && chunk.sentences.length > 0);
  const useCombinedPhases = Boolean(
    originalAudioEnabled &&
      (audioTracks?.orig_trans?.url || audioTracks?.orig_trans?.path),
  );
  const [audioDuration, setAudioDuration] = useState<number | null>(null);
  const [activeSentenceIndex, setActiveSentenceIndex] = useState(0);
  const [activeSentenceProgress, setActiveSentenceProgress] = useState(0);
  const wordSyncQueryState = useMemo<boolean | null>(() => {
    if (typeof window === 'undefined') {
      return null;
    }
    try {
      const params = new URLSearchParams(window.location.search);
      const raw = params.get('wordsync');
      if (raw === null) {
        return null;
      }
      if (raw === '0' || raw.toLowerCase() === 'false') {
        return false;
      }
      return true;
    } catch {
      return null;
    }
  }, []);
  const wordSyncAllowed = (wordSyncQueryState ?? WORD_SYNC.FEATURE) === true;
  const followHighlightEnabled = !prefersReducedMotion;
  useEffect(() => {
    if (!jobId || !wordSyncAllowed) {
      setJobTimingResponse(null);
      setTimingDiagnostics(null);
      return;
    }
    const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    let cancelled = false;
    setJobTimingResponse(null);
    setTimingDiagnostics(null);
    (async () => {
      try {
        const response = await fetchJobTiming(jobId, controller?.signal);
        if (cancelled || controller?.signal.aborted) {
          return;
        }
        if (!response) {
          setJobTimingResponse(null);
          setTimingDiagnostics(null);
          return;
        }
        setJobTimingResponse(response);
      } catch (error) {
        if (controller?.signal.aborted || cancelled) {
          return;
        }
        if (import.meta.env.DEV) {
          console.debug('Failed to load job timing data', error);
        }
        setJobTimingResponse(null);
        setTimingDiagnostics(null);
      }
    })();
    return () => {
      cancelled = true;
      if (controller) {
        controller.abort();
      }
    };
  }, [jobId, wordSyncAllowed]);

  const paragraphs = useMemo(() => buildParagraphs(content), [content]);
  const { timelineSentences, timelineDisplay } = useTimelineDisplay({
    chunk,
    hasTimeline,
    useCombinedPhases,
    audioDuration,
    chunkTime,
    activeSentenceIndex,
    isVariantVisible,
    revealMemoryRef,
  });

  const { rawSentences, textPlayerSentences, sentenceWeightSummary } = useTextPlayerSentences({
    paragraphs,
    timelineDisplay,
    chunk,
    activeSentenceIndex,
    cueVisibility: resolvedCueVisibility,
  });
  const totalSentences = useMemo(
    () => paragraphs.reduce((count, paragraph) => count + paragraph.sentences.length, 0),
    [paragraphs],
  );

  const seekInlineAudioToTime = useCallback((time: number) => {
    if (dictionarySuppressSeekRef.current) {
      return;
    }
    const element = audioRef.current;
    if (!element || !Number.isFinite(time)) {
      return;
    }
    try {
      wordSyncControllerRef.current?.handleSeeking();
      const target = Math.max(0, Math.min(time, Number.isFinite(element.duration) ? element.duration : time));
      element.currentTime = target;
      setChunkTime(target);
      // Keep playback paused while stepping between words.
      wordSyncControllerRef.current?.snap();
    } catch {
      // Ignore seek/play failures.
    }
  }, [setChunkTime]);

  const linguist = useLinguistBubble({
    containerRef,
    audioRef,
    inlineAudioPlayingRef,
    dictionarySuppressSeekRef,
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
    bubbleRef: linguistBubbleRef,
    floatingPlacement: linguistBubbleFloatingPlacement,
    floatingPosition: linguistBubbleFloatingPosition,
    canNavigatePrev: linguistCanNavigatePrev,
    canNavigateNext: linguistCanNavigateNext,
    onTogglePinned: toggleLinguistBubblePinned,
    onClose: closeLinguistBubble,
    onSpeak: handleLinguistSpeak,
    onSpeakSlow: handleLinguistSpeakSlow,
    onNavigateWord: navigateLinguistWord,
    onTokenClickCapture: handleLinguistTokenClickCapture,
    onPointerDownCapture: handlePointerDownCapture,
    onPointerMoveCapture: handlePointerMoveCapture,
    onPointerUpCaptureWithSelection: handlePointerUpCaptureWithSelection,
    onPointerCancelCapture: handlePointerCancelCapture,
    onBackgroundClick: handleInteractiveBackgroundClick,
    requestPositionUpdate: requestLinguistBubblePositionUpdate,
  } = linguist;

  const effectiveAudioUrl = useMemo(() => {
    const combinedUrl = audioTracks?.orig_trans?.url ?? null;
    const translationUrl = audioTracks?.translation?.url ?? audioTracks?.trans?.url ?? null;
    if (originalAudioEnabled && combinedUrl) {
      return combinedUrl;
    }
    if (activeAudioUrl) {
      return activeAudioUrl;
    }
    if (translationUrl) {
      return translationUrl;
    }
    if (combinedUrl) {
      return combinedUrl;
    }
    return null;
  }, [activeAudioUrl, audioTracks, originalAudioEnabled]);

  const resolvedAudioUrl = useMemo(
    () => (effectiveAudioUrl ? appendAccessToken(effectiveAudioUrl) : null),
    [effectiveAudioUrl],
  );
  const chunkSentenceMap = useMemo(() => {
    const map = new Map<number, ChunkSentenceMetadata>();
    if (!chunk?.sentences || chunk.sentences.length === 0) {
      return map;
    }
    chunk.sentences.forEach((metadata, index) => {
      const rawId = metadata?.sentence_number;
      const sentenceId =
        typeof rawId === 'number' && Number.isFinite(rawId) ? rawId : index;
      map.set(sentenceId, metadata);
    });
    return map;
  }, [chunk?.sentences]);
  const wordSyncTracks = chunk?.timingTracks ?? null;
  const wordSyncTrackCandidates = useMemo(() => {
    if (!wordSyncTracks || wordSyncTracks.length === 0) {
      return [] as TrackTimingPayload[];
    }
    const chunkId = chunk?.chunkId ?? null;
    if (!chunkId) {
      return wordSyncTracks.filter((track): track is TrackTimingPayload => Boolean(track));
    }
    const matches = wordSyncTracks.filter(
      (track): track is TrackTimingPayload => Boolean(track && track.chunkId === chunkId)
    );
    return matches.length > 0 ? matches : wordSyncTracks.filter((track): track is TrackTimingPayload => Boolean(track));
  }, [chunk?.chunkId, wordSyncTracks]);
  const wordSyncPreferredTypes = useMemo(() => {
    const preferences: TrackTimingPayload['trackType'][] = [];
    const combinedUrl = audioTracks?.orig_trans?.url ?? null;
    const preferred =
      originalAudioEnabled && combinedUrl && effectiveAudioUrl === combinedUrl
        ? 'original_translated'
        : 'translated';
    preferences.push(preferred);
    if (!preferences.includes('translated')) {
      preferences.push('translated');
    }
    if (!preferences.includes('original_translated')) {
      preferences.push('original_translated');
    }
    return preferences;
  }, [audioTracks, effectiveAudioUrl, originalAudioEnabled]);
  const selectedWordSyncTrack = useMemo(() => {
    if (wordSyncTrackCandidates.length === 0) {
      return null;
    }
    for (const type of wordSyncPreferredTypes) {
      const match = wordSyncTrackCandidates.find((track) => track.trackType === type);
      if (match) {
        return match;
      }
    }
    return wordSyncTrackCandidates[0] ?? null;
  }, [wordSyncPreferredTypes, wordSyncTrackCandidates]);
  const wordIndex = useMemo(() => {
    if (!selectedWordSyncTrack) {
      return null;
    }
    return buildWordIndex(selectedWordSyncTrack);
  }, [selectedWordSyncTrack]);
  const legacyWordSyncEnabled = false;
  const wordSyncSentences = useMemo<WordSyncSentence[] | null>(() => {
    if (!legacyWordSyncEnabled) {
      return null;
    }
    if (!wordIndex) {
      return null;
    }
    const sentences = new Map<
      number,
      { orig: WordSyncRenderableToken[]; trans: WordSyncRenderableToken[]; xlit: WordSyncRenderableToken[] }
    >();
    const ensureBuckets = (sentenceId: number) => {
      let bucket = sentences.get(sentenceId);
      if (!bucket) {
        bucket = { orig: [], trans: [], xlit: [] };
        sentences.set(sentenceId, bucket);
      }
      return bucket;
    };
    wordIndex.words.forEach((word) => {
      const bucket = ensureBuckets(word.sentenceId);
      const metadata = chunkSentenceMap.get(word.sentenceId);
      let displayText = typeof word.text === 'string' ? word.text : '';
      if (metadata) {
        const variantTokens =
          word.lang === 'orig'
            ? metadata.original?.tokens
            : word.lang === 'trans'
              ? metadata.translation?.tokens
              : metadata.transliteration?.tokens;
        if (Array.isArray(variantTokens)) {
          const token = variantTokens[word.tokenIdx];
          if (typeof token === 'string' && token.trim().length > 0) {
            displayText = token;
          }
        }
      }
      if (!displayText || !displayText.trim()) {
        displayText = word.text || '';
      }
      const renderable: WordSyncRenderableToken = {
        ...word,
        displayText,
      };
      bucket[word.lang].push(renderable);
    });
    const entries = Array.from(sentences.entries());
    if (entries.length === 0) {
      return [];
    }
    entries.sort((a, b) => a[0] - b[0]);
    return entries.map(([sentenceId, lanes]) => {
      (['orig', 'trans', 'xlit'] as WordSyncLane[]).forEach((lane) => {
        lanes[lane].sort((left, right) => {
          if (left.tokenIdx !== right.tokenIdx) {
            return left.tokenIdx - right.tokenIdx;
          }
          if (left.t0 !== right.t0) {
            return left.t0 - right.t0;
          }
          return left.id.localeCompare(right.id);
        });
      });
      return {
        id: `ws-sentence-${sentenceId}`,
        sentenceId,
        tokens: lanes,
      };
    });
  }, [chunkSentenceMap, legacyWordSyncEnabled, wordIndex]);
  const hasRemoteTiming = wordSyncAllowed && jobTimingResponse !== null;
  const hasLegacyWordSync = wordSyncAllowed && Boolean(selectedWordSyncTrack && wordIndex);
  const hasWordSyncData =
    hasRemoteTiming ||
    (hasLegacyWordSync &&
      (legacyWordSyncEnabled ? Boolean(wordSyncSentences && wordSyncSentences.length > 0) : true));
  const shouldUseWordSync = hasWordSyncData;
  const activeWordSyncTrack =
    !hasRemoteTiming && shouldUseWordSync && selectedWordSyncTrack ? selectedWordSyncTrack : null;
  const activeWordIndex =
    !hasRemoteTiming && shouldUseWordSync && wordIndex ? wordIndex : null;
  const remoteTrackPayload = useMemo<TimingPayload | null>(() => {
    if (!hasRemoteTiming || !jobTimingResponse) {
      return null;
    }
    return buildTimingPayloadFromJobTiming(jobTimingResponse, activeTimingTrack);
  }, [activeTimingTrack, hasRemoteTiming, jobTimingResponse]);

  const timingPayload = useMemo<TimingPayload | null>(() => {
    if (remoteTrackPayload) {
      return remoteTrackPayload;
    }
    if (!hasLegacyWordSync || !activeWordSyncTrack || !activeWordIndex) {
      return null;
    }
    return buildTimingPayloadFromWordIndex(activeWordSyncTrack, activeWordIndex);
  }, [activeWordIndex, activeWordSyncTrack, hasLegacyWordSync, remoteTrackPayload]);
  const timingPlaybackRate = useMemo(() => {
    const rate = timingPayload?.playbackRate;
    if (typeof rate === 'number' && Number.isFinite(rate) && rate > 0) {
      return rate;
    }
    return 1;
  }, [timingPayload]);
  const effectivePlaybackRate = useMemo(() => {
    const combined = timingPlaybackRate * resolvedTranslationSpeed;
    if (!Number.isFinite(combined) || combined <= 0) {
      return timingPlaybackRate;
    }
    return Math.round(combined * 1000) / 1000;
  }, [resolvedTranslationSpeed, timingPlaybackRate]);

  useEffect(() => {
    if (!timingPayload) {
      setTimingDiagnostics(null);
      return;
    }
    const policy =
      typeof jobTimingResponse?.highlighting_policy === 'string' &&
      jobTimingResponse.highlighting_policy.trim()
        ? jobTimingResponse.highlighting_policy.trim()
        : null;
    const policyLower = policy ? policy.toLowerCase() : null;
    const hasEstimatedSegments =
      jobTimingResponse?.has_estimated_segments === true || policyLower === 'estimated';
    setTimingDiagnostics({
      policy,
      estimated: hasEstimatedSegments,
      punctuation: policyLower === 'estimated_punct',
    });
  }, [jobTimingResponse, timingPayload]);

  useEffect(() => {
    gateListRef.current = buildSentenceGateList(timingPayload);
    timingStore.setActiveGate(null);
  }, [timingPayload]);

  useEffect(() => {
    if (!jobId || !timingPayload) {
      diagnosticsSignatureRef.current = null;
      return;
    }
    const signature = [
      jobId,
      timingPayload.trackKind,
      String(timingPayload.segments.length),
      activeTimingTrack,
      jobTimingResponse?.highlighting_policy ?? 'unknown',
    ].join('|');
    if (diagnosticsSignatureRef.current === signature) {
      return;
    }
    diagnosticsSignatureRef.current = signature;
    if (!timingPayload.segments.length) {
      return;
    }
    const policy =
      typeof jobTimingResponse?.highlighting_policy === 'string' &&
      jobTimingResponse.highlighting_policy.trim()
        ? jobTimingResponse.highlighting_policy.trim()
        : null;
    const metrics = computeTimingMetrics(timingPayload, timingPayload.playbackRate);
    if (import.meta.env.DEV) {
      console.info('[Highlight diagnostics]', {
        jobId,
        trackKind: timingPayload.trackKind,
        policy: policy ?? 'unknown',
        avgTokenMs: Number(metrics.avgTokenMs.toFixed(2)),
        tempoRatio: Number(metrics.tempoRatio.toFixed(3)),
        uniformVsRealMeanDeltaMs: Number(metrics.uniformVsRealMeanDeltaMs.toFixed(2)),
        totalDriftMs: Number(metrics.totalDriftMs.toFixed(2)),
        track: activeTimingTrack,
      });
    }
  }, [jobId, timingPayload, activeTimingTrack, jobTimingResponse]);
  const registerTokenElement = useCallback((id: string, element: HTMLSpanElement | null) => {
    const map = tokenElementsRef.current;
    if (!element) {
      map.delete(id);
      return;
    }
    map.set(id, element);
  }, []);
  const registerSentenceElement = useCallback((sentenceId: number, element: HTMLDivElement | null) => {
    const map = sentenceElementsRef.current;
    if (!element) {
      map.delete(sentenceId);
      return;
    }
    map.set(sentenceId, element);
  }, []);
  useEffect(() => {
    if (!legacyWordSyncEnabled) {
      wordSyncControllerRef.current = null;
      return;
    }
    const controller = createWordSyncController({
      containerRef,
      tokenElementsRef,
      sentenceElementsRef,
      clockRef,
      config: WORD_SYNC,
      followHighlight: followHighlightEnabled,
      isPaused: () => {
        const element = audioRef.current;
        return !element || element.paused;
      },
      debugOverlay: { policyRef: highlightPolicyRef },
    });
    wordSyncControllerRef.current = controller;
    return () => {
      controller.destroy();
      wordSyncControllerRef.current = null;
    };
  }, [clockRef, containerRef, followHighlightEnabled, legacyWordSyncEnabled]);
  useEffect(() => {
    if (!legacyWordSyncEnabled) {
      return;
    }
    wordSyncControllerRef.current?.setFollowHighlight(followHighlightEnabled);
  }, [followHighlightEnabled, legacyWordSyncEnabled]);
  useEffect(() => {
    if (!legacyWordSyncEnabled) {
      return;
    }
    const controller = wordSyncControllerRef.current;
    if (!controller) {
      return;
    }
    if (!shouldUseWordSync || !activeWordSyncTrack || !activeWordIndex) {
      controller.stop();
      controller.setTrack(null, null);
      return;
    }
    controller.setTrack(activeWordSyncTrack, activeWordIndex);
    controller.snap();
    const element = audioRef.current;
    if (element && !element.paused) {
      controller.start();
    }
    return () => {
      controller.stop();
    };
  }, [activeWordIndex, activeWordSyncTrack, shouldUseWordSync, legacyWordSyncEnabled]);
  useEffect(() => {
    const clearTiming = () => {
      timingStore.setPayload(EMPTY_TIMING_PAYLOAD);
      timingStore.setLast(null);
    };
    if (!shouldUseWordSync || !timingPayload) {
      clearTiming();
      return clearTiming;
    }
    timingStore.setPayload(timingPayload);
    timingStore.setLast(null);
    return clearTiming;
  }, [shouldUseWordSync, timingPayload]);
  useEffect(() => {
    if (!shouldUseWordSync || !timingPayload) {
      return;
    }
    timingStore.setRate(effectivePlaybackRate);
  }, [effectivePlaybackRate, shouldUseWordSync, timingPayload]);
  useEffect(() => {
    if (!playerCore || !shouldUseWordSync || !timingPayload) {
      stopAudioSync();
      return () => {
        stopAudioSync();
      };
    }
    startAudioSync(playerCore);
    return () => {
      stopAudioSync();
    };
  }, [playerCore, shouldUseWordSync, timingPayload]);
  useEffect(() => {
    if (!playerCore) {
      return;
    }
    playerCore.setRate(effectivePlaybackRate);
  }, [effectivePlaybackRate, playerCore]);
  useEffect(() => {
    if (!legacyWordSyncEnabled) {
      tokenElementsRef.current.clear();
      sentenceElementsRef.current.clear();
      return;
    }
    if (shouldUseWordSync) {
      return;
    }
    tokenElementsRef.current.forEach((element) => {
      element.classList.remove('is-active');
      element.classList.remove('is-visited');
    });
    tokenElementsRef.current.clear();
    sentenceElementsRef.current.clear();
  }, [legacyWordSyncEnabled, shouldUseWordSync]);
  useEffect(() => {
    if (!legacyWordSyncEnabled || !shouldUseWordSync) {
      return;
    }
    const controller = wordSyncControllerRef.current;
    if (!controller) {
      return;
    }
    if (typeof window === 'undefined') {
      controller.snap();
      return;
    }
    const handle = window.requestAnimationFrame(() => {
      controller.snap();
    });
    return () => {
      window.cancelAnimationFrame(handle);
    };
  }, [legacyWordSyncEnabled, shouldUseWordSync, wordSyncSentences]);

  useEffect(() => {
    if (!onRegisterInlineAudioControls) {
      if (!effectiveAudioUrl) {
        onInlineAudioPlaybackStateChange?.('paused');
      }
      return;
    }
    if (!effectiveAudioUrl) {
      onRegisterInlineAudioControls(null);
      onInlineAudioPlaybackStateChange?.('paused');
      return () => {
        onRegisterInlineAudioControls(null);
      };
    }
    const pauseHandler = () => {
      const element = audioRef.current;
      if (!element) {
        return;
      }
      try {
        element.pause();
      } catch (error) {
        // Ignore pause failures triggered by browsers blocking programmatic control.
      }
      onInlineAudioPlaybackStateChange?.('paused');
    };
    const playHandler = () => {
      const element = audioRef.current;
      if (!element) {
        return;
      }
      try {
        const result = element.play();
        onInlineAudioPlaybackStateChange?.('playing');
        if (result && typeof result.catch === 'function') {
          result.catch(() => {
            onInlineAudioPlaybackStateChange?.('paused');
          });
        }
      } catch (error) {
        // Swallow play failures caused by autoplay restrictions.
        onInlineAudioPlaybackStateChange?.('paused');
      }
    };
    onRegisterInlineAudioControls({ pause: pauseHandler, play: playHandler });
    return () => {
      onRegisterInlineAudioControls(null);
    };
  }, [effectiveAudioUrl, onInlineAudioPlaybackStateChange, onRegisterInlineAudioControls]);
  const pendingInitialSeek = useRef<number | null>(null);
  const lastReportedPosition = useRef(0);

  useEffect(() => {
    if (!hasTimeline) {
      return;
    }
    setChunkTime(0);
    setActiveSentenceIndex(0);
  }, [hasTimeline, chunk?.chunkId, chunk?.rangeFragment, chunk?.startSentence, chunk?.endSentence]);

  useEffect(() => {
    setActiveSentenceIndex(0);
    setActiveSentenceProgress(0);
  }, [content, totalSentences]);

  useEffect(() => {
    if (!onActiveSentenceChange) {
      return;
    }
    if (!totalSentences || totalSentences <= 0) {
      onActiveSentenceChange(null);
      return;
    }
    const activeSentenceNumber = (() => {
      const rawSentenceNumber = chunk?.sentences?.[activeSentenceIndex]?.sentence_number ?? null;
      const chunkSentenceNumber =
        typeof rawSentenceNumber === 'number' && Number.isFinite(rawSentenceNumber)
          ? Math.trunc(rawSentenceNumber)
          : null;
      if (chunkSentenceNumber !== null) {
        return chunkSentenceNumber;
      }
      const start =
        typeof chunk?.startSentence === 'number' && Number.isFinite(chunk.startSentence)
          ? Math.trunc(chunk.startSentence)
          : null;
      if (start !== null) {
        return start + Math.max(0, Math.trunc(activeSentenceIndex));
      }
      return Math.max(1, Math.trunc(activeSentenceIndex) + 1);
    })();
    onActiveSentenceChange(activeSentenceNumber);
  }, [activeSentenceIndex, chunk?.sentences, chunk?.startSentence, onActiveSentenceChange, totalSentences]);

  useEffect(() => {
    if (!timelineDisplay) {
      return;
    }
    const { activeIndex: candidateIndex, effectiveTime } = timelineDisplay;
    if (candidateIndex === activeSentenceIndex) {
      return;
    }
    if (!timelineSentences || timelineSentences.length === 0) {
      setActiveSentenceIndex(candidateIndex);
      return;
    }
    const epsilon = 0.05;
    const clampedIndex = Math.max(0, Math.min(candidateIndex, timelineSentences.length - 1));
    const candidateRuntime = timelineSentences[clampedIndex];
    if (!candidateRuntime) {
      setActiveSentenceIndex(clampedIndex);
      return;
    }
    if (clampedIndex > activeSentenceIndex) {
      if (effectiveTime < candidateRuntime.startTime + epsilon) {
        return;
      }
    } else if (clampedIndex < activeSentenceIndex) {
      if (effectiveTime > candidateRuntime.endTime - epsilon) {
        return;
      }
    }
    setActiveSentenceIndex(clampedIndex);
  }, [timelineDisplay, activeSentenceIndex, timelineSentences]);

  useEffect(() => {
    if (!effectiveAudioUrl) {
      pendingInitialSeek.current = null;
      lastReportedPosition.current = 0;
      setActiveSentenceIndex(0);
      setActiveSentenceProgress(0);
      setAudioDuration(null);
      setChunkTime(0);
      return;
    }
    pendingInitialSeek.current = null;
    lastReportedPosition.current = 0;
    setActiveSentenceIndex(0);
    setActiveSentenceProgress(0);
    setAudioDuration(null);
    setChunkTime(0);
  }, [effectiveAudioUrl, getStoredAudioPosition]);

  const handleScroll = useCallback(
    (event: UIEvent<HTMLDivElement>) => {
      onScroll?.(event);
      if (linguistBubble && !linguistBubblePinned) {
        requestLinguistBubblePositionUpdate();
      }
    },
    [linguistBubble, linguistBubblePinned, onScroll, requestLinguistBubblePositionUpdate],
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

  const emitAudioProgress = useCallback(
    (position: number) => {
      if (!effectiveAudioUrl || !onAudioProgress) {
        return;
      }
      if (Math.abs(position - lastReportedPosition.current) < 0.25) {
        return;
      }
      lastReportedPosition.current = position;
      onAudioProgress(effectiveAudioUrl, position);
    },
    [effectiveAudioUrl, onAudioProgress],
  );

  const updateSentenceForTime = useCallback(
    (time: number, duration: number) => {
      const totalWeight = sentenceWeightSummary.total;
      if (totalWeight <= 0 || duration <= 0 || rawSentences.length === 0) {
        setActiveSentenceIndex(0);
        setActiveSentenceProgress(0);
        return;
      }

      const ratio = time / duration;
      const progress =
        ratio >= 0.995 ? 1 : Math.max(0, Math.min(ratio, 1));
      const targetUnits = progress * totalWeight;
      const cumulative = sentenceWeightSummary.cumulative;

      let sentencePosition = cumulative.findIndex((value) => targetUnits < value);
      if (sentencePosition === -1) {
        sentencePosition = rawSentences.length - 1;
      }

      const sentence = rawSentences[sentencePosition];
      const sentenceStartUnits = sentencePosition === 0 ? 0 : cumulative[sentencePosition - 1];
      const sentenceWeight = Math.max(sentence.weight, 1);
      const intraUnits = targetUnits - sentenceStartUnits;
      const intra = Math.max(0, Math.min(intraUnits / sentenceWeight, 1));

      setActiveSentenceIndex(sentence.index);
      setActiveSentenceProgress(intra);
    },
    [rawSentences, sentenceWeightSummary],
  );

  const updateActiveGateFromTime = useCallback((mediaTime: number) => {
    const gates = gateListRef.current;
    if (!gates.length) {
      timingStore.setActiveGate(null);
      return;
    }
    let candidate: SentenceGate | null = null;
    for (const gate of gates) {
      if (mediaTime >= gate.start && mediaTime <= gate.end) {
        candidate = gate;
        break;
      }
      if (mediaTime < gate.start) {
        candidate = gate;
        break;
      }
    }
    timingStore.setActiveGate(candidate);
  }, []);

  const handleInlineAudioPlay = useCallback(() => {
    inlineAudioPlayingRef.current = true;
    timingStore.setLast(null);
    const startPlayback = () => {
      wordSyncControllerRef.current?.handlePlay();
      onInlineAudioPlaybackStateChange?.('playing');
      const element = audioRef.current;
      if (element && element.ended) {
        element.currentTime = 0;
        setChunkTime(0);
        setActiveSentenceIndex(0);
        setActiveSentenceProgress(0);
        updateActiveGateFromTime(0);
      }
      if (progressTimerRef.current === null) {
        progressTimerRef.current = window.setInterval(() => {
          const mediaEl = audioRef.current;
          if (!mediaEl) {
            return;
          }
          const { currentTime, duration } = mediaEl;
          if (!Number.isFinite(currentTime) || !Number.isFinite(duration) || duration <= 0) {
            return;
          }
          setAudioDuration((existing) =>
            existing && Math.abs(existing - duration) < 0.01 ? existing : duration,
          );
          setChunkTime(currentTime);
          if (!hasTimeline) {
            updateSentenceForTime(currentTime, duration);
          }
          updateActiveGateFromTime(currentTime);
        }, 120);
      }
    };
    const element = audioRef.current;
    if (!element) {
      startPlayback();
      return;
    }
    const scheduleStart = () => {
      if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
        window.requestAnimationFrame(startPlayback);
      } else {
        startPlayback();
      }
    };
    if (element.readyState >= element.HAVE_CURRENT_DATA) {
      scheduleStart();
      return;
    }
    const handleCanPlay = () => {
      element.removeEventListener('canplay', handleCanPlay);
      scheduleStart();
    };
    element.addEventListener('canplay', handleCanPlay, { once: true });
  }, [onInlineAudioPlaybackStateChange, updateActiveGateFromTime, updateSentenceForTime]);

  const handleInlineAudioPause = useCallback(() => {
    inlineAudioPlayingRef.current = false;
    if (progressTimerRef.current !== null) {
      window.clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
    wordSyncControllerRef.current?.handlePause();
    onInlineAudioPlaybackStateChange?.('paused');
  }, [onInlineAudioPlaybackStateChange]);

  const handleAudioSeeking = useCallback(() => {
    wordSyncControllerRef.current?.handleSeeking();
  }, []);

  const handleAudioWaiting = useCallback(() => {
    wordSyncControllerRef.current?.handleWaiting();
  }, []);

  const handleAudioStalled = useCallback(() => {
    wordSyncControllerRef.current?.handleWaiting();
  }, []);

  const handleAudioPlaying = useCallback(() => {
    wordSyncControllerRef.current?.handlePlaying();
  }, []);

  const handleAudioRateChange = useCallback(() => {
    wordSyncControllerRef.current?.handleRateChange();
  }, []);

  const handleLoadedMetadata = useCallback(() => {
    const element = audioRef.current;
    if (!element) {
      return;
    }
    const duration = element.duration;
    if (Number.isFinite(duration) && duration > 0) {
      setAudioDuration(duration);
    } else {
      setAudioDuration(null);
    }
    const initialTime = (() => {
      const current = element.currentTime ?? 0;
      if (Number.isFinite(duration) && duration > 0 && current >= duration - 0.25) {
        return 0;
      }
      return current;
    })();
    if (initialTime !== (element.currentTime ?? 0)) {
      element.currentTime = initialTime;
    }
    setChunkTime(initialTime);
    const seek = pendingInitialSeek.current;
    if (typeof seek === 'number' && seek > 0 && Number.isFinite(duration) && duration > 0) {
      const nearEndThreshold = Math.max(duration * 0.9, duration - 3);
      let targetSeek = seek >= nearEndThreshold ? 0 : Math.min(seek, duration - 0.1);
      if (targetSeek < 0 || !Number.isFinite(targetSeek)) {
        targetSeek = 0;
      }
      element.currentTime = targetSeek;
      if (!hasTimeline) {
        updateSentenceForTime(targetSeek, duration);
      }
      updateActiveGateFromTime(targetSeek);
      emitAudioProgress(targetSeek);
      if (targetSeek > 0.1) {
        const maybePlay = element.play?.();
        if (maybePlay && typeof maybePlay.catch === 'function') {
          maybePlay.catch(() => undefined);
        }
      }
      pendingInitialSeek.current = null;
      wordSyncControllerRef.current?.snap();
      return;
    }
    pendingInitialSeek.current = null;
    updateActiveGateFromTime(element.currentTime ?? 0);
    wordSyncControllerRef.current?.snap();
  }, [emitAudioProgress, hasTimeline, updateSentenceForTime, updateActiveGateFromTime]);

  const handleTimeUpdate = useCallback(() => {
    const element = audioRef.current;
    if (!element) {
      return;
    }
    const { currentTime, duration } = element;
    if (!Number.isFinite(currentTime) || !Number.isFinite(duration) || duration <= 0) {
      return;
    }
    setAudioDuration((existing) => (existing && Math.abs(existing - duration) < 0.01 ? existing : duration));
    setChunkTime(currentTime);
    if (!hasTimeline) {
      updateSentenceForTime(currentTime, duration);
    }
    emitAudioProgress(currentTime);
    updateActiveGateFromTime(currentTime);
    if (element.paused) {
      wordSyncControllerRef.current?.snap();
    }
  }, [emitAudioProgress, hasTimeline, updateSentenceForTime, updateActiveGateFromTime]);

  const handleAudioEnded = useCallback(() => {
    inlineAudioPlayingRef.current = false;
    if (progressTimerRef.current !== null) {
      window.clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
    wordSyncControllerRef.current?.stop();
    onInlineAudioPlaybackStateChange?.('paused');
    if (hasTimeline && timelineDisplay) {
      setChunkTime((prev) => (audioDuration ? audioDuration : prev));
      setActiveSentenceIndex(timelineDisplay.activeIndex);
    } else {
      if (totalSentences > 0) {
        setActiveSentenceIndex(totalSentences - 1);
        setActiveSentenceProgress(1);
      }
    }
    emitAudioProgress(0);
    onRequestAdvanceChunk?.();
  }, [
    audioDuration,
    emitAudioProgress,
    hasTimeline,
    onInlineAudioPlaybackStateChange,
    onRequestAdvanceChunk,
    timelineDisplay,
    totalSentences,
  ]);

const handleAudioSeeked = useCallback(() => {
  wordSyncControllerRef.current?.handleSeeked();
  const element = audioRef.current;
  if (!element || !Number.isFinite(element.duration) || element.duration <= 0) {
    return;
  }
  setChunkTime(element.currentTime ?? 0);
  if (!hasTimeline) {
    updateSentenceForTime(element.currentTime, element.duration);
  }
  emitAudioProgress(element.currentTime);
}, [emitAudioProgress, hasTimeline, updateSentenceForTime]);
  const handleTokenSeek = useCallback(
    (time: number) => {
      if (dictionarySuppressSeekRef.current) {
        return;
      }
      const element = audioRef.current;
      if (!element || !Number.isFinite(time)) {
        return;
      }
      try {
        wordSyncControllerRef.current?.handleSeeking();
        const target = Math.max(0, Math.min(time, Number.isFinite(element.duration) ? element.duration : time));
        element.currentTime = target;
        const maybePlay = element.play?.();
        if (maybePlay && typeof maybePlay.catch === 'function') {
          maybePlay.catch(() => undefined);
        }
      } catch (error) {
        // Ignore seek failures in restricted environments.
      }
    },
    [],
  );

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
    return () => {
      if (progressTimerRef.current !== null) {
        window.clearInterval(progressTimerRef.current);
        progressTimerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    const chunkId = chunk?.chunkId ?? chunk?.rangeFragment ?? null;
    if (lastChunkIdRef.current !== chunkId) {
      revealMemoryRef.current = {
        sentenceIdx: null,
        counts: { original: 0, translit: 0, translation: 0 },
      };
      lastChunkIdRef.current = chunkId;
      lastChunkTimeRef.current = 0;
      setChunkTime(0);
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

  const { sentenceImageReelNode, activeSentenceImagePath } = useSentenceImageReel({
    jobId,
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

  useMyPainterSentence({
    jobId,
    chunk,
    activeSentenceIndex,
    activeSentenceNumber,
    activeSentenceImagePath,
    isLibraryMediaOrigin,
    setPlayerSentence,
  });

  const overlayAudioEl = playerCore?.getElement() ?? audioRef.current ?? null;
  const showTextPlayer =
    !(legacyWordSyncEnabled && shouldUseWordSync && wordSyncSentences && wordSyncSentences.length > 0) &&
    Boolean(textPlayerSentences && textPlayerSentences.length > 0);
  const pinnedLinguistBubbleNode =
    linguistBubble && linguistBubblePinned ? (
      <MyLinguistBubble
        bubble={linguistBubble}
        isPinned={linguistBubblePinned}
        variant="docked"
        bubbleRef={linguistBubbleRef}
        canNavigatePrev={linguistCanNavigatePrev}
        canNavigateNext={linguistCanNavigateNext}
        onTogglePinned={toggleLinguistBubblePinned}
        onNavigatePrev={() => navigateLinguistWord(-1)}
        onNavigateNext={() => navigateLinguistWord(1)}
        onSpeak={handleLinguistSpeak}
        onSpeakSlow={handleLinguistSpeakSlow}
        onClose={closeLinguistBubble}
      />
    ) : null;

  const inlineAudioAvailable = Boolean(resolvedAudioUrl || noAudioAvailable);

  const hasFullscreenPanelContent = Boolean(fullscreenControls) || inlineAudioAvailable;
  const inlineAudioCollapsed = Boolean(isFullscreen && hasFullscreenPanelContent && fullscreenControlsCollapsed);
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
	      >
      <InteractiveFullscreenControls
        isVisible={isFullscreen && hasFullscreenPanelContent}
        collapsed={fullscreenControlsCollapsed}
        inlineAudioAvailable={inlineAudioAvailable}
        onCollapsedChange={setFullscreenControlsCollapsed}
      >
        {fullscreenControls}
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
	      <div
	        key="interactive-body"
	        className="player-panel__document-body player-panel__interactive-frame"
	        style={bodyStyle}
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
                  onError={() => setViewportCoverFailed(true)}
                  loading="lazy"
                />
                {showSecondaryCover ? (
                  <img
                    className="player-panel__player-info-art-secondary"
                    src={resolvedSecondaryCoverUrl ?? undefined}
                    alt=""
                    aria-hidden="true"
                    onError={() => setViewportSecondaryCoverFailed(true)}
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
          ref={containerRef}
          className="player-panel__interactive-body"
          data-has-badge={showInfoHeader ? 'true' : undefined}
          data-testid="player-panel-document"
          onScroll={handleScroll}
          onClickCapture={handleLinguistTokenClickCapture}
          onClick={handleInteractiveBackgroundClick}
          onPointerDownCapture={handlePointerDownCapture}
          onPointerMoveCapture={handlePointerMoveCapture}
          onPointerUpCapture={handlePointerUpCaptureWithSelection}
          onPointerCancelCapture={handlePointerCancelCapture}
        >
          {slideIndicator ? (
            <div className="player-panel__interactive-slide-indicator" title={slideIndicator.label}>
              {slideIndicator.label}
            </div>
          ) : null}
          {legacyWordSyncEnabled && shouldUseWordSync && wordSyncSentences && wordSyncSentences.length > 0 ? null : showTextPlayer ? (
            <>
              {sentenceImageReelNode}
              <TextPlayer
                sentences={textPlayerSentences ?? []}
                onSeek={handleTokenSeek}
                footer={pinnedLinguistBubbleNode}
              />
            </>
          ) : paragraphs.length > 0 ? (
            <>
              {sentenceImageReelNode}
              <pre className="player-panel__document-text">{content}</pre>
            </>
          ) : chunk ? (
            <div className="player-panel__document-status" role="status">
              Loading interactive chunk…
            </div>
          ) : (
            <div className="player-panel__document-status" role="status">
              Text preview will appear once generated.
            </div>
          )}
          {linguistBubble && !linguistBubblePinned ? (
            <MyLinguistBubble
              bubble={linguistBubble}
              isPinned={linguistBubblePinned}
              variant="floating"
              bubbleRef={linguistBubbleRef}
              floatingPlacement={linguistBubbleFloatingPlacement}
              floatingPosition={linguistBubbleFloatingPosition}
              canNavigatePrev={linguistCanNavigatePrev}
              canNavigateNext={linguistCanNavigateNext}
              onTogglePinned={toggleLinguistBubblePinned}
              onNavigatePrev={() => navigateLinguistWord(-1)}
              onNavigateNext={() => navigateLinguistWord(1)}
              onSpeak={handleLinguistSpeak}
              onSpeakSlow={handleLinguistSpeakSlow}
              onClose={closeLinguistBubble}
            />
          ) : null}
        {pinnedLinguistBubbleNode && !showTextPlayer ? (
          <div className="player-panel__my-linguist-dock" aria-label="MyLinguist lookup dock">
            {pinnedLinguistBubbleNode}
          </div>
        ) : null}
      </div>
    </div>
    </div>
    <DebugOverlay audioEl={overlayAudioEl} />
    </>
  );
});

export default InteractiveTextViewer;
