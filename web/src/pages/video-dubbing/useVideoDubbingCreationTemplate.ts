import { useEffect, useRef, useState } from 'react';
import type { BookCreationOptionsResponse } from '../../api/createBook';
import type {
  CreationTemplateEntry,
  JobParameterSnapshot
} from '../../api/dtos';
import {
  extractVideoDubbingTemplateFormState,
  resolveVideoDubPrefill
} from './videoDubbingUtils';

type SetValue<T> = (value: T) => void;
type UpdateMetadataDraft = (updater: (draft: Record<string, unknown>) => void) => void;

type VideoDubbingCreationTemplateOptions = {
  creationTemplate: CreationTemplateEntry | null;
  prefillParameters: JobParameterSnapshot | null;
  pipelineDefaults: BookCreationOptionsResponse['pipeline_defaults'] | null;
  metadataSourceName: string;
  applyPipelineDefaults: (defaults: BookCreationOptionsResponse['pipeline_defaults'] | null) => void;
  updateMediaMetadataDraft: UpdateMetadataDraft;
  setSelectedVideoDiscoveryTemplateState: SetValue<Record<string, unknown> | null>;
  setSelectedVideoPath: SetValue<string | null>;
  setSelectedSubtitlePath: SetValue<string | null>;
  applyTargetLanguage: SetValue<string>;
  setVoice: SetValue<string>;
  setStartOffset: SetValue<string>;
  setEndOffset: SetValue<string>;
  setOriginalMixPercent: SetValue<number>;
  setFlushSentences: SetValue<number>;
  setTranslationBatchSize: SetValue<number>;
  setTargetHeight: SetValue<number>;
  setPreserveAspectRatio: SetValue<boolean>;
  setSplitBatches: SetValue<boolean>;
  setStitchBatches: SetValue<boolean>;
  setLlmModel: SetValue<string>;
  setTranslationProvider: SetValue<string>;
  setTransliterationMode: SetValue<string>;
  setTransliterationModel: SetValue<string>;
  setIncludeTransliteration: SetValue<boolean>;
  setEnableLookupCache: SetValue<boolean>;
  setTemplateStatus: SetValue<string | null>;
  setTemplateError: SetValue<string | null>;
};

