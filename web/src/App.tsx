import { useCallback, useEffect, useMemo, useState } from 'react';
import PipelineSubmissionForm from './components/PipelineSubmissionForm';
import JobList, { JobState } from './components/JobList';
import {
  PipelineRequestPayload,
  PipelineStatusResponse,
  PipelineSubmissionResponse,
  ProgressEventPayload
} from './api/dtos';
import { fetchPipelineStatus, submitPipeline } from './api/client';

interface JobRegistryEntry {
  submission: PipelineSubmissionResponse;
  status?: PipelineStatusResponse;
  latestEvent?: ProgressEventPayload;
}

export function App() {
  const [jobs, setJobs] = useState<Record<string, JobRegistryEntry>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [reloadingJobs, setReloadingJobs] = useState<Record<string, boolean>>({});

  const jobIds = useMemo(() => Object.keys(jobs), [jobs]);
  const jobKey = useMemo(() => jobIds.join('|'), [jobIds]);

  const handleSubmit = useCallback(async (payload: PipelineRequestPayload) => {
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const submission = await submitPipeline(payload);
      setJobs((previous) => ({
        ...previous,
        [submission.job_id]: {
          submission,
          status: undefined,
          latestEvent: undefined
        }
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to submit pipeline job';
      setSubmitError(message);
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  useEffect(() => {
    if (jobIds.length === 0) {
      return;
    }

    let cancelled = false;

    const refresh = async () => {
      const updates = await Promise.all(
        jobIds.map(async (jobId) => {
          try {
            const status = await fetchPipelineStatus(jobId);
            return { jobId, status } as const;
          } catch (error) {
            console.warn('Unable to refresh job', jobId, error);
            return { jobId, status: null } as const;
          }
        })
      );

      if (cancelled) {
        return;
      }

      setJobs((previous) => {
        const next = { ...previous };
        for (const { jobId, status } of updates) {
          if (!next[jobId] || !status) {
            continue;
          }
          next[jobId] = {
            ...next[jobId],
            status,
            latestEvent: status.latest_event ?? next[jobId].latestEvent
          };
        }
        return next;
      });
    };

    refresh();
    const interval = window.setInterval(refresh, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [jobKey]);

  const handleProgressEvent = useCallback((jobId: string, event: ProgressEventPayload) => {
    setJobs((previous) => {
      const current = previous[jobId];
      if (!current) {
        return previous;
      }
      return {
        ...previous,
        [jobId]: {
          ...current,
          latestEvent: event
        }
      };
    });
  }, []);

  const handleRemoveJob = useCallback((jobId: string) => {
    setJobs((previous) => {
      if (!previous[jobId]) {
        return previous;
      }
      const next = { ...previous };
      delete next[jobId];
      return next;
    });
    setReloadingJobs((previous) => {
      if (!previous[jobId]) {
        return previous;
      }
      const next = { ...previous };
      delete next[jobId];
      return next;
    });
  }, []);

  const handleReloadJob = useCallback(async (jobId: string) => {
    setReloadingJobs((previous) => ({ ...previous, [jobId]: true }));
    try {
      const status = await fetchPipelineStatus(jobId);
      setJobs((previous) => {
        const current = previous[jobId];
        if (!current) {
          return previous;
        }
        return {
          ...previous,
          [jobId]: {
            ...current,
            status,
            latestEvent: status.latest_event ?? current.latestEvent
          }
        };
      });
    } catch (error) {
      console.warn('Unable to reload job metadata', jobId, error);
    } finally {
      setReloadingJobs((previous) => {
        if (!previous[jobId]) {
          return previous;
        }
        const next = { ...previous };
        delete next[jobId];
        return next;
      });
    }
  }, []);

  const jobList: JobState[] = useMemo(() => {
    return Object.entries(jobs).map(([jobId, entry]) => ({
      jobId,
      submission: entry.submission,
      status: entry.status,
      latestEvent: entry.latestEvent,
      isReloading: Boolean(reloadingJobs[jobId])
    }));
  }, [jobs, reloadingJobs]);

  return (
    <main>
      <header style={{ marginBottom: '1.5rem' }}>
        <h1>ebook-tools pipeline dashboard</h1>
        <p style={{ maxWidth: 720 }}>
          Submit ebook processing jobs, monitor their current state, and observe real-time progress
          streamed directly from the FastAPI backend.
        </p>
      </header>
      {submitError ? <div className="alert">{submitError}</div> : null}
      <PipelineSubmissionForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      <JobList
        jobs={jobList}
        onProgressEvent={handleProgressEvent}
        onRemoveJob={handleRemoveJob}
        onReloadJob={handleReloadJob}
      />
    </main>
  );
}

export default App;
