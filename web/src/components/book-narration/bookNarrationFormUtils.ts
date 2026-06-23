import type { JobParameterSnapshot, MacOSVoice, PipelineStatusResponse } from '../../api/dtos';
import { checkImageNodeAvailability } from '../../api/client';
import {
  expandImageNodeCandidates,
  getImageNodeFallbacks,
} from '../../constants/imageNodes';
import { isRecord } from './bookNarrationUtils';
import type {
  BookNarrationPipelineDefaults,
  BookNarrationFormProps,
  BookNarrationFormSection,
  FormState,
  ImageDefaults,
} from './bookNarrationFormTypes';

export type BookNarrationSectionMeta = Record<
  BookNarrationFormSection,
  { title: string; description: string }
>;

const BOOK_NARRATION_IMAGE_DEFAULT_FIELDS: Array<keyof FormState> = [
  'add_images',
  'image_prompt_pipeline',
  'image_style_template',
  'image_prompt_context_sentences',
  'image_width',
  'image_height',
];

export function capitalize(value: string): string {
  if (!value) {
    return value;
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function formatMacOSVoiceIdentifier(voice: MacOSVoice): string {
  const quality = voice.quality ? voice.quality : 'Default';
  const genderSuffix = voice.gender ? ` - ${capitalize(voice.gender)}` : '';
  return `${voice.name} - ${voice.lang} - (${quality})${genderSuffix}`;
}

export function formatMacOSVoiceLabel(voice: MacOSVoice): string {
  const segments: string[] = [voice.lang];
  if (voice.gender) {
    segments.push(capitalize(voice.gender));
  }
  if (voice.quality) {
    segments.push(voice.quality);
  }
  const meta = segments.length > 0 ? ` (${segments.join(', ')})` : '';
  return `${voice.name}${meta}`;
}

export function areLanguageArraysEqual(left: string[], right: string[]): boolean {
  if (left.length !== right.length) {
    return false;
  }
  for (let index = 0; index < left.length; index += 1) {
    if (left[index] !== right[index]) {
      return false;
    }
  }
  return true;
}

export function normalizeSingleTargetLanguages(languages: string[]): string[] {
  for (const entry of languages) {
    if (typeof entry !== 'string') {
      continue;
    }
    const trimmed = entry.trim();
    if (trimmed) {
      return [trimmed];
    }
  }
  return [];
}

export function compactBookNarrationPipelineDefaults(
  defaults: BookNarrationPipelineDefaults | null,
): Record<string, unknown> | null {
  if (!defaults) {
    return null;
  }
  const config: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(defaults)) {
    if (value !== undefined && value !== null) {
      config[key] = value;
    }
  }
  return Object.keys(config).length > 0 ? config : null;
}

export function targetLanguagesFromBookNarrationConfig(config: Record<string, unknown>): string[] {
  const targetLanguages = config['target_languages'];
  if (!Array.isArray(targetLanguages)) {
    return [];
  }
  return Array.from(
    new Set(
      targetLanguages
        .filter((language): language is string => typeof language === 'string')
        .map((language) => language.trim())
        .filter((language) => language.length > 0),
    ),
  );
}

export function coerceNumber(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) {
      return undefined;
    }
    const parsed = Number(trimmed);
    if (!Number.isNaN(parsed)) {
      return parsed;
    }
  }
  return undefined;
}

export function coerceStringList(value: unknown): string[] | undefined {
  if (Array.isArray(value)) {
    const entries = value
      .map((entry) => (typeof entry === 'string' ? entry : ''))
      .map((entry) => entry.trim())
      .filter((entry) => entry.length > 0);
    return entries.length > 0 ? entries : undefined;
  }
  if (typeof value === 'string') {
    const entries = value
      .split(',')
      .map((entry) => entry.trim())
      .filter((entry) => entry.length > 0);
    return entries.length > 0 ? entries : undefined;
  }
  return undefined;
}

export function normalizeBaseUrl(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  return trimmed.replace(/\/+$/, '');
}

