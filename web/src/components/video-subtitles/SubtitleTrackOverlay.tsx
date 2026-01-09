import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { CSSProperties, KeyboardEvent as ReactKeyboardEvent, MutableRefObject } from 'react';
import type { TextPlayerVariantKind } from '../../text-player/TextPlayer';
import { MyLinguistBubble } from '../interactive-text/MyLinguistBubble';
import { MY_LINGUIST_BUBBLE_MAX_CHARS } from '../interactive-text/constants';
import type { LinguistBubbleState } from '../interactive-text/types';
import { useLinguistBubbleLayout } from '../interactive-text/useLinguistBubbleLayout';
import { useLinguistBubbleLookup } from '../interactive-text/useLinguistBubbleLookup';
import type { SubtitleTrack } from '../VideoPlayer';
import { parseAssSubtitles, type AssSubtitleCue, type AssSubtitleTrackKind } from './assParser';
import styles from './SubtitleTrackOverlay.module.css';

type TrackKind = AssSubtitleTrackKind;

type Selection = {
  track: TrackKind;
  index: number;
};

type TrackLineMap = {
  lines: number[][];
  tokenLine: Map<number, number>;
};

const TRACK_RENDER_ORDER: TrackKind[] = ['original', 'translation', 'transliteration'];

const EMPTY_LINE_MAP: TrackLineMap = { lines: [], tokenLine: new Map() };

const EMPTY_VISIBILITY = {
  original: true,
  translation: true,
  transliteration: true,
};

function clampScale(value: number | null | undefined): number {
  if (!Number.isFinite(value) || !value) {
    return 1;
  }
  return Math.max(0.25, Math.min(4, value));
}

function clampOpacity(value: number | null | undefined): number {
  if (!Number.isFinite(value ?? NaN)) {
    return 0.6;
  }
  return Math.max(0, Math.min(1, value ?? 0.6));
}

function findActiveCueIndex(cues: AssSubtitleCue[], time: number, lastIndex: number): number {
  if (lastIndex >= 0 && lastIndex < cues.length) {
    const last = cues[lastIndex];
    if (time >= last.start && time < last.end) {
      return lastIndex;
    }
  }
  let low = 0;
  let high = cues.length - 1;
  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    const cue = cues[mid];
    if (time < cue.start) {
      high = mid - 1;
    } else if (time >= cue.end) {
      low = mid + 1;
    } else {
      return mid;
    }
  }
  return -1;
}

function toVariantKind(track: TrackKind): TextPlayerVariantKind {
  if (track === 'transliteration') {
    return 'translit';
  }
  return track === 'translation' ? 'translation' : 'original';
}

function resolveDefaultSelection(
  order: TrackKind[],
  tracks: Partial<Record<TrackKind, AssSubtitleCue['tracks'][TrackKind]>>,
): Selection | null {
  for (const track of ['translation', 'transliteration', 'original'] as TrackKind[]) {
    if (!order.includes(track)) {
      continue;
    }
    const entry = tracks[track];
    if (!entry || entry.tokens.length === 0) {
      continue;
    }
    const currentIndex = entry.currentIndex ?? 0;
    const safeIndex = Math.max(0, Math.min(currentIndex, entry.tokens.length - 1));
    return { track, index: safeIndex };
  }
  return null;
}

function resolveShadowTarget(
  track: TrackKind,
  index: number,
  translationTokens: string[] | null,
  transliterationTokens: string[] | null,
): { track: TrackKind; index: number } | null {
  if (!translationTokens || !transliterationTokens) {
    return null;
  }
  if (translationTokens.length !== transliterationTokens.length) {
    return null;
  }
  if (track === 'translation' && index < transliterationTokens.length) {
    return { track: 'transliteration', index };
  }
  if (track === 'transliteration' && index < translationTokens.length) {
    return { track: 'translation', index };
  }
  return null;
}

function lineMapForTrack(lineMaps: MutableRefObject<Record<TrackKind, TrackLineMap>>, track: TrackKind): TrackLineMap {
  return lineMaps.current[track] ?? EMPTY_LINE_MAP;
}

