import { describe, expect, it } from 'vitest';
import type { LiveMediaChunk, LiveMediaItem } from '../../hooks/useLiveMedia';
import {
  resolveActiveTextChunk,
  resolveChunkForSelectedItem,
  resolveSelectedTextItem
} from '../player-panel/utils';

function item(overrides: Partial<LiveMediaItem> = {}): LiveMediaItem {
  return {
    type: 'text',
    url: 'https://example.com/text/chunk-1.html',
    name: 'chunk-1.html',
    source: 'completed',
    ...overrides
  };
}

function chunk(overrides: Partial<LiveMediaChunk> = {}): LiveMediaChunk {
  return {
    chunkId: 'chunk-1',
    rangeFragment: 'range-1',
    startSentence: 1,
    endSentence: 2,
    files: [item()],
    ...overrides
  };
}

describe('player-panel utils', () => {
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
      files: [item({ url: 'file-match.html' })]
    });

    expect(resolveChunkForSelectedItem([byId, byRange, byFile], item({ chunk_id: 'selected-id' }))).toBe(byId);
    expect(resolveChunkForSelectedItem([byRange, byFile], item({ range_fragment: 'selected-range' }))).toBe(byRange);
    expect(resolveChunkForSelectedItem([byFile], item({ url: 'file-match.html' }))).toBe(byFile);
    expect(resolveChunkForSelectedItem([byFile], null)).toBeNull();
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
        selectedAudioId: null
      }),
    ).toBe(selected);
  });

  it('resolves active chunk from inline audio map and audio track metadata', () => {
    const first = chunk({ chunkId: 'first' });
    const mapped = chunk({ chunkId: 'mapped' });
    const tracked = chunk({
      chunkId: 'tracked',
      audioTracks: {
        original: { url: 'audio/tracked.mp3' }
      }
    });

    expect(
      resolveActiveTextChunk({
        chunks: [first, mapped, tracked],
        selectedChunk: null,
        inlineAudioSelection: 'inline.mp3',
        audioChunkIndexMap: new Map([['inline.mp3', 1]]),
        selectedAudioId: null
      }),
    ).toBe(mapped);

    expect(
      resolveActiveTextChunk({
        chunks: [first, tracked],
        selectedChunk: null,
        inlineAudioSelection: 'https://example.com/audio/tracked.mp3?access_token=redacted',
        audioChunkIndexMap: new Map(),
        selectedAudioId: null
      }),
    ).toBe(tracked);
  });

  it('resolves active chunk from selected audio id or sentence fallback', () => {
    const first = chunk({ chunkId: 'first', sentences: undefined });
    const audioFile = chunk({
      chunkId: 'audio-file',
      files: [item({ type: 'audio', url: 'selected-audio.mp3' })]
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
          totalDuration: 1
        }
      ]
    });

    expect(
      resolveActiveTextChunk({
        chunks: [first, audioFile, withSentences],
        selectedChunk: null,
        inlineAudioSelection: null,
        audioChunkIndexMap: new Map(),
        selectedAudioId: 'selected-audio.mp3'
      }),
    ).toBe(audioFile);

    expect(
      resolveActiveTextChunk({
        chunks: [first, withSentences],
        selectedChunk: null,
        inlineAudioSelection: null,
        audioChunkIndexMap: new Map(),
        selectedAudioId: null
      }),
    ).toBe(withSentences);

    expect(
      resolveActiveTextChunk({
        chunks: [first],
        selectedChunk: null,
        inlineAudioSelection: null,
        audioChunkIndexMap: new Map(),
        selectedAudioId: null
      }),
    ).toBe(first);
  });
});
