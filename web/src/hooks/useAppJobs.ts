import { useCallback, useEffect, useMemo, useRef } from 'react';
import type { JobState } from '../components/JobList';
import type {
  AccessPolicyUpdatePayload,
  JobParameterSnapshot,
  PipelineStatusResponse,
  ProgressEventPayload
} from '../api/dtos';
import { fetchPipelineStatus, moveJobToLibrary, submitPipeline } from '../api/client';
import type { PipelineRequestPayload } from '../api/dtos';
import { useJobsStore } from '../stores/jobsStore';
import { useUIStore } from '../stores/uiStore';
import { canAccessPolicy, normalizeRole } from '../utils/accessControl';
import { resolveMediaCompletion } from '../utils/mediaFormatters';
import {
  JOB_PROGRESS_VIEW,
  JOB_MEDIA_VIEW,
  SUBTITLES_VIEW,
  YOUTUBE_DUB_VIEW
} from '../constants/appViews';

export interface JobRegistryEntry {
  status: PipelineStatusResponse;
  latestEvent?: ProgressEventPayload;
  latestTranslationEvent?: ProgressEventPayload;
  latestMediaEvent?: ProgressEventPayload;
  latestPlayableEvent?: ProgressEventPayload;
}

type JobAction = 'pause' | 'resume' | 'cancel' | 'delete' | 'restart';

interface UseAppJobsOptions {
  sessionUsername: string | null;
  normalizedRole: string | null;
  canScheduleJobs: boolean;
  session: unknown;
}

/**
 * Hook for job management handlers in the App component.
 * Encapsulates job actions, permissions, and state updates.
 */
