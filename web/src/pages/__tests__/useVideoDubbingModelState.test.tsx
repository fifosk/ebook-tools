import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchSubtitleModels } from '../../api/client';
import { DEFAULT_LLM_MODEL } from '../video-dubbing/videoDubbingConfig';
import { useVideoDubbingModelState } from '../video-dubbing/useVideoDubbingModelState';

vi.mock('../../api/client', () => ({
  fetchSubtitleModels: vi.fn()
}));

const mockFetchSubtitleModels = vi.mocked(fetchSubtitleModels);

describe('useVideoDubbingModelState', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchSubtitleModels.mockResolvedValue([]);
  });

  it('loads available subtitle models while keeping the default selected model', async () => {
    mockFetchSubtitleModels.mockResolvedValueOnce([
      'ollama_cloud:fast',
      DEFAULT_LLM_MODEL,
      'lmstudio_local:custom'
    ]);

    const { result } = renderHook(() => useVideoDubbingModelState());

    await waitFor(() => expect(result.current.isLoadingModels).toBe(false));

    expect(mockFetchSubtitleModels).toHaveBeenCalledTimes(1);
    expect(result.current.modelError).toBeNull();
    expect(result.current.llmModels).toEqual([
      'ollama_cloud:fast',
      DEFAULT_LLM_MODEL,
      'lmstudio_local:custom'
    ]);
    expect(result.current.llmModel).toBe(DEFAULT_LLM_MODEL);
  });

  it('surfaces model loading failures without clearing the selected default', async () => {
    mockFetchSubtitleModels.mockRejectedValueOnce(new Error('models offline'));

    const { result } = renderHook(() => useVideoDubbingModelState());

    await waitFor(() => expect(result.current.modelError).toBe('models offline'));

    expect(result.current.isLoadingModels).toBe(false);
    expect(result.current.llmModels).toEqual([]);
    expect(result.current.llmModel).toBe(DEFAULT_LLM_MODEL);
  });

  it('updates selected provider and transliteration state for prefill and form changes', async () => {
    const { result } = renderHook(() => useVideoDubbingModelState());

    await waitFor(() => expect(result.current.isLoadingModels).toBe(false));

    act(() => {
      result.current.setLlmModel('lmstudio_local:reasoner');
      result.current.setTransliterationModel('ollama_cloud:translit');
      result.current.setTranslationProvider('googletrans');
      result.current.setTransliterationMode('python');
    });

    expect(result.current.llmModel).toBe('lmstudio_local:reasoner');
    expect(result.current.transliterationModel).toBe('ollama_cloud:translit');
    expect(result.current.translationProvider).toBe('googletrans');
    expect(result.current.transliterationMode).toBe('python');
  });
});
