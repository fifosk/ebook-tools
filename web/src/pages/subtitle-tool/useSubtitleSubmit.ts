import { useCallback } from 'react';
import type { FormEvent } from 'react';
import { submitSubtitleJob } from '../../api/client';
import type { SubtitleToolTab } from './subtitleToolTypes';
import {
  buildSubtitleSubmitFormData,
  resolveSubtitleSubmitValues,
  type SubtitleSubmitInput
} from './subtitleToolUtils';
import type { RecordSubtitleSubmitInput } from './useSubtitleSubmitFeedback';

type UseSubtitleSubmitOptions = Omit<SubtitleSubmitInput, 'hasUploadFile'> & {
  enableTransliteration: boolean;
  enableHighlight: boolean;
  showOriginal: boolean;
  generateAudioBook: boolean;
  mirrorToSourceDir: boolean;
  uploadFile: File | null;
  mediaMetadataDraft: Record<string, unknown> | null;
  isIntakeAtCapacity: boolean;
  setSubmitError: (message: string | null) => void;
  beginSubmit: () => void;
  finishSubmit: () => void;
  rejectAtCapacity: () => void;
  failSubmit: (error: unknown) => void;
  recordSubmission: (input: RecordSubtitleSubmitInput) => void;
  setStartTime: (value: string) => void;
  setEndTime: (value: string) => void;
  setAssFontSize: (value: number) => void;
  setAssEmphasis: (value: number) => void;
  setActiveTab: (tab: SubtitleToolTab) => void;
  onJobCreated: (jobId: string) => void;
  clearUploadFile: () => void;
  refreshIntakeStatus: () => Promise<void>;
};

export function useSubtitleSubmit({
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
  mediaMetadataDraft,
  isIntakeAtCapacity,
  setSubmitError,
  beginSubmit,
  finishSubmit,
  rejectAtCapacity,
  failSubmit,
  recordSubmission,
  setStartTime,
  setEndTime,
  setAssFontSize,
  setAssEmphasis,
  setActiveTab,
  onJobCreated,
  clearUploadFile,
  refreshIntakeStatus
}: UseSubtitleSubmitOptions) {
  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setSubmitError(null);
      if (isIntakeAtCapacity) {
        rejectAtCapacity();
        return;
      }

      const submitResolution = resolveSubtitleSubmitValues({
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
      if (!submitResolution.ok) {
        setSubmitError(submitResolution.error);
        return;
      }
      const {
        normalizedStartTime,
        normalizedEndTime,
        resolvedAssFontSize,
        resolvedAssEmphasis
      } = submitResolution.values;

      const formData = buildSubtitleSubmitFormData({
        values: submitResolution.values,
        enableTransliteration,
        enableHighlight,
        showOriginal,
        generateAudioBook,
        outputFormat,
        mirrorToSourceDir,
        uploadFile,
        mediaMetadataDraft
      });

      beginSubmit();
      try {
        const response = await submitSubtitleJob(formData);
        recordSubmission({
          response,
          values: submitResolution.values,
          workerCount,
          batchSize,
          translationBatchSize,
          outputFormat
        });
        if (normalizedStartTime !== startTime) {
          setStartTime(normalizedStartTime);
        }
        if (normalizedEndTime !== endTime) {
          setEndTime(normalizedEndTime);
        }
        if (resolvedAssFontSize !== null && assFontSize !== resolvedAssFontSize) {
          setAssFontSize(resolvedAssFontSize);
        }
        if (resolvedAssEmphasis !== null && assEmphasis !== resolvedAssEmphasis) {
          setAssEmphasis(resolvedAssEmphasis);
        }
        onJobCreated(response.job_id);
        setActiveTab('jobs');
        if (sourceMode === 'upload') {
          clearUploadFile();
        }
        await refreshIntakeStatus();
      } catch (error) {
        failSubmit(error);
      } finally {
        finishSubmit();
      }
    },
    [
      assEmphasis,
      assFontSize,
      batchSize,
      beginSubmit,
      clearUploadFile,
      enableHighlight,
      enableTransliteration,
      endTime,
      failSubmit,
      finishSubmit,
      generateAudioBook,
      inputLanguage,
      isAssSelection,
      isIntakeAtCapacity,
      mediaMetadataDraft,
      mirrorToSourceDir,
      onJobCreated,
      outputFormat,
      recordSubmission,
      refreshIntakeStatus,
      rejectAtCapacity,
      selectedModel,
      selectedSource,
      setActiveTab,
      setAssEmphasis,
      setAssFontSize,
      setEndTime,
      setStartTime,
      setSubmitError,
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
    ]
  );

  return { handleSubmit };
}
