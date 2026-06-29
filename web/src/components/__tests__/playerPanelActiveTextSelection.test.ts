import { describe, expect, it } from 'vitest';
import type { LiveMediaChunk, LiveMediaItem } from '../../hooks/useLiveMedia';
import {
  buildInteractiveAudioCatalog,
  resolveActiveTextChunk,
  resolveChunkForSelectedItem,
  resolveSelectedTextItem,
} from '../player-panel/activeTextSelection';

function item(overrides: Partial<LiveMediaItem> = {}): LiveMediaItem {
  return {
    type: 'text',
    url: 'https://example.com/text/chunk-1.html',
    name: 'chunk-1.html',
    source: 'completed',
    ...overrides,
  };
}

function chunk(overrides: Partial<LiveMediaChunk> = {}): LiveMediaChunk {
  return {
    chunkId: 'chunk-1',
    rangeFragment: 'range-1',
    startSentence: 1,
    endSentence: 2,
    files: [item()],
    ...overrides,
  };
}

describe('player panel active text selection', () => {
  it('resolves the selected text item with first-item fallback', () => {
    const first = item({ url: 'first.html' });
    const second = item({ url: 'second.html' });

    expect(resolveSelectedTextItem([], null)).toBeNull();
    expect(resolveSelectedTextItem([first, second], null)).toBe(first);
    expect(resolveSelectedTextItem([first, second], 'second.html')).toBe(second);
    expect(resolveSelectedTextItem([first, second], 'missing.html')).toBe(first);
  });

  it('resolves chunks from selected text metadata before falling back to file URL', () => {
    const byId = chunk({ chunkId: 'selected-id', rangeFragment: 'other', files: [] });
    const byRange = chunk({ chunkId: 'other-id', rangeFragment: 'selected-range', files: [] });
    const byFile = chunk({
      chunkId: 'file-id',
      rangeFragment: 'file-range',
      files: [item({ url: 'file-match.html' })],
    });

    expect(resolveChunkForSelectedItem([byId, byRange, byFile], item({ chunk_id: 'selected-id' }))).toBe(byId);
    expect(resolveChunkForSelectedItem([byRange, byFile], item({ range_fragment: 'selected-range' }))).toBe(byRange);
    expect(resolveChunkForSelectedItem([byFile], item({ url: 'file-match.html' }))).toBe(byFile);
    expect(resolveChunkForSelectedItem([byFile], null)).toBeNull();
  });

  it('builds an audio catalog from files, audio tracks, and standalone audio media', () => {
    const chunks = [
      chunk({
        chunkId: 'chunk-1',
        rangeFragment: 'range-1',
        files: [item({ type: 'audio', url: 'chunk-1.mp3', name: '', source: 'completed' })],
      }),
      chunk({
        chunkId: 'chunk-2',
        rangeFragment: 'range-2',
        files: [],
        audioTracks: {
          translation: { url: 'translation.mp3' },
          duplicate: { path: 'chunk-1.mp3' },
        },
      }),
    ];

    const catalog = buildInteractiveAudioCatalog(chunks, [
      item({ type: 'audio', url: 'standalone.mp3', name: 'Standalone', source: 'completed' }),
      item({ type: 'audio', url: 'translation.mp3', name: 'Duplicate', source: 'completed' }),
    ]);

    expect(catalog.playlist.map((entry) => entry.url)).toEqual([
      'chunk-1.mp3',
      'translation.mp3',
      'standalone.mp3',
    ]);
    expect(catalog.playlist[0].name).toBe('range-1');
    expect(catalog.nameMap.get('translation.mp3')).toBe('range-2');
    expect(catalog.nameMap.get('standalone.mp3')).toBe('Standalone');
    expect(catalog.chunkIndexMap.get('chunk-1.mp3')).toBe(0);
    expect(catalog.chunkIndexMap.get('translation.mp3')).toBe(1);
    expect(catalog.chunkIndexMap.has('standalone.mp3')).toBe(false);
  });

  it('uses selected chunk before audio-driven active chunk fallbacks', () => {
    const selected = chunk({ chunkId: 'selected' });
    const audioMapped = chunk({ chunkId: 'audio-mapped' });

    expect(
      resolveActiveTextChunk({
        chunks: [selected, audioMapped],
        selectedChunk: selected,
        inlineAudioSelection: 'audio.mp3',
        audioChunkIndexMap: new Map([['audio.mp3', 1]]),
        selectedAudioId: null,
      }),
    ).toBe(selected);
  });

  it('resolves active chunk from inline audio map and audio track metadata', () => {
    const first = chunk({ chunkId: 'first' });
    const mapped = chunk({ chunkId: 'mapped' });
    const tracked = chunk({
      chunkId: 'tracked',
      audioTracks: {
        original: { url: 'audio/tracked.mp3' },
      },
    });

    expect(
      resolveActiveTextChunk({
        chunks: [first, mapped, tracked],
        selectedChunk: null,
        inlineAudioSelection: 'inline.mp3',
        audioChunkIndexMap: new Map([['inline.mp3', 1]]),
        selectedAudioId: null,
      }),
    ).toBe(mapped);

    expect(
      resolveActiveTextChunk({
        chunks: [first, tracked],
        selectedChunk: null,
        inlineAudioSelection: 'https://example.com/audio/tracked.mp3?access_token=redacted',
        audioChunkIndexMap: new Map(),
        selectedAudioId: null,
      }),
    ).toBe(tracked);
  });

  it('resolves active chunk from selected audio id or sentence fallback', () => {
    const first = chunk({ chunkId: 'first', sentences: undefined });
    const audioFile = chunk({
      chunkId: 'audio-file',
      files: [item({ type: 'audio', url: 'selected-audio.mp3' })],
    });
    const withSentences = chunk({
      chunkId: 'sentences',
      sentences: [
        {
          sentence_number: 1,
          original: { text: 'Hello', tokens: ['Hello'] },
          translation: null,
          transliteration: null,
          timeline: [],
          totalDuration: 1,
        },
      ],
    });

    expect(
      resolveActiveTextChunk({
        chunks: [first, audioFile, withSentences],
        selectedChunk: null,
        inlineAudioSelection: null,
        audioChunkIndexMap: new Map(),
        selectedAudioId: 'selected-audio.mp3',
      }),
    ).toBe(audioFile);

    expect(
      resolveActiveTextChunk({
        chunks: [first, withSentences],
        selectedChunk: null,
        inlineAudioSelection: null,
        audioChunkIndexMap: new Map(),
        selectedAudioId: null,
      }),
    ).toBe(withSentences);

    expect(
      resolveActiveTextChunk({
        chunks: [first],
        selectedChunk: null,
        inlineAudioSelection: null,
        audioChunkIndexMap: new Map(),
        selectedAudioId: null,
      }),
    ).toBe(first);
  });
});
