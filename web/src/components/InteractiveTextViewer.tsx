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
import type { PlayerFeatureFlags, PlayerMode } from '../types/player';
import { coerceExportPath } from '../utils/storageResolver';

type InlineAudioControls = {
  pause: () => void;
  play: () => void;
};

type SequenceTrack = 'original' | 'translation';
type SequenceSegment = {
  track: SequenceTrack;
  start: number;
  end: number;
  sentenceIndex: number;
};

type SequenceDebugState = {
  enabled?: boolean;
};

declare global {
  interface Window {
    __SEQ_DEBUG__?: SequenceDebugState;
  }
}

const SEQUENCE_DEBUG_EMPTY: SequenceDebugState = { enabled: false };

function useSequenceDebug(): boolean {
  const [enabled, setEnabled] = useState(() => {
    if (typeof window === 'undefined') {
      return false;
    }
    const params = new URLSearchParams(window.location.search);
    const paramEnabled = params.get('seqdebug');
    if (paramEnabled === '1' || paramEnabled === 'true') {
      return true;
    }
    return Boolean(window.__SEQ_DEBUG__?.enabled);
  });

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const handle = () => {
      const params = new URLSearchParams(window.location.search);
      const paramEnabled = params.get('seqdebug');
      const next =
        paramEnabled === '1' ||
        paramEnabled === 'true' ||
        Boolean((window.__SEQ_DEBUG__ ?? SEQUENCE_DEBUG_EMPTY).enabled);
      setEnabled(Boolean(next));
    };
    window.addEventListener('seq_debug_update', handle);
    return () => window.removeEventListener('seq_debug_update', handle);
  }, []);

  return enabled;
}

