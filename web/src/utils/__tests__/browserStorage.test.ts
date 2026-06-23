import { describe, expect, it } from 'vitest';
import {
  getStorageItem,
  isBrowserStorage,
  removeStorageItem,
  setStorageItem,
  type BrowserStorage,
} from '../browserStorage';

describe('browserStorage', () => {
  it('rejects partial storage-like objects', () => {
    expect(isBrowserStorage({})).toBe(false);
    expect(isBrowserStorage({ getItem: () => null, setItem: () => undefined })).toBe(false);
  });

  it('returns null instead of throwing for unavailable reads', () => {
    const brokenStorage = {
      getItem: () => {
        throw new Error('disabled');
      },
      setItem: () => undefined,
      removeItem: () => undefined,
    } satisfies BrowserStorage;

    expect(getStorageItem(brokenStorage, 'key')).toBeNull();
  });

  it('ignores disabled writes and removals', () => {
    const brokenStorage = {
      getItem: () => null,
      setItem: () => {
        throw new Error('quota');
      },
      removeItem: () => {
        throw new Error('disabled');
      },
    } satisfies BrowserStorage;

    expect(() => setStorageItem(brokenStorage, 'key', 'value')).not.toThrow();
    expect(() => removeStorageItem(brokenStorage, 'key')).not.toThrow();
  });
});