export function normalizeBaseUrls(values: string[]): string[] {
  const cleaned: string[] = [];
  const seen = new Set<string>();
  for (const entry of values) {
    const normalized = normalizeBaseUrl(entry);
    if (!normalized || seen.has(normalized)) {
      continue;
    }
    seen.add(normalized);
    cleaned.push(normalized);
  }
  return cleaned;
}

export function normalizeImagePromptPipeline(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const normalized = value.trim().toLowerCase();
  if (!normalized) {
    return null;
  }
  if (normalized === 'visual_canon' || normalized === 'visual-canon' || normalized === 'canon') {
    return 'visual_canon';
  }
  if (normalized === 'prompt_plan' || normalized === 'prompt-plan' || normalized === 'plan') {
    return 'prompt_plan';
  }
  return 'prompt_plan';
}

export function applyBookNarrationImageDefaults({
  state,
  imageDefaults,
  editedFields,
  allowAddImagesDefault = true,
}: {
  state: FormState;
  imageDefaults: ImageDefaults | null;
  editedFields: Iterable<keyof FormState>;
  allowAddImagesDefault?: boolean;
}): FormState {
  if (!imageDefaults) {
    return state;
  }

  const edited = editedFields instanceof Set ? editedFields : new Set(editedFields);
  let next = state;
  let changed = false;

  const merge = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    if (edited.has(key) || state[key] === value) {
      return;
    }
    if (!changed) {
      next = { ...state };
      changed = true;
    }
    next[key] = value;
  };

  if (allowAddImagesDefault) {
    merge('add_images', imageDefaults.add_images);
  }

  const defaultPromptPipeline = normalizeImagePromptPipeline(imageDefaults.image_prompt_pipeline);
  if (defaultPromptPipeline) {
    merge('image_prompt_pipeline', defaultPromptPipeline);
  }

  merge('image_style_template', imageDefaults.image_style_template);
  merge(
    'image_prompt_context_sentences',
    Math.max(0, Math.min(50, Math.trunc(imageDefaults.image_prompt_context_sentences))),
  );
  merge('image_width', imageDefaults.image_width);
  merge('image_height', imageDefaults.image_height);

  return changed ? next : state;
}

export function restoreBookNarrationEditedImageDefaults(
  previous: FormState,
  next: FormState,
  editedFields: Iterable<keyof FormState>,
): FormState {
  const edited = editedFields instanceof Set ? editedFields : new Set(editedFields);
  if (edited.size === 0) {
    return next;
  }

  let result = next;
  let changed = false;
  for (const key of BOOK_NARRATION_IMAGE_DEFAULT_FIELDS) {
    if (!edited.has(key) || next[key] === previous[key]) {
      continue;
    }
    if (!changed) {
      result = { ...next };
      changed = true;
    }
    result = { ...result, [key]: previous[key] };
  }
  return changed ? result : next;
}

export async function resolveImageBaseUrlsForSubmission(values: string[]): Promise<string[]> {
  const normalized = normalizeBaseUrls(values);
  if (normalized.length === 0) {
    return normalized;
  }
  const candidates = expandImageNodeCandidates(normalized);
  if (candidates.length === 0) {
    return normalized;
  }
  try {
    const response = await checkImageNodeAvailability({ base_urls: candidates });
    const available = new Set<string>();
    for (const entry of response.nodes ?? []) {
      if (!entry.available) {
        continue;
      }
      const normalizedUrl = normalizeBaseUrl(entry.base_url);
      if (normalizedUrl) {
        available.add(normalizedUrl);
      }
    }
    const resolved = normalized.map((url) => {
      if (available.has(url)) {
        return url;
      }
      const fallbacks = getImageNodeFallbacks(url);
      const fallback = fallbacks.find((entry) => available.has(entry));
      return fallback ?? url;
    });
    return normalizeBaseUrls(resolved);
  } catch {
    return normalized;
  }
}

