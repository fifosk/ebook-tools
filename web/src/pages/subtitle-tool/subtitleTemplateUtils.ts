import type { CreationTemplateEntry, CreationTemplatePayload } from '../../api/dtos';
import { sanitizeCreationTemplatePayloadExtras } from '../../utils/creationTemplatePayloadExtras';
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
  payloadExtras?: Record<string, unknown> | null;
};

export type AppliedSubtitleTemplate = {
  sourceMode?: SubtitleSourceMode;
  selectedSource?: string;
  inputLanguage?: string;
  targetLanguage?: string;
  enableTransliteration?: boolean;
  enableHighlight?: boolean;
  showOriginal?: boolean;
  generateAudioBook?: boolean;
  outputFormat?: SubtitleOutputFormat;
  mirrorToSourceDir?: boolean;
  startTime?: string;
  endTime?: string;
  selectedModel?: string;
  translationProvider?: string;
  transliterationMode?: string;
  transliterationModel?: string;
  workerCount?: number;
  batchSize?: number;
  translationBatchSize?: number;
  assFontSize?: number;
  assEmphasis?: number;
  mediaMetadataDraft?: Record<string, unknown>;
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
  const safePayloadExtras = sanitizeCreationTemplatePayloadExtras(input.payloadExtras);

  return {
    name: deriveSubtitleTemplateName(input),
    mode: 'subtitle_job',
    payload: {
      kind: 'subtitle_job_form',
      source: 'web',
      version: 1,
      source_mode: input.sourceMode,
      ...safePayloadExtras,
      form_state: formState
    }
  };
}

function formStateFromTemplate(template: CreationTemplateEntry): Record<string, unknown> | null {
  const payload = template.payload;
  const formState = coerceRecord(payload.form_state);
  if (formState) {
    return formState;
  }
  const nested = coerceRecord(payload.payload);
  return coerceRecord(nested?.form_state);
}

function booleanValue(value: unknown): boolean | undefined {
  return typeof value === 'boolean' ? value : undefined;
}

function finiteNumber(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value.trim());
    return Number.isFinite(parsed) ? parsed : undefined;
  }
  return undefined;
}

function subtitleSourceMode(value: unknown): SubtitleSourceMode | undefined {
  if (value === 'server') {
    return 'existing';
  }
  return value === 'existing' || value === 'upload' ? value : undefined;
}

function subtitleOutputFormat(value: unknown): SubtitleOutputFormat | undefined {
  return value === 'srt' || value === 'ass' ? value : undefined;
}

function metadataDraft(value: unknown): Record<string, unknown> | undefined {
  const record = coerceRecord(value);
  if (!record) {
    return undefined;
  }
  return sanitizeTemplateValue(record) as Record<string, unknown>;
}

export function extractSubtitleTemplateFormState(
  template: CreationTemplateEntry | null | undefined
): AppliedSubtitleTemplate | null {
  if (!template || template.mode !== 'subtitle_job') {
    return null;
  }
  if (template.payload.kind && template.payload.kind !== 'subtitle_job_form') {
    return null;
  }
  const formState = formStateFromTemplate(template);
  if (!formState) {
    return null;
  }

  const applied: AppliedSubtitleTemplate = {};
  const sourceMode = subtitleSourceMode(formState.source_mode);
  if (sourceMode) applied.sourceMode = sourceMode;
  const sourcePath = textValue(formState.source_path);
  if (sourcePath) applied.selectedSource = sourcePath;
  const inputLanguage = textValue(formState.input_language) ?? textValue(formState.original_language);
  if (inputLanguage) applied.inputLanguage = inputLanguage;
  const targetLanguage = textValue(formState.target_language);
  if (targetLanguage) applied.targetLanguage = targetLanguage;
  const enableTransliteration = booleanValue(formState.enable_transliteration);
  if (enableTransliteration !== undefined) applied.enableTransliteration = enableTransliteration;
  const enableHighlight = booleanValue(formState.highlight);
  if (enableHighlight !== undefined) applied.enableHighlight = enableHighlight;
  const showOriginal = booleanValue(formState.show_original);
  if (showOriginal !== undefined) applied.showOriginal = showOriginal;
  const generateAudioBook = booleanValue(formState.generate_audio_book);
  if (generateAudioBook !== undefined) applied.generateAudioBook = generateAudioBook;
  const outputFormat = subtitleOutputFormat(formState.output_format);
  if (outputFormat) applied.outputFormat = outputFormat;
  const mirrorToSourceDir = booleanValue(formState.mirror_batches_to_source_dir);
  if (mirrorToSourceDir !== undefined) applied.mirrorToSourceDir = mirrorToSourceDir;
  const startTime = textValue(formState.start_time);
  if (startTime) applied.startTime = startTime;
  const endTime = textValue(formState.end_time);
  if (endTime) applied.endTime = endTime;
  const selectedModel = textValue(formState.llm_model);
  if (selectedModel) applied.selectedModel = selectedModel;
  const translationProvider = textValue(formState.translation_provider);
  if (translationProvider) applied.translationProvider = translationProvider;
  const transliterationMode = textValue(formState.transliteration_mode);
  if (transliterationMode) applied.transliterationMode = transliterationMode;
  const transliterationModel = textValue(formState.transliteration_model);
  if (transliterationModel) applied.transliterationModel = transliterationModel;
  const workerCount = finiteNumber(formState.worker_count);
  if (workerCount !== undefined) applied.workerCount = workerCount;
  const batchSize = finiteNumber(formState.batch_size);
  if (batchSize !== undefined) applied.batchSize = batchSize;
  const translationBatchSize = finiteNumber(formState.translation_batch_size);
  if (translationBatchSize !== undefined) applied.translationBatchSize = translationBatchSize;
  const assFontSize = finiteNumber(formState.ass_font_size);
  if (assFontSize !== undefined) applied.assFontSize = assFontSize;
  const assEmphasis = finiteNumber(formState.ass_emphasis_scale);
  if (assEmphasis !== undefined) applied.assEmphasis = assEmphasis;
  const mediaMetadataDraft = metadataDraft(formState.media_metadata);
  if (mediaMetadataDraft) applied.mediaMetadataDraft = mediaMetadataDraft;

  return Object.keys(applied).length > 0 ? applied : null;
}
