import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { CSSProperties, KeyboardEvent as ReactKeyboardEvent, MutableRefObject, PointerEvent as ReactPointerEvent } from 'react';
import { fetchLlmModels, fetchVoiceInventory } from '../../api/client';
import type { VoiceInventoryResponse } from '../../api/dtos';
import {
  MY_LINGUIST_BUBBLE_MAX_CHARS,
  MY_LINGUIST_DEFAULT_LLM_MODEL,
  MY_LINGUIST_DEFAULT_LOOKUP_LANGUAGE,
  MY_LINGUIST_STORAGE_KEYS,
} from '../interactive-text/constants';
import type { LinguistBubbleState } from '../interactive-text/types';
import { useLinguistBubbleLayout } from '../interactive-text/useLinguistBubbleLayout';
import { useLinguistBubbleLookup } from '../interactive-text/useLinguistBubbleLookup';
import {
  buildMyLinguistLanguageOptions,
  buildMyLinguistModelOptions,
  storeMyLinguistStored,
} from '../interactive-text/utils';
import { type SubtitleTrack, type AssSubtitleCue, parseAssSubtitles, isAssSubtitleTrack, decodeDataUrl } from '../../lib/subtitles';
import {
  EMPTY_LINE_MAP,
  TRACK_RENDER_ORDER,
  buildSubtitleTtsVoiceOptions,
  clampOffset,
  clampOpacity,
  clampScale,
  findActiveCueIndex,
  findCueInsertIndex,
  moveIndexWithinLine,
  resolveDefaultSelection,
  resolveShadowTarget,
  toVariantKind,
  type SubtitleTokenSelection,
  type TrackKind,
  type TrackLineMap,
} from './subtitleTrackOverlayUtils';
import { SubtitleLinguistBubblePortal } from './SubtitleLinguistBubblePortal';
import { SubtitleTrackRows } from './SubtitleTrackRows';
import styles from './SubtitleTrackOverlay.module.css';

const EMPTY_VISIBILITY = {
  original: true,
  translation: true,
  transliteration: true,
};
const SUBTITLE_VERTICAL_OFFSET_KEY = 'video.subtitle.verticalOffset';

interface SubtitleTrackOverlayProps {
  videoRef: MutableRefObject<HTMLVideoElement | null>;
  track: SubtitleTrack | null;
  enabled: boolean;
  linguistEnabled?: boolean;
  deferLoadUntilPlay?: boolean;
  cueVisibility?: {
    original: boolean;
    translation: boolean;
    transliteration: boolean;
  };
  subtitleScale?: number;
  subtitleBackgroundOpacity?: number | null;
  onOverlayActiveChange?: (active: boolean) => void;
  jobId?: string | null;
  jobOriginalLanguage?: string | null;
  jobTranslationLanguage?: string | null;
  dockedContainer?: HTMLElement | null;
}

