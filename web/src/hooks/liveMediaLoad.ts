import type { PipelineMediaResponse } from '../api/dtos';
import { hasChunkSentences, type LiveMediaChunk, type LiveMediaState } from './liveMediaState';
import { normaliseFetchedMedia } from './liveMediaNormalise';

export type NormalisedFetchedMedia = ReturnType<typeof normaliseFetchedMedia>;
export type FetchMediaManifest = (jobId: string) => Promise<PipelineMediaResponse>;

export function hasLiveMediaFiles(media: LiveMediaState): boolean {
  return media.text.length + media.audio.length + media.video.length > 0;
}

export function shouldFetchCompletedMediaFallback(chunks: LiveMediaChunk[]): boolean {
  return !hasChunkSentences(chunks);
}

export async function loadCompletedMediaFallback(
  jobId: string,
  fetchCompletedMedia: FetchMediaManifest,
  liveComplete: boolean,
): Promise<NormalisedFetchedMedia | null> {
  try {
    const fallbackResponse = await fetchCompletedMedia(jobId);
    const fallback = normaliseFetchedMedia(fallbackResponse, jobId);
    if (!hasLiveMediaFiles(fallback.media)) {
      return null;
    }
    return {
      ...fallback,
      complete: fallback.complete || liveComplete,
    };
  } catch {
    return null;
  }
}
