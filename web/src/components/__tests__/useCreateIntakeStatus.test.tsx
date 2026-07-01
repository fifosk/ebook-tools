import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchPipelineIntakeStatus } from '../../api/client';
import type { PipelineIntakeStatusResponse } from '../../api/dtos';
import { useCreateIntakeStatus } from '../create-intake/useCreateIntakeStatus';

vi.mock('../../api/client', () => ({
  fetchPipelineIntakeStatus: vi.fn(),
}));

const mockFetchPipelineIntakeStatus = vi.mocked(fetchPipelineIntakeStatus);

function makeStatus(overrides: Partial<PipelineIntakeStatusResponse>): PipelineIntakeStatusResponse {
  return {
    acceptingJobs: true,
    isUnderPressure: false,
    queueDepth: 0,
    activeCount: 0,
    softLimit: 3,
    hardLimit: 6,
    delayCount: 0,
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}

describe('useCreateIntakeStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('keeps the newest intake refresh when an earlier request settles late', async () => {
    const initialRequest = deferred<PipelineIntakeStatusResponse | null>();
    const refreshRequest = deferred<PipelineIntakeStatusResponse | null>();
    mockFetchPipelineIntakeStatus
      .mockReturnValueOnce(initialRequest.promise)
      .mockReturnValueOnce(refreshRequest.promise);

    const { result } = renderHook(() => useCreateIntakeStatus());

    expect(result.current.isLoadingIntakeStatus).toBe(true);
    await act(async () => {
      void result.current.refreshIntakeStatus();
    });

    await act(async () => {
      refreshRequest.resolve(makeStatus({ acceptingJobs: true, queueDepth: 1 }));
      await refreshRequest.promise;
    });

    await waitFor(() => expect(result.current.isLoadingIntakeStatus).toBe(false));
    expect(result.current.intakeStatus?.queueDepth).toBe(1);
    expect(result.current.isIntakeAtCapacity).toBe(false);

    await act(async () => {
      initialRequest.resolve(makeStatus({ acceptingJobs: false, queueDepth: 6 }));
      await initialRequest.promise;
    });

    expect(result.current.intakeStatus?.queueDepth).toBe(1);
    expect(result.current.isIntakeAtCapacity).toBe(false);
  });
});
