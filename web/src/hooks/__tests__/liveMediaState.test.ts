import { describe, expect, it } from 'vitest';
import {
  createEmptyState,
  extractAudioTracks,
  extractGeneratedFiles,
  hasChunkSentences,
  mergeChunkCollections,
  mergeMediaBuckets,
  type LiveMediaChunk,
  type LiveMediaItem
} from '../liveMediaState';

function item(overrides: Partial<LiveMediaItem> = {}): LiveMediaItem {
  return {
    name: 'chunk.mp3',
    url: 'https://storage.example/chunk.mp3',
    source: 'live',
    type: 'audio',
    chunk_id: null,
    range_fragment: null,
    start_sentence: null,
    end_sentence: null,
    ...overrides
  };
}

function chunk(overrides: Partial<LiveMediaChunk> = {}): LiveMediaChunk {
  return {
    chunkId: 'chunk-1',
    rangeFragment: '001-010',
    startSentence: 1,
    endSentence: 10,
    files: [item()],
    ...overrides
  };
}

describe('liveMediaState', () => {
  it('creates isolated empty buckets', () => {
    const first = createEmptyState();
    const second = createEmptyState();

    first.audio.push(item());

    expect(first.audio).toHaveLength(1);
    expect(second.audio).toHaveLength(0);
  });

  it('merges media buckets by URL while preserving older fallback fields', () => {
    const base = createEmptyState();
    base.audio.push(
      item({
        name: 'old.mp3',
        url: 'https://storage.example/same.mp3',
        size: 10,
        updated_at: '2026-06-22T00:00:00Z'
      })
    );
    const incoming = createEmptyState();
    incoming.audio.push(
      item({
        name: '',
        url: 'https://storage.example/same.mp3',
        size: undefined,
        source: 'completed'
      })
    );
    incoming.text.push(
      item({
        type: 'text',
        name: 'chapter.html',
        url: 'https://storage.example/chapter.html'
      })
    );

    const merged = mergeMediaBuckets(base, incoming);

    expect(merged.audio).toHaveLength(1);
    expect(merged.audio[0]).toMatchObject({
      name: 'old.mp3',
      url: 'https://storage.example/same.mp3',
      size: 10,
      source: 'completed',
      updated_at: '2026-06-22T00:00:00Z'
    });
    expect(merged.text).toHaveLength(1);
  });

  it('merges chunk updates by id and preserves useful current fields', () => {
    const current = chunk({
      files: [item({ name: 'old.mp3' })],
      sentenceCount: 10,
      audioTracks: {
        original: { path: 'old-original.mp3', duration: 4 }
      },
      timingTracks: [{ trackType: 'original', chunkId: 'chunk-1', words: [], pauses: [], trackOffset: 0, tempoFactor: 1, version: '1' }]
    });
    const update = chunk({
      files: [],
      sentences: [
        {
          sentence_number: 1,
          original: { text: 'Hello', tokens: ['Hello'] },
          translation: { text: 'Hola', tokens: ['Hola'] },
          timeline: []
        }
      ],
      audioTracks: {
        original: { url: 'new-original.mp3' },
        translated: { path: 'translated.mp3' }
      },
      timingTracks: null
    });

    const merged = mergeChunkCollections([current], [update]);

    expect(merged).toHaveLength(1);
    expect(merged[0].files).toEqual(current.files);
    expect(merged[0].sentences).toEqual(update.sentences);
    expect(merged[0].sentenceCount).toBe(1);
    expect(merged[0].audioTracks).toEqual({
      original: { path: 'old-original.mp3', duration: 4, url: 'new-original.mp3' },
      translated: { path: 'translated.mp3' }
    });
    expect(merged[0].timingTracks).toEqual(current.timingTracks);
  });

  it('appends and sorts new chunks by sentence range', () => {
    const merged = mergeChunkCollections(
      [chunk({ chunkId: 'chunk-2', rangeFragment: '011-020', startSentence: 11, endSentence: 20 })],
      [chunk({ chunkId: 'chunk-1', rangeFragment: '001-010', startSentence: 1, endSentence: 10 })]
    );

    expect(merged.map((entry) => entry.chunkId)).toEqual(['chunk-1', 'chunk-2']);
  });

  it('extracts generated files and detects sentence-bearing chunks', () => {
    expect(extractGeneratedFiles({ generated_files: { complete: true } })).toEqual({ complete: true });
    expect(extractGeneratedFiles({})).toBeUndefined();
    expect(hasChunkSentences([chunk({ sentences: [] })])).toBe(false);
    expect(hasChunkSentences([chunk({ sentenceCount: 2 })])).toBe(true);
  });

  it('extracts keyed audio track objects while trimming blank values', () => {
    expect(
      extractAudioTracks({
        original: {
          path: ' original.mp3 ',
          url: ' https://storage.example/original.mp3 ',
          duration: 12.5,
          sampleRate: 44100.8
        },
        translated: ' translated.mp3 ',
        empty: { path: ' ', url: ' ' },
        ignored: 42
      })
    ).toEqual({
      original: {
        path: 'original.mp3',
        url: 'https://storage.example/original.mp3',
        duration: 12.5,
        sampleRate: 44100
      },
      translated: { path: 'translated.mp3' }
    });
  });

  it('extracts legacy array audio tracks by key or kind', () => {
    expect(
      extractAudioTracks([
        { key: 'original', url: 'original.mp3' },
        { kind: 'translated', url: 'translated.mp3' },
        { key: 'blank', url: ' ' },
        { url: 'missing-key.mp3' }
      ])
    ).toEqual({
      original: { path: 'original.mp3' },
      translated: { path: 'translated.mp3' }
    });
    expect(extractAudioTracks([{ key: 'blank', url: ' ' }])).toBeNull();
    expect(extractAudioTracks(null)).toBeNull();
  });
});
