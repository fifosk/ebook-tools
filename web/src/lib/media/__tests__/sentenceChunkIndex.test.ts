import { describe, expect, it } from 'vitest';
import {
  buildSentenceChunkIndex,
  lookupSentence,
  findChunkBySentence,
} from '../sentenceChunkIndex';
import type { LiveMediaChunk } from '../../../hooks/useLiveMedia';

/** Helper to create a minimal LiveMediaChunk for testing */
function makeChunk(overrides: Partial<LiveMediaChunk> = {}): LiveMediaChunk {
  return {
    chunkId: null,
    rangeFragment: null,
    startSentence: null,
    endSentence: null,
    files: [],
    ...overrides,
  };
}

describe('buildSentenceChunkIndex', () => {
  it('returns empty index for empty chunks', () => {
    const idx = buildSentenceChunkIndex([]);
    expect(idx.map.size).toBe(0);
    expect(idx.ranges).toHaveLength(0);
    expect(idx.min).toBeNull();
    expect(idx.max).toBeNull();
  });

  it('builds ranges from startSentence / endSentence', () => {
    const chunks = [
      makeChunk({ chunkId: 'c1', startSentence: 1, endSentence: 10 }),
      makeChunk({ chunkId: 'c2', startSentence: 11, endSentence: 20 }),
    ];
    const idx = buildSentenceChunkIndex(chunks);
    expect(idx.ranges).toHaveLength(2);
    expect(idx.min).toBe(1);
    expect(idx.max).toBe(20);
  });

  it('infers endSentence from sentenceCount', () => {
    const chunks = [
      makeChunk({ chunkId: 'c1', startSentence: 1, sentenceCount: 5 }),
    ];
    const idx = buildSentenceChunkIndex(chunks);
    expect(idx.ranges).toHaveLength(1);
    expect(idx.ranges[0].start).toBe(1);
    expect(idx.ranges[0].end).toBe(5);
  });

  it('populates exact map from sentences array', () => {
    const chunks = [
      makeChunk({
        chunkId: 'c1',
        startSentence: 1,
        endSentence: 3,
        sentences: [
          { sentence_number: 1 } as any,
          { sentence_number: 2 } as any,
          { sentence_number: 3 } as any,
        ],
      }),
    ];
    const idx = buildSentenceChunkIndex(chunks);
    expect(idx.map.size).toBe(3);
    expect(idx.map.get(1)).toEqual({
      chunkIndex: 0,
      localIndex: 0,
      total: 3,
      chunkKey: 'c1',
    });
    expect(idx.map.get(2)?.localIndex).toBe(1);
    expect(idx.map.get(3)?.localIndex).toBe(2);
  });

  it('sorts ranges by start', () => {
    const chunks = [
      makeChunk({ chunkId: 'c2', startSentence: 11, endSentence: 20 }),
      makeChunk({ chunkId: 'c1', startSentence: 1, endSentence: 10 }),
    ];
    const idx = buildSentenceChunkIndex(chunks);
    expect(idx.ranges[0].start).toBe(1);
    expect(idx.ranges[1].start).toBe(11);
  });

  it('handles chunks with no sentence bounds', () => {
    const chunks = [
      makeChunk({ chunkId: 'c1' }),
    ];
    const idx = buildSentenceChunkIndex(chunks);
    expect(idx.map.size).toBe(0);
    expect(idx.ranges).toHaveLength(0);
    expect(idx.min).toBeNull();
    expect(idx.max).toBeNull();
  });

  it('uses rangeFragment as chunkKey when chunkId is null', () => {
    const chunks = [
      makeChunk({ rangeFragment: 'range_01', startSentence: 1, endSentence: 5 }),
    ];
    const idx = buildSentenceChunkIndex(chunks);
    expect(idx.ranges[0].chunkKey).toBe('range_01');
  });
});

