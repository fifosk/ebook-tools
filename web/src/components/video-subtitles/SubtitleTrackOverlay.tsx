import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { CSSProperties, MutableRefObject } from 'react';
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
  buildSubtitleTtsVoiceOptions,
  clampOpacity,
  clampScale,
} from './subtitleTrackOverlayUtils';
import { SubtitleLinguistBubblePortal } from './SubtitleLinguistBubblePortal';
import { SubtitleTrackRows } from './SubtitleTrackRows';
import { useAssSubtitleCues } from './useAssSubtitleCues';
import { useAssSubtitlePlaybackState } from './useAssSubtitlePlaybackState';
import { useSubtitleCueKeyboardNavigation } from './useSubtitleCueKeyboardNavigation';
import { useSubtitleOverlayDrag } from './useSubtitleOverlayDrag';
import { useSubtitleTokenNavigation } from './useSubtitleTokenNavigation';
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
  const {
    trackRefs,
    handleTokenClick,
    openSelectionLookup,
    handleKeyDown,
  } = useSubtitleTokenNavigation({
    overlayRef,
    overlayActive,
    activeCue,
    subtitleScale,
    cueVisibility,
    tracks,
    visibleTracks,
    selection,
    setSelection,
    isPlaying,
    linguistEnabled,
    consumeIgnoredClick,
    resumePlaybackAndDefocus,
    requestPositionUpdate: layout.requestPositionUpdate,
    openLinguistBubbleForRect: lookup.openLinguistBubbleForRect,
  });

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