export function extractBookMetadata(config: Record<string, unknown>): Record<string, unknown> | null {
  const metadata: Record<string, unknown> = {};
  const nested = config['media_metadata'] ?? config['book_metadata'];
  if (isRecord(nested)) {
    for (const [key, value] of Object.entries(nested)) {
      if (value !== undefined && value !== null) {
        metadata[key] = value;
      }
    }
  }

  const preferredKeys = [
    'book_cover_title',
    'book_title',
    'book_author',
    'book_year',
    'book_summary',
    'book_cover_file',
  ];

  for (const key of preferredKeys) {
    const value = config[key];
    if (value !== undefined && value !== null) {
      metadata[key] = value;
    }
  }

  return Object.keys(metadata).length > 0 ? metadata : null;
}

export function applyConfigDefaults(previous: FormState, config: Record<string, unknown>): FormState {
  const next: FormState = { ...previous };

  const ollamaModel = config['ollama_model'];
  if (typeof ollamaModel === 'string') {
    next.ollama_model = ollamaModel;
  }

  const inputFile = config['input_file'];
  if (typeof inputFile === 'string') {
    next.input_file = inputFile;
  }

  const baseOutput = config['base_output_file'];
  if (typeof baseOutput === 'string') {
    next.base_output_file = baseOutput;
  }

  const inputLanguage = config['input_language'];
  if (typeof inputLanguage === 'string') {
    next.input_language = inputLanguage;
  }

  const targetLanguages = config['target_languages'];
  if (Array.isArray(targetLanguages)) {
    const normalized = Array.from(
      new Set(
        targetLanguages
          .filter((language): language is string => typeof language === 'string')
          .map((language) => language.trim())
          .filter((language) => language.length > 0),
      ),
    );
    next.target_languages = normalizeSingleTargetLanguages(normalized);
  }

  const sentencesPerOutput = coerceNumber(config['sentences_per_output_file']);
  if (sentencesPerOutput !== undefined) {
    next.sentences_per_output_file = sentencesPerOutput;
  }

  const startSentence = coerceNumber(config['start_sentence']);
  if (startSentence !== undefined) {
    next.start_sentence = startSentence;
  }

  const endSentence = config['end_sentence'];
  if (endSentence === null || endSentence === undefined || endSentence === '') {
    next.end_sentence = '';
  } else {
    const parsedEnd = coerceNumber(endSentence);
    if (parsedEnd !== undefined) {
      next.end_sentence = String(parsedEnd);
    }
  }

  const stitchFull = config['stitch_full'];
  if (typeof stitchFull === 'boolean') {
    next.stitch_full = stitchFull;
  }

  const generateAudio = config['generate_audio'];
  if (typeof generateAudio === 'boolean') {
    next.generate_audio = generateAudio;
  }

  const audioMode = config['audio_mode'];
  if (typeof audioMode === 'string') {
    next.audio_mode = audioMode;
  }

  const audioBitrate = coerceNumber(config['audio_bitrate_kbps']);
  if (audioBitrate !== undefined) {
    next.audio_bitrate_kbps = String(audioBitrate);
  }

  const writtenMode = config['written_mode'];
  if (typeof writtenMode === 'string') {
    next.written_mode = writtenMode;
  }

  const selectedVoice = config['selected_voice'];
  if (typeof selectedVoice === 'string') {
    next.selected_voice = selectedVoice;
  }

  const voiceOverrides = config['voice_overrides'];
  if (isRecord(voiceOverrides)) {
    const sanitized: Record<string, string> = {};
    for (const [key, value] of Object.entries(voiceOverrides)) {
      if (typeof key !== 'string' || typeof value !== 'string') {
        continue;
      }
      const normalizedKey = key.trim();
      const normalizedValue = value.trim();
      if (!normalizedKey || !normalizedValue) {
        continue;
      }
      sanitized[normalizedKey] = normalizedValue;
    }
    next.voice_overrides = sanitized;
  }

  const outputHtml = config['output_html'];
  if (typeof outputHtml === 'boolean') {
    next.output_html = outputHtml;
  }

  const outputPdf = config['output_pdf'];
  if (typeof outputPdf === 'boolean') {
    next.output_pdf = outputPdf;
  }

  const addImages = config['add_images'];
  if (typeof addImages === 'boolean') {
    next.add_images = addImages;
  }

  const imagePromptPipeline = normalizeImagePromptPipeline(config['image_prompt_pipeline']);
  if (imagePromptPipeline) {
    next.image_prompt_pipeline = imagePromptPipeline;
  }

  const imageStyleTemplate = config['image_style_template'];
  if (typeof imageStyleTemplate === 'string' && imageStyleTemplate.trim()) {
    next.image_style_template = imageStyleTemplate.trim();
  }

  const imagePromptBatchingEnabled = config['image_prompt_batching_enabled'];
  if (typeof imagePromptBatchingEnabled === 'boolean') {
    next.image_prompt_batching_enabled = imagePromptBatchingEnabled;
  }

  const imagePromptBatchSize = coerceNumber(config['image_prompt_batch_size']);
  if (imagePromptBatchSize !== undefined) {
    next.image_prompt_batch_size = Math.min(50, Math.max(1, Math.trunc(imagePromptBatchSize)));
  }

  const imagePromptPlanBatchSize = coerceNumber(config['image_prompt_plan_batch_size']);
  if (imagePromptPlanBatchSize !== undefined) {
    next.image_prompt_plan_batch_size = Math.min(50, Math.max(1, Math.trunc(imagePromptPlanBatchSize)));
  }

  const imagePromptContext = coerceNumber(config['image_prompt_context_sentences']);
  if (imagePromptContext !== undefined) {
    next.image_prompt_context_sentences = Math.min(50, Math.max(0, Math.trunc(imagePromptContext)));
  }

  const imageSeedWithPrevious = config['image_seed_with_previous_image'];
  if (typeof imageSeedWithPrevious === 'boolean') {
    next.image_seed_with_previous_image = imageSeedWithPrevious;
  }

  const imageBlankDetectionEnabled = config['image_blank_detection_enabled'];
  if (typeof imageBlankDetectionEnabled === 'boolean') {
    next.image_blank_detection_enabled = imageBlankDetectionEnabled;
  }

  const imageWidth = coerceNumber(config['image_width']);
  if (imageWidth !== undefined) {
    next.image_width = String(Math.max(64, Math.trunc(imageWidth)));
  }

  const imageHeight = coerceNumber(config['image_height']);
  if (imageHeight !== undefined) {
    next.image_height = String(Math.max(64, Math.trunc(imageHeight)));
  }

  const imageSteps = coerceNumber(config['image_steps']);
  if (imageSteps !== undefined) {
    next.image_steps = String(Math.max(1, Math.trunc(imageSteps)));
  }

  const imageCfgScale = coerceNumber(config['image_cfg_scale']);
  if (imageCfgScale !== undefined) {
    next.image_cfg_scale = String(Math.max(0, imageCfgScale));
  }

  const imageSamplerName = config['image_sampler_name'];
  if (typeof imageSamplerName === 'string') {
    next.image_sampler_name = imageSamplerName;
  }

  const imageApiBaseUrls = normalizeBaseUrls(coerceStringList(config['image_api_base_urls']) ?? []);
  const imageApiBaseUrl = normalizeBaseUrl(
    typeof config['image_api_base_url'] === 'string' ? config['image_api_base_url'] : null,
  );
  if (imageApiBaseUrls.length > 0) {
    next.image_api_base_urls = imageApiBaseUrls;
  } else if (imageApiBaseUrl) {
    next.image_api_base_urls = [imageApiBaseUrl];
  }

  const imageApiTimeoutSeconds = coerceNumber(config['image_api_timeout_seconds']);
  if (imageApiTimeoutSeconds !== undefined) {
    next.image_api_timeout_seconds = String(
      Math.max(300, Math.max(1, Math.trunc(imageApiTimeoutSeconds))),
    );
  }

  const includeTransliteration = config['include_transliteration'];
  if (typeof includeTransliteration === 'boolean') {
    next.include_transliteration = includeTransliteration;
  }

  const translationProvider = config['translation_provider'];
  if (typeof translationProvider === 'string' && translationProvider.trim()) {
    next.translation_provider = translationProvider.trim();
  }

  const translationBatchSize = coerceNumber(
    config['translation_batch_size'] ?? config['translation_llm_batch_size'] ?? config['llm_batch_size'],
  );
  if (translationBatchSize !== undefined) {
    next.translation_batch_size = Math.max(1, Math.trunc(translationBatchSize));
  }

  const transliterationMode = config['transliteration_mode'];
  if (typeof transliterationMode === 'string' && transliterationMode.trim()) {
    next.transliteration_mode = transliterationMode.trim();
  }
  const transliterationModel = config['transliteration_model'];
  if (typeof transliterationModel === 'string' && transliterationModel.trim()) {
    next.transliteration_model = transliterationModel.trim();
  }

  const enableLookupCache = config['enable_lookup_cache'];
  if (typeof enableLookupCache === 'boolean') {
    next.enable_lookup_cache = enableLookupCache;
  }

  const lookupCacheBatchSize = coerceNumber(config['lookup_cache_batch_size']);
  if (lookupCacheBatchSize !== undefined) {
    next.lookup_cache_batch_size = Math.max(1, Math.trunc(lookupCacheBatchSize));
  }

  const tempo = coerceNumber(config['tempo']);
  if (tempo !== undefined) {
    next.tempo = tempo;
  }

  const threadCount = coerceNumber(config['thread_count']);
  if (threadCount !== undefined) {
    next.thread_count = String(threadCount);
  }

  const queueSize = coerceNumber(config['queue_size']);
  if (queueSize !== undefined) {
    next.queue_size = String(queueSize);
  }

  const jobMaxWorkers = coerceNumber(config['job_max_workers']);
  if (jobMaxWorkers !== undefined) {
    next.job_max_workers = String(jobMaxWorkers);
  }

  const imageConcurrency = coerceNumber(config['image_concurrency']);
  if (imageConcurrency !== undefined) {
    next.image_concurrency = String(imageConcurrency);
  }

  const metadata = extractBookMetadata(config);
  if (metadata) {
    next.book_metadata = JSON.stringify(metadata, null, 2);
  }

  return next;
}

