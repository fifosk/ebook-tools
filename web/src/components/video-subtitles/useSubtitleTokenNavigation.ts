import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  type Dispatch,
  type KeyboardEvent as ReactKeyboardEvent,
  type MutableRefObject,
  type SetStateAction,
} from 'react';
import type { TextPlayerVariantKind } from '../../text-player/TextPlayer';
import type { AssSubtitleCue } from '../../lib/subtitles';
import {
  EMPTY_LINE_MAP,
  moveIndexWithinLine,
  resolveDefaultSelection,
  toVariantKind,
  type SubtitleTokenSelection,
  type TrackKind,
  type TrackLineMap,
} from './subtitleTrackOverlayUtils';

type CueVisibility = {
  original: boolean;
  translation: boolean;
  transliteration: boolean;
};

type OpenLinguistBubbleForRect = (
  query: string,
  rect: DOMRect,
  trigger: 'click' | 'selection',
  variantKind: TextPlayerVariantKind | null,
  anchorElement: HTMLElement | null,
) => void;

type UseSubtitleTokenNavigationOptions = {
  overlayRef: MutableRefObject<HTMLDivElement | null>;
  overlayActive: boolean;
  activeCue: AssSubtitleCue | null;
  subtitleScale: number;
  cueVisibility: CueVisibility;
  tracks: AssSubtitleCue['tracks'];
  visibleTracks: TrackKind[];
  selection: SubtitleTokenSelection | null;
  setSelection: Dispatch<SetStateAction<SubtitleTokenSelection | null>>;
  isPlaying: boolean;
  linguistEnabled: boolean;
  consumeIgnoredClick: () => boolean;
  resumePlaybackAndDefocus: () => void;
  requestPositionUpdate: () => void;
  openLinguistBubbleForRect: OpenLinguistBubbleForRect;
};

type UseSubtitleTokenNavigationResult = {
  trackRefs: MutableRefObject<Record<TrackKind, HTMLDivElement | null>>;
  rebuildLineMaps: () => void;
  activateToken: (trackKey: TrackKind, index: number, element: HTMLElement | null) => void;
  handleTokenClick: (trackKey: TrackKind, index: number, element: HTMLElement) => void;
  openSelectionLookup: () => boolean;
  handleKeyDown: (event: ReactKeyboardEvent<HTMLDivElement>) => void;
};

const EMPTY_TRACK_REFS: Record<TrackKind, HTMLDivElement | null> = {
  original: null,
  transliteration: null,
  translation: null,
};

const EMPTY_LINE_MAPS: Record<TrackKind, TrackLineMap> = {
  original: EMPTY_LINE_MAP,
  transliteration: EMPTY_LINE_MAP,
  translation: EMPTY_LINE_MAP,
};

export function useSubtitleTokenNavigation({
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
  requestPositionUpdate,
  openLinguistBubbleForRect,
}: UseSubtitleTokenNavigationOptions): UseSubtitleTokenNavigationResult {
  const trackRefs = useRef<Record<TrackKind, HTMLDivElement | null>>({ ...EMPTY_TRACK_REFS });
  const lineMapsRef = useRef<Record<TrackKind, TrackLineMap>>({ ...EMPTY_LINE_MAPS });

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
      requestPositionUpdate();
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, [overlayActive, overlayRef, rebuildLineMaps, requestPositionUpdate]);

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
        openLinguistBubbleForRect(word, rect, 'click', toVariantKind(trackKey), element);
      }
      setSelection({ track: trackKey, index });
      overlayRef.current?.focus();
    },
    [linguistEnabled, openLinguistBubbleForRect, overlayRef, setSelection, tracks],
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

  const openSelectionLookup = useCallback(() => {
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
    openLinguistBubbleForRect(token, rect, 'click', toVariantKind(current.track), anchor);
    setSelection({ track: current.track, index: current.index });
    overlayRef.current?.focus();
    return true;
  }, [linguistEnabled, openLinguistBubbleForRect, overlayRef, selection, setSelection, tracks, visibleTracks]);

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
      openSelectionLookup,
      resumePlaybackAndDefocus,
      setSelection,
    ],
  );

  return {
    trackRefs,
    rebuildLineMaps,
    activateToken,
    handleTokenClick,
    openSelectionLookup,
    handleKeyDown,
  };
}
