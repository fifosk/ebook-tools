import type { ReactNode } from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchPipelineDefaults } from '../../api/client';
import { LanguageProvider } from '../../context/LanguageProvider';
import { useSubtitleLanguageState } from '../subtitle-tool/useSubtitleLanguageState';

vi.mock('../../api/client', () => ({
  fetchPipelineDefaults: vi.fn()
}));

const mockFetchPipelineDefaults = vi.mocked(fetchPipelineDefaults);

function wrapper({ children }: { children: ReactNode }) {
  return <LanguageProvider>{children}</LanguageProvider>;
}

describe('useSubtitleLanguageState', () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.resetAllMocks();
    mockFetchPipelineDefaults.mockResolvedValue({ config: {} });
  });

  afterEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it('starts from shared language preferences and loads backend target languages into options', async () => {
    mockFetchPipelineDefaults.mockResolvedValue({
      config: {
        target_languages: ['German', 'Polish']
      }
    });

    const { result } = renderHook(() => useSubtitleLanguageState(), { wrapper });

    expect(result.current.inputLanguage).toBe('English');
    expect(result.current.targetLanguage).toBe('Arabic');

    await waitFor(() => expect(result.current.sortedLanguageOptions).toContain('German'));
    expect(result.current.sortedLanguageOptions).toContain('Polish');
  });

  it('normalizes target language edits and promotes them to the shared primary target', async () => {
    const { result } = renderHook(() => useSubtitleLanguageState(), { wrapper });

    act(() => {
      result.current.handleTargetLanguageChange('  Spanish  ');
    });

    await waitFor(() => expect(result.current.targetLanguage).toBe('Spanish'));
    expect(result.current.sortedLanguageOptions).toContain('Spanish');
  });

  it('normalizes input language edits and falls back to English for blank input', async () => {
    const { result } = renderHook(() => useSubtitleLanguageState(), { wrapper });

    act(() => {
      result.current.handleInputLanguageChange('  Japanese  ');
    });

    await waitFor(() => expect(result.current.inputLanguage).toBe('Japanese'));

    act(() => {
      result.current.handleInputLanguageChange('   ');
    });

    await waitFor(() => expect(result.current.inputLanguage).toBe('English'));
  });

  it('keeps the target language setter available for rerun prefill', async () => {
    const { result } = renderHook(() => useSubtitleLanguageState(), { wrapper });

    act(() => {
      result.current.setTargetLanguage('Italian');
      result.current.setPrimaryTargetLanguage('Italian');
    });

    await waitFor(() => expect(result.current.targetLanguage).toBe('Italian'));
    expect(result.current.sortedLanguageOptions).toContain('Italian');
  });
});
