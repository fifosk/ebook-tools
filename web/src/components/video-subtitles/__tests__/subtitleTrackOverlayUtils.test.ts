import { describe, expect, it } from 'vitest';
import type { VoiceInventoryResponse } from '../../../api/dtos';
import type { AssSubtitleCue } from '../../../lib/subtitles';
import {
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
  type TrackLineMap
} from '../subtitleTrackOverlayUtils';

function cue(start: number, end: number): AssSubtitleCue {
  return {
    start,
    end,
    tracks: {}
  };
}

function lineMap(lines: number[][]): TrackLineMap {
  const tokenLine = new Map<number, number>();
  lines.forEach((line, lineIndex) => {
    line.forEach((tokenIndex) => {
      tokenLine.set(tokenIndex, lineIndex);
    });
  });
  return { lines, tokenLine };
}

describe('subtitleTrackOverlayUtils', () => {
  it('clamps subtitle scale, opacity, and vertical offset', () => {
    expect(clampScale(null)).toBe(1);
    expect(clampScale(0.1)).toBe(0.25);
    expect(clampScale(8)).toBe(4);
    expect(clampOpacity(undefined)).toBe(0.6);
    expect(clampOpacity(-1)).toBe(0);
    expect(clampOpacity(2)).toBe(1);
    expect(clampOffset(-900, 600)).toBe(-270);
    expect(clampOffset(40, 600)).toBe(0);
  });

  it('finds active and insertion cue indices', () => {
    const cues = [cue(0, 2), cue(2, 5), cue(8, 10)];

    expect(findActiveCueIndex(cues, 3, 1)).toBe(1);
    expect(findActiveCueIndex(cues, 8.5, 1)).toBe(2);
    expect(findCueInsertIndex(cues, 6)).toBe(2);
  });

  it('maps ASS tracks to text-player variants', () => {
    expect(toVariantKind('original')).toBe('original');
    expect(toVariantKind('translation')).toBe('translation');
    expect(toVariantKind('transliteration')).toBe('translit');
  });

  it('prefers translation, then transliteration, then original for default selection', () => {
    expect(
      resolveDefaultSelection(['original', 'transliteration', 'translation'], {
        original: { tokens: ['orig'], currentIndex: 0 },
        transliteration: { tokens: ['translit'], currentIndex: 0 },
        translation: { tokens: ['a', 'b'], currentIndex: 10 }
      })
    ).toEqual({ track: 'translation', index: 1 });
    expect(
      resolveDefaultSelection(['original'], {
        original: { tokens: ['orig'], currentIndex: null }
      })
    ).toEqual({ track: 'original', index: 0 });
  });

  it('links translation and transliteration shadow targets only when token counts match', () => {
    expect(resolveShadowTarget('translation', 1, ['a', 'b'], ['x', 'y'])).toEqual({
      track: 'transliteration',
      index: 1
    });
    expect(resolveShadowTarget('transliteration', 0, ['a'], ['x'])).toEqual({
      track: 'translation',
      index: 0
    });
    expect(resolveShadowTarget('translation', 0, ['a'], ['x', 'y'])).toBeNull();
  });

  it('moves within wrapped token lines and falls back to flat wrapping', () => {
    const maps = {
      original: lineMap([[0, 1, 2], [3, 4]]),
      transliteration: lineMap([]),
      translation: lineMap([])
    };

    expect(moveIndexWithinLine('original', 0, -1, 5, maps)).toBe(2);
    expect(moveIndexWithinLine('original', 2, 1, 5, maps)).toBe(0);
    expect(moveIndexWithinLine('translation', 0, -1, 3, maps)).toBe(2);
  });

  it('builds language-matched subtitle TTS voice options without duplicates', () => {
    const inventory: VoiceInventoryResponse = {
      piper: [
        { name: 'en_US-lessac', lang: 'en_US', quality: 'medium' },
        { name: 'es_ES-sharvard', lang: 'es_ES', quality: 'high' }
      ],
      macos: [
        { name: 'Samantha', lang: 'en-US', quality: 'Enhanced', gender: 'Female' },
        { name: 'Monica', lang: 'es-MX', quality: 'Enhanced', gender: 'Female' }
      ],
      gtts: [
        { code: 'en', name: 'English' },
        { code: 'es', name: 'Spanish' }
      ]
    };

    expect(buildSubtitleTtsVoiceOptions(inventory, 'English', 'Samantha')).toEqual([
      'Samantha',
      'en_US-lessac',
      'gTTS-en'
    ]);
  });
});
