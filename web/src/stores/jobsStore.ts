import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type {
  PipelineStatusResponse,
  ProgressEventPayload,
  AccessPolicyUpdatePayload,
} from '../api/dtos';
import {
  fetchJobs,
  pauseJob,
  resumeJob,
  cancelJob,
  deleteJob,
  restartJob,
  refreshPipelineMetadata,
  updateJobAccess,
} from '../api/client';
import { resolveMediaCompletion } from '../utils/mediaFormatters';
import { resolveProgressStage } from '../utils/progressEvents';

// Types
export interface JobEntry {
  status: PipelineStatusResponse;
  latestEvent?: ProgressEventPayload;
  latestTranslationEvent?: ProgressEventPayload;
  latestMediaEvent?: ProgressEventPayload;
}

export interface LoadingFlags {
  isReloading: boolean;
  isMutating: boolean;
}

export type JobAction = 'pause' | 'resume' | 'cancel' | 'delete' | 'restart';

/**
 * Jobs Store - Manages all job-related state with Zustand
 *
 * Features:
 * - Map-based storage for O(1) job lookups
 * - Separate loading state tracking (prevents nested object updates)
 * - Request deduplication for API calls
 * - Atomic updates prevent race conditions
 * - Computed selectors for derived state
 */
interface JobsState {
  // Data
  /** Map of job IDs to job entries for O(1) lookup performance */
  jobs: Map<string, JobEntry>;
  /** Separate map for loading states (isReloading, isMutating) */
  loadingStates: Map<string, LoadingFlags>;
  /** Currently active/selected job ID */
  activeJobId: string | null;

  // Selectors
  /** Get a specific job by ID */
  getJob: (jobId: string) => JobEntry | undefined;
  /** Get a job with its loading states merged in */
  getJobWithLoading: (jobId: string) => (JobEntry & LoadingFlags) | undefined;
  /** Get all jobs as an array */
  getAllJobs: () => JobEntry[];
  /** Get all job IDs */
  getJobIds: () => string[];
  /** Get jobs sorted by creation date (newest first) */
  getSortedJobs: () => JobEntry[];
  /** Get jobs filtered by job type */
  getJobsByType: (jobType: string) => JobEntry[];

  // Mutations
  /** Replace all jobs (used during initial load and refresh) */
  setJobs: (jobs: PipelineStatusResponse[]) => void;
  /** Update a specific job with partial data */
  updateJob: (jobId: string, updates: Partial<JobEntry>) => void;
  /** Remove a job from the store */
  removeJob: (jobId: string) => void;
  /** Set the currently active job */
  setActiveJob: (jobId: string | null) => void;

  // Progress events
  /** Handle incoming SSE progress events for a job */
  handleProgressEvent: (jobId: string, event: ProgressEventPayload) => void;

  // Loading states
  /** Set a specific loading flag for a job */
  setLoading: (jobId: string, key: keyof LoadingFlags, value: boolean) => void;

  // Async actions
  /** Fetch all jobs from API (deduplicated) */
  refreshJobs: () => Promise<void>;
  /** Perform an action on a job (pause, resume, cancel, delete, restart) */
  performJobAction: (jobId: string, action: JobAction) => Promise<void>;
  /** Reload metadata for a specific job */
  reloadJob: (jobId: string) => Promise<void>;
  /** Update access policy for a job */
  updateJobAccess: (jobId: string, payload: AccessPolicyUpdatePayload) => Promise<void>;
}

// Helper to merge generated_files from metadata
function mergeGeneratedFiles(
  existing: Record<string, unknown> | null | undefined,
  incoming: unknown
): Record<string, unknown> | undefined {
  if (!incoming || typeof incoming !== 'object') {
    return existing || undefined;
  }

  const incomingFiles = incoming as Record<string, unknown>;
  if (!existing) {
    return { ...incomingFiles };
  }

  return { ...existing, ...incomingFiles };
}

// Module-level variable for request deduplication
let refreshPromise: Promise<void> | null = null;

