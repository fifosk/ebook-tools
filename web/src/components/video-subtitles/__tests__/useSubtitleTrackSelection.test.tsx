import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { AssSubtitleCue } from '../../../lib/subtitles';
import { useSubtitleTrackSelection } from '../useSubtitleTrackSelection';

const ALL_VISIBLE = {
  original: true,
  translation: true,
  transliteration: true,
};

function cue(
  tracks: AssSubtitleCue['tracks'] = {
    original: { tokens: ['Source'], currentIndex: null },
    transliteration: { tokens: ['goedemorgen', 'wereld'], currentIndex: 0 },
    translation: { tokens: ['good', 'morning', 'world'], currentIndex: 1 },
  },
): AssSubtitleCue {
  return { start: 1, end: 3, tracks };
}

describe('useSubtitleTrackSelection', () => {
  it('filters hidden or empty tracks and picks the default visible translation token', () => {
    const { result } = renderHook(() =>
      useSubtitleTrackSelection({
        activeCue: cue({
          original: { tokens: ['Source'], currentIndex: null },
          transliteration: { tokens: [], currentIndex: null },
          translation: { tokens: ['good', 'morning'], currentIndex: 1 },
        }),
        cueVisibility: ALL_VISIBLE,
        isPlaying: false,
      }),
    );

    expect(result.current.visibleTracks).toEqual(['original', 'translation']);
    expect(result.current.selection).toEqual({ track: 'translation', index: 1 });
    expect(result.current.shadowTarget).toBeNull();
  });

  it('preserves paused selections while clamping indexes after the active cue changes', () => {
    const firstCue = cue();
    const secondCue = cue({
      original: { tokens: ['Next'], currentIndex: null },
      transliteration: { tokens: ['volgende'], currentIndex: null },
      translation: { tokens: ['next'], currentIndex: 0 },
    });
    const { result, rerender } = renderHook(
      ({ activeCue }) =>
        useSubtitleTrackSelection({
          activeCue,
          cueVisibility: ALL_VISIBLE,
          isPlaying: false,
        }),
      { initialProps: { activeCue: firstCue } },
    );

    act(() => {
      result.current.setSelection({ track: 'translation', index: 2 });
    });
    expect(result.current.selection).toEqual({ track: 'translation', index: 2 });

    rerender({ activeCue: secondCue });

    expect(result.current.visibleTracks).toEqual(['original', 'transliteration', 'translation']);
    expect(result.current.selection).toEqual({ track: 'translation', index: 0 });
  });

  it('follows playback current indexes and shadows aligned translation pairs', () => {
    const { result, rerender } = renderHook(
      ({ isPlaying }) =>
        useSubtitleTrackSelection({
          activeCue: cue({
            original: { tokens: ['Source'], currentIndex: null },
            transliteration: { tokens: ['goedemorgen', 'wereld'], currentIndex: 1 },
            translation: { tokens: ['good', 'world'], currentIndex: 1 },
          }),
          cueVisibility: ALL_VISIBLE,
          isPlaying,
        }),
      { initialProps: { isPlaying: true } },
    );

    expect(result.current.selection).toEqual({ track: 'translation', index: 1 });
    expect(result.current.playbackSelection).toEqual({ track: 'translation', index: 1 });
    expect(result.current.shadowTarget).toEqual({ track: 'transliteration', index: 1 });

    rerender({ isPlaying: false });

    expect(result.current.playbackSelection).toBeNull();
    expect(result.current.shadowTarget).toEqual({ track: 'transliteration', index: 1 });
  });

  it('clears selection when there is no active cue or every visible track is empty', () => {
    const { result, rerender } = renderHook(
      ({ activeCue }) =>
        useSubtitleTrackSelection({
          activeCue,
          cueVisibility: ALL_VISIBLE,
          isPlaying: false,
        }),
      { initialProps: { activeCue: cue() as AssSubtitleCue | null } },
    );

    expect(result.current.selection).toEqual({ track: 'translation', index: 1 });

    rerender({ activeCue: null });

    expect(result.current.tracks).toEqual({});
    expect(result.current.visibleTracks).toEqual([]);
    expect(result.current.selection).toBeNull();
  });
});
