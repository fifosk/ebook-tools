import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchLlmModels } from '../../api/client';
import { useSubtitleModels } from '../subtitle-tool/useSubtitleModels';

vi.mock('../../api/client', () => ({
  fetchLlmModels: vi.fn()
}));

const mockFetchLlmModels = vi.mocked(fetchLlmModels);

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}

describe('useSubtitleModels', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loads available subtitle models', async () => {
    mockFetchLlmModels.mockResolvedValue(['llama3', 'qwen2']);

    const { result } = renderHook(() => useSubtitleModels());

    expect(result.current.modelsLoading).toBe(true);
    await waitFor(() => expect(result.current.modelsLoading).toBe(false));

    expect(mockFetchLlmModels).toHaveBeenCalledTimes(1);
    expect(result.current.availableModels).toEqual(['llama3', 'qwen2']);
    expect(result.current.modelsError).toBeNull();
  });

  it('normalizes null model responses to an empty model list', async () => {
    mockFetchLlmModels.mockResolvedValue(null as unknown as string[]);

    const { result } = renderHook(() => useSubtitleModels());

    await waitFor(() => expect(result.current.modelsLoading).toBe(false));

    expect(result.current.availableModels).toEqual([]);
    expect(result.current.modelsError).toBeNull();
  });

  it('reports fetch failures without leaking the exception into render state', async () => {
    mockFetchLlmModels.mockRejectedValue(new Error('models unavailable'));

    const { result } = renderHook(() => useSubtitleModels());

    await waitFor(() => expect(result.current.modelsLoading).toBe(false));

    expect(result.current.availableModels).toEqual([]);
    expect(result.current.modelsError).toBe('models unavailable');
    expect(console.warn).toHaveBeenCalledWith(
      'Unable to load available subtitle models',
      expect.any(Error)
    );
  });

  it('ignores late model responses after unmount', async () => {
    const pending = deferred<string[]>();
    mockFetchLlmModels.mockReturnValue(pending.promise);

    const { result, unmount } = renderHook(() => useSubtitleModels());
    expect(result.current.modelsLoading).toBe(true);

    unmount();
    pending.resolve(['late-model']);
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(result.current.availableModels).toEqual([]);
    expect(result.current.modelsLoading).toBe(true);
  });
});