describe('lookupSentence', () => {
  const chunks = [
    makeChunk({
      chunkId: 'c1',
      startSentence: 1,
      endSentence: 10,
      sentences: [
        { sentence_number: 1 } as any,
        { sentence_number: 5 } as any,
        { sentence_number: 10 } as any,
      ],
    }),
    makeChunk({ chunkId: 'c2', startSentence: 11, endSentence: 20 }),
    makeChunk({ chunkId: 'c3', startSentence: 21, endSentence: 30 }),
  ];
  const idx = buildSentenceChunkIndex(chunks);

  it('finds exact entries by sentence number', () => {
    const entry = lookupSentence(idx, 5);
    expect(entry).not.toBeNull();
    expect(entry!.chunkIndex).toBe(0);
    expect(entry!.localIndex).toBe(1);
    expect(entry!.total).toBe(3);
  });

  it('falls back to binary search on ranges', () => {
    const entry = lookupSentence(idx, 15);
    expect(entry).not.toBeNull();
    expect(entry!.chunkIndex).toBe(1);
    expect(entry!.localIndex).toBeNull();
    expect(entry!.chunkKey).toBe('c2');
  });

  it('finds first range boundary', () => {
    expect(lookupSentence(idx, 11)?.chunkIndex).toBe(1);
  });

  it('finds last range boundary', () => {
    expect(lookupSentence(idx, 20)?.chunkIndex).toBe(1);
  });

  it('finds in third chunk', () => {
    expect(lookupSentence(idx, 25)?.chunkIndex).toBe(2);
  });

  it('returns null for sentence before all ranges', () => {
    expect(lookupSentence(idx, 0)).toBeNull();
  });

  it('returns null for sentence after all ranges', () => {
    expect(lookupSentence(idx, 31)).toBeNull();
  });

  it('returns null for NaN', () => {
    expect(lookupSentence(idx, NaN)).toBeNull();
  });

  it('returns null for Infinity', () => {
    expect(lookupSentence(idx, Infinity)).toBeNull();
  });

  it('truncates decimal sentence numbers', () => {
    const entry = lookupSentence(idx, 5.7);
    expect(entry).not.toBeNull();
    expect(entry!.chunkIndex).toBe(0);
    expect(entry!.localIndex).toBe(1); // exact match for 5
  });

  it('handles gap between ranges (returns null)', () => {
    // Chunks with a gap: 1-10, 21-30
    const gappedChunks = [
      makeChunk({ chunkId: 'c1', startSentence: 1, endSentence: 10 }),
      makeChunk({ chunkId: 'c2', startSentence: 21, endSentence: 30 }),
    ];
    const gappedIdx = buildSentenceChunkIndex(gappedChunks);
    expect(lookupSentence(gappedIdx, 15)).toBeNull();
  });
});

describe('findChunkBySentence', () => {
  const chunks = [
    makeChunk({ chunkId: 'c1', startSentence: 1, endSentence: 10 }),
    makeChunk({ chunkId: 'c2', startSentence: 11, endSentence: 20 }),
  ];
  const idx = buildSentenceChunkIndex(chunks);

  it('returns the chunk object for a valid sentence', () => {
    const chunk = findChunkBySentence(idx, chunks, 5);
    expect(chunk).toBe(chunks[0]);
  });

  it('returns the second chunk for sentence 15', () => {
    const chunk = findChunkBySentence(idx, chunks, 15);
    expect(chunk).toBe(chunks[1]);
  });

  it('returns null for out-of-range sentence', () => {
    expect(findChunkBySentence(idx, chunks, 25)).toBeNull();
  });
});

describe('exact map priority over ranges', () => {
  it('prefers exact entry when both exist', () => {
    const chunks = [
      makeChunk({
        chunkId: 'c1',
        startSentence: 1,
        endSentence: 10,
        sentences: [
          { sentence_number: 5 } as any,
        ],
      }),
    ];
    const idx = buildSentenceChunkIndex(chunks);
    const entry = lookupSentence(idx, 5);
    // Exact entry has localIndex; range fallback has null
    expect(entry!.localIndex).toBe(0);
    expect(entry!.total).toBe(1);
  });
});

describe('single-sentence chunks', () => {
  it('handles chunk with one sentence', () => {
    const chunks = [
      makeChunk({
        chunkId: 'c1',
        startSentence: 42,
        endSentence: 42,
        sentenceCount: 1,
        sentences: [{ sentence_number: 42 } as any],
      }),
    ];
    const idx = buildSentenceChunkIndex(chunks);
    expect(idx.min).toBe(42);
    expect(idx.max).toBe(42);
    const entry = lookupSentence(idx, 42);
    expect(entry!.chunkIndex).toBe(0);
    expect(entry!.localIndex).toBe(0);
  });
});

describe('large index performance', () => {
  it('handles 1000 chunks efficiently', () => {
    const chunks: LiveMediaChunk[] = [];
    for (let i = 0; i < 1000; i++) {
      chunks.push(makeChunk({
        chunkId: `c${i}`,
        startSentence: i * 10 + 1,
        endSentence: (i + 1) * 10,
      }));
    }
    const idx = buildSentenceChunkIndex(chunks);
    expect(idx.ranges).toHaveLength(1000);
    expect(idx.min).toBe(1);
    expect(idx.max).toBe(10000);

    // First sentence
    expect(lookupSentence(idx, 1)?.chunkIndex).toBe(0);
    // Last sentence
    expect(lookupSentence(idx, 10000)?.chunkIndex).toBe(999);
    // Middle sentence
    expect(lookupSentence(idx, 5005)?.chunkIndex).toBe(500);
    // Out of range
    expect(lookupSentence(idx, 10001)).toBeNull();
  });
});