interface InteractiveTextViewerProps {
  content: string;
  rawContent?: string | null;
  chunk: LiveMediaChunk | null;
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
  const isExportMode = playerMode === 'export';
  const sequenceDebugEnabled = useSequenceDebug();
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
  const [audioDuration, setAudioDuration] = useState<number | null>(null);
  const [activeSentenceIndex, setActiveSentenceIndex] = useState(0);
  const [activeSentenceProgress, setActiveSentenceProgress] = useState(0);
  const combinedTrackUrl =
    audioTracks?.orig_trans?.url ?? audioTracks?.orig_trans?.path ?? null;
  const originalTrackUrl = audioTracks?.orig?.url ?? audioTracks?.orig?.path ?? null;
  const translationTrackUrl =
    audioTracks?.translation?.url ??
    audioTracks?.translation?.path ??
    audioTracks?.trans?.url ??
    audioTracks?.trans?.path ??
    null;
  const allowCombinedAudio = Boolean(combinedTrackUrl) && (!originalTrackUrl || !translationTrackUrl);
  const normaliseAudioUrl = (value: string | null) => {
    if (!value) {
      return null;
    }
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    const stripped = trimmed.replace(/[?#].*$/, '');
    if (!stripped) {
      return null;
    }
    try {
      const base = typeof window !== 'undefined' ? window.location.origin : 'http://localhost';
      const parsed = new URL(stripped, base);
      return parsed.pathname || stripped;
    } catch {
      return stripped;
    }
  };
  const deriveAudioBaseId = (value: string | null) => {
    const normalized = normaliseAudioUrl(value);
    if (!normalized) {
      return null;
    }
    const parts = normalized.split('/');
    const filename = parts[parts.length - 1] ?? '';
    if (!filename) {
      return null;
    }
    const withoutExt = filename.replace(/\.[^.]+$/, '');
    const trimmed = withoutExt.trim();
    if (!trimmed) {
      return null;
    }
    try {
      return trimmed.normalize('NFC').toLowerCase();
    } catch {
      return trimmed.toLowerCase();
    }
  };
  const activeAudioRef = normaliseAudioUrl(activeAudioUrl);
  const originalTrackRef = normaliseAudioUrl(originalTrackUrl);
  const translationTrackRef = normaliseAudioUrl(translationTrackUrl);
  const combinedTrackRef = normaliseAudioUrl(combinedTrackUrl);
  const activeAudioBase = deriveAudioBaseId(activeAudioUrl);
  const originalTrackBase = deriveAudioBaseId(originalTrackUrl);
  const translationTrackBase = deriveAudioBaseId(translationTrackUrl);
  const combinedTrackBase = deriveAudioBaseId(combinedTrackUrl);
  const matchesTrack =
    Boolean(
      activeAudioRef &&
        (activeAudioRef === originalTrackRef ||
          activeAudioRef === translationTrackRef ||
          activeAudioRef === combinedTrackRef),
    ) ||
    Boolean(
      activeAudioBase &&
        (activeAudioBase === originalTrackBase ||
          activeAudioBase === translationTrackBase ||
          activeAudioBase === combinedTrackBase),
    );
  const hasExplicitAudioSelection =
    Boolean(activeAudioUrl && !matchesTrack);

  const resolveNumericValue = (value: unknown): number | null => {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === 'string' && value.trim()) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
    return null;
  };

  const readSentenceGate = (
    sentence: ChunkSentenceMetadata | null | undefined,
    keys: string[],
  ): number | null => {
    if (!sentence) {
      return null;
    }
    const record = sentence as unknown as Record<string, unknown>;
    for (const key of keys) {
      const raw = record[key];
      const numeric = resolveNumericValue(raw);
      if (numeric !== null) {
        return numeric;
      }
    }
    return null;
  };

  const resolveSentenceGate = (
    sentence: ChunkSentenceMetadata | null | undefined,
    track: SequenceTrack,
  ): { start: number; end: number } | null => {
    const start = track === 'original'
      ? readSentenceGate(sentence, ['original_start_gate', 'originalStartGate', 'original_startGate'])
      : readSentenceGate(sentence, ['start_gate', 'startGate']);
    const end = track === 'original'
      ? readSentenceGate(sentence, ['original_end_gate', 'originalEndGate', 'original_endGate'])
      : readSentenceGate(sentence, ['end_gate', 'endGate']);
    if (start === null || end === null) {
      return null;
    }
    const safeStart = Math.max(0, start);
    const safeEnd = Math.max(safeStart, end);
    if (!Number.isFinite(safeStart) || !Number.isFinite(safeEnd)) {
      return null;
    }
    if (safeEnd <= safeStart) {
      return null;
    }
    return { start: safeStart, end: safeEnd };
  };

  const sequencePlan = useMemo<SequenceSegment[]>(() => {
    if (!chunk) {
      return [];
    }
    const isSingleSentence =
      (typeof chunk.sentenceCount === 'number' && chunk.sentenceCount === 1) ||
      (typeof chunk.startSentence === 'number' &&
        typeof chunk.endSentence === 'number' &&
        chunk.startSentence === chunk.endSentence);
    const buildFallbackSegments = (
      includeOriginal: boolean,
      includeTranslation: boolean,
    ): SequenceSegment[] => {
      const fallback: SequenceSegment[] = [];
      const originalDuration = audioTracks?.orig?.duration ?? null;
      const translationDuration = audioTracks?.translation?.duration ?? audioTracks?.trans?.duration ?? null;
      if (
        includeOriginal &&
        typeof originalDuration === 'number' &&
        Number.isFinite(originalDuration) &&
        originalDuration > 0
      ) {
        fallback.push({
          track: 'original',
          start: 0,
          end: originalDuration,
          sentenceIndex: 0,
        });
      }
      if (
        includeTranslation &&
        typeof translationDuration === 'number' &&
        Number.isFinite(translationDuration) &&
        translationDuration > 0
      ) {
        fallback.push({
          track: 'translation',
          start: 0,
          end: translationDuration,
          sentenceIndex: 0,
        });
      }
      return fallback;
    };

    if (!chunk.sentences || chunk.sentences.length === 0) {
      return isSingleSentence ? buildFallbackSegments(true, true) : [];
    }

    const segments: SequenceSegment[] = [];
    let hasOriginalGate = false;
    let hasTranslationGate = false;
    chunk.sentences.forEach((sentence, index) => {
      const originalGate = resolveSentenceGate(sentence, 'original');
      if (originalGate) {
        hasOriginalGate = true;
        segments.push({
          track: 'original',
          start: originalGate.start,
          end: originalGate.end,
          sentenceIndex: index,
        });
      }
      const translationGate = resolveSentenceGate(sentence, 'translation');
      if (translationGate) {
        hasTranslationGate = true;
        segments.push({
          track: 'translation',
          start: translationGate.start,
          end: translationGate.end,
          sentenceIndex: index,
        });
      }
    });

    if (!isSingleSentence) {
      return segments;
    }

    if (!hasOriginalGate || !hasTranslationGate) {
      const fallback = buildFallbackSegments(!hasOriginalGate, !hasTranslationGate);
      if (fallback.length === 0) {
        return segments;
      }
      if (!hasOriginalGate && fallback.some((segment) => segment.track === 'original')) {
        segments.unshift(
          ...fallback.filter((segment) => segment.track === 'original'),
        );
      }
      if (!hasTranslationGate && fallback.some((segment) => segment.track === 'translation')) {
        segments.push(
          ...fallback.filter((segment) => segment.track === 'translation'),
        );
      }
    }

    return segments;
  }, [audioTracks, chunk]);

  const hasOriginalSegments = useMemo(
    () => sequencePlan.some((segment) => segment.track === 'original'),
    [sequencePlan],
  );
  const hasTranslationSegments = useMemo(
    () => sequencePlan.some((segment) => segment.track === 'translation'),
    [sequencePlan],
  );
  const sequenceDefaultTrack: SequenceTrack = hasOriginalSegments ? 'original' : 'translation';
  const sequenceEnabled = Boolean(
    originalAudioEnabled &&
      translationAudioEnabled &&
      originalTrackUrl &&
      translationTrackUrl &&
      hasOriginalSegments &&
      hasTranslationSegments,
  );
  const [sequenceTrack, setSequenceTrack] = useState<SequenceTrack | null>(sequenceDefaultTrack);
  const sequenceTrackRef = useRef<SequenceTrack | null>(sequenceTrack);
  const sequenceIndexRef = useRef(0);
  const pendingSequenceSeekRef = useRef<{ time: number; autoPlay: boolean } | null>(null);
  const activeSentenceIndexRef = useRef(0);
  const lastSequenceEndedRef = useRef<number | null>(null);
  const sequenceAutoPlayRef = useRef(false);
  const pendingChunkAutoPlayRef = useRef(false);
  const pendingChunkAutoPlayKeyRef = useRef<string | null>(null);
  const sequenceChunkKeyRef = useRef<string | null>(null);

  useEffect(() => {
    sequenceTrackRef.current = sequenceTrack;
  }, [sequenceTrack]);
  useEffect(() => {
    activeSentenceIndexRef.current = activeSentenceIndex;
  }, [activeSentenceIndex]);

  const formatSequenceDebugUrl = useCallback((value: string | null) => {
    if (!value) {
      return '—';
    }
    const trimmed = value.trim().replace(/[?#].*$/, '');
    if (!trimmed) {
      return '—';
    }
    const parts = trimmed.split('/');
    return parts[parts.length - 1] || trimmed;
  }, []);

  const sequenceChunkKey = useMemo(() => {
    return (
      chunk?.chunkId ??
      chunk?.rangeFragment ??
      chunk?.metadataPath ??
      chunk?.metadataUrl ??
      null
    );
  }, [chunk?.chunkId, chunk?.metadataPath, chunk?.metadataUrl, chunk?.rangeFragment]);

  useEffect(() => {
    const previous = sequenceChunkKeyRef.current;
    sequenceChunkKeyRef.current = sequenceChunkKey;
    if (!sequenceEnabled || !sequenceChunkKey || previous === sequenceChunkKey) {
      return;
    }
    sequenceIndexRef.current = 0;
    pendingSequenceSeekRef.current = null;
    sequenceTrackRef.current = sequenceDefaultTrack;
    setSequenceTrack(sequenceDefaultTrack);
  }, [sequenceChunkKey, sequenceDefaultTrack, sequenceEnabled]);

  const effectiveAudioUrl = useMemo(() => {
    if (sequenceEnabled) {
      const track = sequenceTrack ?? sequenceDefaultTrack;
      return track === 'original' ? originalTrackUrl : translationTrackUrl;
    }
    if (activeAudioUrl) {
      return activeAudioUrl;
    }
    if (originalAudioEnabled && originalTrackUrl) {
      return originalTrackUrl;
    }
    if (originalAudioEnabled && allowCombinedAudio && combinedTrackUrl) {
      return combinedTrackUrl;
    }
    if (translationAudioEnabled && translationTrackUrl) {
      return translationTrackUrl;
    }
    if (translationAudioEnabled && allowCombinedAudio && combinedTrackUrl) {
      return combinedTrackUrl;
    }
    if (translationTrackUrl) {
      return translationTrackUrl;
    }
    if (allowCombinedAudio && combinedTrackUrl) {
      return combinedTrackUrl;
    }
    return null;
  }, [
    activeAudioUrl,
    allowCombinedAudio,
    combinedTrackUrl,
    originalAudioEnabled,
    originalTrackUrl,
    sequenceEnabled,
    sequenceDefaultTrack,
    sequenceTrack,
    translationAudioEnabled,
    translationTrackUrl,
  ]);

  const resolvedAudioUrl = useMemo(() => {
    if (!effectiveAudioUrl) {
      return null;
    }
    if (isExportMode) {
      return coerceExportPath(effectiveAudioUrl, jobId) ?? effectiveAudioUrl;
    }
    return appendAccessToken(effectiveAudioUrl);
  }, [effectiveAudioUrl, isExportMode, jobId]);

  const audioResetKey = useMemo(() => {
    if (sequenceEnabled) {
      const chunkKey =
        chunk?.chunkId ??
        chunk?.rangeFragment ??
        chunk?.metadataPath ??
        chunk?.metadataUrl ??
        'unknown';
      return `sequence:${chunkKey}:${originalTrackUrl ?? ''}:${translationTrackUrl ?? ''}`;
    }
    return effectiveAudioUrl ?? 'none';
  }, [
    chunk?.chunkId,
    chunk?.metadataPath,
    chunk?.metadataUrl,
    chunk?.rangeFragment,
    effectiveAudioUrl,
    originalTrackUrl,
    sequenceEnabled,
    translationTrackUrl,
  ]);

  const sequenceDebugInfo = sequenceDebugEnabled
    ? {
        enabled: sequenceEnabled,
        origEnabled: originalAudioEnabled,
        transEnabled: translationAudioEnabled,
        hasOrigSeg: hasOriginalSegments,
        hasTransSeg: hasTranslationSegments,
        hasOrigTrack: Boolean(originalTrackUrl),
        hasTransTrack: Boolean(translationTrackUrl),
        track: sequenceTrackRef.current ?? sequenceTrack ?? sequenceDefaultTrack,
        index: sequenceIndexRef.current,
        lastEnded: lastSequenceEndedRef.current ? lastSequenceEndedRef.current.toFixed(3) : 'none',
        autoPlay: sequenceAutoPlayRef.current ? 'true' : 'false',
        plan: sequencePlan.length,
        sentence: activeSentenceIndex,
        time: chunkTime,
        pending: pendingSequenceSeekRef.current
          ? `${pendingSequenceSeekRef.current.time.toFixed(3)}:${pendingSequenceSeekRef.current.autoPlay ? 'auto' : 'manual'}`
          : 'none',
        playing: audioRef.current ? !audioRef.current.paused : inlineAudioPlayingRef.current,
        audio: formatSequenceDebugUrl(resolvedAudioUrl),
        original: formatSequenceDebugUrl(originalTrackUrl),
        translation: formatSequenceDebugUrl(translationTrackUrl),
      }
    : null;

  const findSequenceIndexForSentence = useCallback(
    (sentenceIndex: number, preferredTrack?: SequenceTrack | null) => {
      if (!sequencePlan.length || sentenceIndex < 0) {
        return -1;
      }
      if (preferredTrack) {
        const matched = sequencePlan.findIndex(
          (segment) => segment.sentenceIndex === sentenceIndex && segment.track === preferredTrack,
        );
        if (matched >= 0) {
          return matched;
        }
      }
      return sequencePlan.findIndex((segment) => segment.sentenceIndex === sentenceIndex);
    },
    [sequencePlan],
  );

  useEffect(() => {
    if (!sequenceEnabled || sequencePlan.length === 0) {
      sequenceIndexRef.current = 0;
      setSequenceTrack(null);
      pendingSequenceSeekRef.current = null;
      return;
    }
    const preferredSentence = activeSentenceIndexRef.current ?? 0;
    const preferredTrack = sequenceTrackRef.current ?? sequenceDefaultTrack;
    let nextIndex = findSequenceIndexForSentence(preferredSentence, preferredTrack);
    if (nextIndex < 0) {
      nextIndex = findSequenceIndexForSentence(preferredSentence, null);
    }
    if (nextIndex < 0) {
      nextIndex = 0;
    }
    const segment = sequencePlan[nextIndex];
    if (!segment) {
      return;
    }
    sequenceIndexRef.current = nextIndex;
    if (sequenceTrackRef.current && sequenceTrackRef.current === segment.track) {
      pendingSequenceSeekRef.current = null;
      return;
    }
    if (!sequenceTrackRef.current) {
      setSequenceTrack(segment.track);
      return;
    }
    pendingSequenceSeekRef.current = {
      time: segment.start,
      autoPlay: inlineAudioPlayingRef.current,
    };
    setSequenceTrack(segment.track);
  }, [findSequenceIndexForSentence, sequenceDefaultTrack, sequenceEnabled, sequencePlan]);

  const resolvedTimingTrack: 'mix' | 'translation' | 'original' =
    sequenceEnabled ? sequenceTrack ?? sequenceDefaultTrack : activeTimingTrack;
  const hasCombinedAudio = Boolean(combinedTrackUrl);
  const useCombinedPhases = resolvedTimingTrack === 'mix' && hasCombinedAudio;
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
    if (!jobId || !wordSyncAllowed || isExportMode) {
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
  }, [isExportMode, jobId, wordSyncAllowed]);

  const paragraphs = useMemo(() => buildParagraphs(content), [content]);
  const { timelineSentences, timelineDisplay } = useTimelineDisplay({
    chunk,
    hasTimeline,
    useCombinedPhases,
    activeTimingTrack: resolvedTimingTrack,
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
  } = linguist;

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
    if (resolvedTimingTrack === 'original') {
      preferences.push('original');
    } else if (resolvedTimingTrack === 'mix') {
      preferences.push('original_translated');
    } else {
      preferences.push('translated');
    }
    (['translated', 'original_translated', 'original'] as TrackTimingPayload['trackType'][]).forEach(
      (candidate) => {
        if (!preferences.includes(candidate)) {
          preferences.push(candidate);
        }
      },
    );
    return preferences;
  }, [resolvedTimingTrack]);
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
    return buildTimingPayloadFromJobTiming(jobTimingResponse, resolvedTimingTrack);
  }, [hasRemoteTiming, jobTimingResponse, resolvedTimingTrack]);

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
      resolvedTimingTrack,
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
        track: resolvedTimingTrack,
      });
    }
  }, [jobId, timingPayload, resolvedTimingTrack, jobTimingResponse]);
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
  }, [audioResetKey, getStoredAudioPosition]);

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

  const syncSequenceIndexToTime = useCallback(
    (mediaTime: number) => {
      if (!sequenceEnabled || sequencePlan.length === 0) {
        return;
      }
      const currentTrack = sequenceTrackRef.current;
      if (!currentTrack) {
        return;
      }
      const epsilon = 0.05;
      let matchIndex = sequencePlan.findIndex(
        (segment) =>
          segment.track === currentTrack &&
          mediaTime >= segment.start - epsilon &&
          mediaTime <= segment.end + epsilon,
      );
      if (matchIndex < 0) {
        matchIndex = sequencePlan.findIndex(
          (segment) => segment.track === currentTrack && mediaTime < segment.start,
        );
        if (matchIndex < 0) {
          matchIndex = sequencePlan.length - 1;
        }
      }
      if (matchIndex >= 0) {
        sequenceIndexRef.current = matchIndex;
      }
    },
    [sequenceEnabled, sequencePlan],
  );

  const getSequenceIndexForPlayback = useCallback(() => {
    if (!sequencePlan.length) {
      return -1;
    }
    const currentTrack = sequenceTrackRef.current ?? sequenceDefaultTrack;
    const sentenceIndex = activeSentenceIndexRef.current ?? 0;
    const resolvedIndex = findSequenceIndexForSentence(sentenceIndex, currentTrack);
    if (resolvedIndex >= 0) {
      return resolvedIndex;
    }
    return sequenceIndexRef.current >= 0 ? sequenceIndexRef.current : 0;
  }, [findSequenceIndexForSentence, sequenceDefaultTrack, sequencePlan.length]);

  const applySequenceSegment = useCallback(
    (segment: SequenceSegment, options?: { autoPlay?: boolean }) => {
      if (!segment) {
        return;
      }
      const element = audioRef.current;
      const shouldPlay = options?.autoPlay ?? inlineAudioPlayingRef.current;
      sequenceAutoPlayRef.current = shouldPlay;
      if (sequenceTrackRef.current !== segment.track) {
        sequenceTrackRef.current = segment.track;
        pendingSequenceSeekRef.current = { time: segment.start, autoPlay: shouldPlay };
        setSequenceTrack(segment.track);
        return;
      }
      if (!element) {
        return;
      }
      wordSyncControllerRef.current?.handleSeeking();
      element.currentTime = Math.max(0, segment.start);
      setChunkTime(segment.start);
      if (!hasTimeline && Number.isFinite(element.duration) && element.duration > 0) {
        updateSentenceForTime(segment.start, element.duration);
      }
      updateActiveGateFromTime(segment.start);
      emitAudioProgress(segment.start);
      if (shouldPlay) {
        const result = element.play?.();
        if (result && typeof result.catch === 'function') {
          result.catch(() => undefined);
        }
      }
    },
    [emitAudioProgress, hasTimeline, updateActiveGateFromTime, updateSentenceForTime],
  );

  const advanceSequenceSegment = useCallback(
    (options?: { autoPlay?: boolean }) => {
      if (!sequenceEnabled || sequencePlan.length === 0) {
        return false;
      }
      const currentIndex = getSequenceIndexForPlayback();
      if (currentIndex < 0) {
        return false;
      }
      const nextIndex = currentIndex + 1;
      if (nextIndex >= sequencePlan.length) {
        return false;
      }
      const nextSegment = sequencePlan[nextIndex];
      if (!nextSegment) {
        return false;
      }
      sequenceIndexRef.current = nextIndex;
      applySequenceSegment(nextSegment, options);
      return true;
    },
    [applySequenceSegment, getSequenceIndexForPlayback, sequenceEnabled, sequencePlan],
  );

  const maybeAdvanceSequence = useCallback(
    (mediaTime: number) => {
      if (!sequenceEnabled || sequencePlan.length === 0) {
        return false;
      }
      if (!inlineAudioPlayingRef.current) {
        return false;
      }
      if (pendingSequenceSeekRef.current) {
        return false;
      }
      syncSequenceIndexToTime(mediaTime);
      const currentIndex = getSequenceIndexForPlayback();
      const segment = currentIndex >= 0 ? sequencePlan[currentIndex] : null;
      if (!segment) {
        return false;
      }
      if (mediaTime < segment.end - 0.03) {
        return false;
      }
      return advanceSequenceSegment({ autoPlay: true });
    },
    [advanceSequenceSegment, getSequenceIndexForPlayback, sequenceEnabled, sequencePlan, syncSequenceIndexToTime],
  );

  const handleInlineAudioPlay = useCallback(() => {
    inlineAudioPlayingRef.current = true;
    sequenceAutoPlayRef.current = true;
    pendingChunkAutoPlayRef.current = false;
    pendingChunkAutoPlayKeyRef.current = null;
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
          maybeAdvanceSequence(currentTime);
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
  }, [maybeAdvanceSequence, onInlineAudioPlaybackStateChange, updateActiveGateFromTime, updateSentenceForTime]);

  const handleInlineAudioPause = useCallback(() => {
    const element = audioRef.current;
    if (element?.ended && onRequestAdvanceChunk) {
      const hasNextSegment = sequenceEnabled
        ? (() => {
            const currentIndex = getSequenceIndexForPlayback();
            return currentIndex >= 0 && currentIndex < sequencePlan.length - 1;
          })()
        : false;
      if (!sequenceEnabled || !hasNextSegment) {
        pendingChunkAutoPlayRef.current = true;
        pendingChunkAutoPlayKeyRef.current = audioResetKey;
        return;
      }
    }
    if (sequenceEnabled) {
      if (pendingSequenceSeekRef.current) {
        return;
      }
      if (pendingChunkAutoPlayRef.current && pendingChunkAutoPlayKeyRef.current === audioResetKey) {
        return;
      }
      if (element?.ended) {
        if (sequenceAutoPlayRef.current || inlineAudioPlayingRef.current) {
          pendingChunkAutoPlayRef.current = true;
          pendingChunkAutoPlayKeyRef.current = audioResetKey;
          return;
        }
        const currentIndex = getSequenceIndexForPlayback();
        const hasNextSegment = currentIndex >= 0 && currentIndex < sequencePlan.length - 1;
        if (hasNextSegment) {
          return;
        }
      }
    }
    inlineAudioPlayingRef.current = false;
    sequenceAutoPlayRef.current = false;
    pendingChunkAutoPlayRef.current = false;
    pendingChunkAutoPlayKeyRef.current = null;
    if (progressTimerRef.current !== null) {
      window.clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
    wordSyncControllerRef.current?.handlePause();
    onInlineAudioPlaybackStateChange?.('paused');
  }, [
    audioResetKey,
    getSequenceIndexForPlayback,
    onInlineAudioPlaybackStateChange,
    sequenceEnabled,
    sequencePlan.length,
  ]);

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
    const pendingSequenceSeek = pendingSequenceSeekRef.current;
    if (pendingSequenceSeek) {
      const safeDuration = Number.isFinite(duration) && duration > 0 ? duration : null;
      const nearEndThreshold =
        safeDuration !== null ? Math.max(safeDuration * 0.9, safeDuration - 3) : null;
      let targetSeek = pendingSequenceSeek.time;
      if (nearEndThreshold !== null && targetSeek >= nearEndThreshold) {
        targetSeek = 0;
      }
      if (safeDuration !== null) {
        targetSeek = Math.min(targetSeek, Math.max(safeDuration - 0.1, 0));
      }
      if (targetSeek < 0 || !Number.isFinite(targetSeek)) {
        targetSeek = 0;
      }
      element.currentTime = targetSeek;
      if (safeDuration !== null && !hasTimeline) {
        updateSentenceForTime(targetSeek, safeDuration);
      }
      updateActiveGateFromTime(targetSeek);
      emitAudioProgress(targetSeek);
      if (pendingSequenceSeek.autoPlay) {
        sequenceAutoPlayRef.current = true;
        const maybePlay = element.play?.();
        if (maybePlay && typeof maybePlay.catch === 'function') {
          maybePlay.catch(() => undefined);
        }
      }
      pendingSequenceSeekRef.current = null;
      wordSyncControllerRef.current?.snap();
      return;
    }
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
    maybeAdvanceSequence(currentTime);
    if (element.paused) {
      wordSyncControllerRef.current?.snap();
    }
  }, [emitAudioProgress, hasTimeline, maybeAdvanceSequence, updateSentenceForTime, updateActiveGateFromTime]);

  const handleAudioEnded = useCallback(() => {
    if (sequenceEnabled) {
      const element = audioRef.current;
      if (element && Number.isFinite(element.currentTime)) {
        lastSequenceEndedRef.current = element.currentTime;
      }
    }
    if (sequenceEnabled && pendingSequenceSeekRef.current) {
      return;
    }
    if (sequenceEnabled && advanceSequenceSegment({ autoPlay: true })) {
      return;
    }
    if (onRequestAdvanceChunk) {
      pendingChunkAutoPlayRef.current = true;
      pendingChunkAutoPlayKeyRef.current = audioResetKey;
    }
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
    advanceSequenceSegment,
    audioDuration,
    audioResetKey,
    emitAudioProgress,
    hasTimeline,
    onInlineAudioPlaybackStateChange,
    onRequestAdvanceChunk,
    sequenceEnabled,
    timelineDisplay,
    totalSentences,
  ]);

  useEffect(() => {
    if (!sequenceAutoPlayRef.current) {
      return;
    }
    const element = audioRef.current;
    if (!element) {
      return;
    }
    let active = true;
    const attemptPlay = () => {
      if (!active || !sequenceAutoPlayRef.current) {
        return;
      }
      const result = element.play?.();
      if (result && typeof result.catch === 'function') {
        result.catch(() => undefined);
      }
    };
    if (element.readyState >= element.HAVE_FUTURE_DATA) {
      attemptPlay();
      return;
    }
    element.addEventListener('canplay', attemptPlay, { once: true });
    return () => {
      active = false;
      element.removeEventListener('canplay', attemptPlay);
    };
  }, [resolvedAudioUrl]);

  useEffect(() => {
    if (!pendingChunkAutoPlayRef.current) {
      return;
    }
    if (pendingChunkAutoPlayKeyRef.current === audioResetKey) {
      return;
    }
    pendingChunkAutoPlayRef.current = false;
    pendingChunkAutoPlayKeyRef.current = null;
    const element = audioRef.current;
    if (!element) {
      return;
    }
    let active = true;
    const attemptPlay = () => {
      if (!active) {
        return;
      }
      const result = element.play?.();
      if (result && typeof result.catch === 'function') {
        result.catch(() => undefined);
      }
    };
    if (element.readyState >= element.HAVE_CURRENT_DATA) {
      attemptPlay();
      return;
    }
    element.addEventListener('canplay', attemptPlay, { once: true });
    return () => {
      active = false;
      element.removeEventListener('canplay', attemptPlay);
    };
  }, [audioResetKey, resolvedAudioUrl]);