export function useAppJobs(options: UseAppJobsOptions) {
  const { sessionUsername, normalizedRole, canScheduleJobs, session } = options;

  const {
    getAllJobs,
    getJob,
    activeJobId,
    setActiveJob,
    handleProgressEvent,
    refreshJobs,
    performJobAction,
    reloadJob,
    updateJobAccess: updateJobAccessStore
  } = useJobsStore();

  const {
    isSubmitting,
    submitError,
    setIsSubmitting,
    setSubmitError,
    setSelectedView,
    subtitleRefreshKey,
    incrementSubtitleRefreshKey,
    playerContext,
    setPlayerContext,
    setPlayerSelection,
    setPendingInputFile,
    setCopiedJobParameters,
    setSubtitlePrefillParameters,
    setYoutubeDubPrefillParameters,
    setImmersiveMode
  } = useUIStore();

  // Convert store Map to Record for backward compatibility
  const jobs = useJobsStore(
    (state) => {
      const allJobs = state.getAllJobs();
      const record: Record<string, JobRegistryEntry> = {};
      for (const job of allJobs) {
        record[job.status.job_id] = job;
      }
      return record;
    },
    (prev, next) => {
      const prevIds = Object.keys(prev);
      const nextIds = Object.keys(next);
      if (prevIds.length !== nextIds.length) return false;
      if (!prevIds.every((id) => nextIds.includes(id))) return false;
      for (const id of prevIds) {
        if (prev[id] !== next[id]) return false;
      }
      return true;
    }
  );

  const pipelineJobTypes = useMemo(() => new Set(['pipeline', 'book']), []);

  const recentPipelineJobs = useMemo(() => {
    return Object.values(jobs)
      .map((entry) => entry.status)
      .filter((status) => pipelineJobTypes.has(status.job_type));
  }, [jobs, pipelineJobTypes]);

  // Wrap store refreshJobs to check session
  const refreshJobsIfAuthenticated = useCallback(async () => {
    if (!session) {
      return;
    }
    try {
      await refreshJobs();
    } catch (error) {
      console.warn('Unable to load persisted jobs', error);
    }
  }, [session, refreshJobs]);

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

  const performJobActionWrapper = useCallback(
    async (jobId: string, action: JobAction) => {
      const entry = getJob(jobId);
      const { canManage } = resolveJobPermissions(entry?.status);
      if (!entry || !canManage) {
        console.warn(`Skipping ${action} for unauthorized job`, jobId);
        return;
      }
      try {
        await performJobAction(jobId, action);
      } catch (error) {
        console.warn(`Unable to ${action} job`, jobId, error);
      }
    },
    [getJob, performJobAction, resolveJobPermissions]
  );

  const handleSubmit = useCallback(
    async (payload: PipelineRequestPayload) => {
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
        useJobsStore.getState().updateJob(submission.job_id, {
          status: placeholderStatus,
          latestEvent: undefined,
          latestTranslationEvent: undefined,
          latestMediaEvent: undefined
        });
        setPendingInputFile(null);
        void refreshJobsIfAuthenticated();
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to submit book job';
        setSubmitError(message);
      } finally {
        setIsSubmitting(false);
      }
    },
    [canScheduleJobs, refreshJobsIfAuthenticated, setIsSubmitting, setPendingInputFile, setSubmitError]
  );

  const handleReloadJob = useCallback(
    async (jobId: string) => {
      try {
        await reloadJob(jobId);
      } catch (error) {
        console.warn('Unable to reload job metadata', jobId, error);
      }
    },
    [reloadJob]
  );

  const handleUpdateJobAccess = useCallback(
    async (jobId: string, payload: AccessPolicyUpdatePayload) => {
      const entry = getJob(jobId);
      const { canManage } = resolveJobPermissions(entry?.status);
      if (!entry || !canManage) {
        window.alert('You are not authorized to update this job.');
        return;
      }
      try {
        await updateJobAccessStore(jobId, payload);
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unable to update job access.';
        window.alert(message);
      }
    },
    [getJob, updateJobAccessStore, resolveJobPermissions]
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
        incrementSubtitleRefreshKey();
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
    [
      canScheduleJobs,
      jobs,
      incrementSubtitleRefreshKey,
      setCopiedJobParameters,
      setPendingInputFile,
      setSelectedView,
      setSubtitlePrefillParameters,
      setYoutubeDubPrefillParameters
    ]
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
        window.alert(
          'Only completed or fully paused jobs with finalized media can be moved to the library.'
        );
        return;
      }

      const confirmed = window.confirm(
        `Move job ${jobId} to the library? Its working files will be archived under the configured library root.`
      );
      if (!confirmed) {
        return;
      }

      const statusOverride: 'finished' | 'paused' = isCompleted ? 'finished' : 'paused';
      const { setLoading } = useJobsStore.getState();
      setLoading(jobId, 'isMutating', true);
      try {
        await moveJobToLibrary(jobId, statusOverride);
        window.alert(`Job ${jobId} has been moved into the library.`);
      } catch (error) {
        const message =
          error instanceof Error ? error.message : 'Unable to move the job into the library.';
        window.alert(message);
      } finally {
        setLoading(jobId, 'isMutating', false);
        await refreshJobsIfAuthenticated();
      }
    },
    [jobs, refreshJobsIfAuthenticated, resolveJobPermissions]
  );

  // Build job list with permissions
  const jobList: JobState[] = useMemo(() => {
    const storeState = useJobsStore.getState();
    return Object.entries(jobs).map(([jobId, entry]) => {
      const { canView, canManage } = resolveJobPermissions(entry.status);
      const resolvedStatus = entry.status
        ? {
            ...entry.status,
            media_completed:
              resolveMediaCompletion(entry.status) ?? entry.status.media_completed ?? null
          }
        : entry.status;

      const loadingState = storeState.getJobWithLoading(jobId);

      return {
        jobId,
        status: resolvedStatus,
        latestEvent: entry.latestEvent,
        latestTranslationEvent: entry.latestTranslationEvent,
        latestMediaEvent: entry.latestMediaEvent,
        latestPlayableEvent: entry.latestPlayableEvent,
        isReloading: loadingState?.isReloading ?? false,
        isMutating: loadingState?.isMutating ?? false,
        canManage,
        canView
      };
    });
  }, [jobs, resolveJobPermissions]);

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

  return {
    // State
    jobs,
    jobList,
    sortedJobs,
    sidebarJobs,
    subtitleJobStates,
    youtubeDubJobStates,
    selectedJob,
    recentPipelineJobs,
    activeJobId,
    isSubmitting,
    submitError,
    pipelineJobTypes,

    // Actions
    setActiveJob,
    handleProgressEvent,
    refreshJobs,
    refreshJobsIfAuthenticated,
    handleSubmit,
    handleReloadJob,
    handleUpdateJobAccess,
    handlePauseJob,
    handleResumeJob,
    handleCancelJob,
    handleDeleteJob,
    handleCopyJob,
    handleRestartJob,
    handleMoveJobToLibrary,
    resolveJobPermissions,
    performJobActionWrapper
  };
}
