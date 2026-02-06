import { describe, expect, it } from 'vitest';
import { getBackoffMs, shouldRetry, type RetryState } from '../useChunkPrefetch';

describe('getBackoffMs', () => {
  it('returns 2000ms for 0 failures', () => {
    expect(getBackoffMs(0)).toBe(2000);
  });

  it('returns 4000ms for 1 failure', () => {
    expect(getBackoffMs(1)).toBe(4000);
  });

  it('returns 8000ms for 2 failures', () => {
    expect(getBackoffMs(2)).toBe(8000);
  });

  it('returns 16000ms for 3 failures', () => {
    expect(getBackoffMs(3)).toBe(16000);
  });

  it('caps at 16000ms for higher failure counts', () => {
    expect(getBackoffMs(4)).toBe(16000);
    expect(getBackoffMs(10)).toBe(16000);
  });
});

describe('shouldRetry', () => {
  it('returns true when no prior state exists', () => {
    expect(shouldRetry(undefined, Date.now())).toBe(true);
  });

  it('returns false when failures reach circuit breaker threshold (3)', () => {
    const state: RetryState = { lastAttempt: 0, failures: 3 };
    expect(shouldRetry(state, Date.now())).toBe(false);
  });

  it('returns false when failures exceed circuit breaker threshold', () => {
    const state: RetryState = { lastAttempt: 0, failures: 5 };
    expect(shouldRetry(state, Date.now())).toBe(false);
  });

  it('returns false when not enough time has passed for backoff', () => {
    const now = 10000;
    const state: RetryState = { lastAttempt: now - 1000, failures: 0 };
    // 0 failures => 2000ms backoff, only 1000ms elapsed
    expect(shouldRetry(state, now)).toBe(false);
  });

  it('returns true when backoff period has elapsed (0 failures)', () => {
    const now = 10000;
    const state: RetryState = { lastAttempt: now - 2001, failures: 0 };
    expect(shouldRetry(state, now)).toBe(true);
  });

  it('returns true when backoff period has elapsed (1 failure)', () => {
    const now = 10000;
    const state: RetryState = { lastAttempt: now - 4001, failures: 1 };
    expect(shouldRetry(state, now)).toBe(true);
  });

  it('returns false within backoff period (1 failure, 2s elapsed)', () => {
    const now = 10000;
    const state: RetryState = { lastAttempt: now - 2000, failures: 1 };
    // 1 failure => 4000ms backoff, only 2000ms elapsed
    expect(shouldRetry(state, now)).toBe(false);
  });

  it('returns true when backoff period has elapsed (2 failures)', () => {
    const now = 20000;
    const state: RetryState = { lastAttempt: now - 8001, failures: 2 };
    expect(shouldRetry(state, now)).toBe(true);
  });

  it('returns false within backoff period (2 failures, 4s elapsed)', () => {
    const now = 20000;
    const state: RetryState = { lastAttempt: now - 4000, failures: 2 };
    // 2 failures => 8000ms backoff, only 4000ms elapsed
    expect(shouldRetry(state, now)).toBe(false);
  });

  it('returns true at exact backoff boundary', () => {
    const now = 10000;
    const state: RetryState = { lastAttempt: now - 2000, failures: 0 };
    // 0 failures => 2000ms backoff, exactly 2000ms elapsed
    expect(shouldRetry(state, now)).toBe(true);
  });
});
