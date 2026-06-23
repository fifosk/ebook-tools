import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SHOW_ORIGINAL_STORAGE_KEY } from '../subtitle-tool/subtitleToolConfig';
import { useSubtitleShowOriginalPreference } from '../subtitle-tool/useSubtitleShowOriginalPreference';

const originalLocalStorage = window.localStorage;

function installLocalStorage(storage: Partial<Storage>) {
  const nextStorage = {
    clear: vi.fn(),
    getItem: vi.fn(() => null),
    key: vi.fn(() => null),
    removeItem: vi.fn(),
    setItem: vi.fn(),
    get length() {
      return 0;
    },
    ...storage
  } as Storage;
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: nextStorage
  });
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: nextStorage
  });
  return nextStorage;
}

describe('useSubtitleShowOriginalPreference', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: originalLocalStorage
    });
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      value: originalLocalStorage
    });
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: originalLocalStorage
    });
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      value: originalLocalStorage
    });
    window.localStorage.clear();
  });

  it('defaults to showing original subtitles when no preference is stored', () => {
    const { result } = renderHook(() => useSubtitleShowOriginalPreference());

    expect(result.current.showOriginal).toBe(true);
    expect(window.localStorage.getItem(SHOW_ORIGINAL_STORAGE_KEY)).toBe('true');
  });

  it('loads a stored false preference', () => {
    window.localStorage.setItem(SHOW_ORIGINAL_STORAGE_KEY, 'false');

    const { result } = renderHook(() => useSubtitleShowOriginalPreference());

    expect(result.current.showOriginal).toBe(false);
    expect(window.localStorage.getItem(SHOW_ORIGINAL_STORAGE_KEY)).toBe('false');
  });

  it('persists preference changes', () => {
    const { result } = renderHook(() => useSubtitleShowOriginalPreference());

    act(() => {
      result.current.setShowOriginal(false);
    });

    expect(result.current.showOriginal).toBe(false);
    expect(window.localStorage.getItem(SHOW_ORIGINAL_STORAGE_KEY)).toBe('false');
  });

  it('falls back to showing original subtitles when reading storage fails', () => {
    const storage = installLocalStorage({
      getItem: vi.fn(() => {
        throw new Error('storage unavailable');
      })
    });

    const { result } = renderHook(() => useSubtitleShowOriginalPreference());

    expect(result.current.showOriginal).toBe(true);
    expect(storage.getItem).toHaveBeenCalledWith(SHOW_ORIGINAL_STORAGE_KEY);
  });

  it('keeps state changes when writing storage fails', () => {
    installLocalStorage({
      setItem: vi.fn(() => {
        throw new Error('storage unavailable');
      })
    });

    const { result } = renderHook(() => useSubtitleShowOriginalPreference());

    act(() => {
      result.current.setShowOriginal(false);
    });

    expect(result.current.showOriginal).toBe(false);
  });
});
