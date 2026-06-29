import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { CSSProperties, KeyboardEvent as ReactKeyboardEvent, MutableRefObject } from 'react';
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
import { type SubtitleTrack } from '../../lib/subtitles';
import {
  EMPTY_LINE_MAP,
  buildSubtitleTtsVoiceOptions,
  clampOpacity,
  clampScale,
  moveIndexWithinLine,
  resolveDefaultSelection,
  toVariantKind,
  type TrackKind,
  type TrackLineMap,
} from './subtitleTrackOverlayUtils';
import { SubtitleLinguistBubblePortal } from './SubtitleLinguistBubblePortal';
import { SubtitleTrackRows } from './SubtitleTrackRows';
import { useAssSubtitleCues } from './useAssSubtitleCues';
import { useAssSubtitlePlaybackState } from './useAssSubtitlePlaybackState';
import { useSubtitleCueKeyboardNavigation } from './useSubtitleCueKeyboardNavigation';
import { useSubtitleOverlayDrag } from './useSubtitleOverlayDrag';
import { useSubtitleTrackSelection } from './useSubtitleTrackSelection';
import styles from './SubtitleTrackOverlay.module.css';

const EMPTY_VISIBILITY = {
  original: true,
  translation: true,
  transliteration: true,
};
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
  const { cues, overlayActive } = useAssSubtitleCues({
    videoRef,
    track,
    enabled,
    deferLoadUntilPlay,
  });
  const {
    activeCueIndex,
    activeCueIndexRef,
    isPlaying,
    commitActiveCueIndex,
  } = useAssSubtitlePlaybackState({
    videoRef,
    cues,
    overlayActive,
  });
  const [bubble, setBubble] = useState<LinguistBubbleState | null>(null);
  const llmModelsLoadedRef = useRef(false);
  const [availableLlmModels, setAvailableLlmModels] = useState<string[]>([]);
  const voiceInventoryLoadedRef = useRef(false);
  const [voiceInventory, setVoiceInventory] = useState<VoiceInventoryResponse | null>(null);
  const linguistRequestCounterRef = useRef(0);
  const anchorRectRef = useRef<DOMRect | null>(null);
  const anchorElementRef = useRef<HTMLElement | null>(null);
  const {
    verticalOffset,
    isDraggingSubtitles,
    handleSubtitlePointerDown,
    handleSubtitlePointerMove,
    handleSubtitlePointerEnd,
    consumeIgnoredClick,
  } = useSubtitleOverlayDrag({
    overlayRef,
    overlayActive,
  });

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
    onOverlayActiveChange?.(overlayActive);
  }, [onOverlayActiveChange, overlayActive]);

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
  const {
    tracks,
    visibleTracks,
    selection,
    setSelection,
    shadowTarget,
  } = useSubtitleTrackSelection({
    activeCue,
    cueVisibility,
    isPlaying,
  });

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
      if (consumeIgnoredClick()) {
        return;
      }
      activateToken(trackKey, index, element);
    },
    [activateToken, consumeIgnoredClick],
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

  useSubtitleCueKeyboardNavigation({
    videoRef,
    cues,
    activeCueIndexRef,
    overlayActive,
    isPlaying,
    openSelectionLookup,
    commitActiveCueIndex,
  });

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
