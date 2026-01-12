import { useCallback, useEffect, useMemo, useRef, useState, useId } from 'react';
import type { BookNarrationFormSection } from './components/book-narration/BookNarrationForm';
import type { JobState } from './components/JobList';
import JobProgress from './components/JobProgress';
import LibraryPage from './pages/LibraryPage';
import CreateBookPage from './pages/CreateBookPage';
import PlayerView, { type PlayerContext } from './pages/PlayerView';
import NewImmersiveBookPage from './pages/NewImmersiveBookPage';
import SubtitleToolPage from './pages/SubtitleToolPage';
import YoutubeVideoPage from './pages/YoutubeVideoPage';
import VideoDubbingPage from './pages/VideoDubbingPage';
import DualTrackDemoRoute from './routes/DualTrackDemoRoute';
import Sidebar from './components/Sidebar';
import MyLinguistAssistant from './components/MyLinguistAssistant';
import MyPainterAssistant from './components/MyPainterAssistant';
import {
  AccessPolicyUpdatePayload,
  LibraryItem,
  PipelineRequestPayload,
  JobParameterSnapshot,
  PipelineStatusResponse,
  ProgressEventPayload,
  OAuthLoginRequestPayload
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
  restartJob,
  submitPipeline,
  updateJobAccess
} from './api/client';
import { useTheme } from './components/ThemeProvider';
import type { ThemeMode } from './components/ThemeProvider';
import { useAuth } from './components/AuthProvider';
import LoginForm from './components/LoginForm';
import ChangePasswordForm from './components/ChangePasswordForm';
import UserManagementPanel from './components/admin/UserManagementPanel';
import ReadingBedsPanel from './components/admin/ReadingBedsPanel';
import { resolveMediaCompletion } from './utils/mediaFormatters';
import { buildLibraryBookMetadata } from './utils/libraryMetadata';
import { canAccessPolicy, normalizeRole } from './utils/accessControl';
import { resolveProgressStage } from './utils/progressEvents';
import type { LibraryOpenInput, MediaSelectionRequest } from './types/player';
import { isLibraryOpenRequest } from './types/player';

interface JobRegistryEntry {
  status: PipelineStatusResponse;
  latestEvent?: ProgressEventPayload;
  latestTranslationEvent?: ProgressEventPayload;
  latestMediaEvent?: ProgressEventPayload;
}

type JobAction = 'pause' | 'resume' | 'cancel' | 'delete' | 'restart';

export type PipelineMenuView =
  | 'pipeline:source'
  | 'pipeline:metadata'
  | 'pipeline:language'
  | 'pipeline:output'
  | 'pipeline:images'
  | 'pipeline:performance'
  | 'pipeline:submit';

const ADMIN_USER_MANAGEMENT_VIEW = 'admin:users' as const;
const ADMIN_READING_BEDS_VIEW = 'admin:reading-beds' as const;

const JOB_PROGRESS_VIEW = 'job:progress' as const;
const JOB_MEDIA_VIEW = 'job:media' as const;
const LIBRARY_VIEW = 'library:list' as const;
const CREATE_BOOK_VIEW = 'books:create' as const;
const SUBTITLES_VIEW = 'subtitles:home' as const;
const YOUTUBE_SUBTITLES_VIEW = 'subtitles:youtube' as const;
const YOUTUBE_DUB_VIEW = 'subtitles:youtube-dub' as const;

export type SelectedView =
  | PipelineMenuView
  | typeof ADMIN_USER_MANAGEMENT_VIEW
  | typeof ADMIN_READING_BEDS_VIEW
  | typeof JOB_PROGRESS_VIEW
  | typeof JOB_MEDIA_VIEW
  | typeof LIBRARY_VIEW
  | typeof CREATE_BOOK_VIEW
  | typeof SUBTITLES_VIEW
  | typeof YOUTUBE_SUBTITLES_VIEW
  | typeof YOUTUBE_DUB_VIEW;

const BOOK_NARRATION_SECTION_MAP: Record<PipelineMenuView, BookNarrationFormSection> = {
  'pipeline:source': 'source',
  'pipeline:metadata': 'metadata',
  'pipeline:language': 'language',
  'pipeline:output': 'output',
  'pipeline:images': 'images',
  'pipeline:performance': 'performance',
  'pipeline:submit': 'submit'
};

