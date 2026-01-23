import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useJobsStore } from '../jobsStore';
import type { PipelineStatusResponse, ProgressEventPayload } from '../../api/dtos';

// Mock API client
const fetchJobsMock = vi.hoisted(() => vi.fn());
const pauseJobMock = vi.hoisted(() => vi.fn());
const resumeJobMock = vi.hoisted(() => vi.fn());
const cancelJobMock = vi.hoisted(() => vi.fn());
const deleteJobMock = vi.hoisted(() => vi.fn());
const restartJobMock = vi.hoisted(() => vi.fn());
const refreshPipelineMetadataMock = vi.hoisted(() => vi.fn());
const updateJobAccessMock = vi.hoisted(() => vi.fn());

vi.mock('../../api/client', () => ({
  fetchJobs: fetchJobsMock,
  pauseJob: pauseJobMock,
  resumeJob: resumeJobMock,
  cancelJob: cancelJobMock,
  deleteJob: deleteJobMock,
  restartJob: restartJobMock,
  refreshPipelineMetadata: refreshPipelineMetadataMock,
  updateJobAccess: updateJobAccessMock,
}));

// Mock utilities
vi.mock('../../utils/mediaFormatters', () => ({
  resolveMediaCompletion: vi.fn((status) => status.media_completed ?? null),
}));

vi.mock('../../utils/progressEvents', () => ({
  resolveProgressStage: vi.fn((event) => {
    if (!event) return null;
    if (event.event_type?.includes('translation')) return 'translation';
    if (event.event_type?.includes('media')) return 'media';
    return null;
  }),
}));

// Helper to create mock job status
function createMockJobStatus(
  jobId: string,
  status: string = 'pending'
): PipelineStatusResponse {
  return {
    job_id: jobId,
    job_type: 'pipeline',
    status: status as any,
    created_at: new Date().toISOString(),
    started_at: null,
    completed_at: null,
    result: null,
    error: null,
    latest_event: null,
    tuning: null,
    generated_files: null,
  };
}

// Helper to create mock progress event
function createMockProgressEvent(
  eventType: string = 'translation:progress'
): ProgressEventPayload {
  return {
    event_type: eventType,
    timestamp: Date.now(),
    metadata: {},
    snapshot: {
      completed: 10,
      total: 100,
      elapsed: 5000,
      speed: 2,
      eta: 45000,
    },
    error: null,
  };
}

