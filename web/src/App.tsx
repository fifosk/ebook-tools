import { useCallback, useEffect, useMemo, useState, type ChangeEvent } from 'react';
import PipelineSubmissionForm, { PipelineFormSection } from './components/PipelineSubmissionForm';
import type { JobState } from './components/JobList';
import JobProgress from './components/JobProgress';
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
import { useTheme } from './components/ThemeProvider';
import type { ThemeMode } from './components/ThemeProvider';

interface JobRegistryEntry {
  status: PipelineStatusResponse;
  latestEvent?: ProgressEventPayload;
}

type JobAction = 'pause' | 'resume' | 'cancel' | 'delete';

type PipelineMenuView =
  | 'pipeline:source'
  | 'pipeline:language'
  | 'pipeline:output'
  | 'pipeline:performance'
  | 'pipeline:advanced'
  | 'pipeline:submit';

type SelectedView = PipelineMenuView | string;

const PIPELINE_SECTION_MAP: Record<PipelineMenuView, PipelineFormSection> = {
  'pipeline:source': 'source',
  'pipeline:language': 'language',
  'pipeline:output': 'output',
  'pipeline:performance': 'performance',
  'pipeline:advanced': 'advanced',
  'pipeline:submit': 'submit'
};

const PIPELINE_SETTINGS: Array<{ key: PipelineMenuView; label: string }> = [
  { key: 'pipeline:source', label: 'Source material' },
  { key: 'pipeline:language', label: 'Language & scope' },
  { key: 'pipeline:output', label: 'Output & narration' },
  { key: 'pipeline:performance', label: 'Performance tuning' },
  { key: 'pipeline:advanced', label: 'Advanced options' }
];

