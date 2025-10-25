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
import { useAuth } from './components/AuthProvider';
import LoginForm from './components/LoginForm';
import ChangePasswordForm from './components/ChangePasswordForm';
import UserManagementPanel from './components/admin/UserManagementPanel';

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

const ADMIN_USER_MANAGEMENT_VIEW = 'admin:users' as const;

type SelectedView = PipelineMenuView | typeof ADMIN_USER_MANAGEMENT_VIEW | string;

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
  const { session, isLoading: isAuthLoading, logoutReason, login, logout, updatePassword } = useAuth();
  const [jobs, setJobs] = useState<Record<string, JobRegistryEntry>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [reloadingJobs, setReloadingJobs] = useState<Record<string, boolean>>({});
  const [mutatingJobs, setMutatingJobs] = useState<Record<string, boolean>>({});
  const [selectedView, setSelectedView] = useState<SelectedView>('pipeline:source');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);
  const { mode: themeMode, resolvedTheme, setMode: setThemeMode } = useTheme();
  const isAuthenticated = Boolean(session);
  const sessionUser = session?.user ?? null;
  const sessionUsername = sessionUser?.username ?? null;
  const isAdmin = sessionUser?.role === 'admin';

  const handleLogin = useCallback(
    async (username: string, password: string) => {
      setIsLoggingIn(true);
      setAuthError(null);
      try {
        await login(username, password);
      } catch (error) {
        setAuthError(error instanceof Error ? error.message : 'Unable to sign in.');
      } finally {
        setIsLoggingIn(false);
      }
    },
    [login]
  );

  const handleLogout = useCallback(async () => {
    setShowChangePassword(false);
    setPasswordError(null);
    setPasswordMessage(null);
    await logout();
  }, [logout]);

  const handlePasswordChange = useCallback(
    async (currentPassword: string, newPassword: string) => {
      setPasswordError(null);
      setPasswordMessage(null);
      setIsUpdatingPassword(true);
      try {
        await updatePassword(currentPassword, newPassword);
        setPasswordMessage('Password updated successfully.');
        setShowChangePassword(false);
      } catch (error) {
        setPasswordError(
          error instanceof Error ? error.message : 'Unable to update password. Please try again.'
        );
      } finally {
        setIsUpdatingPassword(false);
      }
    },
    [updatePassword]
  );

  const toggleChangePassword = useCallback(() => {
    setPasswordError(null);
    setPasswordMessage(null);
    setShowChangePassword((previous) => !previous);
  }, []);

  const handlePasswordCancel = useCallback(() => {
    setShowChangePassword(false);
    setPasswordError(null);
  }, []);

  const refreshJobs = useCallback(async () => {
    if (!session) {
      return;
    }
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
  }, [session]);

  useEffect(() => {
    if (!session) {
      setJobs({});
      setReloadingJobs({});
      setMutatingJobs({});
      setSelectedView('pipeline:source');
      return;
    }

    refreshJobs();
    const interval = window.setInterval(() => {
      void refreshJobs();
    }, 5000);
    return () => {
      window.clearInterval(interval);
    };
  }, [refreshJobs, session]);

  useEffect(() => {
    if (typeof selectedView === 'string' && selectedView.startsWith('pipeline:')) {
      return;
    }
    if (selectedView === ADMIN_USER_MANAGEMENT_VIEW) {
      return;
    }
    if (!jobs[selectedView]) {
      setSelectedView('pipeline:submit');
    }
  }, [jobs, selectedView]);

  useEffect(() => {
    if (session) {
      setAuthError(null);
    }
  }, [session]);

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
      const entry = jobs[jobId];
      const owner = typeof entry?.status?.user_id === 'string' ? entry.status.user_id : null;
      const canManage = Boolean(
        isAdmin || !owner || (sessionUsername && owner === sessionUsername)
      );
      if (!entry || !canManage) {
        console.warn(`Skipping ${action} for unauthorized job`, jobId);
        return;
      }
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
    [isAdmin, jobs, refreshJobs, sessionUsername]
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
    return Object.entries(jobs).map(([jobId, entry]) => {
      const owner = typeof entry.status?.user_id === 'string' ? entry.status.user_id : null;
      const canManage = Boolean(
        isAdmin || !owner || (sessionUsername && owner === sessionUsername)
      );
      return {
        jobId,
        status: entry.status,
        latestEvent: entry.latestEvent,
        isReloading: Boolean(reloadingJobs[jobId]),
        isMutating: Boolean(mutatingJobs[jobId]),
        canManage
      };
    });
  }, [isAdmin, jobs, mutatingJobs, reloadingJobs, sessionUsername]);

  const sortedJobs = useMemo(() => {
    return [...jobList].sort((a, b) => {
      const left = new Date(a.status.created_at).getTime();
      const right = new Date(b.status.created_at).getTime();
      return right - left;
    });
  }, [jobList]);

  const sidebarJobs = useMemo(() => {
    return sortedJobs.filter((job) => job.canManage);
  }, [sortedJobs]);

  const isPipelineView = typeof selectedView === 'string' && selectedView.startsWith('pipeline:');
  const isAdminView = selectedView === ADMIN_USER_MANAGEMENT_VIEW;
  const activePipelineSection = useMemo(() => {
    if (!isPipelineView) {
      return null;
    }
    return PIPELINE_SECTION_MAP[selectedView as PipelineMenuView];
  }, [isPipelineView, selectedView]);

  const selectedJob = useMemo(() => {
    if (isPipelineView || isAdminView) {
      return undefined;
    }
    const job = jobList.find((entry) => entry.jobId === selectedView);
    if (job && !job.canManage) {
      return undefined;
    }
    return job;
  }, [isAdminView, isPipelineView, jobList, selectedView]);

  const displayName = useMemo(() => {
    if (!sessionUser) {
      return { label: '', showUsernameTag: false };
    }
    const parts = [sessionUser.first_name, sessionUser.last_name]
      .map((value) => (typeof value === 'string' ? value.trim() : ''))
      .filter((value) => Boolean(value));
    const fullName = parts.length > 0 ? parts.join(' ') : null;
    const label = fullName ?? sessionUser.username;
    const showUsernameTag = Boolean(fullName && sessionUser.username && fullName !== sessionUser.username);
    return { label, showUsernameTag };
  }, [sessionUser]);

  const sessionEmail = useMemo(() => {
    if (!sessionUser?.email) {
      return null;
    }
    const trimmed = sessionUser.email.trim();
    return trimmed || null;
  }, [sessionUser]);

  const lastLoginLabel = useMemo(() => {
    if (!sessionUser?.last_login) {
      return null;
    }
    try {
      return new Date(sessionUser.last_login).toLocaleString();
    } catch (error) {
      console.warn('Unable to parse last login timestamp', error);
      return sessionUser.last_login;
    }
  }, [sessionUser]);

  if (isAuthLoading) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <p>Checking session…</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <h1>ebook-tools pipeline dashboard</h1>
          <p>Sign in to submit jobs and manage pipeline activity.</p>
          <LoginForm
            onSubmit={handleLogin}
            isSubmitting={isLoggingIn}
            error={authError}
            notice={logoutReason}
          />
        </div>
      </div>
    );
  }

  return (
    <div className={`dashboard ${isSidebarOpen ? '' : 'dashboard--collapsed'}`}>
      <aside
        id="dashboard-sidebar"
        className={`dashboard__sidebar ${isSidebarOpen ? '' : 'dashboard__sidebar--collapsed'}`}
      >
        <div className="sidebar__header">
          <div className="sidebar__brand">
            <span className="sidebar__logo-mark" aria-hidden="true">
              et
            </span>
            <span className="sidebar__title">ebook-tools</span>
            <span className="sidebar__subtitle">Pipeline dashboard</span>
          </div>
          <button
            type="button"
            className="sidebar__collapse-toggle"
            onClick={() => setIsSidebarOpen((previous) => !previous)}
            aria-expanded={isSidebarOpen}
            aria-controls="dashboard-sidebar"
          >
            <span className="visually-hidden">
              {isSidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
            </span>
            <span className="sidebar__collapse-icon" aria-hidden="true">
              {isSidebarOpen ? '‹' : '›'}
            </span>
          </button>
        </div>
        <div className="sidebar__account">
          <div className="session-info">
            <div className="session-info__details">
              <span className="session-info__user">
                Signed in as <strong>{displayName.label}</strong>
                {displayName.showUsernameTag ? (
                  <span className="session-info__username">({sessionUser?.username})</span>
                ) : null}
              </span>
              {sessionEmail ? <span className="session-info__email">{sessionEmail}</span> : null}
              <span className="session-info__meta">
                <span className="session-info__role">Role: {sessionUser?.role}</span>
                {lastLoginLabel ? (
                  <span className="session-info__last-login">Last login: {lastLoginLabel}</span>
                ) : null}
              </span>
            </div>
            <div className="session-info__actions">
              <button
                type="button"
                className="session-info__button"
                onClick={toggleChangePassword}
              >
                {showChangePassword ? 'Hide password form' : 'Change password'}
              </button>
              <button
                type="button"
                className="session-info__button session-info__button--logout"
                onClick={() => {
                  void handleLogout();
                }}
              >
                Log out
              </button>
            </div>
            <div className="session-info__preferences">
              <div className="theme-control theme-control--sidebar">
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
            </div>
          </div>
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
            {sidebarJobs.length > 0 ? (
              <ul className="sidebar__list">
                {sidebarJobs.map((job) => {
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
              <p className="sidebar__empty">No accessible jobs yet.</p>
            )}
          </details>
          {isAdmin ? (
            <details className="sidebar__section" open>
              <summary>Administration</summary>
              <button
                type="button"
                className={`sidebar__link ${
                  selectedView === ADMIN_USER_MANAGEMENT_VIEW ? 'is-active' : ''
                }`}
                onClick={() => setSelectedView(ADMIN_USER_MANAGEMENT_VIEW)}
              >
                User management
              </button>
            </details>
          ) : null}
        </nav>
      </aside>
      <div className="dashboard__content">
        <main className="dashboard__main">
          {passwordMessage ? (
            <div className="password-message" role="status">
              {passwordMessage}
            </div>
          ) : null}
          {showChangePassword ? (
            <section className="account-panel">
              <h2>Change password</h2>
              <ChangePasswordForm
                onSubmit={handlePasswordChange}
                onCancel={handlePasswordCancel}
                isSubmitting={isUpdatingPassword}
                error={passwordError}
              />
            </section>
          ) : null}
          <header className="dashboard__header">
            {isAdminView ? (
              <>
                <h1>User management</h1>
                <p>Administer dashboard accounts, reset passwords, and control access for operators.</p>
              </>
            ) : (
              <>
                <h1>ebook-tools pipeline dashboard</h1>
                <p>
                  Submit ebook processing jobs, monitor their current state, and observe real-time progress streamed
                  directly from the FastAPI backend.
                </p>
              </>
            )}
          </header>
          {isAdminView ? (
            <section>
              <UserManagementPanel currentUser={sessionUser?.username ?? ''} />
            </section>
          ) : (
            <>
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
              {activePipelineSection === 'submit' && sidebarJobs.length > 0 ? (
                <section>
                  <h2 style={{ marginTop: 0 }}>Tracked jobs</h2>
                  <p style={{ marginBottom: 0 }}>Select a job from the menu to review its detailed progress.</p>
                </section>
              ) : null}
              {sidebarJobs.length === 0 ? (
                <section>
                  <h2 style={{ marginTop: 0 }}>Tracked jobs</h2>
                  <p style={{ marginBottom: 0 }}>No accessible jobs yet. Submit a pipeline request to get started.</p>
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
                    canManage={selectedJob.canManage}
                  />
                </section>
              ) : null}
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
