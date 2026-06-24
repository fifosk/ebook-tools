import { useCallback, useState } from 'react';
import type { BookCreationOptionsResponse } from '../../api/createBook';
import {
  DEFAULT_ASS_EMPHASIS,
  DEFAULT_ASS_FONT_SIZE,
  DEFAULT_BATCH_SIZE,
  DEFAULT_LLM_MODEL,
  DEFAULT_START_TIME,
  DEFAULT_TRANSLATION_BATCH_SIZE,
  DEFAULT_WORKER_COUNT
} from './subtitleToolConfig';
import type { SubtitleOutputFormat } from './subtitleToolTypes';

export function useSubtitleProcessingOptions() {
  const [enableTransliteration, setEnableTransliteration] = useState<boolean>(true);
  const [enableHighlight, setEnableHighlight] = useState<boolean>(true);
  const [generateAudioBook, setGenerateAudioBook] = useState<boolean>(true);
  const [outputFormat, setOutputFormat] = useState<SubtitleOutputFormat>('ass');
  const [assFontSize, setAssFontSize] = useState<number | ''>(DEFAULT_ASS_FONT_SIZE);
  const [assEmphasis, setAssEmphasis] = useState<number | ''>(DEFAULT_ASS_EMPHASIS);
  const [mirrorToSourceDir, setMirrorToSourceDir] = useState<boolean>(true);
  const [workerCount, setWorkerCount] = useState<number | ''>(DEFAULT_WORKER_COUNT);
  const [batchSize, setBatchSize] = useState<number | ''>(DEFAULT_BATCH_SIZE);
  const [translationBatchSize, setTranslationBatchSize] = useState<number | ''>(
    DEFAULT_TRANSLATION_BATCH_SIZE
  );
  const [startTime, setStartTime] = useState<string>(DEFAULT_START_TIME);
  const [endTime, setEndTime] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState<string>(DEFAULT_LLM_MODEL);
  const [transliterationModel, setTransliterationModel] = useState<string>('');
  const [translationProvider, setTranslationProvider] = useState<string>('llm');
  const [transliterationMode, setTransliterationMode] = useState<string>('default');
  const applySubtitleDefaults = useCallback((defaults: BookCreationOptionsResponse['subtitle_defaults']) => {
    if (!defaults) {
      return;
    }
    setWorkerCount((current) => (current === DEFAULT_WORKER_COUNT ? defaults.worker_count : current));
    setBatchSize((current) => (current === DEFAULT_BATCH_SIZE ? defaults.batch_size : current));
    setTranslationBatchSize((current) =>
      current === DEFAULT_TRANSLATION_BATCH_SIZE ? defaults.translation_batch_size : current
    );
    setAssFontSize((current) => (current === DEFAULT_ASS_FONT_SIZE ? defaults.ass_font_size : current));
    setAssEmphasis((current) =>
      current === DEFAULT_ASS_EMPHASIS ? defaults.ass_emphasis_scale : current
    );
  }, []);

  return {
    enableTransliteration,
    setEnableTransliteration,
    enableHighlight,
    setEnableHighlight,
    generateAudioBook,
    setGenerateAudioBook,
    outputFormat,
    setOutputFormat,
    assFontSize,
    setAssFontSize,
    assEmphasis,
    setAssEmphasis,
    mirrorToSourceDir,
    setMirrorToSourceDir,
    workerCount,
    setWorkerCount,
    batchSize,
    setBatchSize,
    translationBatchSize,
    setTranslationBatchSize,
    startTime,
    setStartTime,
    endTime,
    setEndTime,
    selectedModel,
    setSelectedModel,
    transliterationModel,
    setTransliterationModel,
    translationProvider,
    setTranslationProvider,
    transliterationMode,
    setTransliterationMode,
    applySubtitleDefaults
  };
}
