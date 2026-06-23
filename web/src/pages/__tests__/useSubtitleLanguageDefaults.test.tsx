import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchPipelineDefaults } from '../../api/client';
import { useSubtitleLanguageDefaults } from '../subtitle-tool/useSubtitleLanguageDefaults';

vi.mock('../../api/client', () => ({
  fetchPipelineDefaults: vi.fn()
}));

const mockFetchPipelineDefaults = vi.mocked(fetchPipelineDefaults);

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });
  return { promise, resolve, reject };
}

describe('useSubtitleLanguageDefaults', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loads and normalizes target languages from pipeline defaults', async () => {
    const setInputLanguage = vi.fn();
    mockFetchPipelineDefaults.mockResolvedValue({
      config: {
        target_languages: [' french ', 'German', '', 42],
        input_language: 'English'
      }
    });

    const { result } = renderHook(() =>
      useSubtitleLanguageDefaults({ inputLanguage: 'Spanish', setInputLanguage })
    );

    await waitFor(() => expect(result.current.fetchedLanguages).toEqual(['french', 'German']));

    expect(mockFetchPipelineDefaults).toHaveBeenCalledTimes(1);
    expect(setInputLanguage).not.toHaveBeenCalled();
  });

  it('applies the default input language when there is no current input language', async () => {
    const setInputLanguage = vi.fn();
    mockFetchPipelineDefaults.mockResolvedValue({
      config: {
        target_languages: ['French'],
        input_language: ' english '
      }
    });

    renderHook(() => useSubtitleLanguageDefaults({ inputLanguage: '', setInputLanguage }));

    await waitFor(() => expect(setInputLanguage).toHaveBeenCalledWith('english'));
  });

  it('reports pipeline default failures without changing language state', async () => {
    const setInputLanguage = vi.fn();
    mockFetchPipelineDefaults.mockRejectedValue(new Error('defaults unavailable'));

    const { result } = renderHook(() =>
      useSubtitleLanguageDefaults({ inputLanguage: 'English', setInputLanguage })
    );

    await waitFor(() =>
      expect(console.warn).toHaveBeenCalledWith(
        'Unable to load pipeline defaults for language list',
        expect.any(Error)
      )
    );

    expect(result.current.fetchedLanguages).toEqual([]);
    expect(setInputLanguage).not.toHaveBeenCalled();
  });

  it('ignores late default responses after unmount', async () => {
    const setInputLanguage = vi.fn();
    const pending = deferred<Awaited<ReturnType<typeof fetchPipelineDefaults>>>();
    mockFetchPipelineDefaults.mockReturnValue(pending.promise);

    const { result, unmount } = renderHook(() =>
      useSubtitleLanguageDefaults({ inputLanguage: '', setInputLanguage })
    );

    unmount();
    await act(async () => {
      pending.resolve({
        config: {
          target_languages: ['French'],
          input_language: 'English'
        }
      });
    });

    expect(result.current.fetchedLanguages).toEqual([]);
    expect(setInputLanguage).not.toHaveBeenCalled();
  });

  it('keeps the latest defaults when an older request resolves last', async () => {
    const setInputLanguage = vi.fn();
    const first = deferred<Awaited<ReturnType<typeof fetchPipelineDefaults>>>();
    const second = deferred<Awaited<ReturnType<typeof fetchPipelineDefaults>>>();
    mockFetchPipelineDefaults
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);

    const { result, rerender } = renderHook(
      ({ inputLanguage }) => useSubtitleLanguageDefaults({ inputLanguage, setInputLanguage }),
      { initialProps: { inputLanguage: 'English' } }
    );
    rerender({ inputLanguage: 'Spanish' });

    await act(async () => {
      second.resolve({ config: { target_languages: ['German'] } });
    });
    await waitFor(() => expect(result.current.fetchedLanguages).toEqual(['German']));

    await act(async () => {
      first.resolve({ config: { target_languages: ['French'] } });
    });

    expect(result.current.fetchedLanguages).toEqual(['German']);
  });
});
