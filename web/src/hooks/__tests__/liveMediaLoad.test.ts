import { describe, expect, it, vi } from 'vitest';
import type { PipelineMediaResponse } from '../../api/dtos';
import type { LiveMediaChunk } from '../liveMediaState';
import {
  hasLiveMediaFiles,
  loadCompletedMediaFallback,
  shouldFetchCompletedMediaFallback,
} from '../liveMediaLoad';

const emptyDiagnostics = {
  mediaFileCount: 0,
  chunkCount: 0,
  chunkFileCount: 0,
  audioFileCount: 0,
  imageFileCount: 0,
  chunksWithAudio: 0,
  chunksWithTiming: 0,
  chunksWithImages: 0,
  chunksWithoutFiles: 0,
  chunksWithoutMetadata: 0,
  filesWithoutUrl: 0,
  filesWithoutSize: 0,
  gapCount: 0,
};

describe('liveMediaLoad', () => {
  it('skips completed-media fallback when live chunks already include sentences', () => {
    const chunkWithSentences: LiveMediaChunk = {
      chunkId: 'chunk-1',
      rangeFragment: '001-001',
      startSentence: 1,
      endSentence: 1,
      files: [],
      sentences: [
        {
          sentence_number: 1,
          original: { text: 'Hello', tokens: ['Hello'] },
          timeline: [],
        },
      ],
    };

    expect(shouldFetchCompletedMediaFallback([chunkWithSentences])).toBe(false);
    expect(shouldFetchCompletedMediaFallback([{ ...chunkWithSentences, sentences: [] }])).toBe(true);
  });

  it('loads a completed-media fallback only when it has visible media files', async () => {
    const response: PipelineMediaResponse = {
      media: {
        audio: [
          {
            name: 'final.mp3',
            url: 'https://storage.example/final.mp3',
            source: 'completed',
            type: 'audio',
          },
        ],
      },
      chunks: [],
      complete: false,
      diagnostics: { ...emptyDiagnostics, mediaFileCount: 1, audioFileCount: 1 },
    };
    const fetchCompletedMedia = vi.fn<[string], Promise<PipelineMediaResponse>>().mockResolvedValue(response);

    const fallback = await loadCompletedMediaFallback('job-1', fetchCompletedMedia, true);

    expect(fetchCompletedMedia).toHaveBeenCalledWith('job-1');
    expect(fallback?.complete).toBe(true);
    expect(fallback?.media.audio).toHaveLength(1);
    expect(fallback?.diagnostics).toMatchObject({ mediaFileCount: 1, audioFileCount: 1 });
  });

  it('ignores empty or failed completed-media fallbacks', async () => {
    const emptyResponse: PipelineMediaResponse = {
      media: {},
      chunks: [],
      complete: true,
      diagnostics: emptyDiagnostics,
    };
    const emptyFallback = await loadCompletedMediaFallback(
      'job-1',
      vi.fn<[string], Promise<PipelineMediaResponse>>().mockResolvedValue(emptyResponse),
      false,
    );
    const failedFallback = await loadCompletedMediaFallback(
      'job-1',
      vi.fn<[string], Promise<PipelineMediaResponse>>().mockRejectedValue(new Error('offline')),
      false,
    );

    expect(emptyFallback).toBeNull();
    expect(failedFallback).toBeNull();
    expect(hasLiveMediaFiles({ text: [], audio: [], video: [] })).toBe(false);
  });
});
