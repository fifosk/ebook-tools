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

interface JobsState {
  // Data
  jobs: Map<string, JobEntry>;
  loadingStates: Map<string, LoadingFlags>;
  activeJobId: string | null;

  // Selectors
  getJob: (jobId: string) => JobEntry | undefined;
  getJobWithLoading: (jobId: string) => (JobEntry & LoadingFlags) | undefined;
  getAllJobs: () => JobEntry[];
  getJobIds: () => string[];

  // Mutations
  setJobs: (jobs: PipelineStatusResponse[]) => void;
  updateJob: (jobId: string, updates: Partial<JobEntry>) => void;
  removeJob: (jobId: string) => void;
  setActiveJob: (jobId: string | null) => void;

  // Progress events
  handleProgressEvent: (jobId: string, event: ProgressEventPayload) => void;

  // Loading states
  setLoading: (jobId: string, key: keyof LoadingFlags, value: boolean) => void;

  // Async actions
  refreshJobs: () => Promise<void>;
  performJobAction: (jobId: string, action: JobAction) => Promise<void>;
  reloadJob: (jobId: string) => Promise<void>;
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