export default function SubtitleTrackOverlay({
  videoRef,
  track,
  enabled,
  linguistEnabled = true,
  deferLoadUntilPlay = false,
  cueVisibility = EMPTY_VISIBILITY,
  subtitleScale = 1,
  subtitleBackgroundOpacity = null,
  onOverlayActiveChange,
  jobId = null,
  jobOriginalLanguage = null,
  jobTranslationLanguage = null,
  dockedContainer = null,
}: SubtitleTrackOverlayProps) {
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const trackRefs = useRef<Record<TrackKind, HTMLDivElement | null>>({
    original: null,
    transliteration: null,
    translation: null,
  });
  const lineMapsRef = useRef<Record<TrackKind, TrackLineMap>>({
    original: EMPTY_LINE_MAP,
    transliteration: EMPTY_LINE_MAP,
    translation: EMPTY_LINE_MAP,
  });
  const [assReadyToLoad, setAssReadyToLoad] = useState(!deferLoadUntilPlay);
  const [cues, setCues] = useState<AssSubtitleCue[]>([]);
  const shouldLoadAss = enabled && assReadyToLoad && isAssSubtitleTrack(track);
  const overlayActive = enabled && shouldLoadAss && cues.length > 0;
  const [activeCueIndex, setActiveCueIndex] = useState(-1);
  const activeCueIndexRef = useRef(-1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [selection, setSelection] = useState<SubtitleTokenSelection | null>(null);
  const [bubble, setBubble] = useState<LinguistBubbleState | null>(null);
  const [verticalOffset, setVerticalOffset] = useState(0);
  const [isDraggingSubtitles, setIsDraggingSubtitles] = useState(false);
  const llmModelsLoadedRef = useRef(false);
  const [availableLlmModels, setAvailableLlmModels] = useState<string[]>([]);
  const voiceInventoryLoadedRef = useRef(false);
  const [voiceInventory, setVoiceInventory] = useState<VoiceInventoryResponse | null>(null);
  const dragStateRef = useRef({
    pointerId: null as number | null,
    startX: 0,
    startY: 0,
    startOffset: 0,
    active: false,
    ignoreClick: false,
  });
  const linguistRequestCounterRef = useRef(0);
  const anchorRectRef = useRef<DOMRect | null>(null);
  const anchorElementRef = useRef<HTMLElement | null>(null);

  const layout = useLinguistBubbleLayout({
    anchorRectRef,
    anchorElementRef,
    bubble,
  });

  const resolvedJobTranslationLanguage =
    typeof jobTranslationLanguage === 'string' && jobTranslationLanguage.trim()
      ? jobTranslationLanguage.trim()
      : typeof track?.language === 'string' && track.language.trim()
        ? track.language.trim()
        : null;
  const resolvedJobOriginalLanguage =
    typeof jobOriginalLanguage === 'string' && jobOriginalLanguage.trim()
      ? jobOriginalLanguage.trim()
      : null;
  const globalInputLanguage = resolvedJobOriginalLanguage ?? resolvedJobTranslationLanguage ?? 'English';
  const lookupLanguageOptions = useMemo(
    () =>
      buildMyLinguistLanguageOptions(
        [
          bubble?.lookupLanguage,
          resolvedJobTranslationLanguage,
          resolvedJobOriginalLanguage,
          globalInputLanguage,
          MY_LINGUIST_DEFAULT_LOOKUP_LANGUAGE,
        ],
        MY_LINGUIST_DEFAULT_LOOKUP_LANGUAGE,
      ),
    [
      bubble?.lookupLanguage,
      globalInputLanguage,
      resolvedJobOriginalLanguage,
      resolvedJobTranslationLanguage,
    ],
  );
  const llmModelOptions = useMemo(
    () =>
      buildMyLinguistModelOptions(
        bubble?.llmModel,
        availableLlmModels,
        MY_LINGUIST_DEFAULT_LLM_MODEL,
      ),
    [availableLlmModels, bubble?.llmModel],
  );
  const ttsVoiceOptions = useMemo(() => {
    return buildSubtitleTtsVoiceOptions(
      voiceInventory,
      bubble?.ttsLanguage ?? globalInputLanguage,
      bubble?.ttsVoice
    );
  }, [voiceInventory, bubble?.ttsLanguage, bubble?.ttsVoice, globalInputLanguage]);

  const lookup = useLinguistBubbleLookup({
    isEnabled: linguistEnabled,
    audioRef: videoRef as unknown as MutableRefObject<HTMLAudioElement | null>,
    requestCounterRef: linguistRequestCounterRef,
    bubble,
    setBubble,
    anchorRectRef,
    anchorElementRef,
    jobId,
    chunk: null,
    globalInputLanguage,
    resolvedJobOriginalLanguage,
    resolvedJobTranslationLanguage,
    applyOpenLayout: layout.applyOpenLayout,
    maxQueryChars: MY_LINGUIST_BUBBLE_MAX_CHARS,
    loadingAnswer: 'Lookup in progress...',
    truncationSuffix: '...',
  });

  const closeBubble = useCallback(() => {
    layout.resetLayout();
    setBubble(null);
  }, [layout]);

  useEffect(() => {
    if (!linguistEnabled) {
      llmModelsLoadedRef.current = false;
      setAvailableLlmModels([]);
      closeBubble();
    }
  }, [closeBubble, linguistEnabled]);

  const handleLookupLanguageChange = useCallback((value: string) => {
    const trimmed = value.trim();
    if (!trimmed) {
      return;
    }
    storeMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.lookupLanguage, trimmed);
    setBubble((previous) => {
      if (!previous) {
        return previous;
      }
      return { ...previous, lookupLanguage: trimmed };
    });
  }, []);

  const handleLlmModelChange = useCallback((value: string | null) => {
    const trimmed = (value ?? '').trim();
    storeMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.llmModel, trimmed, { allowEmpty: true });
    setBubble((previous) => {
      if (!previous) {
        return previous;
      }
      return { ...previous, llmModel: trimmed ? trimmed : null };
    });
  }, []);

  const handleTtsVoiceChange = useCallback((value: string | null) => {
    const trimmed = (value ?? '').trim();
    storeMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.ttsVoice, trimmed, { allowEmpty: true });
    setBubble((previous) => {
      if (!previous) {
        return previous;
      }
      return { ...previous, ttsVoice: trimmed ? trimmed : null };
    });
  }, []);

  useEffect(() => {
    if (!linguistEnabled || !bubble || llmModelsLoadedRef.current) {
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
  }, [bubble]);

  useEffect(() => {
    if (!linguistEnabled || !bubble || voiceInventoryLoadedRef.current) {
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
  }, [linguistEnabled, bubble]);

  const resumePlaybackAndDefocus = useCallback(() => {
    closeBubble();
    const video = videoRef.current;
    if (video && video.paused) {
      video.play().catch(() => {
        /* Ignore play failures. */
      });
    }
    if (typeof document !== 'undefined') {
      const active = document.activeElement as HTMLElement | null;
      if (active && overlayRef.current?.contains(active)) {
        active.blur();
        return;
      }
    }
    overlayRef.current?.blur();
  }, [closeBubble, videoRef]);

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
  }, []);

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

  useEffect(() => {
    if (!bubble) {
      return;
    }
    const isTypingTarget = (target: EventTarget | null): boolean => {
      if (!target || !(target instanceof HTMLElement)) {
        return false;
      }
      const tag = target.tagName;
      if (!tag) {
        return false;
      }
      return target.isContentEditable || tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.altKey || event.metaKey || isTypingTarget(event.target)) {
        return;
      }
      const key = event.key;
      const isSpace = key === ' ' || event.code === 'Space';
      if (key === 'Escape' || key === 'Esc' || isSpace) {
        resumePlaybackAndDefocus();
        event.preventDefault();
      }
    };
    const handlePointer = (event: PointerEvent) => {
      const bubbleEl = layout.bubbleRef.current;
      if (!bubbleEl) {
        closeBubble();
        return;
      }
      const target = event.target;
      if (target instanceof Node && bubbleEl.contains(target)) {
        return;
      }
      closeBubble();
    };
    window.addEventListener('keydown', handleKeyDown, true);
    window.addEventListener('pointerdown', handlePointer, true);
    return () => {
      window.removeEventListener('keydown', handleKeyDown, true);
      window.removeEventListener('pointerdown', handlePointer, true);
    };
  }, [bubble, layout.bubbleRef, resumePlaybackAndDefocus]);

  useEffect(() => {
    setAssReadyToLoad(!deferLoadUntilPlay);
  }, [deferLoadUntilPlay, track?.format, track?.url]);

  useEffect(() => {
    if (!deferLoadUntilPlay || assReadyToLoad) {
      return;
    }
    const video = videoRef.current;
    if (!video) {
      return;
    }
    let timeoutId: number | null = null;
    const markReady = () => {
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
        timeoutId = null;
      }
      setAssReadyToLoad(true);
    };
    const handlePlay = () => {
      markReady();
    };
    const handleLoadedMetadata = () => {
      if (timeoutId !== null) {
        return;
      }
      timeoutId = window.setTimeout(markReady, 750);
    };
    video.addEventListener('play', handlePlay);
    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    return () => {
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [assReadyToLoad, deferLoadUntilPlay, videoRef]);

  useEffect(() => {
    if (!shouldLoadAss || typeof fetch !== 'function' || typeof window === 'undefined') {
      setCues([]);
      return;
    }
    const controller = new AbortController();
    const run = async () => {
      try {
        const raw =
          track!.url.startsWith('data:')
            ? decodeDataUrl(track!.url)
            : await (async () => {
                const resolved = new URL(track!.url, window.location.href).toString();
                const response = await fetch(resolved, { signal: controller.signal });
                if (!response.ok) {
                  return null;
                }
                return response.text();
              })();
        if (!raw) {
          setCues([]);
          return;
        }
        const parsed = parseAssSubtitles(raw);
        setCues(parsed);
      } catch (error) {
        void error;
        setCues([]);
      }
    };
    void run();
    return () => controller.abort();
  }, [shouldLoadAss, track?.url]);

  useEffect(() => {
    onOverlayActiveChange?.(overlayActive);
  }, [onOverlayActiveChange, overlayActive]);

  useEffect(() => {
    if (!overlayActive) {
      setActiveCueIndex(-1);
      activeCueIndexRef.current = -1;
      return;
    }
    const video = videoRef.current;
    if (!video) {
      return;
    }
    const updatePlaybackState = () => {
      setIsPlaying(!video.paused);
    };
    updatePlaybackState();
    const updateActiveCue = () => {
      const time = video.currentTime ?? 0;
      const nextIndex = findActiveCueIndex(cues, time, activeCueIndexRef.current);
      if (nextIndex !== activeCueIndexRef.current) {
        activeCueIndexRef.current = nextIndex;
        setActiveCueIndex(nextIndex);
      }
    };
    let rafId: number | null = null;
    const tick = () => {
      updateActiveCue();
      if (!video.paused) {
        rafId = window.requestAnimationFrame(tick);
      } else {
        rafId = null;
      }
    };
    const handlePlay = () => {
      updatePlaybackState();
      if (rafId === null) {
        rafId = window.requestAnimationFrame(tick);
      }
    };
    const handlePause = () => {
      updatePlaybackState();
      if (rafId !== null) {
        window.cancelAnimationFrame(rafId);
        rafId = null;
      }
      updateActiveCue();
    };
    const handleSeeked = () => {
      updateActiveCue();
    };
    const handleTimeUpdate = () => {
      if (video.paused) {
        updateActiveCue();
      }
    };
    updateActiveCue();
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('seeked', handleSeeked);
    video.addEventListener('timeupdate', handleTimeUpdate);
    return () => {
      if (rafId !== null) {
        window.cancelAnimationFrame(rafId);
      }
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('seeked', handleSeeked);
      video.removeEventListener('timeupdate', handleTimeUpdate);
    };
  }, [cues, overlayActive, videoRef]);

  useEffect(() => {
    if (!overlayActive || isPlaying || typeof document === 'undefined') {
      return;
    }
    const active = document.activeElement as HTMLElement | null;
    if (active) {
      if (active.isContentEditable) {
        return;
      }
      const tag = active.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') {
        return;
      }
      if (overlayRef.current && overlayRef.current.contains(active)) {
        return;
      }
    }
    if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
      window.requestAnimationFrame(() => {
        overlayRef.current?.focus({ preventScroll: true });
      });
    } else {
      overlayRef.current?.focus();
    }
  }, [isPlaying, overlayActive]);

  const activeCue = activeCueIndex >= 0 ? cues[activeCueIndex] ?? null : null;
  const tracks = activeCue?.tracks ?? {};

  const visibleTracks = useMemo(() => {
    return TRACK_RENDER_ORDER.filter((trackKey) => {
      if (trackKey === 'original' && !cueVisibility.original) {
        return false;
      }
      if (trackKey === 'translation' && !cueVisibility.translation) {
        return false;
      }
      if (trackKey === 'transliteration' && !cueVisibility.transliteration) {
        return false;
      }
      const entry = tracks[trackKey];
      return Boolean(entry && entry.tokens.length > 0);
    });
  }, [cueVisibility, tracks]);

  useEffect(() => {
    if (!activeCue || visibleTracks.length === 0) {
      setSelection(null);
      return;
    }
    const available: Partial<Record<TrackKind, AssSubtitleCue['tracks'][TrackKind]>> = {};
    visibleTracks.forEach((trackKey) => {
      available[trackKey] = tracks[trackKey];
    });
    const fallback = resolveDefaultSelection(visibleTracks, available);
    if (!fallback) {
      setSelection(null);
      return;
    }
    if (isPlaying) {
      setSelection((prev) => {
        if (prev && prev.track === fallback.track && prev.index === fallback.index) {
          return prev;
        }
        return fallback;
      });
      return;
    }
    setSelection((prev) => {
      if (!prev) {
        return fallback;
      }
      if (!visibleTracks.includes(prev.track)) {
        return fallback;
      }
      const tokens = tracks[prev.track]?.tokens ?? [];
      if (tokens.length === 0) {
        return fallback;
      }
      if (prev.index < 0 || prev.index >= tokens.length) {
        return { track: prev.track, index: Math.min(prev.index, tokens.length - 1) };
      }
      return prev;
    });
  }, [activeCue, isPlaying, tracks, visibleTracks]);

  const rebuildLineMaps = useCallback(() => {
    const next: Record<TrackKind, TrackLineMap> = {
      original: { lines: [], tokenLine: new Map() },
      translation: { lines: [], tokenLine: new Map() },
      transliteration: { lines: [], tokenLine: new Map() },
    };
    (Object.keys(trackRefs.current) as TrackKind[]).forEach((trackKey) => {
      const container = trackRefs.current[trackKey];
      if (!container) {
        return;
      }
      const tokens = Array.from(container.querySelectorAll<HTMLElement>('[data-subtitle-token-index]'));
      if (tokens.length === 0) {
        return;
      }
      const containerRect = container.getBoundingClientRect();
      const rowMap = new Map<number, Array<{ index: number; left: number }>>();
      tokens.forEach((element) => {
        const rawIndex = element.dataset.subtitleTokenIndex;
        const tokenIndex = rawIndex ? Number(rawIndex) : Number.NaN;
        if (!Number.isFinite(tokenIndex)) {
          return;
        }
        const rect = element.getBoundingClientRect();
        const top = Math.round((rect.top - containerRect.top) * 2) / 2;
        const left = rect.left - containerRect.left;
        const bucket = rowMap.get(top) ?? [];
        bucket.push({ index: tokenIndex, left });
        rowMap.set(top, bucket);
      });
      const sortedLines = Array.from(rowMap.entries())
        .sort((a, b) => a[0] - b[0])
        .map(([, entries]) =>
          entries.sort((left, right) => left.left - right.left).map((entry) => entry.index),
        );
      const tokenLine = new Map<number, number>();
      sortedLines.forEach((line, lineIndex) => {
        line.forEach((tokenIndex) => {
          tokenLine.set(tokenIndex, lineIndex);
        });
      });
      next[trackKey] = { lines: sortedLines, tokenLine };
    });
    lineMapsRef.current = next;
  }, []);

  useLayoutEffect(() => {
    if (!overlayActive) {
      return;
    }
    rebuildLineMaps();
  }, [overlayActive, rebuildLineMaps, activeCue, subtitleScale, cueVisibility]);

  useEffect(() => {
    if (!overlayActive || typeof ResizeObserver !== 'function') {
      return;
    }
    const container = overlayRef.current;
    if (!container) {
      return;
    }
    const observer = new ResizeObserver(() => {
      rebuildLineMaps();
      layout.requestPositionUpdate();
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, [layout, overlayActive, rebuildLineMaps]);

  const activateToken = useCallback(
    (trackKey: TrackKind, index: number, element: HTMLElement | null) => {
      const entry = tracks[trackKey];
      const tokens = entry?.tokens ?? [];
      if (!tokens.length || index < 0 || index >= tokens.length) {
        return;
      }
      const word = tokens[index];
      if (!word) {
        return;
      }
      const rect = element?.getBoundingClientRect();
      if (linguistEnabled && rect) {
        lookup.openLinguistBubbleForRect(word, rect, 'click', toVariantKind(trackKey), element);
      }
      setSelection({ track: trackKey, index });
      overlayRef.current?.focus();
    },
    [linguistEnabled, lookup, tracks],
  );

  const handleTokenClick = useCallback(
    (trackKey: TrackKind, index: number, element: HTMLElement) => {
      if (dragStateRef.current.ignoreClick) {
        dragStateRef.current.ignoreClick = false;
        return;
      }
      activateToken(trackKey, index, element);
    },
    [activateToken],
  );

  const openSelectionLookup = useCallback(
    () => {
      if (!linguistEnabled) {
        return false;
      }
      const fallback = resolveDefaultSelection(visibleTracks, tracks);
      const current = selection ?? fallback;
      if (!current) {
        return false;
      }
      const tokens = tracks[current.track]?.tokens ?? [];
      const token = tokens[current.index] ?? '';
      if (!token) {
        return false;
      }
      const anchor = overlayRef.current?.querySelector<HTMLElement>(
        `[data-track="${current.track}"] [data-subtitle-token-index="${current.index}"]`,
      );
      if (!anchor) {
        return false;
      }
      const rect = anchor.getBoundingClientRect();
      lookup.openLinguistBubbleForRect(token, rect, 'click', toVariantKind(current.track), anchor);
      setSelection({ track: current.track, index: current.index });
      overlayRef.current?.focus();
      return true;
    },
    [linguistEnabled, lookup, selection, tracks, visibleTracks],
  );

  const handleKeyDown = useCallback(
    (event: ReactKeyboardEvent<HTMLDivElement>) => {
      if (!overlayActive || visibleTracks.length === 0) {
        return;
      }
      const key = event.key;
      const isArrow =
        key === 'ArrowLeft' || key === 'ArrowRight' || key === 'ArrowUp' || key === 'ArrowDown';
      const isSpace = key === ' ' || event.code === 'Space';
      if (!isArrow && key !== 'Enter' && !isSpace) {
        return;
      }
      if (key === 'Escape' || key === 'Esc' || isSpace) {
        resumePlaybackAndDefocus();
        event.preventDefault();
        return;
      }
      if (isPlaying) {
        return;
      }
      if (key === 'Enter') {
        const opened = openSelectionLookup();
        if (opened) {
          event.preventDefault();
        }
        return;
      }
      event.preventDefault();
      const current = selection ?? resolveDefaultSelection(visibleTracks, tracks);
      if (!current) {
        return;
      }
      if (key === 'ArrowLeft' || key === 'ArrowRight') {
        const entry = tracks[current.track];
        const tokenCount = entry?.tokens.length ?? 0;
        if (tokenCount === 0) {
          return;
        }
        const nextIndex = moveIndexWithinLine(
          current.track,
          current.index,
          key === 'ArrowLeft' ? -1 : 1,
          tokenCount,
          lineMapsRef.current,
        );
        setSelection({ track: current.track, index: nextIndex });
        return;
      }
      const currentPos = visibleTracks.indexOf(current.track);
      if (currentPos === -1) {
        return;
      }
      const nextPos = key === 'ArrowUp' ? currentPos - 1 : currentPos + 1;
      if (nextPos < 0 || nextPos >= visibleTracks.length) {
        return;
      }
      const nextTrack = visibleTracks[nextPos];
      const nextTokens = tracks[nextTrack]?.tokens ?? [];
      if (nextTokens.length === 0) {
        return;
      }
      const nextIndex = Math.min(current.index, nextTokens.length - 1);
      setSelection({ track: nextTrack, index: nextIndex });
    },
    [
      overlayActive,
      visibleTracks,
      isPlaying,
      selection,
      tracks,
      lookup,
      videoRef,
      openSelectionLookup,
      resumePlaybackAndDefocus,
    ],
  );

  const translationTokens = tracks.translation?.tokens ?? null;
  const transliterationTokens = tracks.transliteration?.tokens ?? null;

  const seekCueByOffset = useCallback(
    (direction: -1 | 1) => {
      const video = videoRef.current;
      if (!video || cues.length === 0) {
        return false;
      }
      const time = video.currentTime ?? 0;
      const activeIndex = findActiveCueIndex(cues, time, activeCueIndexRef.current);
      let baseIndex = activeIndex;
      if (baseIndex < 0) {
        const insertIndex = findCueInsertIndex(cues, time);
        baseIndex = direction > 0 ? insertIndex : insertIndex - 1;
      } else {
        baseIndex += direction;
      }
      if (baseIndex < 0 || baseIndex >= cues.length) {
        return false;
      }
      const targetCue = cues[baseIndex];
      if (!targetCue) {
        return false;
      }
      const nextTime = Math.max(0, targetCue.start + 0.001);
      try {
        video.currentTime = nextTime;
      } catch {
        return false;
      }
      activeCueIndexRef.current = baseIndex;
      setActiveCueIndex(baseIndex);
      return true;
    },
    [cues, videoRef],
  );

  useEffect(() => {
    if (!overlayActive || typeof window === 'undefined') {
      return;
    }
    const isTypingTarget = (target: EventTarget | null): boolean => {
      if (!target || !(target instanceof HTMLElement)) {
        return false;
      }
      const tag = target.tagName;
      if (!tag) {
        return false;
      }
      return target.isContentEditable || tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
    };
    const handleGlobalKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.altKey || event.metaKey || isTypingTarget(event.target)) {
        return;
      }
      const code = event.code;
      const key = event.key;
      const isArrowRight = code === 'ArrowRight' || key === 'ArrowRight';
      const isArrowLeft = code === 'ArrowLeft' || key === 'ArrowLeft';
      if ((key === 'Enter' || code === 'Enter') && !isPlaying) {
        const handled = openSelectionLookup();
        if (handled) {
          event.preventDefault();
          event.stopPropagation();
        }
        return;
      }
      if (!isArrowRight && !isArrowLeft) {
        return;
      }
      const video = videoRef.current;
      if (!video || video.paused) {
        return;
      }
      const handled = seekCueByOffset(isArrowRight ? 1 : -1);
      if (handled) {
        event.preventDefault();
        event.stopPropagation();
      }
    };
    window.addEventListener('keydown', handleGlobalKeyDown, true);
    return () => {
      window.removeEventListener('keydown', handleGlobalKeyDown, true);
    };
  }, [isPlaying, openSelectionLookup, overlayActive, seekCueByOffset, videoRef]);

  const playbackSelection = useMemo<SubtitleTokenSelection | null>(() => {
    if (!isPlaying) {
      return null;
    }
    const translationIndex = tracks.translation?.currentIndex;
    if (typeof translationIndex === 'number') {
      return { track: 'translation', index: translationIndex };
    }
    const transliterationIndex = tracks.transliteration?.currentIndex;
    if (typeof transliterationIndex === 'number') {
      return { track: 'transliteration', index: transliterationIndex };
    }
    return null;
  }, [isPlaying, tracks.translation?.currentIndex, tracks.transliteration?.currentIndex]);

  const shadowTarget = useMemo(() => {
    const source = playbackSelection ?? selection;
    if (!source) {
      return null;
    }
    return resolveShadowTarget(source.track, source.index, translationTokens, transliterationTokens);
  }, [playbackSelection, selection, translationTokens, transliterationTokens]);

  if (!overlayActive || !activeCue || visibleTracks.length === 0) {
    return null;
  }

  const scaleValue = clampScale(subtitleScale);
  const backgroundOpacity = clampOpacity(subtitleBackgroundOpacity);
  const overlayStyle: CSSProperties = {
    '--subtitle-overlay-bg': `rgba(0, 0, 0, ${backgroundOpacity})`,
    '--subtitle-overlay-scale': String(scaleValue),
    '--subtitle-overlay-offset': `${verticalOffset}px`,
  } as CSSProperties;

  return (
    <div
      ref={overlayRef}
      className={styles.overlay}
      style={overlayStyle}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onPointerDown={handleSubtitlePointerDown}
      onPointerMove={handleSubtitlePointerMove}
      onPointerUp={handleSubtitlePointerEnd}
      onPointerCancel={handleSubtitlePointerEnd}
      data-dragging={isDraggingSubtitles ? 'true' : undefined}
      aria-label="Subtitle tracks"
    >
      <SubtitleTrackRows
        visibleTracks={visibleTracks}
        tracks={tracks}
        isPlaying={isPlaying}
        selection={selection}
        shadowTarget={shadowTarget}
        trackRefs={trackRefs}
        onTokenClick={handleTokenClick}
      />
      <SubtitleLinguistBubblePortal
        bubble={bubble}
        linguistEnabled={linguistEnabled}
        layout={layout}
        lookup={lookup}
        dockedContainer={dockedContainer}
        lookupLanguageOptions={lookupLanguageOptions}
        llmModelOptions={llmModelOptions}
        ttsVoiceOptions={ttsVoiceOptions}
        onLookupLanguageChange={handleLookupLanguageChange}
        onLlmModelChange={handleLlmModelChange}
        onTtsVoiceChange={handleTtsVoiceChange}
        onClose={closeBubble}
      />
    </div>
  );
}
