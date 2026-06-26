import { useEffect, useRef, useState } from 'react';
import type { CreationTemplateEntry } from '../../api/dtos';
import { extractSubtitleTemplateFormState } from './subtitleTemplateUtils';
import type { SubtitleOutputFormat, SubtitleSourceMode } from './subtitleToolTypes';

type SetValue<T> = (value: T) => void;
type UpdateMetadataDraft = (updater: (draft: Record<string, unknown>) => void) => void;

type UseSubtitleCreationTemplateOptions = {
  creationTemplate: CreationTemplateEntry | null;
  metadataSourceName: string;
  updateMediaMetadataDraft: UpdateMetadataDraft;
  handleSourceModeChange: SetValue<SubtitleSourceMode>;
  setSelectedSource: SetValue<string>;
  setInputLanguage: SetValue<string>;
  setTargetLanguage: SetValue<string>;
  setPrimaryTargetLanguage: SetValue<string>;
  setEnableTransliteration: SetValue<boolean>;
  setEnableHighlight: SetValue<boolean>;
  setShowOriginal: SetValue<boolean>;
  setGenerateAudioBook: SetValue<boolean>;
  setOutputFormat: SetValue<SubtitleOutputFormat>;
  setMirrorToSourceDir: SetValue<boolean>;
  setStartTime: SetValue<string>;
  setEndTime: SetValue<string>;
  setSelectedModel: SetValue<string>;
  setTranslationProvider: SetValue<string>;
  setTransliterationMode: SetValue<string>;
  setTransliterationModel: SetValue<string>;
  setWorkerCount: SetValue<number | ''>;
  setBatchSize: SetValue<number | ''>;
  setTranslationBatchSize: SetValue<number | ''>;
  setAssFontSize: SetValue<number>;
  setAssEmphasis: SetValue<number>;
  setTemplateStatus: SetValue<string | null>;
  setTemplateError: SetValue<string | null>;
};

export function useSubtitleCreationTemplate({
  creationTemplate,
  metadataSourceName,
  updateMediaMetadataDraft,
  handleSourceModeChange,
  setSelectedSource,
  setInputLanguage,
  setTargetLanguage,
  setPrimaryTargetLanguage,
  setEnableTransliteration,
  setEnableHighlight,
  setShowOriginal,
  setGenerateAudioBook,
  setOutputFormat,
  setMirrorToSourceDir,
  setStartTime,
  setEndTime,
  setSelectedModel,
  setTranslationProvider,
  setTransliterationMode,
  setTransliterationModel,
  setWorkerCount,
  setBatchSize,
  setTranslationBatchSize,
  setAssFontSize,
  setAssEmphasis,
  setTemplateStatus,
  setTemplateError
}: UseSubtitleCreationTemplateOptions) {
  const appliedTemplateRef = useRef<string | null>(null);
  const pendingTemplateMetadataRef = useRef<Record<string, unknown> | null>(null);
  const [templateMetadataApplyKey, setTemplateMetadataApplyKey] = useState(0);

  useEffect(() => {
    if (!creationTemplate) {
      appliedTemplateRef.current = null;
      return;
    }
    const applyKey = `${creationTemplate.id}:${creationTemplate.updated_at}`;
    if (appliedTemplateRef.current === applyKey) {
      return;
    }
    const applied = extractSubtitleTemplateFormState(creationTemplate);
    if (!applied) {
      setTemplateStatus(null);
      setTemplateError(`Template "${creationTemplate.name}" is not compatible with Subtitle Tool.`);
      appliedTemplateRef.current = applyKey;
      return;
    }

    if (applied.sourceMode) handleSourceModeChange(applied.sourceMode);
    if (applied.selectedSource) setSelectedSource(applied.selectedSource);
    if (applied.inputLanguage) setInputLanguage(applied.inputLanguage);
    if (applied.targetLanguage) {
      setTargetLanguage(applied.targetLanguage);
      setPrimaryTargetLanguage(applied.targetLanguage);
    }
    if (applied.enableTransliteration !== undefined) setEnableTransliteration(applied.enableTransliteration);
    if (applied.enableHighlight !== undefined) setEnableHighlight(applied.enableHighlight);
    if (applied.showOriginal !== undefined) setShowOriginal(applied.showOriginal);
    if (applied.generateAudioBook !== undefined) setGenerateAudioBook(applied.generateAudioBook);
    if (applied.outputFormat) setOutputFormat(applied.outputFormat);
    if (applied.mirrorToSourceDir !== undefined) setMirrorToSourceDir(applied.mirrorToSourceDir);
    if (applied.startTime) setStartTime(applied.startTime);
    if (applied.endTime !== undefined) setEndTime(applied.endTime);
    if (applied.selectedModel) setSelectedModel(applied.selectedModel);
    if (applied.translationProvider) setTranslationProvider(applied.translationProvider);
    if (applied.transliterationMode) setTransliterationMode(applied.transliterationMode);
    if (applied.transliterationModel) setTransliterationModel(applied.transliterationModel);
    if (applied.workerCount !== undefined) setWorkerCount(applied.workerCount);
    if (applied.batchSize !== undefined) setBatchSize(applied.batchSize);
    if (applied.translationBatchSize !== undefined) setTranslationBatchSize(applied.translationBatchSize);
    if (applied.assFontSize !== undefined) setAssFontSize(applied.assFontSize);
    if (applied.assEmphasis !== undefined) setAssEmphasis(applied.assEmphasis);
    if (applied.mediaMetadataDraft) {
      pendingTemplateMetadataRef.current = applied.mediaMetadataDraft;
      setTemplateMetadataApplyKey((current) => current + 1);
    }
    setTemplateError(null);
    setTemplateStatus(`Applied template "${creationTemplate.name}".`);
    appliedTemplateRef.current = applyKey;
  }, [
    creationTemplate,
    handleSourceModeChange,
    setAssEmphasis,
    setAssFontSize,
    setBatchSize,
    setEnableHighlight,
    setEnableTransliteration,
    setEndTime,
    setGenerateAudioBook,
    setInputLanguage,
    setMirrorToSourceDir,
    setOutputFormat,
    setPrimaryTargetLanguage,
    setSelectedModel,
    setSelectedSource,
    setShowOriginal,
    setStartTime,
    setTargetLanguage,
    setTemplateError,
    setTemplateStatus,
    setTranslationBatchSize,
    setTranslationProvider,
    setTransliterationMode,
    setTransliterationModel,
    setWorkerCount
  ]);

  useEffect(() => {
    const metadata = pendingTemplateMetadataRef.current;
    if (!metadata) {
      return;
    }
    pendingTemplateMetadataRef.current = null;
    updateMediaMetadataDraft((draft) => {
      Object.keys(draft).forEach((key) => {
        delete draft[key];
      });
      Object.assign(draft, metadata);
    });
  }, [metadataSourceName, templateMetadataApplyKey, updateMediaMetadataDraft]);
}
