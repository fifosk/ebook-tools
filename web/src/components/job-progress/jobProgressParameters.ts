import type { PipelineResponsePayload, PipelineStatusResponse } from '../../api/dtos';
import { formatModelLabel } from '../../utils/modelInfo';
import {
  coerceNumber,
  coerceRecord,
  countGeneratedImages,
  extractVoiceOverrides,
  formatLanguageList,
  formatPercent,
  formatRetryCounts,
  formatTimeOffset,
  formatTransliterationModeLabel,
  formatTranslationProviderLabel,
  formatVoiceOverrides,
  getStringField,
  normalizeTranslationProvider,
  normalizeTransliterationMode,
  resolveImagePromptPlanSummary,
  resolveSentenceRange,
  resolveSubtitleMetadata,
  sumRetryCounts,
} from './jobProgressUtils';

export type JobParameterEntry = {
  key: string;
  label: string;
  value: React.ReactNode;
};

export function buildJobParameterEntries(
  status: PipelineStatusResponse | undefined,
): JobParameterEntry[] {
  if (!status) {
    return [];
  }
  const entries: JobParameterEntry[] = [];
  const parameters = status.parameters ?? null;
  const isPipelineLike = status.job_type === 'pipeline' || status.job_type === 'book';
  const pipelineResult =
    isPipelineLike && status.result && typeof status.result === 'object'
      ? (status.result as PipelineResponsePayload)
      : null;
  const pipelineConfig =
    pipelineResult && pipelineResult.pipeline_config && typeof pipelineResult.pipeline_config === 'object'
      ? (pipelineResult.pipeline_config as Record<string, unknown>)
      : null;
  const pipelineMetadata =
    pipelineResult && pipelineResult.book_metadata && typeof pipelineResult.book_metadata === 'object'
      ? (pipelineResult.book_metadata as Record<string, unknown>)
      : null;
  const generatedFiles =
    status.generated_files && typeof status.generated_files === 'object'
      ? (status.generated_files as Record<string, unknown>)
      : null;
  const translationFallback = coerceRecord(generatedFiles?.['translation_fallback']);
  const translationFallbackModel = getStringField(translationFallback, 'fallback_model');
  const translationFallbackScope = getStringField(translationFallback, 'scope');
  const languageValues = (parameters?.target_languages ?? []).filter(
    (value): value is string => typeof value === 'string' && value.trim().length > 0,
  );
  const sentenceRange = resolveSentenceRange(status);
  const startSentence = parameters?.start_sentence ?? sentenceRange.start;
  const endSentence = parameters?.end_sentence ?? sentenceRange.end;
  const llmModelRaw = parameters?.llm_model ?? getStringField(pipelineConfig, 'ollama_model');
  const llmModel = formatModelLabel(llmModelRaw);
  const translationProviderRaw =
    parameters?.translation_provider ?? getStringField(pipelineMetadata, 'translation_provider');
  const translationProvider = normalizeTranslationProvider(translationProviderRaw);
  const translationBatchSize = coerceNumber(parameters?.translation_batch_size);
  const translationModel = getStringField(pipelineMetadata, 'translation_model');
  const normalizedLlmModel = llmModelRaw ? llmModelRaw.trim().toLowerCase() : null;
  const normalizedTranslationModel = translationModel ? translationModel.trim().toLowerCase() : null;
  const effectiveTranslationModel =
    translationProvider === 'llm' && normalizedLlmModel
      ? !normalizedTranslationModel || normalizedTranslationModel !== normalizedLlmModel
        ? llmModelRaw
        : translationModel
      : translationModel;
  const translationModelLabel = effectiveTranslationModel ? formatModelLabel(effectiveTranslationModel) : null;
  const translationProviderLabel = formatTranslationProviderLabel(
    translationProvider,
    effectiveTranslationModel,
    llmModelRaw,
  );
  const transliterationModeRaw =
    parameters?.transliteration_mode ?? getStringField(pipelineMetadata, 'transliteration_mode');
  const transliterationMode = normalizeTransliterationMode(transliterationModeRaw);
  const transliterationModelRaw =
    parameters?.transliteration_model ?? getStringField(pipelineMetadata, 'transliteration_model');
  const normalizedTransliterationModel = transliterationModelRaw ? transliterationModelRaw.trim().toLowerCase() : null;
  const effectiveTransliterationModel =
    transliterationMode === 'default' && normalizedLlmModel
      ? !normalizedTransliterationModel || normalizedTransliterationModel !== normalizedLlmModel
        ? llmModelRaw
        : transliterationModelRaw
      : transliterationModelRaw;
  const transliterationModule =
    parameters?.transliteration_module ?? getStringField(pipelineMetadata, 'transliteration_module');
  const resolvedTransliterationModel =
    effectiveTransliterationModel ?? (transliterationMode === 'default' ? llmModelRaw : null);
  const transliterationModelLabel = resolvedTransliterationModel
    ? formatModelLabel(resolvedTransliterationModel)
    : null;
  const transliterationModeLabel = formatTransliterationModeLabel(transliterationMode);
  const showTransliterationModel =
    Boolean(transliterationModelLabel) &&
    (transliterationMode !== 'default' || translationProvider === 'googletrans');
  const retrySummary = status.retry_summary ?? null;
  const imageStats = status.image_generation ?? null;
  const imageEnabled = parameters?.add_images ?? (imageStats ? imageStats.enabled : null);
  const imageApiBaseUrl = getStringField(pipelineConfig, 'image_api_base_url');
  const generatedImageCount = countGeneratedImages(status);
  const expectedImages =
    imageStats && typeof imageStats.expected === 'number' && Number.isFinite(imageStats.expected)
      ? imageStats.expected
      : null;
  const resolvedGeneratedImages =
    imageStats && typeof imageStats.generated === 'number' && Number.isFinite(imageStats.generated)
      ? imageStats.generated
      : generatedImageCount;
  const imagePercent =
    imageStats && typeof imageStats.percent === 'number' && Number.isFinite(imageStats.percent)
      ? imageStats.percent
      : expectedImages !== null && expectedImages > 0
        ? Math.round((resolvedGeneratedImages / expectedImages) * 100)
        : null;
  const imagePending =
    imageStats && typeof imageStats.pending === 'number' && Number.isFinite(imageStats.pending)
      ? imageStats.pending
      : null;
  const imageBatchSize =
    imageStats && typeof imageStats.batch_size === 'number' && Number.isFinite(imageStats.batch_size)
      ? imageStats.batch_size
      : null;
  const imagePromptPlanSummary = resolveImagePromptPlanSummary(status);
  const imagePromptPlanQuality = imagePromptPlanSummary
    ? coerceRecord(imagePromptPlanSummary['quality'])
    : null;
  const imageRetryCounts =
    retrySummary && typeof retrySummary === 'object'
      ? (retrySummary as Record<string, Record<string, number>>).image
      : null;
  const imageRetryDetails = formatRetryCounts(imageRetryCounts);
  const imageErrors = sumRetryCounts(imageRetryCounts);

  if (status.job_type === 'subtitle') {
    const subtitleMetadata = resolveSubtitleMetadata(status);
    const translationLanguage =
      languageValues[0] ?? getStringField(subtitleMetadata, 'target_language');
    if (translationLanguage) {
      entries.push({
        key: 'subtitle-translation-language',
        label: 'Translation language',
        value: translationLanguage,
      });
    }
    if (translationProviderLabel) {
      entries.push({
        key: 'subtitle-translation-provider',
        label: 'Translation provider',
        value: translationProviderLabel,
      });
    }
    if (translationModelLabel && translationProvider === 'googletrans') {
      entries.push({
        key: 'subtitle-translation-model',
        label: 'Translation model',
        value: translationModelLabel,
      });
    }
    if (transliterationModeLabel) {
      entries.push({
        key: 'subtitle-transliteration-mode',
        label: 'Transliteration mode',
        value: transliterationModeLabel,
      });
    }
    if (showTransliterationModel) {
      entries.push({
        key: 'subtitle-transliteration-model',
        label: 'Transliteration model',
        value: transliterationModelLabel,
      });
    }
    if (transliterationModule) {
      entries.push({
        key: 'subtitle-transliteration-module',
        label: 'Transliteration module',
        value: transliterationModule,
      });
    }
    const detectedLanguage = getStringField(subtitleMetadata, 'detected_language');
    const detectedLanguageCode = getStringField(subtitleMetadata, 'detected_language_code');
    if (detectedLanguage || detectedLanguageCode) {
      const detectedLabel = detectedLanguageCode
        ? `${detectedLanguage ?? 'Detected'} (${detectedLanguageCode})`
        : detectedLanguage;
      entries.push({
        key: 'subtitle-detected-language',
        label: 'Detected language',
        value: detectedLabel ?? 'Unknown',
      });
    }
    const originTranslation =
      subtitleMetadata && typeof subtitleMetadata['origin_translation'] === 'object'
        ? (subtitleMetadata['origin_translation'] as Record<string, unknown>)
        : null;
    const originTranslationActive =
      typeof originTranslation?.['active'] === 'boolean'
        ? (originTranslation['active'] as boolean)
        : Boolean(subtitleMetadata?.['origin_translation_applied']);
    const originSource =
      getStringField(originTranslation, 'source_language') ??
      getStringField(subtitleMetadata, 'translation_source_language');
    const originSourceCode =
      getStringField(originTranslation, 'source_language_code') ??
      getStringField(subtitleMetadata, 'translation_source_language_code');
    const originTarget =
      getStringField(originTranslation, 'target_language') ??
      getStringField(subtitleMetadata, 'original_language');
    const originTargetCode =
      getStringField(originTranslation, 'target_language_code') ??
      getStringField(subtitleMetadata, 'original_language_code');
    const originFromLabel = originSourceCode ?? originSource ?? 'source';
    const originToLabel = originTargetCode ?? originTarget ?? 'origin';
    entries.push({
      key: 'subtitle-origin-translation',
      label: 'Origin translation',
      value: originTranslationActive
        ? `Active (${originFromLabel} → ${originToLabel})`
        : `Matched (${originFromLabel} → ${originToLabel})`,
    });
    if (llmModel) {
      entries.push({ key: 'subtitle-llm-model', label: 'LLM model', value: llmModel });
    }
    if (startSentence !== null) {
      entries.push({
        key: 'subtitle-start-sentence',
        label: 'Start sentence',
        value: startSentence.toString(),
      });
    }
    if (endSentence !== null) {
      entries.push({
        key: 'subtitle-end-sentence',
        label: 'End sentence',
        value: endSentence.toString(),
      });
    }
    const startOffset = formatTimeOffset(parameters?.start_time_offset_seconds);
    if (startOffset) {
      entries.push({
        key: 'subtitle-start-offset',
        label: 'Start offset',
        value: startOffset,
      });
    }
    const endOffset = formatTimeOffset(parameters?.end_time_offset_seconds);
    if (endOffset) {
      entries.push({
        key: 'subtitle-end-offset',
        label: 'End offset',
        value: endOffset,
      });
    }
    const subtitleTracks =
      subtitleMetadata && typeof subtitleMetadata['subtitle_tracks'] === 'string'
        ? subtitleMetadata['subtitle_tracks'].split(',').map((track) => track.trim())
        : [];
    if (subtitleTracks.length) {
      entries.push({
        key: 'subtitle-track-languages',
        label: 'Subtitle tracks',
        value: formatLanguageList(subtitleTracks) ?? subtitleTracks.join(', '),
      });
    }
    const narrativeLanguage =
      getStringField(subtitleMetadata, 'narration_language') ??
      getStringField(subtitleMetadata, 'narration_language_code');
    if (narrativeLanguage) {
      entries.push({
        key: 'subtitle-narration-language',
        label: 'Narration language',
        value: narrativeLanguage,
      });
    }
  }

  if (status.job_type === 'pipeline' || status.job_type === 'book') {
    const languageList = formatLanguageList(languageValues);
    if (languageList) {
      entries.push({
        key: 'pipeline-target-languages',
        label: 'Target languages',
        value: languageList,
      });
    }
    const sourceLanguage = getStringField(pipelineMetadata, 'input_language');
    if (sourceLanguage) {
      entries.push({
        key: 'pipeline-source-language',
        label: 'Source language',
        value: sourceLanguage,
      });
    }
    const originalLanguage = getStringField(pipelineMetadata, 'original_language');
    if (originalLanguage) {
      entries.push({
        key: 'pipeline-original-language',
        label: 'Original language',
        value: originalLanguage,
      });
    }
    if (translationProviderLabel) {
      entries.push({
        key: 'pipeline-translation-provider',
        label: 'Translation provider',
        value: translationProviderLabel,
      });
    }
    if (translationFallbackModel) {
      const fallbackLabel =
        translationFallbackScope === 'transliteration'
          ? 'Transliteration fallback model'
          : 'Translation fallback model';
      entries.push({
        key: 'pipeline-translation-fallback-model',
        label: fallbackLabel,
        value: formatModelLabel(translationFallbackModel) ?? translationFallbackModel,
      });
    }
    if (translationBatchSize !== null) {
      entries.push({
        key: 'pipeline-translation-batch-size',
        label: 'LLM batch size',
        value: translationBatchSize,
      });
    }
    if (translationModelLabel && translationProvider === 'googletrans') {
      entries.push({
        key: 'pipeline-translation-model',
        label: 'Translation model',
        value: translationModelLabel,
      });
    }
    if (transliterationModeLabel) {
      entries.push({
        key: 'pipeline-transliteration-mode',
        label: 'Transliteration mode',
        value: transliterationModeLabel,
      });
    }
    if (showTransliterationModel) {
      entries.push({
        key: 'pipeline-transliteration-model',
        label: 'Transliteration model',
        value: transliterationModelLabel,
      });
    }
    if (transliterationModule) {
      entries.push({
        key: 'pipeline-transliteration-module',
        label: 'Transliteration module',
        value: transliterationModule,
      });
    }
    if (llmModel) {
      entries.push({ key: 'pipeline-llm-model', label: 'LLM model', value: llmModel });
    }
    if (startSentence !== null) {
      entries.push({
        key: 'pipeline-start-sentence',
        label: 'Start sentence',
        value: startSentence.toString(),
      });
    }
    if (endSentence !== null) {
      entries.push({
        key: 'pipeline-end-sentence',
        label: 'End sentence',
        value: endSentence.toString(),
      });
    }
    if (imageEnabled !== null || generatedImageCount > 0 || imageErrors > 0 || imagePromptPlanQuality) {
      const statusParts: string[] = [];
      if (imageEnabled === false) {
        statusParts.push('disabled');
      }
      if (imagePercent !== null) {
        statusParts.push(`${imagePercent}% generated`);
      }
      if (imagePending !== null) {
        statusParts.push(`${imagePending} pending`);
      }
      if (imageBatchSize !== null) {
        statusParts.push(`batch ${imageBatchSize}`);
      }
      if (imageRetryDetails) {
        statusParts.push(`retries ${imageRetryDetails}`);
      }
      if (imageErrors > 0) {
        statusParts.push(`${imageErrors} failures`);
      }
      if (statusParts.length === 0) {
        statusParts.push('enabled');
      }
      entries.push({
        key: 'pipeline-image-generation',
        label: 'Image generation',
        value: statusParts.join(', '),
      });
      if (imageApiBaseUrl) {
        entries.push({
          key: 'pipeline-image-api',
          label: 'Image API',
          value: imageApiBaseUrl,
        });
      }
    }
    if (imagePromptPlanQuality) {
      const total = coerceNumber(imagePromptPlanQuality['total_sentences']);
      const fallbacks = coerceNumber(imagePromptPlanQuality['final_fallback']);
      const llmCoverageRate = coerceNumber(imagePromptPlanQuality['llm_coverage_rate']);
      const retryAttempts = coerceNumber(imagePromptPlanQuality['retry_attempts']);
      const retryRequested = coerceNumber(imagePromptPlanQuality['retry_requested']);
      const retryRecovered = coerceNumber(imagePromptPlanQuality['retry_recovered']);
      const retrySuccessRate = coerceNumber(imagePromptPlanQuality['retry_success_rate']);
      const llmRequests = coerceNumber(imagePromptPlanQuality['llm_requests']);
      const statusValueRaw =
        typeof imagePromptPlanSummary?.['status'] === 'string'
          ? (imagePromptPlanSummary['status'] as string).trim()
          : '';
      const statusLabel = statusValueRaw ? statusValueRaw.toUpperCase() : null;
      const errorMessage =
        typeof imagePromptPlanSummary?.['error'] === 'string'
          ? (imagePromptPlanSummary['error'] as string).trim()
          : null;

      const llmCount =
        total !== null && fallbacks !== null ? Math.max(0, Math.round(total - fallbacks)) : null;
      const coverageLabel =
        total !== null && llmCount !== null
          ? `${llmCount}/${Math.round(total)} (${formatPercent(llmCoverageRate)})`
          : null;

      const parts: string[] = [];
      if (statusLabel) {
        parts.push(statusLabel);
      }
      if (coverageLabel) {
        parts.push(`LLM ${coverageLabel}`);
      }
      if (fallbacks !== null) {
        parts.push(`fallbacks ${Math.round(fallbacks)}`);
      }
      if (retryAttempts !== null && retryAttempts > 0) {
        const recoveredLabel =
          retryRecovered !== null && retryRequested !== null
            ? `${Math.round(retryRecovered)}/${Math.round(retryRequested)}`
            : null;
        const successLabel = retrySuccessRate !== null ? formatPercent(retrySuccessRate) : null;
        if (recoveredLabel && successLabel) {
          parts.push(
            `retries ${Math.round(retryAttempts)} (recovered ${recoveredLabel}, ${successLabel})`,
          );
        } else if (recoveredLabel) {
          parts.push(`retries ${Math.round(retryAttempts)} (recovered ${recoveredLabel})`);
        } else {
          parts.push(`retries ${Math.round(retryAttempts)}`);
        }
      }
      if (llmRequests !== null && llmRequests > 0) {
        parts.push(`LLM calls ${Math.round(llmRequests)}`);
      }
      if (errorMessage) {
        parts.push(`error: ${errorMessage}`);
      }

      entries.push({
        key: 'pipeline-image-prompt-plan',
        label: 'Prompt map quality',
        value: parts.length > 0 ? parts.join(', ') : '—',
      });
    }
  }
  const parameterOverrides =
    parameters?.voice_overrides && Object.keys(parameters.voice_overrides).length > 0
      ? parameters.voice_overrides
      : undefined;
  const configOverrides = extractVoiceOverrides(pipelineConfig);
  const voiceOverrideText = formatVoiceOverrides(parameterOverrides ?? configOverrides);
  if (voiceOverrideText) {
    entries.push({
      key: 'pipeline-voice-overrides',
      label: 'Voice overrides',
      value: voiceOverrideText,
    });
  }
  if (retrySummary && typeof retrySummary === 'object') {
    const translationRetries = formatRetryCounts(
      (retrySummary as Record<string, Record<string, number>>).translation,
    );
    if (translationRetries) {
      entries.push({
        key: 'pipeline-translation-retry-summary',
        label: 'Translation retries',
        value: translationRetries,
      });
    }
    const transliterationRetries = formatRetryCounts(
      (retrySummary as Record<string, Record<string, number>>).transliteration,
    );
    if (transliterationRetries) {
      entries.push({
        key: 'pipeline-transliteration-retry-summary',
        label: 'Transliteration retries',
        value: transliterationRetries,
      });
    }
  }
  return entries;
}
