import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import {
  DEFAULT_ASS_EMPHASIS,
  DEFAULT_ASS_FONT_SIZE,
  DEFAULT_BATCH_SIZE,
  DEFAULT_LLM_MODEL,
  DEFAULT_START_TIME,
  DEFAULT_TRANSLATION_BATCH_SIZE,
  DEFAULT_WORKER_COUNT
} from '../subtitle-tool/subtitleToolConfig';
import { useSubtitleProcessingOptions } from '../subtitle-tool/useSubtitleProcessingOptions';

describe('useSubtitleProcessingOptions', () => {
  it('starts with the Subtitle Tool defaults used by the Web form', () => {
    const { result } = renderHook(() => useSubtitleProcessingOptions());

    expect(result.current.enableTransliteration).toBe(true);
    expect(result.current.enableHighlight).toBe(true);
    expect(result.current.generateAudioBook).toBe(true);
    expect(result.current.outputFormat).toBe('ass');
    expect(result.current.assFontSize).toBe(DEFAULT_ASS_FONT_SIZE);
    expect(result.current.assEmphasis).toBe(DEFAULT_ASS_EMPHASIS);
    expect(result.current.mirrorToSourceDir).toBe(true);
    expect(result.current.workerCount).toBe(DEFAULT_WORKER_COUNT);
    expect(result.current.batchSize).toBe(DEFAULT_BATCH_SIZE);
    expect(result.current.translationBatchSize).toBe(DEFAULT_TRANSLATION_BATCH_SIZE);
    expect(result.current.startTime).toBe(DEFAULT_START_TIME);
    expect(result.current.endTime).toBe('');
    expect(result.current.selectedModel).toBe(DEFAULT_LLM_MODEL);
    expect(result.current.transliterationModel).toBe('');
    expect(result.current.translationProvider).toBe('llm');
    expect(result.current.transliterationMode).toBe('default');
  });

  it('exposes setters used by prefill, submit normalization, and option panels', () => {
    const { result } = renderHook(() => useSubtitleProcessingOptions());

    act(() => {
      result.current.setEnableTransliteration(false);
      result.current.setEnableHighlight(false);
      result.current.setGenerateAudioBook(false);
      result.current.setOutputFormat('srt');
      result.current.setAssFontSize(44);
      result.current.setAssEmphasis(1.4);
      result.current.setMirrorToSourceDir(false);
      result.current.setWorkerCount(3);
      result.current.setBatchSize(9);
      result.current.setTranslationBatchSize(5);
      result.current.setStartTime('00:12');
      result.current.setEndTime('+01:20');
      result.current.setSelectedModel('gpt-5');
      result.current.setTransliterationModel('gpt-5-mini');
      result.current.setTranslationProvider('deepl');
      result.current.setTransliterationMode('strict');
    });

    expect(result.current.enableTransliteration).toBe(false);
    expect(result.current.enableHighlight).toBe(false);
    expect(result.current.generateAudioBook).toBe(false);
    expect(result.current.outputFormat).toBe('srt');
    expect(result.current.assFontSize).toBe(44);
    expect(result.current.assEmphasis).toBe(1.4);
    expect(result.current.mirrorToSourceDir).toBe(false);
    expect(result.current.workerCount).toBe(3);
    expect(result.current.batchSize).toBe(9);
    expect(result.current.translationBatchSize).toBe(5);
    expect(result.current.startTime).toBe('00:12');
    expect(result.current.endTime).toBe('+01:20');
    expect(result.current.selectedModel).toBe('gpt-5');
    expect(result.current.transliterationModel).toBe('gpt-5-mini');
    expect(result.current.translationProvider).toBe('deepl');
    expect(result.current.transliterationMode).toBe('strict');
  });
});
