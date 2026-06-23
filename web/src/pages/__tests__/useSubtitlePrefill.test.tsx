import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { JobParameterSnapshot } from '../../api/dtos';
import { useSubtitlePrefill } from '../subtitle-tool/useSubtitlePrefill';

function createSetters() {
  return {
    setTargetLanguage: vi.fn(),
    setPrimaryTargetLanguage: vi.fn(),
    setInputLanguage: vi.fn(),
    setEnableTransliteration: vi.fn(),
    setShowOriginal: vi.fn(),
    setWorkerCount: vi.fn(),
    setBatchSize: vi.fn(),
    setTranslationBatchSize: vi.fn(),
    setStartTime: vi.fn(),
    setEndTime: vi.fn(),
    setSelectedModel: vi.fn(),
    setTranslationProvider: vi.fn(),
    setTransliterationMode: vi.fn(),
    setTransliterationModel: vi.fn(),
    setSelectedSource: vi.fn()
  };
}

describe('useSubtitlePrefill', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not update form state when no prefill parameters are available', () => {
    const setters = createSetters();

    renderHook(() => useSubtitlePrefill({ prefillParameters: null, ...setters }));

    for (const setter of Object.values(setters)) {
      expect(setter).not.toHaveBeenCalled();
    }
  });

  it('applies all resolved subtitle prefill fields to the page setters', async () => {
    const setters = createSetters();
    const prefillParameters: JobParameterSnapshot = {
      target_languages: ['  French  ', 'German'],
      input_language: '  English ',
      enable_transliteration: false,
      show_original: false,
      worker_count: 4,
      batch_size: 20,
      translation_batch_size: 8,
      start_time_offset_seconds: 62,
      end_time_offset_seconds: 3723,
      llm_model: ' gpt-test ',
      translation_provider: ' llm ',
      transliteration_mode: ' custom ',
      transliteration_model: ' romanizer ',
      subtitle_path: ' /media/show.srt ',
      input_file: '/fallback/input.srt'
    };

    renderHook(() => useSubtitlePrefill({ prefillParameters, ...setters }));

    await waitFor(() => expect(setters.setTargetLanguage).toHaveBeenCalledWith('French'));
    expect(setters.setPrimaryTargetLanguage).toHaveBeenCalledWith('French');
    expect(setters.setInputLanguage).toHaveBeenCalledWith('English');
    expect(setters.setEnableTransliteration).toHaveBeenCalledWith(false);
    expect(setters.setShowOriginal).toHaveBeenCalledWith(false);
    expect(setters.setWorkerCount).toHaveBeenCalledWith(4);
    expect(setters.setBatchSize).toHaveBeenCalledWith(20);
    expect(setters.setTranslationBatchSize).toHaveBeenCalledWith(8);
    expect(setters.setStartTime).toHaveBeenCalledWith('01:02');
    expect(setters.setEndTime).toHaveBeenCalledWith('01:02:03');
    expect(setters.setSelectedModel).toHaveBeenCalledWith('gpt-test');
    expect(setters.setTranslationProvider).toHaveBeenCalledWith('llm');
    expect(setters.setTransliterationMode).toHaveBeenCalledWith('custom');
    expect(setters.setTransliterationModel).toHaveBeenCalledWith('romanizer');
    expect(setters.setSelectedSource).toHaveBeenCalledWith('/media/show.srt');
  });

  it('only updates fields present in partial prefill parameters', async () => {
    const setters = createSetters();

    renderHook(() =>
      useSubtitlePrefill({
        prefillParameters: {
          input_language: 'Japanese',
          input_file: '/media/fallback.srt'
        },
        ...setters
      })
    );

    await waitFor(() => expect(setters.setInputLanguage).toHaveBeenCalledWith('Japanese'));
    expect(setters.setSelectedSource).toHaveBeenCalledWith('/media/fallback.srt');
    expect(setters.setTargetLanguage).not.toHaveBeenCalled();
    expect(setters.setPrimaryTargetLanguage).not.toHaveBeenCalled();
    expect(setters.setShowOriginal).not.toHaveBeenCalled();
    expect(setters.setWorkerCount).not.toHaveBeenCalled();
    expect(setters.setSelectedModel).not.toHaveBeenCalled();
  });

  it('applies new prefill parameters after rerender', async () => {
    const setters = createSetters();
    const { rerender } = renderHook(
      ({ prefillParameters }) => useSubtitlePrefill({ prefillParameters, ...setters }),
      { initialProps: { prefillParameters: null as JobParameterSnapshot | null } }
    );

    rerender({ prefillParameters: { target_languages: ['German'] } });

    await waitFor(() => expect(setters.setTargetLanguage).toHaveBeenCalledWith('German'));
    expect(setters.setPrimaryTargetLanguage).toHaveBeenCalledWith('German');
  });
});