export function parseOptionalNumberInput(value: string): number | undefined {
  const trimmed = value.trim();
  if (!trimmed) {
    return undefined;
  }
  const parsed = Number(trimmed);
  if (Number.isNaN(parsed)) {
    return undefined;
  }
  return parsed;
}

export function parseEndSentenceInput(
  value: string,
  startSentence: number,
  implicitOffsetThreshold?: number | null,
): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  const parsedStart = Number(startSentence);
  if (!Number.isFinite(parsedStart) || parsedStart < 1) {
    throw new Error('Start sentence must be a positive number before setting an end sentence.');
  }
  const normalizedStart = Math.max(1, Math.trunc(parsedStart));

  const isOffset = trimmed.startsWith('+');
  const numericPortion = isOffset ? trimmed.slice(1).trim() : trimmed;
  const parsedEnd = Number(numericPortion);
  if (!Number.isFinite(parsedEnd)) {
    throw new Error('End sentence must be a number or a +offset from the start sentence.');
  }
  const normalizedEnd = Math.trunc(parsedEnd);
  if (normalizedEnd <= 0) {
    throw new Error('End sentence must be positive.');
  }

  const treatAsImplicitOffset =
    !isOffset &&
    typeof implicitOffsetThreshold === 'number' &&
    implicitOffsetThreshold > 0 &&
    normalizedEnd < implicitOffsetThreshold;

  const candidate =
    isOffset || treatAsImplicitOffset ? normalizedStart + normalizedEnd - 1 : normalizedEnd;
  if (candidate < normalizedStart) {
    throw new Error('End sentence must be greater than or equal to the start sentence.');
  }

  return candidate;
}

