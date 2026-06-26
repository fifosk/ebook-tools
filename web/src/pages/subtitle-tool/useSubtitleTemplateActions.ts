import { useCallback, useState } from 'react';
import { saveCreationTemplate } from '../../api/client';
import {
  resolveSubtitleSubmitValues,
  type SubtitleSubmitInput
} from './subtitleSubmitUtils';
import { buildSubtitleTemplatePayload } from './subtitleTemplateUtils';

type UseSubtitleTemplateActionsOptions = Omit<SubtitleSubmitInput, 'hasUploadFile'> & {
  enableTransliteration: boolean;
  enableHighlight: boolean;
  showOriginal: boolean;
  generateAudioBook: boolean;
  mirrorToSourceDir: boolean;
  uploadFile: File | null;
  mediaMetadataDraft: Record<string, unknown> | null;
};

const DEFAULT_SUBTITLE_TEMPLATE_ERROR = 'Unable to save subtitle template.';

export function useSubtitleTemplateActions({
  inputLanguage,
  targetLanguage,
  isAssSelection,
  sourceMode,
  selectedSource,
  startTime,
  endTime,
  outputFormat,
  assFontSize,
  assEmphasis,
  selectedModel,
  translationProvider,
  transliterationMode,
  transliterationModel,
  workerCount,
  batchSize,
  translationBatchSize,
  enableTransliteration,
  enableHighlight,
  showOriginal,
  generateAudioBook,
  mirrorToSourceDir,
  uploadFile,
  mediaMetadataDraft
}: UseSubtitleTemplateActionsOptions) {
  const [templateStatus, setTemplateStatus] = useState<string | null>(null);
  const [templateError, setTemplateError] = useState<string | null>(null);
  const [isSavingTemplate, setIsSavingTemplate] = useState(false);

  const handleSaveTemplate = useCallback(async () => {
    const resolution = resolveSubtitleSubmitValues({
      inputLanguage,
      targetLanguage,
      isAssSelection,
      sourceMode,
      selectedSource,
      hasUploadFile: Boolean(uploadFile),
      startTime,
      endTime,
      outputFormat,
      assFontSize,
      assEmphasis,
      selectedModel,
      translationProvider,
      transliterationMode,
      transliterationModel,
      workerCount,
      batchSize,
      translationBatchSize
    });
    if (!resolution.ok) {
      setTemplateError(resolution.error);
      setTemplateStatus(null);
      return;
    }

    setIsSavingTemplate(true);
    setTemplateError(null);
    setTemplateStatus(null);
    try {
      const payload = buildSubtitleTemplatePayload({
        values: resolution.values,
        sourceMode,
        enableTransliteration,
        enableHighlight,
        showOriginal,
        generateAudioBook,
        outputFormat,
        mirrorToSourceDir,
        mediaMetadataDraft
      });
      const saved = await saveCreationTemplate(payload);
      setTemplateStatus(`Saved template "${saved.name}". Apple Create can apply it from Subtitles.`);
    } catch (error) {
      const message =
        error instanceof Error ? error.message || DEFAULT_SUBTITLE_TEMPLATE_ERROR : DEFAULT_SUBTITLE_TEMPLATE_ERROR;
      setTemplateError(message);
    } finally {
      setIsSavingTemplate(false);
    }
  }, [
    assEmphasis,
    assFontSize,
    batchSize,
    enableHighlight,
    enableTransliteration,
    endTime,
    generateAudioBook,
    inputLanguage,
    isAssSelection,
    mediaMetadataDraft,
    mirrorToSourceDir,
    outputFormat,
    selectedModel,
    selectedSource,
    showOriginal,
    sourceMode,
    startTime,
    targetLanguage,
    translationBatchSize,
    translationProvider,
    transliterationMode,
    transliterationModel,
    uploadFile,
    workerCount
  ]);

  return {
    templateStatus,
    setTemplateStatus,
    templateError,
    setTemplateError,
    isSavingTemplate,
    handleSaveTemplate
  };
}