export function App() {
  const [jobs, setJobs] = useState<Record<string, JobRegistryEntry>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [reloadingJobs, setReloadingJobs] = useState<Record<string, boolean>>({});
  const [mutatingJobs, setMutatingJobs] = useState<Record<string, boolean>>({});
  const [selectedView, setSelectedView] = useState<SelectedView>('pipeline:source');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const { mode: themeMode, resolvedTheme, setMode: setThemeMode } = useTheme();

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

  useEffect(() => {
    if (typeof selectedView === 'string' && selectedView.startsWith('pipeline:')) {
      return;
    }
    if (!jobs[selectedView]) {
      setSelectedView('pipeline:submit');
    }
  }, [jobs, selectedView]);

  const handleThemeChange = useCallback(
    (event: ChangeEvent<HTMLSelectElement>) => {
      setThemeMode(event.target.value as ThemeMode);
    },
    [setThemeMode]
  );

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
        latest_event: null,
        tuning: null
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

  const sortedJobs = useMemo(() => {
    return [...jobList].sort((a, b) => {
      const left = new Date(a.status.created_at).getTime();
      const right = new Date(b.status.created_at).getTime();
      return right - left;
    });
  }, [jobList]);

  const isPipelineView = typeof selectedView === 'string' && selectedView.startsWith('pipeline:');
  const activePipelineSection = useMemo(() => {
    if (!isPipelineView) {
      return null;
    }
    return PIPELINE_SECTION_MAP[selectedView as PipelineMenuView];
  }, [isPipelineView, selectedView]);

  const selectedJob = useMemo(() => {
    if (isPipelineView) {
      return undefined;
    }
    return jobList.find((job) => job.jobId === selectedView);
  }, [isPipelineView, jobList, selectedView]);

  return (
    <div className={`dashboard ${isSidebarOpen ? '' : 'dashboard--collapsed'}`}>
      <aside
        id="dashboard-sidebar"
        className={`dashboard__sidebar ${isSidebarOpen ? '' : 'dashboard__sidebar--collapsed'}`}
      >
        <div className="sidebar__brand">
          <span className="sidebar__title">ebook-tools</span>
          <span className="sidebar__subtitle">Pipeline dashboard</span>
        </div>
        <nav className="sidebar__nav" aria-label="Dashboard menu">
          <details className="sidebar__section" open>
            <summary>Pipeline</summary>
            <button
              type="button"
              className={`sidebar__link ${selectedView === 'pipeline:submit' ? 'is-active' : ''}`}
              onClick={() => setSelectedView('pipeline:submit')}
            >
              Submit pipeline job
            </button>
            <details className="sidebar__section sidebar__section--nested" open>
              <summary>Pipeline settings</summary>
              <ul className="sidebar__list sidebar__list--nested">
                {PIPELINE_SETTINGS.map((entry) => (
                  <li key={entry.key}>
                    <button
                      type="button"
                      className={`sidebar__link ${selectedView === entry.key ? 'is-active' : ''}`}
                      onClick={() => setSelectedView(entry.key)}
                    >
                      {entry.label}
                    </button>
                  </li>
                ))}
              </ul>
            </details>
          </details>
          <details className="sidebar__section" open>
            <summary>Tracked jobs</summary>
            {sortedJobs.length > 0 ? (
              <ul className="sidebar__list">
                {sortedJobs.map((job) => {
                  const statusValue = job.status?.status ?? 'pending';
                  return (
                    <li key={job.jobId}>
                      <button
                        type="button"
                        className={`sidebar__link sidebar__link--job ${
                          selectedView === job.jobId ? 'is-active' : ''
                        }`}
                        onClick={() => setSelectedView(job.jobId)}
                      >
                        <span className="sidebar__job-label">Job {job.jobId}</span>
                        <span className="job-status" data-state={statusValue}>
                          {statusValue}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="sidebar__empty">No persisted jobs yet.</p>
            )}
          </details>
        </nav>
      </aside>
      <main className="dashboard__main">
        <div className="dashboard__toolbar">
          <div className="theme-control">
            <label className="theme-control__label" htmlFor="theme-select">
              Theme
            </label>
            <select id="theme-select" value={themeMode} onChange={handleThemeChange}>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="system">System</option>
            </select>
            {themeMode === 'system' ? (
              <span className="theme-control__hint">Following {resolvedTheme} mode</span>
            ) : null}
          </div>
          <button
            type="button"
            className="sidebar-toggle"
            onClick={() => setIsSidebarOpen((previous) => !previous)}
            aria-expanded={isSidebarOpen}
            aria-controls="dashboard-sidebar"
          >
            {isSidebarOpen ? 'Hide menu' : 'Show menu'}
          </button>
        </div>
        <header className="dashboard__header">
          <h1>ebook-tools pipeline dashboard</h1>
          <p>
            Submit ebook processing jobs, monitor their current state, and observe real-time progress streamed
            directly from the FastAPI backend.
          </p>
        </header>
        {activePipelineSection ? (
          <section>
            <PipelineSubmissionForm
              onSubmit={handleSubmit}
              isSubmitting={isSubmitting}
              activeSection={activePipelineSection ?? undefined}
              externalError={activePipelineSection === 'submit' ? submitError : null}
            />
          </section>
        ) : null}
        {activePipelineSection === 'submit' && sortedJobs.length > 0 ? (
          <section>
            <h2 style={{ marginTop: 0 }}>Tracked jobs</h2>
            <p style={{ marginBottom: 0 }}>Select a job from the menu to review its detailed progress.</p>
          </section>
        ) : null}
        {sortedJobs.length === 0 ? (
          <section>
            <h2 style={{ marginTop: 0 }}>Tracked jobs</h2>
            <p style={{ marginBottom: 0 }}>No persisted jobs yet. Submit a pipeline request to get started.</p>
          </section>
        ) : null}
        {selectedJob ? (
          <section>
            <JobProgress
              jobId={selectedJob.jobId}
              status={selectedJob.status}
              latestEvent={selectedJob.latestEvent}
              onEvent={(event) => handleProgressEvent(selectedJob.jobId, event)}
              onPause={() => handlePauseJob(selectedJob.jobId)}
              onResume={() => handleResumeJob(selectedJob.jobId)}
              onCancel={() => handleCancelJob(selectedJob.jobId)}
              onDelete={() => handleDeleteJob(selectedJob.jobId)}
              onReload={() => handleReloadJob(selectedJob.jobId)}
              isReloading={selectedJob.isReloading}
              isMutating={selectedJob.isMutating}
            />
          </section>
        ) : null}
      </main>
    </div>
  );
}

export default App;
