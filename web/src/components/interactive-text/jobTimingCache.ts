import { fetchJobTiming } from '../../api/client';
import type { JobTimingResponse } from '../../api/dtos';

type JobTimingFetcher = (jobId: string) => Promise<JobTimingResponse | null>;

const jobTimingPromises = new Map<string, Promise<JobTimingResponse | null>>();

export function loadCachedJobTiming(
  jobId: string,
  fetcher: JobTimingFetcher = fetchJobTiming,
): Promise<JobTimingResponse | null> {
  const cached = jobTimingPromises.get(jobId);
  if (cached) {
    return cached;
  }

  const promise = fetcher(jobId).catch((error) => {
    jobTimingPromises.delete(jobId);
    throw error;
  });
  jobTimingPromises.set(jobId, promise);
  return promise;
}

export function clearCachedJobTiming(jobId?: string): void {
  if (jobId) {
    jobTimingPromises.delete(jobId);
    return;
  }
  jobTimingPromises.clear();
}