export function formatList(items: string[]): string {
  if (items.length === 0) {
    return '';
  }
  if (items.length === 1) {
    return items[0];
  }
  if (items.length === 2) {
    return `${items[0]} and ${items[1]}`;
  }
  const initial = items.slice(0, -1).join(', ');
  return `${initial}, and ${items[items.length - 1]}`;
}

export function resolveBookNarrationSectionMeta(
  base: BookNarrationSectionMeta,
  overrides: BookNarrationFormProps['sectionOverrides'],
): BookNarrationSectionMeta {
  const next: BookNarrationSectionMeta = { ...base };
  for (const [key, override] of Object.entries(overrides ?? {})) {
    if (!override) {
      continue;
    }
    const sectionKey = key as BookNarrationFormSection;
    next[sectionKey] = { ...base[sectionKey], ...override };
  }
  return next;
}

export function preserveBookNarrationUserEditedFields(
  previous: FormState,
  next: FormState,
  editedFields: Iterable<keyof FormState>,
): FormState {
  let result = next;
  let changed = false;
  for (const key of editedFields) {
    if (next[key] === previous[key]) {
      continue;
    }
    if (!changed) {
      result = { ...next };
      changed = true;
    }
    (result as Record<keyof FormState, FormState[keyof FormState]>)[key] = previous[key];
  }
  return result;
}

