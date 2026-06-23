import { useEffect } from 'react';
import type { JobParameterSnapshot } from '../../api/dtos';
import { resolveSubtitlePrefillValues } from './subtitlePrefillUtils';

type Setter<T> = (value: T) => void;

type UseSubtitlePrefillOptions = {
  prefillParameters?: JobParameterSnapshot | null;
  setTargetLanguage: Setter<string>;
  setPrimaryTargetLanguage: Setter<string>;
  setInputLanguage: Setter<string>;
  setEnableTransliteration: Setter<boolean>;
  setShowOriginal: Setter<boolean>;
  setWorkerCount: Setter<number>;
  setBatchSize: Setter<number>;
  setTranslationBatchSize: Setter<number>;
  setStartTime: Setter<string>;
  setEndTime: Setter<string>;
  setSelectedModel: Setter<string>;
  setTranslationProvider: Setter<string>;
  setTransliterationMode: Setter<string>;
  setTransliterationModel: Setter<string>;
  setSelectedSource: Setter<string>;
};

export function useSubtitlePrefill({
  prefillParameters,
  setTargetLanguage,
  setPrimaryTargetLanguage,
  setInputLanguage,
  setEnableTransliteration,
  setShowOriginal,
  setWorkerCount,
  setBatchSize,
  setTranslationBatchSize,
  setStartTime,
  setEndTime,
  setSelectedModel,
  setTranslationProvider,
  setTransliterationMode,
  setTransliterationModel,
  setSelectedSource
}: UseSubtitlePrefillOptions) {
  useEffect(() => {
    if (!prefillParameters) {
      return;
    }
    const prefill = resolveSubtitlePrefillValues(prefillParameters);
    if (prefill.targetLanguage) {
      setTargetLanguage(prefill.targetLanguage);
      setPrimaryTargetLanguage(prefill.targetLanguage);
    }
    if (prefill.inputLanguage) {
      setInputLanguage(prefill.inputLanguage);
    }
    if (prefill.enableTransliteration !== null) {
      setEnableTransliteration(prefill.enableTransliteration);
    }
    if (prefill.showOriginal !== null) {
      setShowOriginal(prefill.showOriginal);
    }
    if (prefill.workerCount !== null) {
      setWorkerCount(prefill.workerCount);
    }
    if (prefill.batchSize !== null) {
      setBatchSize(prefill.batchSize);
    }
    if (prefill.translationBatchSize !== null) {
      setTranslationBatchSize(prefill.translationBatchSize);
    }
    if (prefill.startTime !== null) {
      setStartTime(prefill.startTime);
    }
    if (prefill.endTime !== null) {
      setEndTime(prefill.endTime);
    }
    if (prefill.selectedModel) {
      setSelectedModel(prefill.selectedModel);
    }
    if (prefill.translationProvider) {
      setTranslationProvider(prefill.translationProvider);
    }
    if (prefill.transliterationMode) {
      setTransliterationMode(prefill.transliterationMode);
    }
    if (prefill.transliterationModel) {
      setTransliterationModel(prefill.transliterationModel);
    }
    if (prefill.sourcePath) {
      setSelectedSource(prefill.sourcePath);
    }
  }, [
    prefillParameters,
    setBatchSize,
    setEnableTransliteration,
    setEndTime,
    setInputLanguage,
    setPrimaryTargetLanguage,
    setSelectedModel,
    setSelectedSource,
    setShowOriginal,
    setStartTime,
    setTargetLanguage,
    setTranslationBatchSize,
    setTranslationProvider,
    setTransliterationMode,
    setTransliterationModel,
    setWorkerCount
  ]);
}
