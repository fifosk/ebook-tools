import { describe, expect, it } from 'vitest';
import type { LiveMediaChunk, LiveMediaItem } from '../../hooks/useLiveMedia';
import {
  buildMediaFileId,
  deriveSentenceCountFromChunks,
  formatChunkLabel,
  isAudioFileType,
} from '../player-panel/utils';

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

describe('player-panel utils', () => {
  it('detects audio file type signatures', () => {
    expect(isAudioFileType('audio')).toBe(true);
    expect(isAudioFileType('audio_translation')).toBe(true);
    expect(isAudioFileType('video')).toBe(false);
    expect(isAudioFileType(null)).toBe(false);
  });

  it('builds stable media file ids from strongest available reference', () => {
    expect(buildMediaFileId(item({ relative_path: 'media/chunk.mp3' }), 3)).toBe('media/chunk.mp3');
    expect(buildMediaFileId(item({ relative_path: '', path: '/tmp/chunk.mp3' }), 3)).toBe('/tmp/chunk.mp3');
    expect(buildMediaFileId(item({ relative_path: '', path: '', url: 'https://example.com/a.mp3?token=x' }), 3)).toBe(
      'https://example.com/a.mp3',
    );
    expect(buildMediaFileId(item({ relative_path: '', path: '', url: '', name: 'Audio' }), 3)).toBe('Audio');
    expect(buildMediaFileId(item({ relative_path: '', path: '', url: '', name: '', chunk_id: 'chunk-1' }), 3)).toBe(
      'text:chunk-1',
    );
    expect(
      buildMediaFileId(
        item({ relative_path: '', path: '', url: '', name: '', chunk_id: '', range_fragment: 'range-1' }),
        3,
      ),
    ).toBe('text:range-1');
  });

  it('formats chunk labels from range, chunk id, or sentence range', () => {
    expect(formatChunkLabel(chunk({ rangeFragment: 'range-1' }), 0)).toBe('range-1');
    expect(formatChunkLabel(chunk({ rangeFragment: '', chunkId: 'chunk-2' }), 1)).toBe('chunk-2');
    expect(formatChunkLabel(chunk({ rangeFragment: '', chunkId: '', startSentence: 3, endSentence: 4 }), 1)).toBe(
      'Chunk 2 · 3–4',
    );
    expect(
      formatChunkLabel(
        chunk({ rangeFragment: '', chunkId: '', startSentence: undefined, endSentence: undefined }),
        1,
      ),
    ).toBe('Chunk 2');
  });

  it('derives sentence count from chunk sentence metadata', () => {
    expect(
      deriveSentenceCountFromChunks([
        chunk({ startSentence: 1, endSentence: 2 }),
        chunk({ startSentence: 3, endSentence: undefined, sentenceCount: 4 }),
      ]),
    ).toBe(6);
    expect(deriveSentenceCountFromChunks([chunk({ startSentence: undefined, endSentence: undefined })])).toBeNull();
  });
});
