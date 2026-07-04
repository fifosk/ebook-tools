import { describe, expect, it, vi } from 'vitest';
import type { PipelineMediaResponse } from '../../api/dtos';
import { loadRefreshedCompletedMedia } from '../liveMediaRefresh';

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

describe('liveMediaRefresh', () => {
  it('normalises refreshed completed media manifests', async () => {
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
      complete: true,
      diagnostics: { ...emptyDiagnostics, mediaFileCount: 1, audioFileCount: 1 },
    };
    const fetchCompletedMedia = vi.fn<[string], Promise<PipelineMediaResponse>>().mockResolvedValue(response);

    const refreshed = await loadRefreshedCompletedMedia('job-1', fetchCompletedMedia);

    expect(fetchCompletedMedia).toHaveBeenCalledWith('job-1');
    expect(refreshed?.complete).toBe(true);
    expect(refreshed?.media.audio[0]).toMatchObject({
      name: 'final.mp3',
      source: 'completed',
      type: 'audio',
    });
    expect(refreshed?.diagnostics).toMatchObject({ mediaFileCount: 1, audioFileCount: 1 });
  });

  it('keeps the last known live snapshot when completed media cannot be refreshed', async () => {
    const fetchCompletedMedia = vi
      .fn<[string], Promise<PipelineMediaResponse>>()
      .mockRejectedValue(new Error('offline'));

    const refreshed = await loadRefreshedCompletedMedia('job-1', fetchCompletedMedia);

    expect(fetchCompletedMedia).toHaveBeenCalledWith('job-1');
    expect(refreshed).toBeNull();
  });
});
