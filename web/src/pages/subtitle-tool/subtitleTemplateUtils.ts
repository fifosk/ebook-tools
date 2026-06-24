import type { CreationTemplatePayload } from '../../api/dtos';
import { sanitizeTemplateValue } from '../../utils/creationTemplateSanitizer';
import type { ResolvedSubtitleSubmitValues } from './subtitleSubmitUtils';
import type { SubtitleOutputFormat, SubtitleSourceMode } from './subtitleToolTypes';

export type BuildSubtitleTemplatePayloadInput = {
  values: ResolvedSubtitleSubmitValues;
  sourceMode: SubtitleSourceMode;
  enableTransliteration: boolean;
  enableHighlight: boolean;
  showOriginal: boolean;
  generateAudioBook: boolean;
  outputFormat: SubtitleOutputFormat;
  mirrorToSourceDir: boolean;
  mediaMetadataDraft?: Record<string, unknown> | null;
};

function basenameFromPath(value: string | null | undefined): string {
  const trimmed = typeof value === 'string' ? value.trim() : '';
  if (!trimmed) {
    return '';
  }
  const normalized = trimmed.replace(/\\\\/g, '/');
  const parts = normalized.split('/');
  return parts.length ? parts[parts.length - 1] : trimmed;
}

function coerceRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function textValue(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const cleaned = value.trim();
  return cleaned.length > 0 ? cleaned : null;
}

function firstMetadataText(
  metadata: Record<string, unknown> | null | undefined,
  paths: string[][]
): string | null {
  for (const path of paths) {
    let current: unknown = metadata;
    for (const key of path) {
      const record = coerceRecord(current);
      current = record ? record[key] : null;
    }
    const text = textValue(current);
    if (text) {
      return text;
    }
  }
  return null;
}

export function deriveSubtitleTemplateName(input: BuildSubtitleTemplatePayloadInput): string {
  const metadataName = firstMetadataText(input.mediaMetadataDraft, [
    ['title'],
    ['episode', 'name'],
    ['episode', 'title'],
    ['show', 'name'],
    ['tv', 'title']
  ]);
  if (metadataName) {
    return metadataName;
  }

  const sourceName = basenameFromPath(input.values.sourcePath);
  if (sourceName) {
    return sourceName.replace(/\.[^.]+$/, '');
  }

  return 'Subtitle job template';
}

export function buildSubtitleTemplatePayload(input: BuildSubtitleTemplatePayloadInput): CreationTemplatePayload {
  const { values } = input;
  const formState: Record<string, unknown> = {
    source_mode: input.sourceMode,
    input_language: values.originalLanguage,
    original_language: values.originalLanguage,
    target_language: values.targetLanguage,
    enable_transliteration: input.enableTransliteration,
    highlight: input.enableHighlight,
    show_original: input.showOriginal,
    generate_audio_book: input.generateAudioBook,
    output_format: input.outputFormat,
    mirror_batches_to_source_dir: input.mirrorToSourceDir,
    start_time: values.normalizedStartTime
  };

  if (values.normalizedEndTime) {
    formState.end_time = values.normalizedEndTime;
  }
  if (values.sourcePath) {
    formState.source_path = values.sourcePath;
  }
  if (values.resolvedAssFontSize !== null) {
    formState.ass_font_size = values.resolvedAssFontSize;
  }
  if (values.resolvedAssEmphasis !== null) {
    formState.ass_emphasis_scale = values.resolvedAssEmphasis;
  }
  if (values.selectedModel) {
    formState.llm_model = values.selectedModel;
  }
  if (values.translationProvider) {
    formState.translation_provider = values.translationProvider;
  }
  if (values.transliterationMode) {
    formState.transliteration_mode = values.transliterationMode;
  }
  if (values.transliterationModel) {
    formState.transliteration_model = values.transliterationModel;
  }
  if (values.workerCount !== null) {
    formState.worker_count = values.workerCount;
  }
  if (values.batchSize !== null) {
    formState.batch_size = values.batchSize;
  }
  if (values.translationBatchSize !== null) {
    formState.translation_batch_size = values.translationBatchSize;
  }
  if (input.mediaMetadataDraft) {
    formState.media_metadata = sanitizeTemplateValue(input.mediaMetadataDraft);
  }

  return {
    name: deriveSubtitleTemplateName(input),
    mode: 'subtitle_job',
    payload: {
      kind: 'subtitle_job_form',
      source: 'web',
      version: 1,
      source_mode: input.sourceMode,
      form_state: formState
    }
  };
}
