import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchPipelineDefaults } from '../../api/client';
import { useVideoDubbingLanguageState } from '../video-dubbing/useVideoDubbingLanguageState';

vi.mock('../../api/client', () => ({
  fetchPipelineDefaults: vi.fn()
}));

const mockFetchPipelineDefaults = vi.mocked(fetchPipelineDefaults);

describe('useVideoDubbingLanguageState', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchPipelineDefaults.mockResolvedValue({ config: {} });
  });

  it('loads backend target languages and seeds the shared preference when empty', async () => {
    const setPrimaryTargetLanguage = vi.fn();
    mockFetchPipelineDefaults.mockResolvedValueOnce({
      config: {
        target_languages: [' Spanish ', 'Arabic', '', 42, 'Japanese']
      }
    });

    const { result } = renderHook(() =>
      useVideoDubbingLanguageState({
        primaryTargetLanguage: '',
        setPrimaryTargetLanguage,
        subtitleLanguageCode: null,
        subtitleLanguageLabel: null
      })
    );

    await waitFor(() => expect(setPrimaryTargetLanguage).toHaveBeenCalledWith('Spanish'));

    expect(result.current.sortedLanguageOptions).toEqual(
      expect.arrayContaining(['Arabic', 'Japanese', 'Spanish'])
    );
  });

  it('uses the subtitle language as the target fallback when no target is selected', async () => {
    const setPrimaryTargetLanguage = vi.fn();

    const { result } = renderHook(() =>
      useVideoDubbingLanguageState({
        primaryTargetLanguage: '',
        setPrimaryTargetLanguage,
        subtitleLanguageCode: 'es',
        subtitleLanguageLabel: 'Spanish'
      })
    );

    await waitFor(() => expect(result.current.targetLanguage).toBe('Spanish'));

    expect(setPrimaryTargetLanguage).toHaveBeenCalledWith('Spanish');
    expect(result.current.targetLanguageCode).toBe('es');
  });

  it('applies explicit target language changes to local and shared state', async () => {
    const setPrimaryTargetLanguage = vi.fn();

    const { result } = renderHook(() =>
      useVideoDubbingLanguageState({
        primaryTargetLanguage: 'Arabic',
        setPrimaryTargetLanguage,
        subtitleLanguageCode: 'en',
        subtitleLanguageLabel: 'English'
      })
    );

    act(() => {
      result.current.applyTargetLanguage('  Japanese  ');
    });

    expect(result.current.targetLanguage).toBe('Japanese');
    expect(result.current.targetLanguageCode).toBe('ja');
    expect(setPrimaryTargetLanguage).toHaveBeenCalledWith('Japanese');
  });

  it('resolves the subtitle language code when only a code is available', () => {
    const { result } = renderHook(() =>
      useVideoDubbingLanguageState({
        primaryTargetLanguage: '',
        setPrimaryTargetLanguage: vi.fn(),
        subtitleLanguageCode: 'fr',
        subtitleLanguageLabel: ''
      })
    );

    expect(result.current.targetLanguageCode).toBe('fr');
  });
});