const handleAudioSeeked = useCallback(() => {
  wordSyncControllerRef.current?.handleSeeked();
  const element = audioRef.current;
  if (!element || !Number.isFinite(element.duration) || element.duration <= 0) {
    return;
  }
  setChunkTime(element.currentTime ?? 0);
  syncSequenceIndexToTime(element.currentTime ?? 0);
  if (!hasTimeline) {
    updateSentenceForTime(element.currentTime, element.duration);
  }
  emitAudioProgress(element.currentTime);
}, [emitAudioProgress, hasTimeline, syncSequenceIndexToTime, updateSentenceForTime]);
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
  const hasVisibleCues =
    resolvedCueVisibility.original || resolvedCueVisibility.transliteration || resolvedCueVisibility.translation;
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
            className="player-panel__interactive-body"
            data-has-badge={showInfoHeader ? 'true' : undefined}
          >
            {slideIndicator ? (
              <div className="player-panel__interactive-slide-indicator" title={slideIndicator.label}>
                {slideIndicator.label}
              </div>
            ) : null}
            {sentenceImageReelNode}
            <div
              ref={containerRef}
              className="player-panel__interactive-text-scroll"
              data-testid="player-panel-document"
              onScroll={handleScroll}
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
                  footer={pinnedLinguistBubbleNode}
                />
              ) : paragraphs.length > 0 ? (
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
