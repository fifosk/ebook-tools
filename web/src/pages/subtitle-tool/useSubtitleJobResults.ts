import { useEffect, useState } from 'react';
import { fetchSubtitleResult } from '../../api/client';
import type { SubtitleJobResultPayload } from '../../api/dtos';
import type { JobState } from '../../components/JobList';
import { selectMissingCompletedSubtitleJobs } from './subtitleToolUtils';

export function useSubtitleJobResults(subtitleJobs: JobState[]) {
  const [jobResults, setJobResults] = useState<Record<string, SubtitleJobResultPayload>>({});

  useEffect(() => {
    const missing = selectMissingCompletedSubtitleJobs(subtitleJobs, jobResults);
    if (missing.length === 0) {
      return;
    }

    let cancelled = false;
    (async () => {
      const results = await Promise.all(
        missing.map(async (job) => {
          try {
            const payload = await fetchSubtitleResult(job.jobId);
            return { jobId: job.jobId, payload };
          } catch (error) {
            console.warn('Unable to load subtitle result', job.jobId, error);
            return null;
          }
        })
      );
      if (cancelled) {
        return;
      }
      setJobResults((previous) => {
        const next = { ...previous };
        for (const entry of results) {
          if (!entry) {
            continue;
          }
          next[entry.jobId] = entry.payload;
        }
        return next;
      });
    })();

    return () => {
      cancelled = true;
    };
  }, [subtitleJobs, jobResults]);

  return jobResults;
}
