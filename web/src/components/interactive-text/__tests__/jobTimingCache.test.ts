import { afterEach, describe, expect, it, vi } from 'vitest';
import type { JobTimingResponse } from '../../../api/dtos';
import { clearCachedJobTiming, loadCachedJobTiming } from '../jobTimingCache';

function timingResponse(jobId: string): JobTimingResponse {
  return {
    job_id: jobId,
    tracks: {},
    audio: {},
    highlighting_policy: null,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, resolve, reject };
}

describe('loadCachedJobTiming', () => {
  afterEach(() => {
    clearCachedJobTiming();
    vi.restoreAllMocks();
  });

  it('deduplicates concurrent timing loads for the same job', async () => {
    const pending = deferred<JobTimingResponse | null>();
    const fetcher = vi.fn<[string], Promise<JobTimingResponse | null>>().mockReturnValue(pending.promise);

    const first = loadCachedJobTiming('job-1', fetcher);
    const second = loadCachedJobTiming('job-1', fetcher);

    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher).toHaveBeenCalledWith('job-1');

    const response = timingResponse('job-1');
    pending.resolve(response);

    await expect(first).resolves.toBe(response);
    await expect(second).resolves.toBe(response);
  });

  it('reuses settled timing responses for later chunk swaps', async () => {
    const response = timingResponse('job-2');
    const fetcher = vi.fn<[string], Promise<JobTimingResponse | null>>().mockResolvedValue(response);

    await expect(loadCachedJobTiming('job-2', fetcher)).resolves.toBe(response);
    await expect(loadCachedJobTiming('job-2', fetcher)).resolves.toBe(response);

    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it('caches missing timing responses so legacy-free jobs do not refetch on every mount', async () => {
    const fetcher = vi.fn<[string], Promise<JobTimingResponse | null>>().mockResolvedValue(null);

    await expect(loadCachedJobTiming('job-without-timing', fetcher)).resolves.toBeNull();
    await expect(loadCachedJobTiming('job-without-timing', fetcher)).resolves.toBeNull();

    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it('evicts rejected loads so a later reader mount can retry', async () => {
    const response = timingResponse('job-3');
    const fetcher = vi
      .fn<[string], Promise<JobTimingResponse | null>>()
      .mockRejectedValueOnce(new Error('temporary timing outage'))
      .mockResolvedValueOnce(response);

    await expect(loadCachedJobTiming('job-3', fetcher)).rejects.toThrow('temporary timing outage');
    await expect(loadCachedJobTiming('job-3', fetcher)).resolves.toBe(response);

    expect(fetcher).toHaveBeenCalledTimes(2);
  });
});
