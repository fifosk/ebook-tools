import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent } from 'react';
import type { PipelineFormSection } from './components/PipelineSubmissionForm';
import type { JobState } from './components/JobList';
import JobProgress from './components/JobProgress';
import LibraryPage from './pages/LibraryPage';
import CreateBookPage from './pages/CreateBookPage';
import PlayerView, { type PlayerContext } from './pages/PlayerView';
import NewImmersiveBookPage from './pages/NewImmersiveBookPage';
import Sidebar from './components/Sidebar';
import {
  LibraryItem,
  PipelineRequestPayload,
  PipelineStatusResponse,
  ProgressEventPayload
} from './api/dtos';
import {
  cancelJob,
  deleteJob,
  fetchJobs,
  fetchPipelineStatus,
  moveJobToLibrary,
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
import { resolveMediaCompletion } from './utils/mediaFormatters';
import { buildLibraryBookMetadata } from './utils/libraryMetadata';

interface JobRegistryEntry {
  status: PipelineStatusResponse;
  latestEvent?: ProgressEventPayload;
}

type JobAction = 'pause' | 'resume' | 'cancel' | 'delete';

export type PipelineMenuView =
  | 'pipeline:source'
  | 'pipeline:language'
  | 'pipeline:output'
  | 'pipeline:performance'
  | 'pipeline:submit';

const ADMIN_USER_MANAGEMENT_VIEW = 'admin:users' as const;

const JOB_PROGRESS_VIEW = 'job:progress' as const;
const JOB_MEDIA_VIEW = 'job:media' as const;
const LIBRARY_VIEW = 'library:list' as const;
const CREATE_BOOK_VIEW = 'books:create' as const;

export type SelectedView =
  | PipelineMenuView
  | typeof ADMIN_USER_MANAGEMENT_VIEW
  | typeof JOB_PROGRESS_VIEW
  | typeof JOB_MEDIA_VIEW
  | typeof LIBRARY_VIEW
  | typeof CREATE_BOOK_VIEW;

const PIPELINE_SECTION_MAP: Record<PipelineMenuView, PipelineFormSection> = {
  'pipeline:source': 'source',
  'pipeline:language': 'language',
  'pipeline:output': 'output',
  'pipeline:performance': 'performance',
  'pipeline:submit': 'submit'
};

const PIPELINE_SECTION_TO_VIEW: Record<PipelineFormSection, PipelineMenuView> = {
  source: 'pipeline:source',
  language: 'pipeline:language',
  output: 'pipeline:output',
  performance: 'pipeline:performance',
  submit: 'pipeline:submit'
};

export function App() {
  const { session, isLoading: isAuthLoading, logoutReason, login, logout, updatePassword } = useAuth();
  const [jobs, setJobs] = useState<Record<string, JobRegistryEntry>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [reloadingJobs, setReloadingJobs] = useState<Record<string, boolean>>({});
  const [mutatingJobs, setMutatingJobs] = useState<Record<string, boolean>>({});
  const [selectedView, setSelectedView] = useState<SelectedView>('pipeline:source');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [playerContext, setPlayerContext] = useState<PlayerContext | null>(null);
  const [pendingInputFile, setPendingInputFile] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isImmersiveMode, setIsImmersiveMode] = useState(false);
  const [isAccountExpanded, setIsAccountExpanded] = useState(false);
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
    setShowChangePassword((previous) => {
      const next = !previous;
      if (next) {
        setIsAccountExpanded(true);
      }
      return next;
    });
  }, [setIsAccountExpanded]);

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
          const resolvedCompletion = resolveMediaCompletion(status);
          const normalizedStatus =
            resolvedCompletion !== null
              ? { ...status, media_completed: resolvedCompletion }
              : status;
          next[status.job_id] = {
            status: normalizedStatus,
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
      setActiveJobId(null);
      setPlayerContext(null);
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

  const activeJobMetadata = useMemo(() => {
    if (!activeJobId) {
      return null;
    }
    const jobEntry = jobs[activeJobId];
    const metadata = jobEntry?.status?.result?.book_metadata;
    return metadata && typeof metadata === 'object' ? metadata : null;
  }, [activeJobId, jobs]);

  const playerJobMetadata = useMemo(() => {
    if (playerContext?.type !== 'job') {
      return null;
    }
    if (playerContext.jobId === activeJobId) {
      return activeJobMetadata;
    }
    const entry = jobs[playerContext.jobId];
    const metadata = entry?.status?.result?.book_metadata;
    return metadata && typeof metadata === 'object' ? metadata : null;
  }, [activeJobId, activeJobMetadata, jobs, playerContext]);

  useEffect(() => {
    if (typeof selectedView === 'string' && selectedView.startsWith('pipeline:')) {
      return;
    }
    if (selectedView === ADMIN_USER_MANAGEMENT_VIEW) {
      return;
    }
    if (selectedView === JOB_PROGRESS_VIEW) {
      if (!activeJobId || !jobs[activeJobId]) {
        setActiveJobId(null);
        setSelectedView('pipeline:submit');
      }
      return;
    }
    if (selectedView === JOB_MEDIA_VIEW) {
      if (!playerContext) {
        setSelectedView('pipeline:submit');
        return;
      }
      if (playerContext.type === 'job' && !jobs[playerContext.jobId]) {
        setPlayerContext(null);
        setSelectedView('pipeline:submit');
      }
    }
  }, [activeJobId, jobs, playerContext, selectedView]);

  useEffect(() => {
    if (selectedView === JOB_PROGRESS_VIEW && !activeJobId) {
      setSelectedView('pipeline:submit');
      return;
    }
    if (selectedView === JOB_MEDIA_VIEW && playerContext?.type === 'job' && !activeJobId) {
      setPlayerContext(null);
      setSelectedView('pipeline:submit');
    }
  }, [activeJobId, playerContext, selectedView]);

  useEffect(() => {
    if (selectedView !== JOB_MEDIA_VIEW) {
      return;
    }
    if (playerContext?.type !== 'job') {
      return;
    }
    if (activeJobId && playerContext.jobId !== activeJobId) {
      setPlayerContext({ type: 'job', jobId: activeJobId });
    }
  }, [activeJobId, playerContext, selectedView]);

  useEffect(() => {
    if (selectedView !== JOB_MEDIA_VIEW) {
      setIsImmersiveMode(false);
    }
  }, [selectedView]);

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
      setPendingInputFile(null);
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

      const nextStatus = current.status ? { ...current.status } : undefined;
      const metadata = event.metadata;

      if (nextStatus && metadata && typeof metadata === 'object') {
        const generated = (metadata as Record<string, unknown>).generated_files;
        if (generated && typeof generated === 'object') {
          nextStatus.generated_files = generated as Record<string, unknown>;
        }

        const mediaCompletedMeta = (metadata as Record<string, unknown>).media_completed;
        if (typeof mediaCompletedMeta === 'boolean') {
          nextStatus.media_completed = mediaCompletedMeta;
        }
      }

      if (nextStatus) {
        const resolvedCompletion = resolveMediaCompletion(nextStatus);
        if (resolvedCompletion !== null) {
          nextStatus.media_completed = resolvedCompletion;
        }
      }

      return {
        ...previous,
        [jobId]: {
          ...current,
          status: nextStatus ?? current.status,
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
      const resolvedCompletion = resolveMediaCompletion(status);
      const normalizedStatus =
        resolvedCompletion !== null ? { ...status, media_completed: resolvedCompletion } : status;
      setJobs((previous) => {
        const current = previous[jobId];
        if (!current) {
          return previous;
        }
        return {
          ...previous,
          [jobId]: {
            ...current,
            status: normalizedStatus,
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
          const resolvedCompletion = resolveMediaCompletion(response);
          const normalizedResponse =
            resolvedCompletion !== null ? { ...response, media_completed: resolvedCompletion } : response;
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
                  status: normalizedResponse!,
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

  const handleVideoPlaybackStateChange = useCallback((isPlaying: boolean) => {
    setIsImmersiveMode((previous) => {
      if (previous === isPlaying) {
        return previous;
      }
      return isPlaying;
    });
  }, []);

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

  const handleMoveJobToLibrary = useCallback(
    async (jobId: string) => {
      const entry = jobs[jobId];
      if (!entry?.status) {
        window.alert('Job metadata is unavailable; refresh and try again.');
        return;
      }

      const statusValue = entry.status.status;
      const mediaCompleted = resolveMediaCompletion(entry.status);
      const isCompleted = statusValue === 'completed';
      const isPausedReady = statusValue === 'paused' && mediaCompleted === true;

      if (!isCompleted && !isPausedReady) {
        window.alert('Only completed or fully paused jobs with finalized media can be moved to the library.');
        return;
      }

      const confirmed = window.confirm(
        `Move job ${jobId} to the library? Its working files will be archived under the configured library root.`
      );
      if (!confirmed) {
        return;
      }

      const statusOverride: 'finished' | 'paused' = isCompleted ? 'finished' : 'paused';
      setMutatingJobs((previous) => ({ ...previous, [jobId]: true }));
      try {
        await moveJobToLibrary(jobId, statusOverride);
        window.alert(`Job ${jobId} has been moved into the library.`);
      } catch (error) {
        const message =
          error instanceof Error ? error.message : 'Unable to move the job into the library.';
        window.alert(message);
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
    [jobs, refreshJobs]
  );

  const handleOpenPlayerForJob = useCallback(() => {
    if (!activeJobId) {
      return;
    }
    setPlayerContext({ type: 'job', jobId: activeJobId });
    setSelectedView(JOB_MEDIA_VIEW);
    setIsImmersiveMode(false);
  }, [activeJobId]);

  const handlePlayLibraryItem = useCallback(
    (entry: LibraryItem | string) => {
      if (typeof entry === 'string') {
        setPlayerContext({
          type: 'library',
          jobId: entry,
          bookMetadata: null
        });
      } else {
        const metadata = buildLibraryBookMetadata(entry);
        setPlayerContext({
          type: 'library',
          jobId: entry.jobId,
          bookMetadata: metadata
        });
      }
      setActiveJobId(null);
      setSelectedView(JOB_MEDIA_VIEW);
      setIsImmersiveMode(false);
    },
    []
  );

  const handleSelectSidebarJob = useCallback(
    (jobId: string) => {
      setActiveJobId(jobId);
      setSelectedView(JOB_PROGRESS_VIEW);
    },
    [setActiveJobId, setSelectedView]
  );

  const handleImmersiveSectionChange = useCallback(
    (section: PipelineFormSection) => {
      const nextView = PIPELINE_SECTION_TO_VIEW[section];
      setSelectedView(nextView);
    },
    [setSelectedView]
  );

  const handleSidebarSelectView = useCallback(
    (view: SelectedView) => {
      setSelectedView(view);
    },
    [setSelectedView]
  );

  const jobList: JobState[] = useMemo(() => {
    return Object.entries(jobs).map(([jobId, entry]) => {
      const owner = typeof entry.status?.user_id === 'string' ? entry.status.user_id : null;
      const canManage = Boolean(
        isAdmin || !owner || (sessionUsername && owner === sessionUsername)
      );
      const resolvedStatus = entry.status
        ? {
            ...entry.status,
            media_completed:
              resolveMediaCompletion(entry.status) ?? entry.status.media_completed ?? null
          }
        : entry.status;
      return {
        jobId,
        status: resolvedStatus,
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
  const isLibraryView = selectedView === LIBRARY_VIEW;
  const isCreateBookView = selectedView === CREATE_BOOK_VIEW;
  const isNewImmersiveBookView = isPipelineView;
  const activePipelineSection = useMemo(() => {
    if (!isPipelineView) {
      return null;
    }
    return PIPELINE_SECTION_MAP[selectedView as PipelineMenuView];
  }, [isPipelineView, selectedView]);

  const selectedJob = useMemo(() => {
    if (!activeJobId) {
      return undefined;
    }
    const job = jobList.find((entry) => entry.jobId === activeJobId);
    if (job && !job.canManage) {
      return undefined;
    }
    return job;
  }, [activeJobId, jobList]);

  const lastFetchedJobRef = useRef<string | null>(null);
  const lastFetchedAtRef = useRef<number>(0);

  useEffect(() => {
    if (!activeJobId) {
      return;
    }
    if (selectedView !== JOB_MEDIA_VIEW && selectedView !== JOB_PROGRESS_VIEW) {
      return;
    }

    const metadataEmpty = !activeJobMetadata || Object.keys(activeJobMetadata).length === 0;
    const jobChanged = lastFetchedJobRef.current !== activeJobId;
    const now = Date.now();
    const elapsed = now - lastFetchedAtRef.current;
    if (!jobChanged && (!metadataEmpty || elapsed < 5000)) {
      return;
    }

    let cancelled = false;

    const fetchSelectedJobStatus = async () => {
      try {
        const status = await fetchPipelineStatus(activeJobId);
        if (cancelled) {
          return;
        }
        setJobs((previous) => {
          const current = previous[activeJobId];
          if (!current) {
            return previous;
          }
          return {
            ...previous,
            [activeJobId]: {
              ...current,
              status,
              latestEvent: status.latest_event ?? current.latestEvent
            }
          };
        });
      } catch (error) {
        if (!cancelled) {
          console.warn('Unable to refresh job metadata for job detail view', activeJobId, error);
        }
      } finally {
        if (!cancelled) {
          lastFetchedJobRef.current = activeJobId;
          lastFetchedAtRef.current = Date.now();
        }
      }
    };

    void fetchSelectedJobStatus();

    return () => {
      cancelled = true;
    };
  }, [activeJobId, selectedView, activeJobMetadata]);

  useEffect(() => {
    if (!selectedJob) {
      setIsImmersiveMode(false);
    }
  }, [selectedJob]);

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

  const dashboardClassNames = ['dashboard'];
  if (!isSidebarOpen) {
    dashboardClassNames.push('dashboard--collapsed');
  }
  if (isImmersiveMode) {
    dashboardClassNames.push('dashboard--immersive');
  }

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
          <h1>Language tools</h1>
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
    <div className={dashboardClassNames.join(' ')}>
      <aside
        id="dashboard-sidebar"
        className={`dashboard__sidebar ${isSidebarOpen ? '' : 'dashboard__sidebar--collapsed'}`}
      >
        <div className="sidebar__header">
          <div className="sidebar__brand">
            <span className="sidebar__logo-mark" aria-hidden="true">
              LT
            </span>
            <span className="sidebar__title">Language tools</span>
            <span className="sidebar__subtitle">Language tools</span>
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
          <div
            className={`session-info ${
              isAccountExpanded ? 'session-info--expanded' : 'session-info--collapsed'
            }`}
          >
            <button
              type="button"
              className="session-info__summary"
              onClick={() => setIsAccountExpanded((previous) => !previous)}
              aria-expanded={isAccountExpanded}
              aria-controls="session-info-content"
            >
              <span className="session-info__summary-text">
                <span className="session-info__user">
                  Signed in as <strong>{displayName.label}</strong>
                  {displayName.showUsernameTag ? (
                    <span className="session-info__username">({sessionUser?.username})</span>
                  ) : null}
                </span>
              </span>
              <span className="session-info__summary-icon" aria-hidden="true">
                ▾
              </span>
            </button>
            <div
              id="session-info-content"
              className="session-info__content"
              hidden={!isAccountExpanded}
            >
              <div className="session-info__details">
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
                    <option value="magenta">Magenta</option>
                    <option value="system">System</option>
                  </select>
                  {themeMode === 'system' ? (
                    <span className="theme-control__hint">Following {resolvedTheme} mode</span>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        </div>
        <Sidebar
          selectedView={selectedView}
          onSelectView={handleSidebarSelectView}
          sidebarJobs={sidebarJobs}
          activeJobId={activeJobId}
          onSelectJob={handleSelectSidebarJob}
          onOpenPlayer={handleOpenPlayerForJob}
          isAdmin={isAdmin}
          createBookView={CREATE_BOOK_VIEW}
          libraryView={LIBRARY_VIEW}
          jobMediaView={JOB_MEDIA_VIEW}
          adminView={ADMIN_USER_MANAGEMENT_VIEW}
        />
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
          ) : isLibraryView ? (
            <>
              <h1>Library</h1>
              <p>Browse archived jobs, review metadata, and manage stored media across completed runs.</p>
            </>
          ) : isCreateBookView ? (
            <>
              <h1>Create book</h1>
              <p>Generate a seed EPUB with the LLM, then fine-tune the pipeline settings before submitting.</p>
            </>
          ) : isNewImmersiveBookView ? (
            <>
              <h1>New immersive book</h1>
            </>
          ) : (
            <>
              <h1>Language tools</h1>
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
          ) : isLibraryView ? (
            <LibraryPage onPlay={handlePlayLibraryItem} />
          ) : isCreateBookView ? (
            <section>
              <CreateBookPage
                onCreated={(creation) => {
                  setIsImmersiveMode(false);
                  setActiveJobId(null);
                  const nextInput =
                    creation.input_file ??
                    (creation.epub_path && creation.epub_path.trim() ? creation.epub_path : null);
                  if (nextInput) {
                    setPendingInputFile(nextInput);
                  }
                  setSelectedView('pipeline:source');
                }}
              />
            </section>
          ) : (
            <>
              {isNewImmersiveBookView ? (
                <section>
                  <NewImmersiveBookPage
                    activeSection={activePipelineSection ?? 'source'}
                    onSectionChange={handleImmersiveSectionChange}
                    onSubmit={handleSubmit}
                    isSubmitting={isSubmitting}
                    prefillInputFile={pendingInputFile}
                    submitError={activePipelineSection === 'submit' ? submitError : null}
                  />
                </section>
              ) : null}
              {selectedView === JOB_PROGRESS_VIEW ? (
                <section className="job-progress-section">
                  {selectedJob ? (
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
                      onMoveToLibrary={() => handleMoveJobToLibrary(selectedJob.jobId)}
                      isReloading={selectedJob.isReloading}
                      isMutating={selectedJob.isMutating}
                      canManage={selectedJob.canManage}
                    />
                  ) : (
                    <div className="job-card job-card--placeholder" aria-live="polite">
                      <h3 style={{ marginTop: 0 }}>No job selected</h3>
                      <p>Select an active job to monitor its pipeline progress and live status updates.</p>
                    </div>
                  )}
                </section>
              ) : null}
              {selectedView === JOB_MEDIA_VIEW ? (
                <section className="job-media-section">
                  <PlayerView
                    context={playerContext}
                    jobBookMetadata={playerJobMetadata}
                    onVideoPlaybackStateChange={handleVideoPlaybackStateChange}
                    onOpenLibraryItem={handlePlayLibraryItem}
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
