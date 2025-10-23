import { useCallback, useEffect, useMemo, useState } from 'react';
import PipelineSubmissionForm from './components/PipelineSubmissionForm';
import JobList, { JobState } from './components/JobList';
import { PipelineRequestPayload, PipelineStatusResponse, ProgressEventPayload } from './api/dtos';
import {
  cancelJob,
  deleteJob,
  fetchJobs,
  fetchPipelineStatus,
  pauseJob,
  refreshPipelineMetadata,
  resumeJob,
  submitPipeline
} from './api/client';

interface JobRegistryEntry {
  status: PipelineStatusResponse;
  latestEvent?: ProgressEventPayload;
}

type JobAction = 'pause' | 'resume' | 'cancel' | 'delete';

export function App() {
  const [jobs, setJobs] = useState<Record<string, JobRegistryEntry>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [reloadingJobs, setReloadingJobs] = useState<Record<string, boolean>>({});
  const [mutatingJobs, setMutatingJobs] = useState<Record<string, boolean>>({});

  const refreshJobs = useCallback(async () => {
    try {
      const statuses = await fetchJobs();
      const knownJobIds = new Set(statuses.map((job) => job.job_id));

      setJobs((previous) => {
        const next: Record<string, JobRegistryEntry> = {};
        for (const status of statuses) {
          const current = previous[status.job_id];
          next[status.job_id] = {
            status,
            latestEvent: status.latest_event ?? current?.latestEvent
          };
        }
        return next;
      });

      setReloadingJobs((previous) => {
        const next = { ...previous };
        for (const jobId of Object.keys(next)) {
          if (!knownJobIds.has(jobId)) {
            delete next[jobId];
          }
        }
        return next;
      });

      setMutatingJobs((previous) => {
        const next = { ...previous };
        for (const jobId of Object.keys(next)) {
          if (!knownJobIds.has(jobId)) {
            delete next[jobId];
          }
        }
        return next;
      });
    } catch (error) {
      console.warn('Unable to load persisted jobs', error);
    }
  }, []);

  useEffect(() => {
    refreshJobs();
    const interval = window.setInterval(() => {
      void refreshJobs();
    }, 5000);
    return () => {
      window.clearInterval(interval);
    };
  }, [refreshJobs]);

  const handleSubmit = useCallback(async (payload: PipelineRequestPayload) => {
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const submission = await submitPipeline(payload);
      const placeholderStatus: PipelineStatusResponse = {
        job_id: submission.job_id,
        status: submission.status,
        created_at: submission.created_at,
        started_at: null,
        completed_at: null,
        result: null,
        error: null,
        latest_event: null
      };
      setJobs((previous) => ({
        ...previous,
        [submission.job_id]: {
          status: placeholderStatus,
          latestEvent: undefined
        }
      }));
      void refreshJobs();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to submit pipeline job';
      setSubmitError(message);
    } finally {
      setIsSubmitting(false);
    }
  }, [refreshJobs]);

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

  const handleReloadJob = useCallback(async (jobId: string) => {
    setReloadingJobs((previous) => ({ ...previous, [jobId]: true }));
    try {
      let status: PipelineStatusResponse;
      try {
        status = await refreshPipelineMetadata(jobId);
      } catch (refreshError) {
        console.warn('Unable to force metadata refresh for job', jobId, refreshError);
        status = await fetchPipelineStatus(jobId);
      }
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
      void refreshJobs();
    }
  }, [refreshJobs]);

  const performJobAction = useCallback(
    async (jobId: string, action: JobAction) => {
      setMutatingJobs((previous) => ({ ...previous, [jobId]: true }));
      let response: PipelineStatusResponse | null = null;
      let errorMessage: string | null = null;

      try {
        if (action === 'pause') {
          const payload = await pauseJob(jobId);
          response = payload.job;
          errorMessage = payload.error ?? null;
        } else if (action === 'resume') {
          const payload = await resumeJob(jobId);
          response = payload.job;
          errorMessage = payload.error ?? null;
        } else if (action === 'cancel') {
          const payload = await cancelJob(jobId);
          response = payload.job;
          errorMessage = payload.error ?? null;
        } else if (action === 'delete') {
          const payload = await deleteJob(jobId);
          response = payload.job;
          errorMessage = payload.error ?? null;
        }

        if (errorMessage) {
          window.alert(errorMessage);
        }

        if (response) {
          if (action === 'delete') {
            setJobs((previous) => {
              if (!previous[jobId]) {
                return previous;
              }
              const next = { ...previous };
              delete next[jobId];
              return next;
            });
          } else {
            setJobs((previous) => {
              const current = previous[jobId];
              const nextLatestEvent = response?.latest_event ?? current?.latestEvent;
              return {
                ...previous,
                [jobId]: {
                  status: response!,
                  latestEvent: nextLatestEvent
                }
              };
            });
          }
        }
      } catch (error) {
        console.warn(`Unable to ${action} job`, jobId, error);
      } finally {
        setMutatingJobs((previous) => {
          if (!previous[jobId]) {
            return previous;
          }
          const next = { ...previous };
          delete next[jobId];
          return next;
        });
        await refreshJobs();
      }
    },
    [refreshJobs]
  );

  const handlePauseJob = useCallback(
    async (jobId: string) => {
      await performJobAction(jobId, 'pause');
    },
    [performJobAction]
  );

  const handleResumeJob = useCallback(
    async (jobId: string) => {
      await performJobAction(jobId, 'resume');
    },
    [performJobAction]
  );

  const handleCancelJob = useCallback(
    async (jobId: string) => {
      const confirmed = window.confirm(`Cancel job ${jobId}? This will stop any in-progress work.`);
      if (!confirmed) {
        return;
      }
      await performJobAction(jobId, 'cancel');
    },
    [performJobAction]
  );

  const handleDeleteJob = useCallback(
    async (jobId: string) => {
      const confirmed = window.confirm(`Delete job ${jobId}? This will remove persisted metadata.`);
      if (!confirmed) {
        return;
      }
      await performJobAction(jobId, 'delete');
    },
    [performJobAction]
  );

  const jobList: JobState[] = useMemo(() => {
    return Object.entries(jobs).map(([jobId, entry]) => ({
      jobId,
      status: entry.status,
      latestEvent: entry.latestEvent,
      isReloading: Boolean(reloadingJobs[jobId]),
      isMutating: Boolean(mutatingJobs[jobId])
    }));
  }, [jobs, mutatingJobs, reloadingJobs]);

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
        onPauseJob={handlePauseJob}
        onResumeJob={handleResumeJob}
        onCancelJob={handleCancelJob}
        onDeleteJob={handleDeleteJob}
        onReloadJob={handleReloadJob}
      />
    </main>
  );
}

export default App;