export function resolveBookNarrationMissingRequirements({
  formState,
  normalizedTargetLanguages,
  isGeneratedSource,
  chapterSelectionMode,
  hasChapterSelection,
}: {
  formState: FormState;
  normalizedTargetLanguages: string[];
  isGeneratedSource: boolean;
  chapterSelectionMode: string;
  hasChapterSelection: boolean;
}): string[] {
  const missingRequirements: string[] = [];
  if (!isGeneratedSource && !formState.input_file.trim()) {
    missingRequirements.push('an input EPUB');
  }
  if (!formState.base_output_file.trim()) {
    missingRequirements.push('a base output path');
  }
  if (normalizedTargetLanguages.length === 0) {
    missingRequirements.push('at least one target language');
  }
  if (!isGeneratedSource && chapterSelectionMode === 'chapters' && !hasChapterSelection) {
    missingRequirements.push('a chapter selection');
  }
  return missingRequirements;
}

export function deriveBaseOutputName(inputPath: string): string {
  if (!inputPath) {
    return '';
  }
  const segments = inputPath.split(/[/\\]/);
  const filename = segments[segments.length - 1] || inputPath;
  const withoutExtension = filename.replace(/\.epub$/i, '') || filename;
  const normalized = withoutExtension
    .trim()
    .replace(/[^A-Za-z0-9]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .toLowerCase();
  if (normalized) {
    return normalized;
  }
  if (withoutExtension.trim()) {
    return withoutExtension.trim();
  }
  return 'book-output';
}

export type LatestBookNarrationJobSelection = {
  input?: string | null;
  base?: string | null;
};

export type LatestBookNarrationJobSettings = {
  inputLanguage: string | null;
  targetLanguages: string[] | null;
  enableLookupCache: boolean | null;
};

export function normalizeBookNarrationPath(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const withoutTrail = trimmed.replace(/[\\/]+$/, '');
  return withoutTrail.toLowerCase();
}

function isReusableBookNarrationJob(job: PipelineStatusResponse | null | undefined): job is PipelineStatusResponse {
  return Boolean(job && job.job_type !== 'subtitle');
}

export function resolveStartFromNarrationHistory(
  inputPath: string,
  jobs: PipelineStatusResponse[] | null | undefined,
): number | null {
  const normalizedInput = normalizeBookNarrationPath(inputPath);
  if (!normalizedInput || !jobs || jobs.length === 0) {
    return null;
  }

  let latest: { created: number; anchor: number } | null = null;
  for (const job of jobs) {
    if (!isReusableBookNarrationJob(job)) {
      continue;
    }
    const params = job.parameters;
    if (!params) {
      continue;
    }
    const candidate = normalizeBookNarrationPath(params.input_file ?? params.base_output_file);
    if (!candidate || candidate !== normalizedInput) {
      continue;
    }
    const anchor =
      typeof params.end_sentence === 'number'
        ? params.end_sentence
        : typeof params.start_sentence === 'number'
          ? params.start_sentence
          : null;
    if (anchor === null) {
      continue;
    }
    const createdAt = new Date(job.created_at).getTime();
    if (!Number.isFinite(createdAt)) {
      continue;
    }
    if (!latest || createdAt > latest.created) {
      latest = { created: createdAt, anchor };
    }
  }

  if (!latest) {
    return null;
  }
  return Math.max(1, latest.anchor - 5);
}

export function resolveLatestBookNarrationJobSelection(
  jobs: PipelineStatusResponse[] | null | undefined,
): LatestBookNarrationJobSelection | null {
  if (!jobs || jobs.length === 0) {
    return null;
  }
  let latest: { created: number; input?: string | null; base?: string | null } | null = null;
  for (const job of jobs) {
    if (!isReusableBookNarrationJob(job)) {
      continue;
    }
    const createdAt = new Date(job.created_at).getTime();
    if (!Number.isFinite(createdAt)) {
      continue;
    }
    const params = job.parameters;
    const inputFile = params?.input_file ?? null;
    const baseOutput = params?.base_output_file ?? null;
    if (!inputFile && !baseOutput) {
      continue;
    }
    if (!latest || createdAt > latest.created) {
      latest = { created: createdAt, input: inputFile, base: baseOutput };
    }
  }
  if (!latest) {
    return null;
  }
  return { input: latest.input, base: latest.base };
}

export function resolveLatestBookNarrationJobSettings(
  jobs: PipelineStatusResponse[] | null | undefined,
): LatestBookNarrationJobSettings | null {
  if (!jobs || jobs.length === 0) {
    return null;
  }
  let latest: {
    created: number;
    inputLanguage: string | null;
    targetLanguages: string[] | null;
    enableLookupCache: boolean | null;
  } | null = null;
  for (const job of jobs) {
    if (!isReusableBookNarrationJob(job)) {
      continue;
    }
    const createdAt = new Date(job.created_at).getTime();
    if (!Number.isFinite(createdAt)) {
      continue;
    }
    const params = job.parameters;
    if (!params) {
      continue;
    }
    const inputLanguage =
      (typeof params.input_language === 'string' && params.input_language.trim()) ||
      (typeof params.source_language === 'string' && params.source_language.trim()) ||
      null;
    const targetLanguages =
      Array.isArray(params.target_languages) && params.target_languages.length > 0
        ? params.target_languages.filter((x): x is string => typeof x === 'string' && x.trim() !== '')
        : null;
    const enableLookupCache =
      typeof params.enable_lookup_cache === 'boolean' ? params.enable_lookup_cache : null;
    if (!inputLanguage && !targetLanguages && enableLookupCache === null) {
      continue;
    }
    if (!latest || createdAt > latest.created) {
      latest = { created: createdAt, inputLanguage, targetLanguages, enableLookupCache };
    }
  }
  if (!latest) {
    return null;
  }
  return {
    inputLanguage: latest.inputLanguage,
    targetLanguages: latest.targetLanguages,
    enableLookupCache: latest.enableLookupCache,
  };
}

export function applyBookNarrationPrefillParameters(
  previous: FormState,
  prefillParameters: JobParameterSnapshot,
  forcedBaseOutputFile: string | null | undefined,
): FormState {
  const targetLanguages =
    Array.isArray(prefillParameters.target_languages) && prefillParameters.target_languages.length > 0
      ? prefillParameters.target_languages
          .map((entry) => (typeof entry === 'string' ? entry.trim() : ''))
          .filter((entry) => entry.length > 0)
      : previous.target_languages;
  const normalizedTargetLanguages = normalizeSingleTargetLanguages(targetLanguages);
  const startSentence =
    typeof prefillParameters.start_sentence === 'number' && Number.isFinite(prefillParameters.start_sentence)
      ? prefillParameters.start_sentence
      : previous.start_sentence;
  const endSentence =
    typeof prefillParameters.end_sentence === 'number' && Number.isFinite(prefillParameters.end_sentence)
      ? String(prefillParameters.end_sentence)
      : previous.end_sentence;
  const inputLanguage =
    typeof prefillParameters.input_language === 'string' && prefillParameters.input_language.trim()
      ? prefillParameters.input_language.trim()
      : previous.input_language;
  const inputFile =
    typeof prefillParameters.input_file === 'string' && prefillParameters.input_file.trim()
      ? prefillParameters.input_file.trim()
      : previous.input_file;
  const baseOutputFile =
    typeof prefillParameters.base_output_file === 'string' && prefillParameters.base_output_file.trim()
      ? prefillParameters.base_output_file.trim()
      : previous.base_output_file;
  const sentencesPerOutput =
    typeof prefillParameters.sentences_per_output_file === 'number' &&
    Number.isFinite(prefillParameters.sentences_per_output_file)
      ? prefillParameters.sentences_per_output_file
      : previous.sentences_per_output_file;
  const audioMode =
    typeof prefillParameters.audio_mode === 'string' && prefillParameters.audio_mode.trim()
      ? prefillParameters.audio_mode.trim()
      : previous.audio_mode;
  const audioBitrate =
    typeof prefillParameters.audio_bitrate_kbps === 'number' &&
    Number.isFinite(prefillParameters.audio_bitrate_kbps)
      ? String(Math.trunc(prefillParameters.audio_bitrate_kbps))
      : previous.audio_bitrate_kbps;
  const selectedVoice =
    typeof prefillParameters.selected_voice === 'string' && prefillParameters.selected_voice.trim()
      ? prefillParameters.selected_voice.trim()
      : previous.selected_voice;
  const tempo =
    typeof prefillParameters.tempo === 'number' && Number.isFinite(prefillParameters.tempo)
      ? prefillParameters.tempo
      : previous.tempo;
  const includeTransliteration =
    typeof prefillParameters.enable_transliteration === 'boolean'
      ? prefillParameters.enable_transliteration
      : previous.include_transliteration;
  const translationProvider =
    typeof prefillParameters.translation_provider === 'string' && prefillParameters.translation_provider.trim()
      ? prefillParameters.translation_provider.trim()
      : previous.translation_provider;
  const translationBatchSize =
    typeof prefillParameters.translation_batch_size === 'number' &&
    Number.isFinite(prefillParameters.translation_batch_size)
      ? Math.max(1, Math.trunc(prefillParameters.translation_batch_size))
      : previous.translation_batch_size;
  const transliterationMode =
    typeof prefillParameters.transliteration_mode === 'string' && prefillParameters.transliteration_mode.trim()
      ? prefillParameters.transliteration_mode.trim()
      : previous.transliteration_mode;
  const transliterationModel =
    typeof prefillParameters.transliteration_model === 'string' &&
    prefillParameters.transliteration_model.trim()
      ? prefillParameters.transliteration_model.trim()
      : previous.transliteration_model;
  const addImages =
    typeof prefillParameters.add_images === 'boolean' ? prefillParameters.add_images : previous.add_images;
  const voiceOverrides =
    prefillParameters.voice_overrides && typeof prefillParameters.voice_overrides === 'object'
      ? { ...prefillParameters.voice_overrides }
      : previous.voice_overrides;

  return {
    ...previous,
    input_file: inputFile,
    base_output_file: forcedBaseOutputFile ?? baseOutputFile,
    input_language: inputLanguage,
    target_languages: normalizedTargetLanguages.length ? normalizedTargetLanguages : previous.target_languages,
    custom_target_languages: '',
    start_sentence: startSentence,
    end_sentence: endSentence,
    sentences_per_output_file: sentencesPerOutput,
    audio_mode: audioMode,
    audio_bitrate_kbps: audioBitrate,
    selected_voice: selectedVoice,
    tempo,
    include_transliteration: includeTransliteration,
    translation_provider: translationProvider,
    translation_batch_size: translationBatchSize,
    transliteration_mode: transliterationMode,
    transliteration_model: transliterationModel,
    add_images: addImages,
    voice_overrides: voiceOverrides,
  };
}
