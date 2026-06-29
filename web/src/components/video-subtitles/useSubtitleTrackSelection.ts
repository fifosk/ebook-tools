import {
  useEffect,
  useMemo,
  useState,
  type Dispatch,
  type SetStateAction,
} from 'react';
import type { AssSubtitleCue } from '../../lib/subtitles';
import {
  TRACK_RENDER_ORDER,
  resolveDefaultSelection,
  resolveShadowTarget,
  type SubtitleTokenSelection,
  type TrackKind,
} from './subtitleTrackOverlayUtils';

type SubtitleCueVisibility = {
  original: boolean;
  translation: boolean;
  transliteration: boolean;
};

type UseSubtitleTrackSelectionOptions = {
  activeCue: AssSubtitleCue | null;
  cueVisibility: SubtitleCueVisibility;
  isPlaying: boolean;
};

type UseSubtitleTrackSelectionResult = {
  tracks: AssSubtitleCue['tracks'];
  visibleTracks: TrackKind[];
  selection: SubtitleTokenSelection | null;
  setSelection: Dispatch<SetStateAction<SubtitleTokenSelection | null>>;
  playbackSelection: SubtitleTokenSelection | null;
  shadowTarget: SubtitleTokenSelection | null;
};

const EMPTY_TRACKS: AssSubtitleCue['tracks'] = {};

export function useSubtitleTrackSelection({
  activeCue,
  cueVisibility,
  isPlaying,
}: UseSubtitleTrackSelectionOptions): UseSubtitleTrackSelectionResult {
  const tracks = activeCue?.tracks ?? EMPTY_TRACKS;

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
  }, [
    cueVisibility.original,
    cueVisibility.translation,
    cueVisibility.transliteration,
    tracks,
  ]);

  const [selection, setSelection] = useState<SubtitleTokenSelection | null>(null);

  useEffect(() => {
    if (!activeCue || visibleTracks.length === 0) {
      setSelection(null);
      return;
    }
    const fallback = resolveDefaultSelection(visibleTracks, tracks);
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

  const translationTokens = tracks.translation?.tokens ?? null;
  const transliterationTokens = tracks.transliteration?.tokens ?? null;
  const shadowTarget = useMemo(() => {
    const source = playbackSelection ?? selection;
    if (!source) {
      return null;
    }
    return resolveShadowTarget(source.track, source.index, translationTokens, transliterationTokens);
  }, [playbackSelection, selection, translationTokens, transliterationTokens]);

  return {
    tracks,
    visibleTracks,
    selection,
    setSelection,
    playbackSelection,
    shadowTarget,
  };
}