function moveIndexWithinLine(
  track: TrackKind,
  index: number,
  delta: -1 | 1,
  tokenCount: number,
  lineMaps: MutableRefObject<Record<TrackKind, TrackLineMap>>,
): number {
  if (tokenCount <= 1) {
    return 0;
  }
  const map = lineMapForTrack(lineMaps, track);
  const lineIndex = map.tokenLine.get(index);
  if (lineIndex === undefined) {
    const next = (index + delta + tokenCount) % tokenCount;
    return next;
  }
  const lineTokens = map.lines[lineIndex] ?? [];
  if (lineTokens.length === 0) {
    const next = (index + delta + tokenCount) % tokenCount;
    return next;
  }
  const pos = lineTokens.indexOf(index);
  if (pos === -1) {
    const next = (index + delta + tokenCount) % tokenCount;
    return next;
  }
  let nextPos = pos + delta;
  if (nextPos < 0) {
    nextPos = lineTokens.length - 1;
  } else if (nextPos >= lineTokens.length) {
    nextPos = 0;
  }
  return lineTokens[nextPos] ?? index;
}

interface SubtitleTrackOverlayProps {
  videoRef: MutableRefObject<HTMLVideoElement | null>;
  track: SubtitleTrack | null;
  enabled: boolean;
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
}