export const useJobsStore = create<JobsState>()(
  devtools(
    (set, get) => ({
      // Initial state
      jobs: new Map(),
      loadingStates: new Map(),
      activeJobId: null,

      // Selectors
      getJob: (jobId: string) => {
        return get().jobs.get(jobId);
      },

      getJobWithLoading: (jobId: string) => {
        const job = get().jobs.get(jobId);
        const loading = get().loadingStates.get(jobId) || {
          isReloading: false,
          isMutating: false,
        };

        if (!job) return undefined;

        return { ...job, ...loading };
      },

      getAllJobs: () => {
        return Array.from(get().jobs.values());
      },

      getJobIds: () => {
        return Array.from(get().jobs.keys());
      },

      // Computed selectors (sorted, filtered)
      getSortedJobs: () => {
        const jobs = Array.from(get().jobs.values());
        return jobs.sort((a, b) => {
          const left = new Date(a.status.created_at).getTime();
          const right = new Date(b.status.created_at).getTime();
          return right - left; // Newest first
        });
      },

      getJobsByType: (jobType: string) => {
        const jobs = get().getAllJobs();
        return jobs.filter((job) => job.status.job_type === jobType);
      },

      // Mutations
      setJobs: (statuses: PipelineStatusResponse[]) => {
        set((state) => {
          const newJobs = new Map<string, JobEntry>();
          const newLoadingStates = new Map<string, LoadingFlags>();
          const knownJobIds = new Set<string>();

          for (const status of statuses) {
            const jobId = status.job_id;
            knownJobIds.add(jobId);

            const current = state.jobs.get(jobId);
            const statusStage = resolveProgressStage(status.latest_event);
            const resolvedCompletion = resolveMediaCompletion(status);

            // Normalize status with resolved media completion
            const normalizedStatus =
              resolvedCompletion !== null
                ? { ...status, media_completed: resolvedCompletion }
                : status;

            newJobs.set(jobId, {
              status: normalizedStatus,
              latestEvent: status.latest_event ?? current?.latestEvent,
              latestTranslationEvent:
                statusStage === 'translation'
                  ? status.latest_event ?? undefined
                  : current?.latestTranslationEvent,
              latestMediaEvent:
                statusStage === 'media'
                  ? status.latest_event ?? undefined
                  : current?.latestMediaEvent,
            });

            // Preserve loading states for known jobs, clean up removed jobs
            const currentLoading = state.loadingStates.get(jobId);
            if (currentLoading) {
              newLoadingStates.set(jobId, currentLoading);
            }
          }

          return {
            jobs: newJobs,
            loadingStates: newLoadingStates,
          };
        });
      },

      updateJob: (jobId: string, updates: Partial<JobEntry>) => {
        set((state) => {
          const current = state.jobs.get(jobId);
          if (!current) return state;

          const newJobs = new Map(state.jobs);
          newJobs.set(jobId, { ...current, ...updates });

          return { jobs: newJobs };
        });
      },

      removeJob: (jobId: string) => {
        set((state) => {
          const newJobs = new Map(state.jobs);
          const newLoadingStates = new Map(state.loadingStates);

          newJobs.delete(jobId);
          newLoadingStates.delete(jobId);

          return {
            jobs: newJobs,
            loadingStates: newLoadingStates,
            activeJobId: state.activeJobId === jobId ? null : state.activeJobId,
          };
        });
      },

      setActiveJob: (jobId: string | null) => {
        set({ activeJobId: jobId });
      },

      // Progress event handling
      handleProgressEvent: (jobId: string, event: ProgressEventPayload) => {
        set((state) => {
          const current = state.jobs.get(jobId);
          if (!current) return state;

          let nextStatus = current.status ? { ...current.status } : undefined;
          const metadata = event.metadata;
          const stage = resolveProgressStage(event);

          // Merge generated_files from metadata if present
          if (nextStatus && metadata && typeof metadata === 'object') {
            const generated = (metadata as Record<string, unknown>).generated_files;
            if (generated && typeof generated === 'object') {
              nextStatus.generated_files = mergeGeneratedFiles(
                nextStatus.generated_files,
                generated
              );
            }

            // Update media_completed from metadata if present
            const mediaCompletedMeta = (metadata as Record<string, unknown>).media_completed;
            if (typeof mediaCompletedMeta === 'boolean') {
              nextStatus.media_completed = mediaCompletedMeta;
            }
          }

          // Resolve media completion
          if (nextStatus) {
            const resolvedCompletion = resolveMediaCompletion(nextStatus);
            if (resolvedCompletion !== null) {
              nextStatus.media_completed = resolvedCompletion;
            }
          }

          const newJobs = new Map(state.jobs);
          newJobs.set(jobId, {
            ...current,
            status: nextStatus ?? current.status,
            latestEvent: event,
            latestTranslationEvent:
              stage === 'translation' ? event : current.latestTranslationEvent,
            latestMediaEvent:
              stage === 'media' ? event : current.latestMediaEvent,
          });

          return { jobs: newJobs };
        });
      },

      // Loading state management
      setLoading: (jobId: string, key: keyof LoadingFlags, value: boolean) => {
        set((state) => {
          const newLoadingStates = new Map(state.loadingStates);
          const current = newLoadingStates.get(jobId) || {
            isReloading: false,
            isMutating: false,
          };

          newLoadingStates.set(jobId, { ...current, [key]: value });

          return { loadingStates: newLoadingStates };
        });
      },

      // Async actions
      refreshJobs: async () => {
        // Request deduplication: if already refreshing, return existing promise
        if (refreshPromise) {
          return refreshPromise;
        }

        refreshPromise = (async () => {
          try {
            const statuses = await fetchJobs();
            get().setJobs(statuses);
          } catch (error) {
            console.error('Failed to refresh jobs:', error);
            throw error;
          } finally {
            refreshPromise = null;
          }
        })();

        return refreshPromise;
      },

      performJobAction: async (jobId: string, action: JobAction) => {
        const { setLoading, updateJob, removeJob, refreshJobs } = get();

        setLoading(jobId, 'isMutating', true);

        try {
          let response: PipelineStatusResponse | null = null;

          switch (action) {
            case 'pause':
              response = (await pauseJob(jobId)).job;
              break;
            case 'resume':
              response = (await resumeJob(jobId)).job;
              break;
            case 'cancel':
              response = (await cancelJob(jobId)).job;
              break;
            case 'restart':
              response = (await restartJob(jobId)).job;
              break;
            case 'delete':
              await deleteJob(jobId);
              removeJob(jobId);
              return;
          }

          if (response) {
            const resolvedCompletion = resolveMediaCompletion(response);
            const normalizedResponse =
              resolvedCompletion !== null
                ? { ...response, media_completed: resolvedCompletion }
                : response;

            const nextLatestEvent = response.latest_event;

            updateJob(jobId, {
              status: normalizedResponse,
              latestEvent: nextLatestEvent ?? undefined,
            });
          }

          // Refresh to ensure consistency
          await refreshJobs();
        } catch (error) {
          console.error(`Failed to ${action} job ${jobId}:`, error);
          throw error;
        } finally {
          setLoading(jobId, 'isMutating', false);
        }
      },

      reloadJob: async (jobId: string) => {
        const { setLoading, updateJob } = get();

        setLoading(jobId, 'isReloading', true);

        try {
          const response = await refreshPipelineMetadata(jobId);
          const resolvedCompletion = resolveMediaCompletion(response);
          const normalizedResponse =
            resolvedCompletion !== null
              ? { ...response, media_completed: resolvedCompletion }
              : response;

          updateJob(jobId, {
            status: normalizedResponse,
            latestEvent: response.latest_event ?? undefined,
          });
        } catch (error) {
          console.error(`Failed to reload job ${jobId}:`, error);
          throw error;
        } finally {
          setLoading(jobId, 'isReloading', false);
        }
      },

      updateJobAccess: async (jobId: string, payload: AccessPolicyUpdatePayload) => {
        const { setLoading, updateJob } = get();

        setLoading(jobId, 'isMutating', true);

        try {
          const response = await updateJobAccess(jobId, payload);

          updateJob(jobId, {
            status: response,
          });
        } catch (error) {
          console.error(`Failed to update job access for ${jobId}:`, error);
          throw error;
        } finally {
          setLoading(jobId, 'isMutating', false);
        }
      },
    }),
    { name: 'JobsStore' }
  )
);

