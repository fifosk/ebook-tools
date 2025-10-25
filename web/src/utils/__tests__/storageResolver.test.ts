import { afterEach, describe, expect, it, vi } from 'vitest';
import { resolve } from '../storageResolver';

const originalStorageBase = (import.meta.env as Record<string, string | undefined>).VITE_STORAGE_BASE_URL;
const originalApiBase = (import.meta.env as Record<string, string | undefined>).VITE_API_BASE_URL;
const originalWindow = globalThis.window;

function setStorageBase(value: string | undefined): void {
  const env = import.meta.env as Record<string, string | undefined>;
  if (value === undefined) {
    delete env.VITE_STORAGE_BASE_URL;
  } else {
    env.VITE_STORAGE_BASE_URL = value;
  }
}

function setApiBase(value: string | undefined): void {
  const env = import.meta.env as Record<string, string | undefined>;
  if (value === undefined) {
    delete env.VITE_API_BASE_URL;
  } else {
    env.VITE_API_BASE_URL = value;
  }
}

afterEach(() => {
  setStorageBase(originalStorageBase);
  setApiBase(originalApiBase);
  if (globalThis.window !== originalWindow) {
    vi.stubGlobal('window', originalWindow as typeof globalThis.window);
  }
});

describe('storageResolver', () => {
  it('joins the storage base, job ID, and file name', () => {
    setStorageBase('https://storage.example');
    expect(resolve('job-123', 'output/book.epub')).toBe('https://storage.example/job-123/output/book.epub');
  });

  it('trims trailing slashes from the base URL', () => {
    setStorageBase('https://storage.example/');
    expect(resolve('job-123', 'cover.png')).toBe('https://storage.example/job-123/cover.png');
  });

  it('handles leading slashes on file names', () => {
    setStorageBase('https://storage.example');
    expect(resolve('job-123', '/nested/cover.png')).toBe('https://storage.example/job-123/nested/cover.png');
  });

  it('returns the base URL when the file name is empty', () => {
    setStorageBase('https://storage.example');
    expect(resolve('job-123', '')).toBe('https://storage.example/job-123');
  });

  it('falls back to the API base URL when the storage base is not set', () => {
    setStorageBase('');
    setApiBase('https://api.example');
    expect(resolve('job-123', 'output.epub')).toBe('https://api.example/job-123/output.epub');
  });

  it('throws when no storage base URL can be resolved', () => {
    setStorageBase('');
    setApiBase('');
    vi.stubGlobal('window', undefined as unknown as typeof globalThis.window);
    try {
      expect(() => resolve('job-123', 'cover.png')).toThrowError('VITE_STORAGE_BASE_URL is not configured.');
    } finally {
      vi.stubGlobal('window', originalWindow as typeof globalThis.window);
    }
  });
});
