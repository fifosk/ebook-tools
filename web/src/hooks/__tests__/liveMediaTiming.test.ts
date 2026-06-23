import { describe, expect, it } from 'vitest';
import {
  attachChunkIdToTimingSource,
  normalisePauseTimings,
  normaliseTrackTimingCollection,
  normaliseTrackType,
  normaliseWordLanguage,
  normaliseWordTimings
} from '../liveMediaTiming';

describe('liveMediaTiming', () => {
  it('normalises track type aliases', () => {
    expect(normaliseTrackType('translation')).toBe('translated');
    expect(normaliseTrackType('translated')).toBe('translated');
    expect(normaliseTrackType('original-translated')).toBe('original_translated');
    expect(normaliseTrackType('originaltranslated')).toBe('original_translated');
    expect(normaliseTrackType('orig')).toBe('original');
    expect(normaliseTrackType('commentary')).toBeNull();
  });

  it('normalises word language aliases', () => {
    expect(normaliseWordLanguage('original')).toBe('orig');
    expect(normaliseWordLanguage('transliteration')).toBe('xlit');
    expect(normaliseWordLanguage('translation')).toBe('trans');
    expect(normaliseWordLanguage('notes')).toBeNull();
  });

  it('filters and sorts word timings by playback order', () => {
    expect(
      normaliseWordTimings([
        { id: 'later', sentenceId: 2, tokenIdx: 1, lang: 'translation', text: 'later', t0: 4, t1: 5 },
        { id: 'missing-lang', sentenceId: 1, tokenIdx: 0, text: 'drop', t0: 1, t1: 2 },
        { id: 'tie-b', sentenceId: 1, tokenIdx: 2, lang: 'orig', text: 'b', t0: 2, t1: 3 },
        { id: 'tie-a', sentenceId: 1, tokenIdx: 1, lang: 'original', text: 'a', t0: 2, t1: 3 },
        { id: 'first', sentenceId: '1', tokenIdx: '0', lang: 'translit', text: 'first', t0: '0.5', t1: '1' }
      ]).map((entry) => entry.id)
    ).toEqual(['first', 'tie-a', 'tie-b', 'later']);
  });

  it('filters and sorts pause timings', () => {
    expect(
      normalisePauseTimings([
        { t0: 5, t1: 6, reason: 'tempo' },
        { t0: null, t1: 2, reason: 'gap' },
        { t0: '1', t1: '1.5', reason: 'custom' },
        { t0: 3, t1: 4, reason: 'silence' }
      ])
    ).toEqual([
      { t0: 1, t1: 1.5, reason: undefined },
      { t0: 3, t1: 4, reason: 'silence' },
      { t0: 5, t1: 6, reason: 'tempo' }
    ]);
  });

  it('normalises modern track timing payloads', () => {
    expect(
      normaliseTrackTimingCollection({
        track_type: 'translation',
        chunk_id: 'chunk-1',
        track_offset: '1.25',
        tempo_factor: '0.95',
        version: '2',
        words: [
          { id: 'w2', sentenceId: 1, tokenIdx: 1, lang: 'trans', text: 'mundo', t0: 2, t1: 3 },
          { id: 'w1', sentenceId: 1, tokenIdx: 0, lang: 'translation', text: 'hola', t0: 1, t1: 2 }
        ],
        pauses: [
          { t0: 2.8, t1: 3.2, reason: 'gap' },
          { t0: 0.4, t1: 0.8, reason: 'invalid' }
        ]
      })
    ).toEqual([
      {
        trackType: 'translated',
        chunkId: 'chunk-1',
        words: [
          { id: 'w1', sentenceId: 1, tokenIdx: 0, lang: 'trans', text: 'hola', t0: 1, t1: 2 },
          { id: 'w2', sentenceId: 1, tokenIdx: 1, lang: 'trans', text: 'mundo', t0: 2, t1: 3 }
        ],
        pauses: [
          { t0: 0.4, t1: 0.8, reason: undefined },
          { t0: 2.8, t1: 3.2, reason: 'gap' }
        ],
        trackOffset: 1.25,
        tempoFactor: 0.95,
        version: '2'
      }
    ]);
  });

  it('converts legacy timing tracks into typed payloads', () => {
    expect(
      normaliseTrackTimingCollection({
        chunk_id: 'chunk-7',
        track_offset: 0.5,
        tempo_factor: -2,
        version: 'legacy',
        translation: [
          { sentenceIdx: 2, wordIdx: 1, text: 'hola', start: 12, end: 13, startGate: 10 }
        ],
        mix: [
          { sentenceIdx: 2, wordIdx: 0, text: 'hello', start: 1, end: 1.2, lane: 'original' },
          { sentenceIdx: 2, wordIdx: 1, text: 'hola', start: 1.4, end: 1.8, lane: 'translation' }
        ],
        original: [
          { sentenceIdx: 2, wordIdx: 0, text: 'hello', start: 0.5, end: 0.9 }
        ]
      })
    ).toEqual([
      {
        trackType: 'translated',
        chunkId: 'chunk-7',
        words: [
          { id: 'chunk-7:trans:2:1', sentenceId: 2, tokenIdx: 1, lang: 'trans', text: 'hola', t0: 2, t1: 3 }
        ],
        pauses: [],
        trackOffset: 0.5,
        tempoFactor: 1,
        version: 'legacy'
      },
      {
        trackType: 'original_translated',
        chunkId: 'chunk-7',
        words: [
          { id: 'chunk-7:orig:2:0', sentenceId: 2, tokenIdx: 0, lang: 'orig', text: 'hello', t0: 1, t1: 1.2 },
          { id: 'chunk-7:trans:2:1', sentenceId: 2, tokenIdx: 1, lang: 'trans', text: 'hola', t0: 1.4, t1: 1.8 }
        ],
        pauses: [],
        trackOffset: 0.5,
        tempoFactor: 1,
        version: 'legacy'
      },
      {
        trackType: 'original',
        chunkId: 'chunk-7',
        words: [
          { id: 'chunk-7:orig:2:0', sentenceId: 2, tokenIdx: 0, lang: 'orig', text: 'hello', t0: 0.5, t1: 0.9 }
        ],
        pauses: [],
        trackOffset: 0.5,
        tempoFactor: 1,
        version: 'legacy'
      }
    ]);
  });

  it('attaches missing chunk ids to object timing sources only', () => {
    expect(attachChunkIdToTimingSource({ translation: [] }, 'chunk-9')).toEqual({
      chunk_id: 'chunk-9',
      translation: []
    });
    expect(attachChunkIdToTimingSource({ chunkId: 'existing', translation: [] }, 'chunk-9')).toEqual({
      chunkId: 'existing',
      translation: []
    });
    const arraySource = [{ translation: [] }];
    expect(attachChunkIdToTimingSource(arraySource, 'chunk-9')).toBe(arraySource);
  });
});