export function useVideoDubbingCreationTemplate({
  creationTemplate,
  prefillParameters,
  pipelineDefaults,
  metadataSourceName,
  applyPipelineDefaults,
  updateMediaMetadataDraft,
  setSelectedVideoDiscoveryTemplateState,
  setSelectedVideoPath,
  setSelectedSubtitlePath,
  applyTargetLanguage,
  setVoice,
  setStartOffset,
  setEndOffset,
  setOriginalMixPercent,
  setFlushSentences,
  setTranslationBatchSize,
  setTargetHeight,
  setPreserveAspectRatio,
  setSplitBatches,
  setStitchBatches,
  setLlmModel,
  setTranslationProvider,
  setTransliterationMode,
  setTransliterationModel,
  setIncludeTransliteration,
  setEnableLookupCache,
  setTemplateStatus,
  setTemplateError
}: VideoDubbingCreationTemplateOptions) {
  const appliedTemplateRef = useRef<string | null>(null);
  const pendingTemplateMetadataRef = useRef<Record<string, unknown> | null>(null);
  const [templateMetadataApplyKey, setTemplateMetadataApplyKey] = useState(0);

  useEffect(() => {
    const prefill = resolveVideoDubPrefill(prefillParameters);
    if (!prefill) {
      return;
    }
    if (prefill.videoPath) {
      setSelectedVideoPath(prefill.videoPath);
    }
    if (prefill.subtitlePath) {
      setSelectedSubtitlePath(prefill.subtitlePath);
    }
    if (prefill.targetLanguage) {
      applyTargetLanguage(prefill.targetLanguage);
    }
    if (prefill.voice !== undefined) {
      setVoice(prefill.voice);
    }
    if (prefill.llmModel) {
      setLlmModel(prefill.llmModel);
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
  }, [
    applyTargetLanguage,
    prefillParameters,
    setLlmModel,
    setSelectedSubtitlePath,
    setSelectedVideoPath,
    setTransliterationMode,
    setTransliterationModel,
    setTranslationProvider,
    setVoice
  ]);

  useEffect(() => {
    if (prefillParameters || creationTemplate) {
      return;
    }
    applyPipelineDefaults(pipelineDefaults);
  }, [applyPipelineDefaults, creationTemplate, pipelineDefaults, prefillParameters]);

  useEffect(() => {
    if (!creationTemplate) {
      appliedTemplateRef.current = null;
      return;
    }
    const applyKey = `${creationTemplate.id}:${creationTemplate.updated_at}`;
    if (appliedTemplateRef.current === applyKey) {
      return;
    }
    const applied = extractVideoDubbingTemplateFormState(creationTemplate);
    if (!applied) {
      setTemplateStatus(null);
      setTemplateError(`Template "${creationTemplate.name}" is not compatible with Video Dubbing.`);
      appliedTemplateRef.current = applyKey;
      return;
    }

    setSelectedVideoDiscoveryTemplateState(applied.discoveryState ?? null);
    if (applied.videoPath) setSelectedVideoPath(applied.videoPath);
    if (applied.subtitlePath) setSelectedSubtitlePath(applied.subtitlePath);
    if (applied.targetLanguage) applyTargetLanguage(applied.targetLanguage);
    if (applied.voice !== undefined) setVoice(applied.voice);
    if (applied.startOffset !== undefined) setStartOffset(applied.startOffset);
    if (applied.endOffset !== undefined) setEndOffset(applied.endOffset);
    if (applied.originalMixPercent !== undefined) setOriginalMixPercent(applied.originalMixPercent);
    if (applied.flushSentences !== undefined) setFlushSentences(applied.flushSentences);
    if (applied.translationBatchSize !== undefined) setTranslationBatchSize(applied.translationBatchSize);
    if (applied.targetHeight !== undefined) setTargetHeight(applied.targetHeight);
    if (applied.preserveAspectRatio !== undefined) setPreserveAspectRatio(applied.preserveAspectRatio);
    if (applied.splitBatches !== undefined) setSplitBatches(applied.splitBatches);
    if (applied.stitchBatches !== undefined) setStitchBatches(applied.stitchBatches);
    if (applied.llmModel) setLlmModel(applied.llmModel);
    if (applied.translationProvider) setTranslationProvider(applied.translationProvider);
    if (applied.transliterationMode) setTransliterationMode(applied.transliterationMode);
    if (applied.transliterationModel) setTransliterationModel(applied.transliterationModel);
    if (applied.includeTransliteration !== undefined) setIncludeTransliteration(applied.includeTransliteration);
    if (applied.enableLookupCache !== undefined) setEnableLookupCache(applied.enableLookupCache);
    if (applied.mediaMetadataDraft) {
      pendingTemplateMetadataRef.current = applied.mediaMetadataDraft;
      setTemplateMetadataApplyKey((current) => current + 1);
    }
    setTemplateError(null);
    setTemplateStatus(`Applied template "${creationTemplate.name}".`);
    appliedTemplateRef.current = applyKey;
  }, [
    applyTargetLanguage,
    creationTemplate,
    setEnableLookupCache,
    setEndOffset,
    setFlushSentences,
    setIncludeTransliteration,
    setLlmModel,
    setOriginalMixPercent,
    setPreserveAspectRatio,
    setSelectedSubtitlePath,
    setSelectedVideoDiscoveryTemplateState,
    setSelectedVideoPath,
    setSplitBatches,
    setStartOffset,
    setStitchBatches,
    setTargetHeight,
    setTemplateError,
    setTemplateStatus,
    setTranslationBatchSize,
    setTranslationProvider,
    setTransliterationMode,
    setTransliterationModel,
    setVoice
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