export default function SubtitleTrackOverlay({
  videoRef,
  track,
  enabled,
  cueVisibility = EMPTY_VISIBILITY,
  subtitleScale = 1,
  subtitleBackgroundOpacity = null,
  onOverlayActiveChange,
  jobId = null,
  jobOriginalLanguage = null,
  jobTranslationLanguage = null,
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
  const [cues, setCues] = useState<AssSubtitleCue[]>([]);
  const [activeCueIndex, setActiveCueIndex] = useState(-1);
  const activeCueIndexRef = useRef(-1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [bubble, setBubble] = useState<LinguistBubbleState | null>(null);
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

  const lookup = useLinguistBubbleLookup({
    isEnabled: true,
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
    if (!bubble) {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' || event.key === 'Esc') {
        closeBubble();
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
  }, [bubble, closeBubble, layout.bubbleRef]);

  const shouldLoadAss =
    enabled &&
    typeof track?.url === 'string' &&
    track.url.toLowerCase().split(/[?#]/)[0]?.endsWith('.ass');

  useEffect(() => {
    if (!shouldLoadAss || typeof fetch !== 'function' || typeof window === 'undefined') {
      setCues([]);
      return;
    }
    const decodeDataUrl = (value: string): string | null => {
      const match = value.match(/^data:(.*?)(;base64)?,(.*)$/);
      if (!match) {
        return null;
      }
      const isBase64 = Boolean(match[2]);
      const payload = match[3] ?? '';
      try {
        if (isBase64) {
          return atob(payload);
        }
        return decodeURIComponent(payload);
      } catch {
        return null;
      }
    };
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
  }, [shouldLoadAss, track]);

  const overlayActive = enabled && shouldLoadAss && cues.length > 0;

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
      if (rect) {
        lookup.openLinguistBubbleForRect(word, rect, 'click', toVariantKind(trackKey), element);
      }
      setSelection({ track: trackKey, index });
      overlayRef.current?.focus();
    },
    [lookup, tracks],
  );

  const handleKeyDown = useCallback(
    (event: ReactKeyboardEvent<HTMLDivElement>) => {
      if (!overlayActive || visibleTracks.length === 0) {
        return;
      }
      const key = event.key;
      if (key !== 'ArrowLeft' && key !== 'ArrowRight' && key !== 'ArrowUp' && key !== 'ArrowDown' && key !== 'Enter') {
        return;
      }
      if (key === 'Enter') {
        if (selection) {
          const tokens = tracks[selection.track]?.tokens ?? [];
          const token = tokens[selection.index] ?? '';
          const anchor = overlayRef.current?.querySelector<HTMLElement>(
            `[data-track="${selection.track}"] [data-subtitle-token-index="${selection.index}"]`,
          );
          if (token && anchor) {
            const rect = anchor.getBoundingClientRect();
            lookup.openLinguistBubbleForRect(token, rect, 'click', toVariantKind(selection.track), anchor);
          }
        }
        event.preventDefault();
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
          lineMapsRef,
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
    [overlayActive, selection, tracks, visibleTracks, lookup],
  );

  const translationTokens = tracks.translation?.tokens ?? null;
  const transliterationTokens = tracks.transliteration?.tokens ?? null;

  const playbackSelection = useMemo<Selection | null>(() => {
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
  } as CSSProperties;

  return (
    <div
      ref={overlayRef}
      className={styles.overlay}
      style={overlayStyle}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      aria-label="Subtitle tracks"
    >
      {visibleTracks.map((trackKey) => {
        const entry = tracks[trackKey];
        const tokens = entry?.tokens ?? [];
        if (tokens.length === 0) {
          return null;
        }
        const playbackIndex = isPlaying ? entry?.currentIndex ?? null : null;
        return (
          <div
            key={trackKey}
            ref={(node) => {
              trackRefs.current[trackKey] = node;
            }}
            className={styles.trackRow}
            data-track={trackKey}
          >
            {tokens.map((token, index) => {
              const isPast = isPlaying && playbackIndex !== null && index < playbackIndex;
              const isCurrent = isPlaying && playbackIndex !== null && index === playbackIndex;
              const isSelected = !isPlaying && selection?.track === trackKey && selection.index === index;
              const isShadow = shadowTarget?.track === trackKey && shadowTarget.index === index;
              const classNames = [styles.token];
              if (trackKey === 'original') {
                classNames.push(styles.tokenOriginal);
              } else if (trackKey === 'translation') {
                classNames.push(styles.tokenTranslation);
              } else {
                classNames.push(styles.tokenTransliteration);
              }
              if (isPast) {
                classNames.push(styles.tokenPast);
              }
              if (isCurrent) {
                classNames.push(styles.tokenCurrent);
              }
              if (isSelected) {
                classNames.push(styles.tokenSelected);
              }
              if (isShadow) {
                classNames.push(styles.tokenShadow);
              }
              return (
                <button
                  type="button"
                  key={`${trackKey}-${index}`}
                  className={classNames.join(' ')}
                  data-subtitle-token-index={index}
                  data-track={trackKey}
                  onClick={(event) => {
                    event.stopPropagation();
                    activateToken(trackKey, index, event.currentTarget);
                  }}
                >
                  {token}
                </button>
              );
            })}
          </div>
        );
      })}
      {bubble ? (
        <MyLinguistBubble
          bubble={bubble}
          isPinned={layout.bubblePinned}
          isDocked={layout.bubbleDocked}
          isDragging={layout.bubbleDragging}
          isResizing={layout.bubbleResizing}
          variant={layout.bubbleDocked ? 'docked' : 'floating'}
          bubbleRef={layout.bubbleRef}
          floatingPlacement={layout.floatingPlacement}
          floatingPosition={layout.floatingPosition}
          floatingSize={layout.floatingSize}
          canNavigatePrev={false}
          canNavigateNext={false}
          onTogglePinned={layout.onTogglePinned}
          onToggleDocked={layout.onToggleDocked}
          onNavigatePrev={() => {}}
          onNavigateNext={() => {}}
          onSpeak={lookup.onSpeak}
          onSpeakSlow={lookup.onSpeakSlow}
          onClose={closeBubble}
          onBubblePointerDown={layout.onBubblePointerDown}
          onBubblePointerMove={layout.onBubblePointerMove}
          onBubblePointerUp={layout.onBubblePointerUp}
          onBubblePointerCancel={layout.onBubblePointerCancel}
          onResizeHandlePointerDown={layout.onResizeHandlePointerDown}
          onResizeHandlePointerMove={layout.onResizeHandlePointerMove}
          onResizeHandlePointerUp={layout.onResizeHandlePointerUp}
          onResizeHandlePointerCancel={layout.onResizeHandlePointerCancel}
        />
      ) : null}
    </div>
  );
}
