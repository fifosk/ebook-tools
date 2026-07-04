import type { PipelineMediaResponse } from '../api/dtos';
import { normaliseFetchedMedia } from './liveMediaNormalise';

export type RefreshedCompletedMedia = ReturnType<typeof normaliseFetchedMedia>;
export type FetchCompletedMediaManifest = (jobId: string) => Promise<PipelineMediaResponse>;

export async function loadRefreshedCompletedMedia(
  jobId: string,
  fetchCompletedMedia: FetchCompletedMediaManifest,
): Promise<RefreshedCompletedMedia | null> {
  try {
    const response = await fetchCompletedMedia(jobId);
    return normaliseFetchedMedia(response, jobId);
  } catch {
    return null;
  }
}
