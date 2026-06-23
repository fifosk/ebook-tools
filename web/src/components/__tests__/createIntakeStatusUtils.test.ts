import { describe, expect, it } from 'vitest';
import type { PipelineIntakeStatusResponse } from '../../api/dtos';
import { resolvePipelineIntakeStatusPresentation } from '../create-intake/createIntakeStatusUtils';

function makeIntakeStatus(
  overrides: Partial<PipelineIntakeStatusResponse> = {},
): PipelineIntakeStatusResponse {
  return {
    acceptingJobs: true,
    isUnderPressure: false,
    queueDepth: 1,
    activeCount: 2,
    softLimit: 3,
    hardLimit: 6,
    delayCount: 0,
    ...overrides,
  };
}

describe('createIntakeStatusUtils', () => {
  it('formats intake loading, limit, and delay details', () => {
    expect(resolvePipelineIntakeStatusPresentation(null, true)).toEqual({
      message: 'Checking job intake...',
      detailLines: [],
      tone: 'info',
      role: 'status',
    });

    expect(
      resolvePipelineIntakeStatusPresentation(makeIntakeStatus({ delayCount: 4 }), false),
    ).toEqual({
      message: 'Job intake is available: 1 pending and 2 running.',
      detailLines: ['Delayed jobs: 4', 'Slowdown starts at 3 pending', 'Capacity limit is 6 pending'],
      tone: 'success',
      role: 'status',
    });

    expect(
      resolvePipelineIntakeStatusPresentation(
        makeIntakeStatus({
          acceptingJobs: false,
          queueDepth: 6,
          delayCount: 2,
        }),
        false,
      ),
    ).toMatchObject({
      message: 'Job queue is at capacity: 6 pending of 6. New submissions are paused until pending jobs clear.',
      detailLines: ['Delayed jobs: 2', 'Slowdown starts at 3 pending', 'Capacity limit is 6 pending'],
      tone: 'warning',
      role: 'alert',
    });
  });
});