// Selective subscription hooks for performance
// These hooks prevent unnecessary re-renders by subscribing only to specific slices of state

/**
 * Subscribe to a specific job's data
 * Only re-renders when the specified job changes
 */
export const useJobData = (jobId: string | null) => {
  return useJobsStore(
    (state) => (jobId ? state.getJob(jobId) : undefined),
    (a, b) => {
      if (!a && !b) return true; // Both undefined
      if (!a || !b) return false; // One undefined
      // Compare job data shallowly
      return (
        a.status === b.status &&
        a.latestEvent === b.latestEvent &&
        a.latestTranslationEvent === b.latestTranslationEvent &&
        a.latestMediaEvent === b.latestMediaEvent
      );
    }
  );
};

/**
 * Subscribe to a specific job's loading states
 * Only re-renders when loading states change
 */
export const useJobLoading = (jobId: string | null) => {
  return useJobsStore(
    (state) => {
      if (!jobId) return { isReloading: false, isMutating: false };
      const loading = state.loadingStates.get(jobId);
      return loading || { isReloading: false, isMutating: false };
    },
    (a, b) => a.isReloading === b.isReloading && a.isMutating === b.isMutating
  );
};

/**
 * Subscribe to all job IDs (for lists)
 * Only re-renders when the set of job IDs changes
 */
export const useJobIds = () => {
  return useJobsStore(
    (state) => state.getJobIds(),
    (a, b) => {
      if (a.length !== b.length) return false;
      return a.every((id, i) => id === b[i]);
    }
  );
};

/**
 * Subscribe to active job ID only
 * Only re-renders when active job changes
 */
export const useActiveJobId = () => {
  return useJobsStore((state) => state.activeJobId);
};