const BOOK_NARRATION_SECTION_TO_VIEW: Record<BookNarrationFormSection, PipelineMenuView> = {
  source: 'pipeline:source',
  metadata: 'pipeline:metadata',
  language: 'pipeline:language',
  output: 'pipeline:output',
  images: 'pipeline:images',
  performance: 'pipeline:performance',
  submit: 'pipeline:submit'
};

const JOB_CREATION_VIEWS = new Set<SelectedView>([
  CREATE_BOOK_VIEW,
  SUBTITLES_VIEW,
  YOUTUBE_SUBTITLES_VIEW,
  YOUTUBE_DUB_VIEW
]);

const mergeGeneratedFiles = (
  current: unknown,
  incoming: unknown,
): Record<string, unknown> | null => {
  if (!incoming || typeof incoming !== 'object') {
    return current && typeof current === 'object' ? (current as Record<string, unknown>) : null;
  }
  const incomingRecord = incoming as Record<string, unknown>;
  if (!current || typeof current !== 'object') {
    return incomingRecord;
  }
  const currentRecord = current as Record<string, unknown>;
  const merged: Record<string, unknown> = {
    ...currentRecord,
    ...incomingRecord
  };
  const stickyKeys = ['translation_batch_stats', 'translation_fallback', 'tts_fallback'];
  stickyKeys.forEach((key) => {
    if (!(key in incomingRecord) && key in currentRecord) {
      merged[key] = currentRecord[key];
    }
  });
  return merged;
};

const isJobCreationView = (view: SelectedView): boolean => {
  if (typeof view === 'string' && view.startsWith('pipeline:')) {
    return true;
  }
  return JOB_CREATION_VIEWS.has(view);
};