describe('jobsStore', () => {
  beforeEach(() => {
    // Reset store state between tests
    const { result } = renderHook(() => useJobsStore());
    act(() => {
      result.current.setJobs([]);
    });

    // Reset mocks
    fetchJobsMock.mockReset();
    pauseJobMock.mockReset();
    resumeJobMock.mockReset();
    cancelJobMock.mockReset();
    deleteJobMock.mockReset();
    restartJobMock.mockReset();
    refreshPipelineMetadataMock.mockReset();
    updateJobAccessMock.mockReset();
  });

  describe('setJobs', () => {
    it('should initialize jobs from status array', () => {
      const { result } = renderHook(() => useJobsStore());
      const statuses = [
        createMockJobStatus('job-1', 'pending'),
        createMockJobStatus('job-2', 'running'),
      ];

      act(() => {
        result.current.setJobs(statuses);
      });

      expect(result.current.getJob('job-1')).toBeDefined();
      expect(result.current.getJob('job-2')).toBeDefined();
      expect(result.current.getJob('job-1')?.status.status).toBe('pending');
      expect(result.current.getJob('job-2')?.status.status).toBe('running');
    });

    it('should preserve existing events when updating jobs', () => {
      const { result } = renderHook(() => useJobsStore());
      const event = createMockProgressEvent();

      // Initial setup with event
      const status = createMockJobStatus('job-1', 'running');
      status.latest_event = event;

      act(() => {
        result.current.setJobs([status]);
      });

      expect(result.current.getJob('job-1')?.latestEvent).toEqual(event);

      // Update without event - should preserve
      const statusWithoutEvent = createMockJobStatus('job-1', 'completed');
      statusWithoutEvent.latest_event = null;

      act(() => {
        result.current.setJobs([statusWithoutEvent]);
      });

      expect(result.current.getJob('job-1')?.latestEvent).toEqual(event);
    });
  });

  describe('updateJob', () => {
    it('should update specific job fields', () => {
      const { result } = renderHook(() => useJobsStore());

      act(() => {
        result.current.setJobs([createMockJobStatus('job-1', 'pending')]);
      });

      const newStatus = createMockJobStatus('job-1', 'running');

      act(() => {
        result.current.updateJob('job-1', { status: newStatus });
      });

      expect(result.current.getJob('job-1')?.status.status).toBe('running');
    });

    it('should not error when updating non-existent job', () => {
      const { result } = renderHook(() => useJobsStore());

      act(() => {
        result.current.updateJob('non-existent', {
          status: createMockJobStatus('non-existent'),
        });
      });

      expect(result.current.getJob('non-existent')).toBeUndefined();
    });
  });

  describe('removeJob', () => {
    it('should remove job and loading states', () => {
      const { result } = renderHook(() => useJobsStore());

      act(() => {
        result.current.setJobs([createMockJobStatus('job-1')]);
        result.current.setLoading('job-1', 'isReloading', true);
      });

      expect(result.current.getJob('job-1')).toBeDefined();

      act(() => {
        result.current.removeJob('job-1');
      });

      expect(result.current.getJob('job-1')).toBeUndefined();
      expect(result.current.getJobWithLoading('job-1')).toBeUndefined();
    });

    it('should clear activeJobId when removing active job', () => {
      const { result } = renderHook(() => useJobsStore());

      act(() => {
        result.current.setJobs([createMockJobStatus('job-1')]);
        result.current.setActiveJob('job-1');
      });

      expect(result.current.activeJobId).toBe('job-1');

      act(() => {
        result.current.removeJob('job-1');
      });

      expect(result.current.activeJobId).toBeNull();
    });
  });

  describe('handleProgressEvent', () => {
    it('should update job with new event', () => {
      const { result } = renderHook(() => useJobsStore());
      const event = createMockProgressEvent('translation:progress');

      act(() => {
        result.current.setJobs([createMockJobStatus('job-1', 'running')]);
      });

      act(() => {
        result.current.handleProgressEvent('job-1', event);
      });

      expect(result.current.getJob('job-1')?.latestEvent).toEqual(event);
    });

    it('should categorize events by stage', () => {
      const { result } = renderHook(() => useJobsStore());
      const translationEvent = createMockProgressEvent('translation:progress');
      const mediaEvent = createMockProgressEvent('media:audio_generated');

      act(() => {
        result.current.setJobs([createMockJobStatus('job-1', 'running')]);
      });

      act(() => {
        result.current.handleProgressEvent('job-1', translationEvent);
      });

      expect(result.current.getJob('job-1')?.latestTranslationEvent).toEqual(
        translationEvent
      );

      act(() => {
        result.current.handleProgressEvent('job-1', mediaEvent);
      });

      expect(result.current.getJob('job-1')?.latestMediaEvent).toEqual(mediaEvent);
    });
  });

  describe('setLoading', () => {
    it('should track loading states separately', () => {
      const { result } = renderHook(() => useJobsStore());

      act(() => {
        result.current.setJobs([createMockJobStatus('job-1')]);
        result.current.setLoading('job-1', 'isReloading', true);
      });

      const jobWithLoading = result.current.getJobWithLoading('job-1');
      expect(jobWithLoading?.isReloading).toBe(true);
      expect(jobWithLoading?.isMutating).toBe(false);

      act(() => {
        result.current.setLoading('job-1', 'isMutating', true);
      });

      const updated = result.current.getJobWithLoading('job-1');
      expect(updated?.isReloading).toBe(true);
      expect(updated?.isMutating).toBe(true);
    });
  });

  describe('refreshJobs', () => {
    it('should fetch and update jobs', async () => {
      const statuses = [createMockJobStatus('job-1'), createMockJobStatus('job-2')];
      fetchJobsMock.mockResolvedValue(statuses);

      const { result } = renderHook(() => useJobsStore());

      await act(async () => {
        await result.current.refreshJobs();
      });

      expect(fetchJobsMock).toHaveBeenCalledTimes(1);
      expect(result.current.getAllJobs()).toHaveLength(2);
    });

    it('should deduplicate concurrent refresh requests', async () => {
      fetchJobsMock.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve([]), 100))
      );

      const { result } = renderHook(() => useJobsStore());

      // Fire multiple refresh requests simultaneously
      await act(async () => {
        await Promise.all([
          result.current.refreshJobs(),
          result.current.refreshJobs(),
          result.current.refreshJobs(),
        ]);
      });

      // Should only call API once due to deduplication
      expect(fetchJobsMock).toHaveBeenCalledTimes(1);
    });
  });

  describe('performJobAction', () => {
    it('should pause job successfully', async () => {
      const { result } = renderHook(() => useJobsStore());
      const pausedStatus = createMockJobStatus('job-1', 'paused');
      pauseJobMock.mockResolvedValue({ job: pausedStatus });
      fetchJobsMock.mockResolvedValue([pausedStatus]);

      act(() => {
        result.current.setJobs([createMockJobStatus('job-1', 'running')]);
      });

      await act(async () => {
        await result.current.performJobAction('job-1', 'pause');
      });

      expect(pauseJobMock).toHaveBeenCalledWith('job-1');
      expect(result.current.getJob('job-1')?.status.status).toBe('paused');
    });

    it('should delete job and remove from store', async () => {
      const { result } = renderHook(() => useJobsStore());
      deleteJobMock.mockResolvedValue({});

      act(() => {
        result.current.setJobs([createMockJobStatus('job-1')]);
      });

      expect(result.current.getJob('job-1')).toBeDefined();

      await act(async () => {
        await result.current.performJobAction('job-1', 'delete');
      });

      expect(deleteJobMock).toHaveBeenCalledWith('job-1');
      expect(result.current.getJob('job-1')).toBeUndefined();
    });

    it('should set and clear mutating flag', async () => {
      const { result } = renderHook(() => useJobsStore());
      const resumedStatus = createMockJobStatus('job-1', 'running');
      resumeJobMock.mockResolvedValue({ job: resumedStatus });
      fetchJobsMock.mockResolvedValue([resumedStatus]);

      act(() => {
        result.current.setJobs([createMockJobStatus('job-1', 'paused')]);
      });

      let isMutatingDuringCall = false;

      // Intercept the resume call to check loading state
      resumeJobMock.mockImplementation(async () => {
        isMutatingDuringCall =
          result.current.getJobWithLoading('job-1')?.isMutating ?? false;
        return { job: resumedStatus };
      });

      await act(async () => {
        await result.current.performJobAction('job-1', 'resume');
      });

      expect(isMutatingDuringCall).toBe(true);
      expect(result.current.getJobWithLoading('job-1')?.isMutating).toBe(false);
    });
  });

  describe('reloadJob', () => {
    it('should fetch fresh metadata for specific job', async () => {
      const { result } = renderHook(() => useJobsStore());
      const refreshedStatus = createMockJobStatus('job-1', 'completed');
      refreshPipelineMetadataMock.mockResolvedValue(refreshedStatus);

      act(() => {
        result.current.setJobs([createMockJobStatus('job-1', 'running')]);
      });

      await act(async () => {
        await result.current.reloadJob('job-1');
      });

      expect(refreshPipelineMetadataMock).toHaveBeenCalledWith('job-1');
      expect(result.current.getJob('job-1')?.status.status).toBe('completed');
    });
  });

  describe('selectors', () => {
    it('should return all jobs', () => {
      const { result } = renderHook(() => useJobsStore());

      act(() => {
        result.current.setJobs([
          createMockJobStatus('job-1'),
          createMockJobStatus('job-2'),
          createMockJobStatus('job-3'),
        ]);
      });

      expect(result.current.getAllJobs()).toHaveLength(3);
    });

    it('should return all job IDs', () => {
      const { result } = renderHook(() => useJobsStore());

      act(() => {
        result.current.setJobs([
          createMockJobStatus('job-1'),
          createMockJobStatus('job-2'),
        ]);
      });

      const ids = result.current.getJobIds();
      expect(ids).toContain('job-1');
      expect(ids).toContain('job-2');
      expect(ids).toHaveLength(2);
    });
  });
});
