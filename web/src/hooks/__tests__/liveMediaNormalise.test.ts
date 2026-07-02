import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { PipelineMediaResponse } from '../../api/dtos';
import {
  normaliseFetchedMedia,
  normaliseGeneratedSnapshot,
} from '../liveMediaNormalise';

const resolveStorageMock = vi.hoisted(() => vi.fn<[string | null | undefined, string | null | undefined], string>());

vi.mock('../../api/client', () => ({
  appendAccessTokenToStorageUrl: (url: string) => `${url}?token=stub`,
}));

vi.mock('../../utils/storageResolver', async () => {
  const actual = await vi.importActual<typeof import('../../utils/storageResolver')>(
    '../../utils/storageResolver'
  );
  return {
    ...actual,
    resolve: resolveStorageMock,
  };
});

describe('liveMediaNormalise', () => {
  beforeEach(() => {
    resolveStorageMock.mockReset();
    resolveStorageMock.mockImplementation((jobId, path) => `https://storage.example/${jobId}/${path}`);
  });

  it('normalises completed media with chunk metadata, timing, and tokenised URLs', () => {
    const response = {
      media: {
        html: [
          {
            name: ' chapter.html ',
            relative_path: 'html/chapter.html',
            source: 'completed',
          },
        ],
      },
      chunks: [
        {
          chunk_id: 'chunk-2',
          range_fragment: '011-020',
          startSentence: 11,
          endSentence: 20,
          files: [
            {
              type: 'audio',
              path: '/jobs/job-1/media/audio/chunk-2.mp3',
            },
          ],
          sentence_count: '2',
          audioTracks: {
            original: { path: 'orig.mp3', duration: 5 },
          },
          timingTracks: [
            {
              trackType: 'original',
              chunkId: 'chunk-2',
              words: [],
              pauses: [],
              trackOffset: 0,
              tempoFactor: 1,
              version: '2',
            },
          ],
          timing_validation: { ok: true },
        },
      ],
      complete: true,
      diagnostics: {
        mediaFileCount: 2,
        chunkCount: 1,
        chunkFileCount: 1,
        audioFileCount: 1,
        imageFileCount: 0,
        chunksWithAudio: 1,
        chunksWithTiming: 1,
        chunksWithImages: 0,
        chunksWithoutFiles: 0,
        chunksWithoutMetadata: 0,
        filesWithoutUrl: 0,
        filesWithoutSize: 0,
      },
    } as unknown as PipelineMediaResponse;

    const snapshot = normaliseFetchedMedia(response, 'job-1');

    expect(snapshot.complete).toBe(true);
    expect(snapshot.diagnostics).toMatchObject({ mediaFileCount: 2, chunksWithTiming: 1 });
    expect(snapshot.media.text[0]).toMatchObject({
      name: 'chapter.html',
      url: 'https://storage.example/job-1/html/chapter.html?token=stub',
      source: 'completed',
      type: 'text',
    });
    expect(snapshot.chunks).toHaveLength(1);
    expect(snapshot.chunks[0]).toMatchObject({
      chunkId: 'chunk-2',
      rangeFragment: '011-020',
      startSentence: 11,
      endSentence: 20,
      sentenceCount: 2,
      audioTracks: {
        original: { path: 'orig.mp3', duration: 5 },
      },
      timingValidation: { ok: true },
    });
    expect(snapshot.chunks[0].timingTracks?.[0]).toMatchObject({
      chunkId: 'chunk-2',
      trackType: 'original',
    });
    expect(resolveStorageMock).toHaveBeenCalledWith('job-1', 'html/chapter.html');
    expect(resolveStorageMock).toHaveBeenCalledWith('job-1', 'media/audio/chunk-2.mp3');
  });

  it('normalises progress generated-file snapshots into media buckets and sorted chunks', () => {
    const snapshot = normaliseGeneratedSnapshot(
      {
        files: [
          { type: 'audio', path: '/jobs/job-1/media/audio/011-020.mp3' },
          { type: 'html', relative_path: 'html/001-010.html' },
          { type: 'image', path: '/ignored/image.png' },
        ],
        chunks: [
          {
            chunkId: 'chunk-2',
            rangeFragment: '011-020',
            start_sentence: 11,
            end_sentence: 20,
            files: [{ type: 'audio', path: '/jobs/job-1/media/audio/011-020.mp3' }],
          },
          {
            chunkId: 'chunk-1',
            rangeFragment: '001-010',
            start_sentence: 1,
            end_sentence: 10,
            files: [{ type: 'html', relative_path: 'html/001-010.html' }],
          },
        ],
        complete: true,
      },
      'job-1',
    );

    expect(snapshot.complete).toBe(true);
    expect(snapshot.media.audio).toHaveLength(1);
    expect(snapshot.media.text).toHaveLength(1);
    expect(snapshot.media.video).toHaveLength(0);
    expect(snapshot.chunks.map((chunk) => chunk.chunkId)).toEqual(['chunk-1', 'chunk-2']);
  });
});