export function App() {
  const isDualTrackDemo =
    typeof window !== 'undefined' && window.location.pathname.startsWith('/demo/dual-track');

  if (isDualTrackDemo) {
    return <DualTrackDemoRoute />;
  }

  const {
    session,
    isLoading: isAuthLoading,
    logoutReason,
    login,
    loginWithOAuth,
    logout,
    updatePassword
  } = useAuth();
  const [jobs, setJobs] = useState<Record<string, JobRegistryEntry>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [reloadingJobs, setReloadingJobs] = useState<Record<string, boolean>>({});
  const [mutatingJobs, setMutatingJobs] = useState<Record<string, boolean>>({});
  const [selectedView, setSelectedView] = useState<SelectedView>('pipeline:source');
  const [subtitleRefreshKey, setSubtitleRefreshKey] = useState<number>(0);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [playerContext, setPlayerContext] = useState<PlayerContext | null>(null);
  const [playerSelection, setPlayerSelection] = useState<MediaSelectionRequest | null>(null);
  const [libraryFocusRequest, setLibraryFocusRequest] = useState<{
    jobId: string;
    itemType: 'book' | 'video' | 'narrated_subtitle';
    token: number;
  } | null>(null);
  const [pendingInputFile, setPendingInputFile] = useState<string | null>(null);
  const [copiedJobParameters, setCopiedJobParameters] = useState<JobParameterSnapshot | null>(null);
  const [subtitlePrefillParameters, setSubtitlePrefillParameters] = useState<JobParameterSnapshot | null>(null);
  const [youtubeDubPrefillParameters, setYoutubeDubPrefillParameters] = useState<JobParameterSnapshot | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isImmersiveMode, setIsImmersiveMode] = useState(false);
  const [isPlayerFullscreen, setIsPlayerFullscreen] = useState(false);
  const [isAccountExpanded, setIsAccountExpanded] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);
  const { mode: themeMode, resolvedTheme, setMode: setThemeMode } = useTheme();
  const pipelineJobTypes = useMemo(() => new Set(['pipeline', 'book']), []);
  const recentPipelineJobs = useMemo(() => {
    return Object.values(jobs)
      .map((entry) => entry.status)
      .filter((status) => pipelineJobTypes.has(status.job_type));
  }, [jobs, pipelineJobTypes]);
  const isAuthenticated = Boolean(session);
  const sessionUser = session?.user ?? null;
  const sessionUsername = sessionUser?.username ?? null;
  const normalizedRole = normalizeRole(sessionUser?.role ?? null);
  const isAdmin = normalizedRole === 'admin';
  const canScheduleJobs = normalizedRole === 'admin' || normalizedRole === 'editor';

  useEffect(() => {
    if (!sessionUser) {
      return;
    }
    if (!canScheduleJobs && isJobCreationView(selectedView)) {
      setSelectedView(LIBRARY_VIEW);
    }
    if (
      !isAdmin &&
      (selectedView === ADMIN_USER_MANAGEMENT_VIEW || selectedView === ADMIN_READING_BEDS_VIEW)
    ) {
      setSelectedView(LIBRARY_VIEW);
    }
  }, [canScheduleJobs, isAdmin, selectedView, sessionUser]);

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

  const handleOAuthLogin = useCallback(
    async (payload: OAuthLoginRequestPayload) => {
      setIsLoggingIn(true);
      setAuthError(null);
      try {
        await loginWithOAuth(payload);
      } catch (error) {
        setAuthError(error instanceof Error ? error.message : 'Unable to sign in.');
      } finally {
        setIsLoggingIn(false);
      }
    },
    [loginWithOAuth]
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
          const statusStage = resolveProgressStage(status.latest_event);
          const resolvedCompletion = resolveMediaCompletion(status);
          const normalizedStatus =
            resolvedCompletion !== null
              ? { ...status, media_completed: resolvedCompletion }
              : status;
          next[status.job_id] = {
            status: normalizedStatus,
            latestEvent: status.latest_event ?? current?.latestEvent,
            latestTranslationEvent:
              statusStage === 'translation'
                ? status.latest_event ?? undefined
                : current?.latestTranslationEvent,
            latestMediaEvent:
              statusStage === 'media'
                ? status.latest_event ?? undefined
                : current?.latestMediaEvent
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
      setPlayerSelection(null);
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

  const activeJobMetadata = useMemo<Record<string, unknown> | null>(() => {
    if (!activeJobId) {
      return null;
    }
    const jobEntry = jobs[activeJobId];
    if (!jobEntry || !pipelineJobTypes.has(jobEntry.status.job_type)) {
      return null;
    }
    const rawResult = jobEntry.status.result;
    const metadata =
      rawResult && typeof rawResult === 'object' && 'book_metadata' in rawResult
        ? (rawResult as Record<string, unknown>).book_metadata
        : null;
    return metadata && typeof metadata === 'object' ? (metadata as Record<string, unknown>) : null;
  }, [activeJobId, jobs, pipelineJobTypes]);

  const playerJobMetadata = useMemo<Record<string, unknown> | null>(() => {
    if (playerContext?.type !== 'job') {
      return null;
    }
    if (playerContext.jobId === activeJobId) {
      return activeJobMetadata;
    }
    const entry = jobs[playerContext.jobId];
    if (!entry || !pipelineJobTypes.has(entry.status.job_type)) {
      return null;
    }
    const rawResult = entry.status.result;
    const metadata =
      rawResult && typeof rawResult === 'object' && 'book_metadata' in rawResult
        ? (rawResult as Record<string, unknown>).book_metadata
        : null;
    return metadata && typeof metadata === 'object' ? (metadata as Record<string, unknown>) : null;
  }, [activeJobId, activeJobMetadata, jobs, pipelineJobTypes, playerContext]);

  useEffect(() => {
    if (typeof selectedView === 'string' && selectedView.startsWith('pipeline:')) {
      return;
    }
    if (selectedView === ADMIN_USER_MANAGEMENT_VIEW || selectedView === ADMIN_READING_BEDS_VIEW) {
      return;
    }
    if (selectedView === JOB_PROGRESS_VIEW) {
      if (!activeJobId || !jobs[activeJobId]) {
        setActiveJobId(null);
        setSelectedView('pipeline:source');
      }
      return;
    }
    if (selectedView === JOB_MEDIA_VIEW) {
      if (!playerContext) {
        setSelectedView('pipeline:source');
        return;
      }
      if (playerContext.type === 'job' && !jobs[playerContext.jobId]) {
        setPlayerContext(null);
        setPlayerSelection(null);
        setSelectedView('pipeline:source');
      }
    }
  }, [activeJobId, jobs, playerContext, selectedView]);

  useEffect(() => {
    if (selectedView === JOB_PROGRESS_VIEW && !activeJobId) {
      setSelectedView('pipeline:source');
      return;
    }
    if (selectedView === JOB_MEDIA_VIEW && playerContext?.type === 'job' && !activeJobId) {
      setPlayerContext(null);
      setPlayerSelection(null);
      setSelectedView('pipeline:source');
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
      const entry = jobs[activeJobId];
      const jobType = entry?.status?.job_type ?? null;
      setPlayerContext({ type: 'job', jobId: activeJobId, jobType });
      setPlayerSelection(null);
    }
  }, [activeJobId, jobs, playerContext, selectedView]);

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

  const themeLabelId = useId();
  const themeHintId = useId();

  const handleThemeSelect = useCallback(
    (mode: ThemeMode) => {
      setThemeMode(mode);
    },
    [setThemeMode]
  );

  const themeOptions = useMemo(
    () => [
      {
        mode: 'light' as const,
        label: 'Light',
        description: 'Bright surfaces with dark text for daytime environments.'
      },
      {
        mode: 'dark' as const,
        label: 'Dark',
        description: 'Dim surfaces with light text to reduce glare at night.'
      },
      {
        mode: 'magenta' as const,
        label: 'Magenta',
        description: 'High-contrast magenta palette for vibrant accents.'
      },
      {
        mode: 'system' as const,
        label: 'System',
        description: 'Automatically match your operating system theme.'
      }
    ],
    []
  );

  const handleSubmit = useCallback(async (payload: PipelineRequestPayload) => {
    if (!canScheduleJobs) {
      setSubmitError('You need editor access to submit new jobs.');
      return;
    }
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const submission = await submitPipeline(payload);
      const placeholderStatus: PipelineStatusResponse = {
        job_id: submission.job_id,
        job_type: submission.job_type,
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
          latestEvent: undefined,
          latestTranslationEvent: undefined,
          latestMediaEvent: undefined
        }
      }));
      setPendingInputFile(null);
      void refreshJobs();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to submit book job';
      setSubmitError(message);
    } finally {
      setIsSubmitting(false);
    }
  }, [canScheduleJobs, refreshJobs]);

  const handleProgressEvent = useCallback((jobId: string, event: ProgressEventPayload) => {
    setJobs((previous) => {
      const current = previous[jobId];
      if (!current) {
        return previous;
      }

      const nextStatus = current.status ? { ...current.status } : undefined;
      const metadata = event.metadata;
      const stage = resolveProgressStage(event);

      if (nextStatus && metadata && typeof metadata === 'object') {
        const generated = (metadata as Record<string, unknown>).generated_files;
        if (generated && typeof generated === 'object') {
          nextStatus.generated_files = mergeGeneratedFiles(nextStatus.generated_files, generated);
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
          latestEvent: event,
          latestTranslationEvent:
            stage === 'translation' ? event : current.latestTranslationEvent,
          latestMediaEvent: stage === 'media' ? event : current.latestMediaEvent
        }
      };
    });
  }, []);

  const handleReloadJob = useCallback(async (jobId: string) => {
    setReloadingJobs((previous) => ({ ...previous, [jobId]: true }));
    try {
      let status: PipelineStatusResponse;
      const jobType = jobs[jobId]?.status?.job_type ?? null;
      if (jobType === 'pipeline' || jobType === 'book') {
        try {
          status = await refreshPipelineMetadata(jobId);
        } catch (refreshError) {
          console.warn('Unable to force metadata refresh for job', jobId, refreshError);
          status = await fetchPipelineStatus(jobId);
        }
      } else {
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
  }, [jobs, refreshJobs]);

  const resolveJobPermissions = useCallback(
    (status: PipelineStatusResponse | undefined | null) => {
      if (!status) {
        return { canView: false, canManage: false };
      }
      const ownerId = typeof status.user_id === 'string' ? status.user_id : null;
      const defaultVisibility = ownerId ? 'private' : 'public';
      const canView = canAccessPolicy(status.access ?? null, {
        ownerId,
        userId: sessionUsername,
        userRole: normalizedRole,
        permission: 'view',
        defaultVisibility
      });
      const canManage = canAccessPolicy(status.access ?? null, {
        ownerId,
        userId: sessionUsername,
        userRole: normalizedRole,
        permission: 'edit',
        defaultVisibility
      });
      return { canView, canManage };
    },
    [normalizedRole, sessionUsername]
  );

  const performJobAction = useCallback(
    async (jobId: string, action: JobAction) => {
      const entry = jobs[jobId];
      const { canManage } = resolveJobPermissions(entry?.status);
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
        } else if (action === 'restart') {
          const payload = await restartJob(jobId);
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
    [jobs, refreshJobs, resolveJobPermissions]
  );

  const handleUpdateJobAccess = useCallback(
    async (jobId: string, payload: AccessPolicyUpdatePayload) => {
      const entry = jobs[jobId];
      const { canManage } = resolveJobPermissions(entry?.status);
      if (!entry || !canManage) {
        window.alert('You are not authorized to update this job.');
        return;
      }
      setMutatingJobs((previous) => ({ ...previous, [jobId]: true }));
      try {
        const updated = await updateJobAccess(jobId, payload);
        const resolvedCompletion = resolveMediaCompletion(updated);
        const normalizedStatus =
          resolvedCompletion !== null ? { ...updated, media_completed: resolvedCompletion } : updated;
        setJobs((previous) => {
          const current = previous[jobId];
          if (!current) {
            return previous;
          }
          return {
            ...previous,
            [jobId]: {
              ...current,
              status: normalizedStatus
            }
          };
        });
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unable to update job access.';
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
      }
    },
    [jobs, resolveJobPermissions]
  );

  const handleVideoPlaybackStateChange = useCallback(
    (_isPlaying: boolean) => {
      // Keep sidebar visible during regular playback; immersive mode is driven by fullscreen.
      if (!isPlayerFullscreen) {
        setIsImmersiveMode(false);
      }
    },
    [isPlayerFullscreen]
  );

  const handleSidebarToggle = useCallback(() => {
    if (isPlayerFullscreen) {
      return;
    }
    setIsSidebarOpen((previous) => !previous);
  }, [isPlayerFullscreen]);

  const handlePlayerFullscreenChange = useCallback(
    (isFullscreen: boolean) => {
      setIsPlayerFullscreen(isFullscreen);
      setIsImmersiveMode(isFullscreen);
    },
    []
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

  const handleCopyJob = useCallback(
    (jobId: string) => {
      if (!canScheduleJobs) {
        window.alert('You need editor access to create new jobs.');
        return;
      }
      const entry = jobs[jobId];
      const parameters = entry?.status?.parameters ?? null;
      if (!parameters) {
        window.alert('Job parameters are unavailable; please refresh and try again.');
        return;
      }
      const jobType = entry.status?.job_type ?? '';
      setCopiedJobParameters(null);
      setSubtitlePrefillParameters(null);
      setYoutubeDubPrefillParameters(null);
      setPendingInputFile(null);

      if (jobType === 'subtitle') {
        setSubtitlePrefillParameters(parameters);
        setSubtitleRefreshKey((value) => value + 1);
        setSelectedView(SUBTITLES_VIEW);
        return;
      }
      if (jobType === 'youtube_dub') {
        setYoutubeDubPrefillParameters(parameters);
        setSelectedView(YOUTUBE_DUB_VIEW);
        return;
      }

      setCopiedJobParameters(parameters);
      const inputFile =
        typeof parameters.input_file === 'string' && parameters.input_file.trim()
          ? parameters.input_file.trim()
          : null;
      setPendingInputFile(inputFile);
      setSelectedView('pipeline:source');
    },
    [canScheduleJobs, jobs]
  );

  const handleRestartJob = useCallback(
    async (jobId: string) => {
      const confirmed = window.confirm(
        `Restart job ${jobId}? Generated outputs will be overwritten using the same settings.`
      );
      if (!confirmed) {
        return;
      }
      await performJobAction(jobId, 'restart');
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
      const { canManage } = resolveJobPermissions(entry.status);
      if (!canManage) {
        window.alert('You are not authorized to move this job into the library.');
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
    [jobs, refreshJobs, resolveJobPermissions]
  );

  const handleOpenPlayerForJob = useCallback(() => {
    if (!activeJobId) {
      return;
    }
    const entry = jobs[activeJobId];
    const jobType = entry?.status?.job_type ?? null;
    setPlayerContext({ type: 'job', jobId: activeJobId, jobType });
    setPlayerSelection(null);
    setSelectedView(JOB_MEDIA_VIEW);
    setIsImmersiveMode(false);
  }, [activeJobId, jobs]);

  const handlePlayLibraryItem = useCallback(
    (entry: LibraryOpenInput) => {
      let jobId: string | null = null;
      let itemType: 'book' | 'video' | 'narrated_subtitle' | null = null;
      let metadata: Record<string, unknown> | null = null;
      let libraryItem: LibraryItem | null = null;
      let selection: MediaSelectionRequest | null = null;

      if (typeof entry === 'string') {
        jobId = entry;
      } else if (isLibraryOpenRequest(entry)) {
        jobId = entry.jobId;
        selection = entry.selection ?? null;
        if (entry.item) {
          libraryItem = entry.item;
          metadata = buildLibraryBookMetadata(entry.item);
          itemType = entry.item.itemType ?? null;
        }
      } else {
        const resolvedItem = entry as LibraryItem;
        libraryItem = resolvedItem;
        jobId = resolvedItem.jobId;
        itemType = resolvedItem.itemType ?? null;
        metadata = buildLibraryBookMetadata(resolvedItem);
      }

      if (!jobId) {
        return;
      }

      setPlayerContext({
        type: 'library',
        jobId,
        itemType,
        bookMetadata: metadata,
        item: libraryItem,
      });
      setPlayerSelection(
        selection
          ? {
              baseId: selection.baseId,
              preferredType: selection.preferredType ?? null,
              offsetRatio: selection.offsetRatio ?? null,
              approximateTime: selection.approximateTime ?? null,
              token: selection.token ?? Date.now()
            }
          : null
      );
      setActiveJobId(null);
      setSelectedView(JOB_MEDIA_VIEW);
      setIsImmersiveMode(false);
    },
    []
  );

  const handleBackToLibraryFromPlayer = useCallback(
    (payload: { jobId: string; itemType: 'book' | 'video' | 'narrated_subtitle' | null }) => {
      const jobId = payload.jobId;
      if (!jobId) {
        return;
      }
      const itemType = payload.itemType ?? 'book';
      setLibraryFocusRequest({ jobId, itemType, token: Date.now() });
      setSelectedView(LIBRARY_VIEW);
      setIsImmersiveMode(false);
    },
    []
  );

  const handleConsumeLibraryFocusRequest = useCallback(() => {
    setLibraryFocusRequest(null);
  }, []);

  const handleSelectSidebarJob = useCallback(
    (jobId: string) => {
      setActiveJobId(jobId);
      setSelectedView(JOB_PROGRESS_VIEW);
    },
    [setActiveJobId, setSelectedView]
  );

  const handleImmersiveSectionChange = useCallback(
    (section: BookNarrationFormSection) => {
      const nextView = BOOK_NARRATION_SECTION_TO_VIEW[section];
      setSelectedView(nextView);
    },
    [setSelectedView]
  );

  const handleSidebarSelectView = useCallback(
    (view: SelectedView) => {
      if (!canScheduleJobs && isJobCreationView(view)) {
        window.alert('You need editor access to submit jobs.');
        return;
      }
      if (
        !isAdmin &&
        (view === ADMIN_USER_MANAGEMENT_VIEW || view === ADMIN_READING_BEDS_VIEW)
      ) {
        window.alert('Administrator access required.');
        return;
      }
      if (view === SUBTITLES_VIEW) {
        setSubtitleRefreshKey((value) => value + 1);
      }
      setSelectedView(view);
    },
    [canScheduleJobs, isAdmin, setSelectedView, setSubtitleRefreshKey]
  );

  const handleSubtitleJobCreated = useCallback(
    (jobId: string) => {
      setActiveJobId(jobId);
      void refreshJobs();
    },
    [refreshJobs]
  );

  const handleSubtitleJobSelected = useCallback(
    (jobId: string) => {
      setActiveJobId(jobId);
      setSelectedView(JOB_PROGRESS_VIEW);
    },
    [setSelectedView]
  );

  const handleYoutubeDubJobCreated = useCallback(
    (jobId: string) => {
      setActiveJobId(jobId);
      void refreshJobs();
    },
    [refreshJobs]
  );

  const handleYoutubeDubJobSelected = useCallback(
    (jobId: string) => {
      setActiveJobId(jobId);
      setSelectedView(JOB_PROGRESS_VIEW);
    },
    [setSelectedView]
  );

  const handleOpenYoutubeDubMedia = useCallback(
    (jobId: string) => {
      setActiveJobId(jobId);
      const entry = jobs[jobId];
      const jobType = entry?.status?.job_type ?? 'youtube_dub';
      setPlayerContext({ type: 'job', jobId, jobType });
      setPlayerSelection(null);
      setSelectedView(JOB_MEDIA_VIEW);
      setIsImmersiveMode(false);
    },
    [jobs]
  );

  const jobList: JobState[] = useMemo(() => {
    return Object.entries(jobs).map(([jobId, entry]) => {
      const { canView, canManage } = resolveJobPermissions(entry.status);
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
        latestTranslationEvent: entry.latestTranslationEvent,
        latestMediaEvent: entry.latestMediaEvent,
        isReloading: Boolean(reloadingJobs[jobId]),
        isMutating: Boolean(mutatingJobs[jobId]),
        canManage,
        canView
      };
    });
  }, [jobs, mutatingJobs, reloadingJobs, resolveJobPermissions]);

  const sortedJobs = useMemo(() => {
    return [...jobList].sort((a, b) => {
      const left = new Date(a.status.created_at).getTime();
      const right = new Date(b.status.created_at).getTime();
      return right - left;
    });
  }, [jobList]);

  const sidebarJobs = useMemo(() => {
    return sortedJobs.filter((job) => job.canView ?? job.canManage);
  }, [sortedJobs]);

  const subtitleJobStates = useMemo(() => {
    return sortedJobs.filter((job) => job.status.job_type === 'subtitle');
  }, [sortedJobs]);
  const youtubeDubJobStates = useMemo(() => {
    return sortedJobs.filter((job) => job.status.job_type === 'youtube_dub');
  }, [sortedJobs]);

  const isPipelineView = typeof selectedView === 'string' && selectedView.startsWith('pipeline:');
  const isAdminUsersView = selectedView === ADMIN_USER_MANAGEMENT_VIEW;
  const isAdminReadingBedsView = selectedView === ADMIN_READING_BEDS_VIEW;
  const isAdminView = isAdminUsersView || isAdminReadingBedsView;
  const isLibraryView = selectedView === LIBRARY_VIEW;
  const isCreateBookView = selectedView === CREATE_BOOK_VIEW;
  const isSubtitlesView = selectedView === SUBTITLES_VIEW;
  const isYoutubeSubtitlesView = selectedView === YOUTUBE_SUBTITLES_VIEW;
  const isYoutubeDubView = selectedView === YOUTUBE_DUB_VIEW;
  const isAddBookView = isPipelineView;
  const activePipelineSection = useMemo(() => {
    if (!isPipelineView) {
      return null;
    }
    return BOOK_NARRATION_SECTION_MAP[selectedView as PipelineMenuView];
  }, [isPipelineView, selectedView]);

  const selectedJob = useMemo(() => {
    if (!activeJobId) {
      return undefined;
    }
    const job = jobList.find((entry) => entry.jobId === activeJobId);
    if (job && !(job.canView ?? job.canManage)) {
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
          <div className="auth-card__header">
            <div className="auth-card__logo" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="9" />
                <path d="M3 12h18" />
                <path d="M5 7c2.2 1.4 4.7 2 7 2s4.8-.6 7-2" />
                <path d="M5 17c2.2-1.4 4.7-2 7-2s4.8.6 7 2" />
                <path d="M12 3c2.5 3 2.5 15 0 18c-2.5-3-2.5-15 0-18z" />
              </svg>
            </div>
            <h1>Language tools</h1>
          </div>
          <LoginForm
            onSubmit={handleLogin}
            onOAuthSubmit={handleOAuthLogin}
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
            <button
              type="button"
              className="sidebar__logo-mark"
              onClick={handleSidebarToggle}
              aria-expanded={isSidebarOpen}
              aria-controls="dashboard-sidebar"
              aria-label={isSidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
              title={isSidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
            >
              <span aria-hidden="true">🌐</span>
            </button>
            <span className="sidebar__title" aria-label="Language Tools">
              Language Tools
            </span>
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
          canScheduleJobs={canScheduleJobs}
          createBookView={CREATE_BOOK_VIEW}
          libraryView={LIBRARY_VIEW}
          subtitlesView={SUBTITLES_VIEW}
          youtubeSubtitlesView={YOUTUBE_SUBTITLES_VIEW}
          youtubeDubView={YOUTUBE_DUB_VIEW}
          jobMediaView={JOB_MEDIA_VIEW}
          adminUserManagementView={ADMIN_USER_MANAGEMENT_VIEW}
          adminReadingBedsView={ADMIN_READING_BEDS_VIEW}
        />
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
                  <span className="theme-control__label" id={themeLabelId}>
                    Theme
                  </span>
                  <div className="theme-control__options" role="group" aria-labelledby={themeLabelId}>
                    {themeOptions.map((option) => {
                      const descriptionId = `${themeLabelId}-${option.mode}`;
                      const describedBy =
                        themeMode === 'system' && option.mode === 'system'
                          ? `${descriptionId} ${themeHintId}`
                          : descriptionId;
                      return (
                        <button
                          key={option.mode}
                          type="button"
                          className="theme-control__option"
                          data-theme-option={option.mode}
                          aria-pressed={themeMode === option.mode}
                          aria-describedby={describedBy}
                          onClick={() => {
                            handleThemeSelect(option.mode);
                          }}
                        >
                          <span
                            className={`theme-control__option-swatch theme-control__option-swatch--${option.mode}`}
                            aria-hidden="true"
                          />
                          <span className="theme-control__option-copy">
                            <span className="theme-control__option-label">{option.label}</span>
                            <span className="theme-control__option-description" id={descriptionId}>
                              {option.description}
                            </span>
                          </span>
                        </button>
                      );
                    })}
                  </div>
                  {themeMode === 'system' ? (
                    <span className="theme-control__hint" id={themeHintId} aria-live="polite">
                      Following {resolvedTheme} mode
                    </span>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        </div>
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
          {isAdminUsersView ? (
            <header className="dashboard__header">
              <h1>User management</h1>
              <p>Administer dashboard accounts, reset passwords, and control access for operators.</p>
            </header>
          ) : isAdminReadingBedsView ? (
            <header className="dashboard__header">
              <h1>Reading music</h1>
              <p>Manage background music tracks shown in the interactive player.</p>
            </header>
          ) : null}
          {isAdminUsersView ? (
            <section>
              <UserManagementPanel currentUser={sessionUser?.username ?? ''} />
            </section>
          ) : isAdminReadingBedsView ? (
            <section>
              <ReadingBedsPanel />
            </section>
          ) : isLibraryView ? (
            <LibraryPage
              onPlay={handlePlayLibraryItem}
              focusRequest={libraryFocusRequest}
              onConsumeFocusRequest={handleConsumeLibraryFocusRequest}
            />
          ) : isCreateBookView && canScheduleJobs ? (
            <section>
              <CreateBookPage
                onJobSubmitted={(jobId) => {
                  if (jobId) {
                    setActiveJobId(jobId);
                    setSelectedView(JOB_PROGRESS_VIEW);
                    setIsImmersiveMode(false);
                  }
                }}
                recentJobs={recentPipelineJobs}
              />
            </section>
          ) : (
            <>
              {isAddBookView && canScheduleJobs ? (
                <section>
                  <NewImmersiveBookPage
                    activeSection={activePipelineSection ?? 'source'}
                    onSectionChange={handleImmersiveSectionChange}
                    onSubmit={handleSubmit}
                    isSubmitting={isSubmitting}
                    prefillInputFile={pendingInputFile}
                    prefillParameters={copiedJobParameters}
                    submitError={submitError}
                    recentJobs={recentPipelineJobs}
                  />
                </section>
              ) : null}
              {isSubtitlesView && canScheduleJobs ? (
                <section>
                  <SubtitleToolPage
                    subtitleJobs={subtitleJobStates}
                    onJobCreated={handleSubtitleJobCreated}
                    onSelectJob={handleSubtitleJobSelected}
                    onMoveToLibrary={handleMoveJobToLibrary}
                    prefillParameters={subtitlePrefillParameters}
                    refreshSignal={subtitleRefreshKey}
                  />
                </section>
              ) : null}
              {isYoutubeSubtitlesView && canScheduleJobs ? (
                <section>
                  <YoutubeVideoPage />
                </section>
              ) : null}
              {isYoutubeDubView && canScheduleJobs ? (
                <section>
                  <VideoDubbingPage
                    jobs={youtubeDubJobStates}
                    onJobCreated={handleYoutubeDubJobCreated}
                    onSelectJob={handleYoutubeDubJobSelected}
                    onOpenJobMedia={handleOpenYoutubeDubMedia}
                    prefillParameters={youtubeDubPrefillParameters}
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
                      onRestart={() => handleRestartJob(selectedJob.jobId)}
                      onReload={() => handleReloadJob(selectedJob.jobId)}
                      onCopy={canScheduleJobs ? () => handleCopyJob(selectedJob.jobId) : undefined}
                      onMoveToLibrary={() => handleMoveJobToLibrary(selectedJob.jobId)}
                      onUpdateAccess={(payload) => handleUpdateJobAccess(selectedJob.jobId, payload)}
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
                <div className="job-media-section">
                  <PlayerView
                    context={playerContext}
                    jobBookMetadata={playerJobMetadata}
                    onVideoPlaybackStateChange={handleVideoPlaybackStateChange}
                    onFullscreenChange={handlePlayerFullscreenChange}
                    onOpenLibraryItem={handlePlayLibraryItem}
                    onBackToLibrary={handleBackToLibraryFromPlayer}
                    selectionRequest={playerSelection}
                  />
                </div>
              ) : null}
            </>
          )}
        </main>
      </div>
      <MyLinguistAssistant />
      <MyPainterAssistant />
    </div>
  );
}

export default App;
