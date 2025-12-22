import {
  DragEvent,
  FormEvent,
  ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from 'react';
import {
  MacOSVoice,
  PipelineFileBrowserResponse,
  PipelineFileEntry,
  PipelineRequestPayload,
  PipelineStatusResponse,
  JobParameterSnapshot,
  VoiceInventoryResponse,
  BookOpenLibraryMetadataPreviewResponse
} from '../../api/dtos';
import {
  fetchPipelineDefaults,
  fetchPipelineFiles,
  fetchBookContentIndex,
  fetchVoiceInventory,
  fetchLlmModels,
  deletePipelineEbook,
  synthesizeVoicePreview,
  uploadEpubFile,
  lookupBookOpenLibraryMetadataPreview,
  appendAccessToken,
  checkImageNodeAvailability
} from '../../api/client';
import {
  AUDIO_MODE_OPTIONS,
  AUDIO_QUALITY_OPTIONS,
  MenuOption,
  VOICE_OPTIONS,
  WRITTEN_MODE_OPTIONS
} from '../../constants/menuOptions';
import { resolveLanguageCode, resolveLanguageName } from '../../constants/languageCodes';
import { formatLanguageWithFlag } from '../../utils/languages';
import { sampleSentenceFor } from '../../utils/sampleSentences';
import {
  loadCachedBookCoverDataUrl,
  loadCachedBookCoverSourceUrl,
  loadCachedBookMetadataJson,
  persistCachedBookCoverDataUrl,
  persistCachedBookMetadataJson
} from '../../utils/bookMetadataCache';
import { useLanguagePreferences } from '../../context/LanguageProvider';
import BookNarrationSourceSection from './BookNarrationSourceSection';
import BookNarrationLanguageSection, {
  BookNarrationChapterOption
} from './BookNarrationLanguageSection';
import BookNarrationOutputSection from './BookNarrationOutputSection';
import BookNarrationImageSection from './BookNarrationImageSection';
import {
  DEFAULT_IMAGE_API_BASE_URLS,
  expandImageNodeCandidates,
  getImageNodeFallbacks
} from '../../constants/imageNodes';
import BookNarrationPerformanceSection from './BookNarrationPerformanceSection';
import BookMetadataSection from './BookMetadataSection';
import FileSelectionDialog from '../FileSelectionDialog';
import {
  basenameFromPath,
  blobToDataUrl,
  coerceRecord,
  isRecord,
  normalizeTextValue,
  parseJsonField,
  resolveCoverPreviewUrlFromCoverFile
} from './bookNarrationUtils';

const PREFERRED_SAMPLE_EBOOK = 'test-agatha-poirot-30sentences.epub';

function capitalize(value: string): string {
  if (!value) {
    return value;
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatMacOSVoiceIdentifier(voice: MacOSVoice): string {
  const quality = voice.quality ? voice.quality : 'Default';
  const genderSuffix = voice.gender ? ` - ${capitalize(voice.gender)}` : '';
  return `${voice.name} - ${voice.lang} - (${quality})${genderSuffix}`;
}

function formatMacOSVoiceLabel(voice: MacOSVoice): string {
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

const toFiniteNumber = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.trunc(value);
  }
  if (typeof value === 'string') {
    const parsed = Number.parseFloat(value);
    if (Number.isFinite(parsed)) {
      return Math.trunc(parsed);
    }
  }
  return null;
};

const normaliseContentIndexChapters = (payload: unknown): BookNarrationChapterOption[] => {
  if (!payload || typeof payload !== 'object') {
    return [];
  }
  const record = payload as Record<string, unknown>;
  const rawChapters = record.chapters;
  if (!Array.isArray(rawChapters)) {
    return [];
  }
  const chapters: BookNarrationChapterOption[] = [];
  rawChapters.forEach((entry, index) => {
    if (!entry || typeof entry !== 'object') {
      return;
    }
    const raw = entry as Record<string, unknown>;
    const start =
      toFiniteNumber(raw.start_sentence ?? raw.startSentence ?? raw.start) ?? null;
    if (!start || start <= 0) {
      return;
    }
    const sentenceCount =
      toFiniteNumber(raw.sentence_count ?? raw.sentenceCount) ?? null;
    let end = toFiniteNumber(raw.end_sentence ?? raw.endSentence ?? raw.end);
    if (end === null && sentenceCount !== null) {
      end = start + Math.max(sentenceCount - 1, 0);
    }
    const id =
      (typeof raw.id === 'string' && raw.id.trim()) || `chapter-${index + 1}`;
    const title =
      (typeof raw.title === 'string' && raw.title.trim()) ||
      (typeof raw.toc_label === 'string' && raw.toc_label.trim()) ||
      `Chapter ${index + 1}`;
    chapters.push({
      id,
      title,
      startSentence: start,
      endSentence: end ?? null
    });
  });
  return chapters;
};

const extractContentIndexTotalSentences = (payload: unknown): number | null => {
  if (!payload || typeof payload !== 'object') {
    return null;
  }
  const record = payload as Record<string, unknown>;
  const direct =
    toFiniteNumber(record.total_sentences ?? record.totalSentences ?? record.sentence_total ?? record.sentenceTotal);
  if (direct && direct > 0) {
    return direct;
  }
  const alignment = record.alignment;
  if (alignment && typeof alignment === 'object') {
    const alignmentRecord = alignment as Record<string, unknown>;
    const aligned =
      toFiniteNumber(alignmentRecord.sentence_total ?? alignmentRecord.sentenceTotal ?? alignmentRecord.total_sentences);
    if (aligned && aligned > 0) {
      return aligned;
    }
  }
  return null;
};
export type BookNarrationFormSection =
  | 'source'
  | 'metadata'
  | 'language'
  | 'output'
  | 'images'
  | 'performance'
  | 'submit';

type BookNarrationFormProps = {
  onSubmit: (payload: PipelineRequestPayload) => Promise<void> | void;
  isSubmitting?: boolean;
  activeSection?: BookNarrationFormSection;
  onSectionChange?: (section: BookNarrationFormSection) => void;
  externalError?: string | null;
  prefillInputFile?: string | null;
  prefillParameters?: JobParameterSnapshot | null;
  recentJobs?: PipelineStatusResponse[] | null;
  sourceMode?: 'upload' | 'generated';
  submitLabel?: string;
  forcedBaseOutputFile?: string | null;
  customSourceSection?: ReactNode;
  implicitEndOffsetThreshold?: number | null;
  sectionOverrides?: Partial<Record<BookNarrationFormSection, { title: string; description: string }>>;
  showInfoHeader?: boolean;
  showOutputPathControls?: boolean;
  defaultImageSettings?: ImageDefaults | null;
};

type JsonFields =
  | 'config'
  | 'environment_overrides'
  | 'pipeline_overrides'
  | 'book_metadata';

type FormState = {
  input_file: string;
  base_output_file: string;
  input_language: string;
  target_languages: string[];
  custom_target_languages: string;
  ollama_model: string;
  sentences_per_output_file: number;
  start_sentence: number;
  end_sentence: string;
  stitch_full: boolean;
  generate_audio: boolean;
  audio_mode: string;
  audio_bitrate_kbps: string;
  written_mode: string;
  selected_voice: string;
  voice_overrides: Record<string, string>;
  output_html: boolean;
  output_pdf: boolean;
  generate_video: boolean;
  add_images: boolean;
  image_style_template: string;
  image_prompt_batching_enabled: boolean;
  image_prompt_batch_size: number;
  image_prompt_plan_batch_size: number;
  image_prompt_context_sentences: number;
  image_seed_with_previous_image: boolean;
  image_blank_detection_enabled: boolean;
  image_api_base_urls: string[];
  image_width: string;
  image_height: string;
  image_steps: string;
  image_cfg_scale: string;
  image_sampler_name: string;
  image_api_timeout_seconds: string;
  include_transliteration: boolean;
  tempo: number;
  thread_count: string;
  queue_size: string;
  job_max_workers: string;
  image_concurrency: string;
  slide_parallelism: string;
  slide_parallel_workers: string;
  config: string;
  environment_overrides: string;
  pipeline_overrides: string;
  book_metadata: string;
};

type ImageDefaults = {
  add_images: boolean;
  image_style_template: string;
  image_prompt_context_sentences: number;
  image_width: string;
  image_height: string;
};

const IMAGE_DEFAULT_FIELDS = new Set<keyof FormState>([
  'add_images',
  'image_style_template',
  'image_prompt_context_sentences',
  'image_width',
  'image_height',
]);

const DEFAULT_FORM_STATE: FormState = {
  input_file: '',
  base_output_file: '',
  input_language: 'English',
  target_languages: ['Arabic'],
  custom_target_languages: '',
  ollama_model: 'kimi-k2:1t-cloud',
  sentences_per_output_file: 1,
  start_sentence: 1,
  end_sentence: '',
  stitch_full: false,
  generate_audio: true,
  audio_mode: '4',
  audio_bitrate_kbps: '96',
  written_mode: '4',
  selected_voice: 'gTTS',
  voice_overrides: {},
  output_html: false,
  output_pdf: false,
  generate_video: false,
  add_images: false,
  image_style_template: 'comics',
  image_prompt_batching_enabled: true,
  image_prompt_batch_size: 10,
  image_prompt_plan_batch_size: 50,
  image_prompt_context_sentences: 2,
  image_seed_with_previous_image: false,
  image_blank_detection_enabled: false,
  image_api_base_urls: [...DEFAULT_IMAGE_API_BASE_URLS],
  image_width: '',
  image_height: '',
  image_steps: '',
  image_cfg_scale: '',
  image_sampler_name: '',
  image_api_timeout_seconds: '300',
  include_transliteration: true,
  tempo: 1,
  thread_count: '',
  queue_size: '',
  job_max_workers: '',
  image_concurrency: '',
  slide_parallelism: '',
  slide_parallel_workers: '',
  config: '{}',
  environment_overrides: '{}',
  pipeline_overrides: '{}',
  book_metadata: '{}'
};

const BOOK_NARRATION_TAB_SECTIONS: BookNarrationFormSection[] = [
  'source',
  'metadata',
  'language',
  'output',
  'images',
  'performance'
];

export const BOOK_NARRATION_SECTION_META: Record<
  BookNarrationFormSection,
  { title: string; description: string }
> = {
  source: {
    title: 'Source',
    description: 'Select the EPUB to ingest and where generated files should be written.'
  },
  metadata: {
    title: 'Metadata',
    description: 'Load book metadata from Open Library (no API key) and edit it before submitting the job.'
  },
  language: {
    title: 'Language & translation',
    description: 'Configure the input language, target translations, and processing window.'
  },
  output: {
    title: 'Output & narration',
    description: 'Control narration voices, written formats, and presentation options.'
  },
  images: {
    title: 'Images',
    description: 'Generate sentence images and tune the diffusion settings.'
  },
  performance: {
    title: 'Performance tuning',
    description: 'Adjust concurrency and orchestration parameters to fit your environment.'
  },
  submit: {
    title: 'Submit book job',
    description: 'Review the configured settings and enqueue the book job for processing.'
  }
};

function areLanguageArraysEqual(left: string[], right: string[]): boolean {
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

function normalizeSingleTargetLanguages(languages: string[]): string[] {
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

function coerceNumber(value: unknown): number | undefined {
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

function coerceStringList(value: unknown): string[] | undefined {
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

function normalizeBaseUrl(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  return trimmed.replace(/\/+$/, '');
}

function normalizeBaseUrls(values: string[]): string[] {
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

async function resolveImageBaseUrlsForSubmission(values: string[]): Promise<string[]> {
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

function extractBookMetadata(config: Record<string, unknown>): Record<string, unknown> | null {
  const metadata: Record<string, unknown> = {};
  const nested = config['book_metadata'];
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
    'book_cover_file'
  ];

  for (const key of preferredKeys) {
    const value = config[key];
    if (value !== undefined && value !== null) {
      metadata[key] = value;
    }
  }

  return Object.keys(metadata).length > 0 ? metadata : null;
}

function applyConfigDefaults(previous: FormState, config: Record<string, unknown>): FormState {
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
          .filter((language) => language.length > 0)
      )
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

  const generateVideo = config['generate_video'];
  if (typeof generateVideo === 'boolean') {
    next.generate_video = generateVideo;
  }

  const addImages = config['add_images'];
  if (typeof addImages === 'boolean') {
    next.add_images = addImages;
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
    typeof config['image_api_base_url'] === 'string' ? config['image_api_base_url'] : null
  );
  if (imageApiBaseUrls.length > 0) {
    next.image_api_base_urls = imageApiBaseUrls;
  } else if (imageApiBaseUrl) {
    next.image_api_base_urls = [imageApiBaseUrl];
  }

  const imageApiTimeoutSeconds = coerceNumber(config['image_api_timeout_seconds']);
  if (imageApiTimeoutSeconds !== undefined) {
    next.image_api_timeout_seconds = String(
      Math.max(300, Math.max(1, Math.trunc(imageApiTimeoutSeconds)))
    );
  }

  const includeTransliteration = config['include_transliteration'];
  if (typeof includeTransliteration === 'boolean') {
    next.include_transliteration = includeTransliteration;
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

  const slideParallelism = config['slide_parallelism'];
  if (typeof slideParallelism === 'string') {
    next.slide_parallelism = slideParallelism;
  }

  const slideParallelWorkers = coerceNumber(config['slide_parallel_workers']);
  if (slideParallelWorkers !== undefined) {
    next.slide_parallel_workers = String(slideParallelWorkers);
  }

  const metadata = extractBookMetadata(config);
  if (metadata) {
    next.book_metadata = JSON.stringify(metadata, null, 2);
  }

  return next;
}

function parseOptionalNumberInput(value: string): number | undefined {
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

function parseEndSentenceInput(
  value: string,
  startSentence: number,
  implicitOffsetThreshold?: number | null
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

function formatList(items: string[]): string {
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

const ESTIMATED_AUDIO_SECONDS_PER_SENTENCE = 6.4;

function formatDuration(seconds: number): string {
  const total = Math.max(0, Math.trunc(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const remainingSeconds = total % 60;
  return `${hours.toString().padStart(2, '0')}:${minutes
    .toString()
    .padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function deriveBaseOutputName(inputPath: string): string {
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

export function BookNarrationForm({
  onSubmit,
  isSubmitting = false,
  activeSection,
  onSectionChange,
  externalError = null,
  prefillInputFile = null,
  prefillParameters = null,
  recentJobs = null,
  sourceMode = 'upload',
  submitLabel,
  forcedBaseOutputFile = null,
  customSourceSection = null,
  implicitEndOffsetThreshold = null,
  sectionOverrides = {},
  showInfoHeader = true,
  showOutputPathControls = true,
  defaultImageSettings = null
}: BookNarrationFormProps) {
  const isGeneratedSource = sourceMode === 'generated';
  const imageDefaults = defaultImageSettings ?? null;
  const userEditedImageDefaultsRef = useRef<Set<keyof FormState>>(new Set());
  const {
    inputLanguage: sharedInputLanguage,
    setInputLanguage: setSharedInputLanguage,
    targetLanguages: sharedTargetLanguages,
    setTargetLanguages: setSharedTargetLanguages
  } = useLanguagePreferences();
  const hasPrefillAddImages = typeof prefillParameters?.add_images === 'boolean';
  const applyImageDefaults = useCallback(
    (state: FormState): FormState => {
      if (!imageDefaults) {
        return state;
      }
      const edited = userEditedImageDefaultsRef.current;
      let next = state;
      let changed = false;
      const merge = (partial: Partial<FormState>) => {
        if (!changed) {
          next = { ...state, ...partial };
          changed = true;
          return;
        }
        next = { ...next, ...partial };
      };
      if (!hasPrefillAddImages && !edited.has('add_images') && state.add_images !== imageDefaults.add_images) {
        merge({ add_images: imageDefaults.add_images });
      }
      if (!edited.has('image_style_template') && state.image_style_template !== imageDefaults.image_style_template) {
        merge({ image_style_template: imageDefaults.image_style_template });
      }
      const normalizedContext = Math.max(
        0,
        Math.min(50, Math.trunc(imageDefaults.image_prompt_context_sentences))
      );
      if (
        !edited.has('image_prompt_context_sentences') &&
        state.image_prompt_context_sentences !== normalizedContext
      ) {
        merge({ image_prompt_context_sentences: normalizedContext });
      }
      if (!edited.has('image_width') && state.image_width !== imageDefaults.image_width) {
        merge({ image_width: imageDefaults.image_width });
      }
      if (!edited.has('image_height') && state.image_height !== imageDefaults.image_height) {
        merge({ image_height: imageDefaults.image_height });
      }
      return changed ? next : state;
    },
    [hasPrefillAddImages, imageDefaults]
  );
  const [formState, setFormState] = useState<FormState>(() => ({
    ...DEFAULT_FORM_STATE,
    base_output_file: forcedBaseOutputFile ?? DEFAULT_FORM_STATE.base_output_file,
    input_language: sharedInputLanguage ?? DEFAULT_FORM_STATE.input_language,
    target_languages:
      sharedTargetLanguages.length > 0
        ? normalizeSingleTargetLanguages(sharedTargetLanguages)
        : [...DEFAULT_FORM_STATE.target_languages]
  }));
  useEffect(() => {
    setFormState((previous) => applyImageDefaults(previous));
  }, [applyImageDefaults]);
  const [error, setError] = useState<string | null>(null);
  const [fileOptions, setFileOptions] = useState<PipelineFileBrowserResponse | null>(null);
  const [fileDialogError, setFileDialogError] = useState<string | null>(null);
  const [isLoadingFiles, setIsLoadingFiles] = useState<boolean>(true);
  const [activeFileDialog, setActiveFileDialog] = useState<'input' | 'output' | null>(null);
  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [recentUploadName, setRecentUploadName] = useState<string | null>(null);
  const [voiceInventory, setVoiceInventory] = useState<VoiceInventoryResponse | null>(null);
  const [voiceInventoryError, setVoiceInventoryError] = useState<string | null>(null);
  const [isLoadingVoiceInventory, setIsLoadingVoiceInventory] = useState<boolean>(false);
  const [voicePreviewStatus, setVoicePreviewStatus] = useState<Record<string, 'idle' | 'loading' | 'playing'>>({});
  const [voicePreviewError, setVoicePreviewError] = useState<Record<string, string>>({});
  const [availableLlmModels, setAvailableLlmModels] = useState<string[]>([]);
  const [llmModelError, setLlmModelError] = useState<string | null>(null);
  const [isLoadingLlmModels, setIsLoadingLlmModels] = useState<boolean>(false);
  const previewAudioRef = useRef<{ audio: HTMLAudioElement; url: string; code: string } | null>(null);
  const prefillAppliedRef = useRef<string | null>(null);
  const prefillParametersRef = useRef<string | null>(null);
  const recentJobsRef = useRef<PipelineStatusResponse[] | null>(recentJobs ?? null);
  const userEditedStartRef = useRef<boolean>(false);
  const userEditedInputRef = useRef<boolean>(false);
  const userEditedEndRef = useRef<boolean>(false);
  const userEditedFieldsRef = useRef<Set<keyof FormState>>(new Set<keyof FormState>());
  const defaultsAppliedRef = useRef<boolean>(false);
  const lastAutoEndSentenceRef = useRef<string | null>(null);

  const metadataSourceName = useMemo(() => {
    if (isGeneratedSource) {
      return '';
    }
    if (!formState.input_file.trim()) {
      return '';
    }
    return basenameFromPath(formState.input_file);
  }, [formState.input_file, isGeneratedSource]);
  const [metadataLookupQuery, setMetadataLookupQuery] = useState<string>('');
  const [metadataPreview, setMetadataPreview] = useState<BookOpenLibraryMetadataPreviewResponse | null>(null);
  const [metadataLoading, setMetadataLoading] = useState<boolean>(false);
  const [metadataError, setMetadataError] = useState<string | null>(null);
  const metadataLookupIdRef = useRef<number>(0);
  const metadataAutoLookupRef = useRef<string | null>(null);
  const [chapterOptions, setChapterOptions] = useState<BookNarrationChapterOption[]>([]);
  const [contentIndexTotalSentences, setContentIndexTotalSentences] = useState<number | null>(null);
  const [chaptersLoading, setChaptersLoading] = useState<boolean>(false);
  const [chaptersError, setChaptersError] = useState<string | null>(null);
  const [chapterSelectionMode, setChapterSelectionMode] = useState<'range' | 'chapters'>('range');
  const [chapterRangeSelection, setChapterRangeSelection] = useState<{ startIndex: number; endIndex: number } | null>(
    null
  );
  const chapterLookupIdRef = useRef<number>(0);

  const sectionMeta = useMemo(() => {
    const base: Record<BookNarrationFormSection, { title: string; description: string }> = {
      ...BOOK_NARRATION_SECTION_META
    };
    for (const [key, override] of Object.entries(sectionOverrides)) {
      if (!override) {
        continue;
      }
      const sectionKey = key as BookNarrationFormSection;
      base[sectionKey] = { ...BOOK_NARRATION_SECTION_META[sectionKey], ...override };
    }
    return base;
  }, [sectionOverrides]);

  useEffect(() => {
    recentJobsRef.current = recentJobs ?? null;
  }, [recentJobs]);
  const normalizePath = useCallback((value: string | null | undefined): string | null => {
    if (!value) {
      return null;
    }
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    const withoutTrail = trimmed.replace(/[\\/]+$/, '');
    return withoutTrail.toLowerCase();
  }, []);
  const chapterIndexLookup = useMemo(() => {
    const map = new Map<string, number>();
    chapterOptions.forEach((chapter, index) => {
      map.set(chapter.id, index);
    });
    return map;
  }, [chapterOptions]);
  const selectedChapterIds = useMemo(() => {
    if (!chapterRangeSelection) {
      return [];
    }
    const { startIndex, endIndex } = chapterRangeSelection;
    if (startIndex < 0 || endIndex < startIndex || startIndex >= chapterOptions.length) {
      return [];
    }
    return chapterOptions.slice(startIndex, endIndex + 1).map((chapter) => chapter.id);
  }, [chapterOptions, chapterRangeSelection]);
  const chapterSelection = useMemo(() => {
    if (!chapterRangeSelection) {
      return null;
    }
    const { startIndex, endIndex } = chapterRangeSelection;
    const startChapter = chapterOptions[startIndex];
    const endChapter = chapterOptions[endIndex];
    if (!startChapter || !endChapter) {
      return null;
    }
    const startSentence = startChapter.startSentence;
    const endSentence =
      typeof endChapter.endSentence === 'number' ? endChapter.endSentence : endChapter.startSentence;
    return {
      startIndex,
      endIndex,
      startSentence,
      endSentence,
      count: Math.max(1, endIndex - startIndex + 1)
    };
  }, [chapterOptions, chapterRangeSelection]);
  const chapterSelectionSummary = useMemo(() => {
    if (chapterSelectionMode !== 'chapters') {
      return '';
    }
    if (chaptersLoading || chaptersError || chapterOptions.length === 0) {
      return '';
    }
    if (!chapterSelection) {
      return 'Select consecutive chapters to set the processing window.';
    }
    const startLabel = chapterOptions[chapterSelection.startIndex]?.title ?? 'Chapter';
    const endLabel = chapterOptions[chapterSelection.endIndex]?.title ?? 'Chapter';
    const chapterLabel =
      chapterSelection.count === 1 ? startLabel : `${startLabel} – ${endLabel}`;
    return `${chapterLabel} • sentences ${chapterSelection.startSentence}-${chapterSelection.endSentence}`;
  }, [
    chapterOptions,
    chapterSelection,
    chapterSelectionMode,
    chaptersError,
    chaptersLoading
  ]);
  const totalSentencesFromIndex = useMemo(() => {
    if (contentIndexTotalSentences && contentIndexTotalSentences > 0) {
      return contentIndexTotalSentences;
    }
    if (chapterOptions.length === 0) {
      return null;
    }
    let maxSentence = 0;
    chapterOptions.forEach((chapter) => {
      const end =
        typeof chapter.endSentence === 'number' ? chapter.endSentence : chapter.startSentence;
      if (end > maxSentence) {
        maxSentence = end;
      }
    });
    return maxSentence > 0 ? maxSentence : null;
  }, [chapterOptions, contentIndexTotalSentences]);
  const estimatedSentenceRange = useMemo(() => {
    if (chapterSelectionMode === 'chapters') {
      if (!chapterSelection) {
        return null;
      }
      return {
        start: chapterSelection.startSentence,
        end: chapterSelection.endSentence
      };
    }
    const start = Math.max(1, Math.trunc(Number(formState.start_sentence)));
    if (!Number.isFinite(start)) {
      return null;
    }
    let end: number | null = null;
    try {
      end = parseEndSentenceInput(
        formState.end_sentence,
        start,
        implicitEndOffsetThreshold
      );
    } catch {
      end = null;
    }
    if (end === null) {
      end = totalSentencesFromIndex;
    }
    if (end === null || !Number.isFinite(end)) {
      return null;
    }
    if (end < start) {
      return null;
    }
    return { start, end };
  }, [
    chapterSelection,
    chapterSelectionMode,
    formState.end_sentence,
    formState.start_sentence,
    implicitEndOffsetThreshold,
    totalSentencesFromIndex
  ]);
  const estimatedSentenceCount = useMemo(() => {
    if (!estimatedSentenceRange) {
      return null;
    }
    const count = Math.max(0, estimatedSentenceRange.end - estimatedSentenceRange.start + 1);
    return count > 0 ? count : null;
  }, [estimatedSentenceRange]);
  const estimatedAudioDurationLabel = useMemo(() => {
    if (!estimatedSentenceCount) {
      return null;
    }
    const estimatedSeconds = estimatedSentenceCount * ESTIMATED_AUDIO_SECONDS_PER_SENTENCE;
    if (!Number.isFinite(estimatedSeconds) || estimatedSeconds <= 0) {
      return null;
    }
    const sentenceLabel = estimatedSentenceCount === 1 ? 'sentence' : 'sentences';
    return `Estimated audio duration: ~${formatDuration(estimatedSeconds)} (${estimatedSentenceCount} ${sentenceLabel}, ${ESTIMATED_AUDIO_SECONDS_PER_SENTENCE.toFixed(
      1
    )}s/sentence)`;
  }, [estimatedSentenceCount]);
  const markUserEditedField = useCallback((key: keyof FormState) => {
    userEditedFieldsRef.current.add(key);
  }, []);
  const preserveUserEditedFields = useCallback((previous: FormState, next: FormState): FormState => {
    const edited = userEditedFieldsRef.current;
    if (edited.size === 0) {
      return next;
    }
    let result = next;
    let changed = false;
    for (const key of edited) {
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
  }, []);

  const normalizedInputForBookMetadataCache = useMemo(() => {
    if (isGeneratedSource) {
      return null;
    }
    return normalizePath(formState.input_file);
  }, [formState.input_file, isGeneratedSource, normalizePath]);
  const chaptersDisabled = isGeneratedSource || !formState.input_file.trim();

  useEffect(() => {
    setChapterRangeSelection(null);
  }, [normalizedInputForBookMetadataCache]);

  useEffect(() => {
    const trimmedInput = formState.input_file.trim();
    if (isGeneratedSource || !trimmedInput) {
      chapterLookupIdRef.current += 1;
      setChapterOptions([]);
      setContentIndexTotalSentences(null);
      setChaptersLoading(false);
      setChaptersError(null);
      return;
    }
    const requestId = chapterLookupIdRef.current + 1;
    chapterLookupIdRef.current = requestId;
    setChaptersLoading(true);
    setChaptersError(null);
    void (async () => {
      try {
        const payload = await fetchBookContentIndex(trimmedInput);
        if (chapterLookupIdRef.current !== requestId) {
          return;
        }
        const chapters = normaliseContentIndexChapters(payload.content_index);
        const totalSentences = extractContentIndexTotalSentences(payload.content_index);
        setChapterOptions(chapters);
        setContentIndexTotalSentences(totalSentences);
      } catch (error) {
        if (chapterLookupIdRef.current !== requestId) {
          return;
        }
        const message = error instanceof Error ? error.message : 'Unable to load chapter data.';
        setChaptersError(message);
        setChapterOptions([]);
        setContentIndexTotalSentences(null);
      } finally {
        if (chapterLookupIdRef.current === requestId) {
          setChaptersLoading(false);
        }
      }
    })();
  }, [formState.input_file, isGeneratedSource]);

  useEffect(() => {
    if (chaptersDisabled && chapterSelectionMode === 'chapters') {
      setChapterSelectionMode('range');
    }
  }, [chaptersDisabled, chapterSelectionMode]);

  const [cachedCoverDataUrl, setCachedCoverDataUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!normalizedInputForBookMetadataCache) {
      setCachedCoverDataUrl(null);
      return;
    }
    setCachedCoverDataUrl(loadCachedBookCoverDataUrl(normalizedInputForBookMetadataCache));
  }, [normalizedInputForBookMetadataCache]);

  const lastCoverCacheRequestRef = useRef<string | null>(null);
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (!normalizedInputForBookMetadataCache) {
      lastCoverCacheRequestRef.current = null;
      return;
    }

    let parsed: Record<string, unknown> | null = null;
    try {
      parsed = parseJsonField('book_metadata', formState.book_metadata);
    } catch {
      parsed = null;
    }

    const coverAssetUrl = normalizeTextValue(parsed?.['job_cover_asset_url']);
    const coverFile = normalizeTextValue(parsed?.['book_cover_file']);
    const coverUrl = normalizeTextValue(parsed?.['cover_url']);
    const coverCandidate =
      (coverAssetUrl ? appendAccessToken(coverAssetUrl) : null) ||
      resolveCoverPreviewUrlFromCoverFile(coverFile) ||
      (coverUrl && (/^https?:\/\//i.test(coverUrl) || coverUrl.startsWith('//')) ? coverUrl : null);
    if (!coverCandidate || coverCandidate.startsWith('data:')) {
      return;
    }

    let url: URL;
    try {
      url = new URL(coverCandidate, window.location.href);
    } catch {
      return;
    }

    const isSameOrigin = url.origin === window.location.origin;
    const stableSource =
      isSameOrigin && url.pathname.startsWith('/storage/covers/')
        ? `${url.origin}${url.pathname}`
        : url.href;
    const existingSource = loadCachedBookCoverSourceUrl(normalizedInputForBookMetadataCache);
    if (existingSource === stableSource && cachedCoverDataUrl) {
      return;
    }
    if (lastCoverCacheRequestRef.current === stableSource) {
      return;
    }
    lastCoverCacheRequestRef.current = stableSource;

    const controller = new AbortController();
    void (async () => {
      try {
        const response = await fetch(url.href, {
          credentials: isSameOrigin ? 'include' : 'omit',
          signal: controller.signal
        });
        if (!response.ok) {
          return;
        }
        const blob = await response.blob();
        if (!blob.type.startsWith('image/')) {
          return;
        }
        if (blob.size > 250_000) {
          return;
        }
        const dataUrl = await blobToDataUrl(blob);
        if (!dataUrl) {
          return;
        }
        persistCachedBookCoverDataUrl(normalizedInputForBookMetadataCache, stableSource, dataUrl);
        setCachedCoverDataUrl(dataUrl);
      } catch {
        // ignore
      }
    })();

    return () => controller.abort();
  }, [cachedCoverDataUrl, formState.book_metadata, normalizedInputForBookMetadataCache]);

  const bookMetadataCacheHydratedRef = useRef<string | null>(null);
  useEffect(() => {
    if (!normalizedInputForBookMetadataCache) {
      bookMetadataCacheHydratedRef.current = null;
      return;
    }
    if (bookMetadataCacheHydratedRef.current === normalizedInputForBookMetadataCache) {
      return;
    }
    bookMetadataCacheHydratedRef.current = normalizedInputForBookMetadataCache;

    const cached = loadCachedBookMetadataJson(normalizedInputForBookMetadataCache);
    if (!cached) {
      return;
    }
    setFormState((previous) => {
      const previousNormalized = normalizePath(previous.input_file);
      if (previousNormalized !== normalizedInputForBookMetadataCache) {
        return previous;
      }
      const current = previous.book_metadata.trim();
      if (current && current !== '{}' && current !== 'null') {
        return previous;
      }
      return { ...previous, book_metadata: cached };
    });
  }, [normalizedInputForBookMetadataCache, normalizePath]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (!normalizedInputForBookMetadataCache) {
      return;
    }
    const raw = formState.book_metadata;
    const trimmed = raw.trim();
    if (!trimmed || trimmed === '{}' || trimmed === 'null') {
      return;
    }

    const handle = window.setTimeout(() => {
      persistCachedBookMetadataJson(normalizedInputForBookMetadataCache, raw);
    }, 600);
    return () => {
      window.clearTimeout(handle);
    };
  }, [formState.book_metadata, normalizedInputForBookMetadataCache]);

  const resolveStartFromHistory = useCallback(
    (inputPath: string): number | null => {
      const normalizedInput = normalizePath(inputPath);
      const jobs = recentJobsRef.current;
      if (!normalizedInput || !jobs || jobs.length === 0) {
        return null;
      }

      let latest: { created: number; anchor: number } | null = null;
      for (const job of jobs) {
        if (!job || job.job_type === 'subtitle') {
          continue;
        }
        const params = job.parameters;
        if (!params) {
          continue;
        }
        const candidate = normalizePath(params.input_file ?? params.base_output_file);
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
    },
    [normalizePath]
  );

  const applyMetadataLookupToDraft = useCallback(
    (payload: BookOpenLibraryMetadataPreviewResponse) => {
      const lookup = coerceRecord(payload.book_metadata_lookup);
      const query = coerceRecord(payload.query);
      const book = lookup ? coerceRecord(lookup['book']) : null;

      const jobLabel =
        normalizeTextValue(lookup?.['job_label']) ||
        normalizeTextValue(book?.['title']) ||
        normalizeTextValue(query?.['title']) ||
        (payload.source_name ? basenameFromPath(payload.source_name) : null);
      const bookTitle = normalizeTextValue(book?.['title']) || normalizeTextValue(query?.['title']);
      const bookAuthor = normalizeTextValue(book?.['author']) || normalizeTextValue(query?.['author']);
      const bookYear = normalizeTextValue(book?.['year']);
      const isbn =
        normalizeTextValue(book?.['isbn']) || normalizeTextValue(query?.['isbn']) || normalizeTextValue(lookup?.['isbn']);
      const summary = normalizeTextValue(book?.['summary']);
      const coverUrl = normalizeTextValue(book?.['cover_url']);
      const coverFile = normalizeTextValue(book?.['cover_file']);
      const openlibraryWorkKey = normalizeTextValue(book?.['openlibrary_work_key']);
      const openlibraryWorkUrl = normalizeTextValue(book?.['openlibrary_work_url']);
      const openlibraryBookKey = normalizeTextValue(book?.['openlibrary_book_key']);
      const openlibraryBookUrl = normalizeTextValue(book?.['openlibrary_book_url']);

      setFormState((previous) => {
        let draft: Record<string, unknown> = {};
        try {
          const parsed = parseJsonField('book_metadata', previous.book_metadata);
          draft = { ...parsed };
        } catch {
          draft = {};
        }

        if (jobLabel) {
          draft['job_label'] = jobLabel;
        }
        if (bookTitle) {
          draft['book_title'] = bookTitle;
        }
        if (bookAuthor) {
          draft['book_author'] = bookAuthor;
        }
        if (bookYear) {
          draft['book_year'] = bookYear;
        }
        if (isbn) {
          draft['isbn'] = isbn;
          draft['book_isbn'] = isbn;
        }
        if (summary) {
          draft['book_summary'] = summary;
        }
        if (coverUrl) {
          draft['cover_url'] = coverUrl;
        }
        if (coverFile) {
          draft['book_cover_file'] = coverFile;
        }
        if (openlibraryWorkKey) {
          draft['openlibrary_work_key'] = openlibraryWorkKey;
        }
        if (openlibraryWorkUrl) {
          draft['openlibrary_work_url'] = openlibraryWorkUrl;
        }
        if (openlibraryBookKey) {
          draft['openlibrary_book_key'] = openlibraryBookKey;
        }
        if (openlibraryBookUrl) {
          draft['openlibrary_book_url'] = openlibraryBookUrl;
        }
        const queriedAt = normalizeTextValue(lookup?.['queried_at']);
        if (queriedAt) {
          draft['openlibrary_queried_at'] = queriedAt;
        }
        if (lookup) {
          draft['book_metadata_lookup'] = lookup;
        } else if ('book_metadata_lookup' in draft) {
          delete draft['book_metadata_lookup'];
        }

        const nextJson = JSON.stringify(draft, null, 2);
        if (previous.book_metadata === nextJson) {
          return previous;
        }
        return { ...previous, book_metadata: nextJson };
      });
    },
    []
  );

  const performMetadataLookup = useCallback(
    async (query: string, force: boolean) => {
      const normalized = query.trim();
      if (!normalized) {
        setMetadataPreview(null);
        setMetadataError(null);
        setMetadataLoading(false);
        return;
      }

      const requestId = metadataLookupIdRef.current + 1;
      metadataLookupIdRef.current = requestId;
      setMetadataLoading(true);
      setMetadataError(null);
      try {
        const payload = await lookupBookOpenLibraryMetadataPreview({ query: normalized, force });
        if (metadataLookupIdRef.current !== requestId) {
          return;
        }
        setMetadataPreview(payload);
        applyMetadataLookupToDraft(payload);
      } catch (error) {
        if (metadataLookupIdRef.current !== requestId) {
          return;
        }
        const message = error instanceof Error ? error.message : 'Unable to lookup book metadata.';
        setMetadataError(message);
        setMetadataPreview(null);
      } finally {
        if (metadataLookupIdRef.current === requestId) {
          setMetadataLoading(false);
        }
      }
    },
    [applyMetadataLookupToDraft]
  );

  const handleClearMetadata = useCallback(() => {
    setMetadataPreview(null);
    setMetadataError(null);
    setMetadataLoading(false);
    markUserEditedField('book_metadata');
    setFormState((previous) => ({ ...previous, book_metadata: '{}' }));
  }, [markUserEditedField]);

  const resolveLatestJobSelection = useCallback((): { input?: string | null; base?: string | null } | null => {
    const jobs = recentJobsRef.current;
    if (!jobs || jobs.length === 0) {
      return null;
    }
    let latest: { created: number; input?: string | null; base?: string | null } | null = null;
    for (const job of jobs) {
      if (!job || job.job_type === 'subtitle') {
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
    return latest;
  }, []);

  const cleanupPreviewAudio = useCallback(() => {
    const current = previewAudioRef.current;
    if (!current) {
      return;
    }

    current.audio.onended = null;
    current.audio.onerror = null;
    current.audio.pause();
    previewAudioRef.current = null;
    URL.revokeObjectURL(current.url);
    setVoicePreviewStatus((previous) => {
      if (previous[current.code] === 'idle') {
        return previous;
      }
      return { ...previous, [current.code]: 'idle' };
    });
  }, []);

  const tabSections: BookNarrationFormSection[] = BOOK_NARRATION_TAB_SECTIONS;
  const [activeTab, setActiveTab] = useState<BookNarrationFormSection>(() => {
    if (activeSection && tabSections.includes(activeSection)) {
      return activeSection;
    }
    return 'source';
  });

  const handleSectionChange = useCallback(
    (section: BookNarrationFormSection) => {
      setActiveTab(section);
      onSectionChange?.(section);
    },
    [onSectionChange]
  );

  useEffect(() => {
    if (activeSection && tabSections.includes(activeSection)) {
      setActiveTab(activeSection);
    }
  }, [activeSection, tabSections]);

  useEffect(() => {
    if (prefillInputFile === undefined) {
      return;
    }
    const normalizedPrefill = prefillInputFile && prefillInputFile.trim();
    if (!normalizedPrefill) {
      prefillAppliedRef.current = null;
      return;
    }
    if (prefillAppliedRef.current === normalizedPrefill) {
      return;
    }
    userEditedStartRef.current = false;
    userEditedInputRef.current = false;
    userEditedEndRef.current = false;
    lastAutoEndSentenceRef.current = null;
    const normalizedInput = normalizePath(normalizedPrefill);
    const cachedBookMetadata = normalizedInput ? loadCachedBookMetadataJson(normalizedInput) : null;
    setFormState((previous) => {
      if (previous.input_file === normalizedPrefill) {
        return previous;
      }
      const previousDerivedBase = deriveBaseOutputName(previous.input_file);
      const nextDerivedBase = deriveBaseOutputName(normalizedPrefill);
      const shouldUpdateBase =
        !previous.base_output_file || previous.base_output_file === previousDerivedBase;
      const suggestedStart = resolveStartFromHistory(normalizedPrefill);
      const resolvedBase =
        forcedBaseOutputFile ?? (shouldUpdateBase ? nextDerivedBase : previous.base_output_file);
      return {
        ...previous,
        input_file: normalizedPrefill,
        base_output_file: resolvedBase,
        book_metadata: cachedBookMetadata ?? '{}',
        start_sentence: suggestedStart ?? DEFAULT_FORM_STATE.start_sentence
      };
    });
    prefillAppliedRef.current = normalizedPrefill;
  }, [prefillInputFile, resolveStartFromHistory, forcedBaseOutputFile, normalizePath]);

  useEffect(() => {
    const normalized = metadataSourceName.trim();
    setMetadataLookupQuery(normalized);
    setMetadataPreview(null);
    setMetadataError(null);
    setMetadataLoading(false);
    metadataAutoLookupRef.current = null;
  }, [metadataSourceName]);

  useEffect(() => {
    if (activeTab !== 'metadata') {
      return;
    }
    const normalized = metadataSourceName.trim();
    if (!normalized) {
      return;
    }
    if (metadataAutoLookupRef.current === normalized) {
      return;
    }
    metadataAutoLookupRef.current = normalized;
    void performMetadataLookup(normalized, false);
  }, [activeTab, metadataSourceName, performMetadataLookup]);

  useEffect(() => {
    if (!prefillParameters) {
      prefillParametersRef.current = null;
      return;
    }
    const key = JSON.stringify(prefillParameters);
    if (prefillParametersRef.current === key) {
      return;
    }
    prefillParametersRef.current = key;

    setFormState((previous) => {
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
      const addImages =
        typeof prefillParameters.add_images === 'boolean' ? prefillParameters.add_images : previous.add_images;
      const voiceOverrides =
        prefillParameters.voice_overrides && typeof prefillParameters.voice_overrides === 'object'
          ? { ...prefillParameters.voice_overrides }
          : previous.voice_overrides;

      const next = {
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
        add_images: addImages,
        voice_overrides: voiceOverrides
      };
      return preserveUserEditedFields(previous, next);
    });
  }, [prefillParameters, forcedBaseOutputFile, preserveUserEditedFields]);

  useEffect(() => {
    let cancelled = false;
    const loadDefaults = async () => {
      if (defaultsAppliedRef.current) {
        return;
      }
      try {
        const defaults = await fetchPipelineDefaults();
        if (cancelled) {
          return;
        }
        const config = defaults?.config ?? {};
        const allowInputDefaults = !userEditedFieldsRef.current.has('input_language');
        const allowTargetDefaults = !userEditedFieldsRef.current.has('target_languages');
        // Preserve user edits; defaults should not overwrite in-flight changes.
        lastAutoEndSentenceRef.current = null;
        setFormState((previous) => {
          let next = applyImageDefaults(applyConfigDefaults(previous, config));
          if (isGeneratedSource || userEditedInputRef.current) {
            next = { ...next, input_file: previous.input_file };
          }
          if (userEditedStartRef.current) {
            next = { ...next, start_sentence: previous.start_sentence };
          }
          if (userEditedEndRef.current) {
            next = { ...next, end_sentence: previous.end_sentence };
          }
          const editedImageFields = userEditedImageDefaultsRef.current;
          if (editedImageFields.size > 0) {
            const restored: Partial<FormState> = {};
            if (editedImageFields.has('add_images')) {
              restored.add_images = previous.add_images;
            }
            if (editedImageFields.has('image_style_template')) {
              restored.image_style_template = previous.image_style_template;
            }
            if (editedImageFields.has('image_prompt_context_sentences')) {
              restored.image_prompt_context_sentences = previous.image_prompt_context_sentences;
            }
            if (editedImageFields.has('image_width')) {
              restored.image_width = previous.image_width;
            }
            if (editedImageFields.has('image_height')) {
              restored.image_height = previous.image_height;
            }
            if (Object.keys(restored).length > 0) {
              next = { ...next, ...restored };
            }
          }
          next = preserveUserEditedFields(previous, next);
          const suggestedStart = resolveStartFromHistory(next.input_file);
          const baseOutput = forcedBaseOutputFile ?? next.base_output_file;
          const shouldApplySuggestedStart =
            suggestedStart !== null &&
            !userEditedStartRef.current &&
            !userEditedFieldsRef.current.has('start_sentence');
          if (shouldApplySuggestedStart) {
            return { ...next, start_sentence: suggestedStart, base_output_file: baseOutput };
          }
          return { ...next, base_output_file: baseOutput };
        });
        const inputLanguage = typeof config['input_language'] === 'string' ? config['input_language'] : null;
        if (allowInputDefaults && inputLanguage) {
          setSharedInputLanguage(inputLanguage);
        }
        const targetLanguages = Array.isArray(config['target_languages'])
          ? Array.from(
              new Set(
                config['target_languages']
                  .filter((language): language is string => typeof language === 'string')
                  .map((language) => language.trim())
                  .filter((language) => language.length > 0)
              )
            )
          : [];
        if (allowTargetDefaults && targetLanguages.length > 0) {
          setSharedTargetLanguages(normalizeSingleTargetLanguages(targetLanguages));
        }
        defaultsAppliedRef.current = true;
      } catch (defaultsError) {
        console.warn('Unable to load pipeline defaults', defaultsError);
      }
    };
    void loadDefaults();
    return () => {
      cancelled = true;
    };
  }, [
    resolveStartFromHistory,
    setSharedInputLanguage,
    setSharedTargetLanguages,
    forcedBaseOutputFile,
    applyImageDefaults,
    preserveUserEditedFields
  ]);

  useEffect(() => {
    let cancelled = false;
    const loadModels = async () => {
      setIsLoadingLlmModels(true);
      try {
        const models = await fetchLlmModels();
        if (cancelled) {
          return;
        }
        setAvailableLlmModels(models ?? []);
        setLlmModelError(null);
      } catch (modelError) {
        if (!cancelled) {
          const message =
            modelError instanceof Error ? modelError.message : 'Unable to load model list.';
          setLlmModelError(message);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingLlmModels(false);
        }
      }
    };
    void loadModels();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setFormState((previous) => {
      if (previous.input_language === sharedInputLanguage) {
        return previous;
      }
      return {
        ...previous,
        input_language: sharedInputLanguage
      };
    });
  }, [sharedInputLanguage]);

  useEffect(() => {
    setFormState((previous) => {
      if (areLanguageArraysEqual(previous.target_languages, sharedTargetLanguages)) {
        return previous;
      }
      return {
        ...previous,
        target_languages: [...sharedTargetLanguages]
      };
    });
  }, [sharedTargetLanguages]);

  useEffect(() => {
    if (isGeneratedSource || forcedBaseOutputFile) {
      return;
    }
    if (userEditedInputRef.current) {
      return;
    }
    const latest = resolveLatestJobSelection();
    if (!latest) {
      return;
    }
    const nextInput = latest.input ? latest.input.trim() : '';
    const nextBase = latest.base ? latest.base.trim() : '';
    setFormState((previous) => {
      if (userEditedInputRef.current) {
        return previous;
      }
      const inputChanged = nextInput && previous.input_file !== nextInput;
      const baseChanged = nextBase && previous.base_output_file !== nextBase;
      if (!inputChanged && !baseChanged) {
        return previous;
      }
      const suggestedStart = resolveStartFromHistory(nextInput || previous.input_file);
      return {
        ...previous,
        input_file: inputChanged ? nextInput : previous.input_file,
        base_output_file: baseChanged ? nextBase : previous.base_output_file,
        start_sentence: suggestedStart ?? previous.start_sentence
      };
    });
  }, [resolveLatestJobSelection, resolveStartFromHistory, recentJobs, isGeneratedSource, forcedBaseOutputFile]);

  useEffect(() => {
    if (userEditedStartRef.current) {
      return;
    }
    const suggestedStart = resolveStartFromHistory(formState.input_file);
    if (suggestedStart === null || formState.start_sentence === suggestedStart) {
      return;
    }
    setFormState((previous) => {
      if (previous.input_file !== formState.input_file) {
        return previous;
      }
      if (userEditedStartRef.current || previous.start_sentence === suggestedStart) {
        return previous;
      }
      return { ...previous, start_sentence: suggestedStart };
    });
  }, [formState.input_file, formState.start_sentence, resolveStartFromHistory, recentJobs]);

  useEffect(() => {
    if (userEditedEndRef.current) {
      return;
    }

    const start = formState.start_sentence;
    if (!Number.isFinite(start)) {
      return;
    }

    const suggestedEnd = String(Math.max(1, Math.trunc(start)) + 99);
    const currentEnd = formState.end_sentence;
    const lastAuto = lastAutoEndSentenceRef.current;
    const shouldApply = currentEnd === '' || (lastAuto !== null && currentEnd === lastAuto);

    if (!shouldApply) {
      lastAutoEndSentenceRef.current = null;
      return;
    }

    if (currentEnd === suggestedEnd) {
      lastAutoEndSentenceRef.current = suggestedEnd;
      return;
    }

    setFormState((previous) => {
      if (userEditedEndRef.current) {
        return previous;
      }

      const previousStart = previous.start_sentence;
      if (!Number.isFinite(previousStart)) {
        return previous;
      }

      const nextSuggestedEnd = String(Math.max(1, Math.trunc(previousStart)) + 99);
      const previousEnd = previous.end_sentence;
      const previousLastAuto = lastAutoEndSentenceRef.current;
      const previousShouldApply =
        previousEnd === '' || (previousLastAuto !== null && previousEnd === previousLastAuto);

      if (!previousShouldApply && previousEnd !== nextSuggestedEnd) {
        return previous;
      }

      lastAutoEndSentenceRef.current = nextSuggestedEnd;
      return { ...previous, end_sentence: nextSuggestedEnd };
    });
  }, [formState.end_sentence, formState.start_sentence]);

  const handleChange = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    if (key === 'base_output_file' && forcedBaseOutputFile !== null && forcedBaseOutputFile !== undefined) {
      return;
    }
    if (key === 'start_sentence') {
      userEditedStartRef.current = true;
    } else if (key === 'end_sentence') {
      userEditedEndRef.current = true;
      lastAutoEndSentenceRef.current = null;
    } else if (key === 'base_output_file') {
      userEditedInputRef.current = true;
    }
    markUserEditedField(key);
    if (IMAGE_DEFAULT_FIELDS.has(key)) {
      userEditedImageDefaultsRef.current.add(key);
    }
    setFormState((previous) => {
      if (previous[key] === value) {
        return previous;
      }
      return {
        ...previous,
        [key]: value
      };
    });

    if (key === 'input_language' && typeof value === 'string') {
      setSharedInputLanguage(value);
    } else if (key === 'target_languages' && Array.isArray(value)) {
      const nextLanguages = value as string[];
      const normalized = normalizeSingleTargetLanguages(nextLanguages);
      if (!areLanguageArraysEqual(sharedTargetLanguages, normalized)) {
        setSharedTargetLanguages(normalized);
      }
    }
  };

  const handleChapterModeChange = useCallback((mode: 'range' | 'chapters') => {
    setChapterSelectionMode(mode);
  }, []);

  const handleChapterToggle = useCallback(
    (chapterId: string) => {
      const index = chapterIndexLookup.get(chapterId);
      if (index === undefined) {
        return;
      }
      setChapterRangeSelection((previous) => {
        if (!previous) {
          return { startIndex: index, endIndex: index };
        }
        const { startIndex, endIndex } = previous;
        if (index < startIndex) {
          return { startIndex: index, endIndex };
        }
        if (index > endIndex) {
          return { startIndex, endIndex: index };
        }
        if (startIndex === endIndex && index === startIndex) {
          return null;
        }
        if (index === startIndex) {
          return { startIndex: startIndex + 1, endIndex };
        }
        if (index === endIndex) {
          return { startIndex, endIndex: endIndex - 1 };
        }
        return { startIndex: index, endIndex: index };
      });
    },
    [chapterIndexLookup]
  );

  const handleChapterClear = useCallback(() => {
    setChapterRangeSelection(null);
  }, []);

  const updateVoiceOverride = useCallback((languageCode: string, voiceValue: string) => {
    const trimmedCode = languageCode.trim();
    if (!trimmedCode) {
      return;
    }
    markUserEditedField('voice_overrides');
    setFormState((previous) => {
      const normalizedVoice = voiceValue.trim();
      const overrides = previous.voice_overrides;
      if (!normalizedVoice) {
        if (!(trimmedCode in overrides)) {
          return previous;
        }
        const nextOverrides = { ...overrides };
        delete nextOverrides[trimmedCode];
        return { ...previous, voice_overrides: nextOverrides };
      }
      if (overrides[trimmedCode] === normalizedVoice) {
        return previous;
      }
      return {
        ...previous,
        voice_overrides: {
          ...overrides,
          [trimmedCode]: normalizedVoice
        }
      };
    });
  }, [markUserEditedField]);

  const handleInputFileChange = (value: string) => {
    setRecentUploadName(null);
    setUploadError(null);
    userEditedStartRef.current = false;
    userEditedInputRef.current = true;
    userEditedEndRef.current = false;
    lastAutoEndSentenceRef.current = null;
    markUserEditedField('input_file');
    const normalizedInput = normalizePath(value);
    const cachedBookMetadata = normalizedInput ? loadCachedBookMetadataJson(normalizedInput) : null;
    setFormState((previous) => {
      if (previous.input_file === value) {
        return previous;
      }
      const previousDerivedBase = deriveBaseOutputName(previous.input_file);
      const nextDerivedBase = deriveBaseOutputName(value);
      const shouldUpdateBase =
        !previous.base_output_file ||
        previous.base_output_file === previousDerivedBase;
      const suggestedStart = resolveStartFromHistory(value);
      const resolvedBase =
        forcedBaseOutputFile ?? (shouldUpdateBase ? nextDerivedBase : previous.base_output_file);
      return {
        ...previous,
        input_file: value,
        base_output_file: resolvedBase,
        book_metadata: cachedBookMetadata ?? '{}',
        start_sentence: suggestedStart ?? DEFAULT_FORM_STATE.start_sentence
      };
    });
  };

  const availableAudioModes = useMemo<MenuOption[]>(() => AUDIO_MODE_OPTIONS, []);
  const availableWrittenModes = useMemo<MenuOption[]>(() => WRITTEN_MODE_OPTIONS, []);
  const availableVoices = useMemo<MenuOption[]>(() => VOICE_OPTIONS, []);
  const normalizedTargetLanguages = useMemo(() => {
    const manualTargets = formState.custom_target_languages
      .split(',')
      .map((language) => language.trim())
      .filter(Boolean);
    return normalizeSingleTargetLanguages([...formState.target_languages, ...manualTargets]);
  }, [formState.custom_target_languages, formState.target_languages]);

  const languagesForOverride = useMemo(() => {
    const seen = new Set<string>();
    const entries: Array<{ label: string; code: string | null }> = [];

    const addLanguage = (label: string) => {
      const trimmed = label.trim();
      if (!trimmed) {
        return;
      }
      const code = resolveLanguageCode(trimmed);
      const key = (code ?? trimmed).toLowerCase();
      if (seen.has(key)) {
        return;
      }
      seen.add(key);
      entries.push({ label: trimmed, code: code ?? null });
    };

    addLanguage(formState.input_language);
    normalizedTargetLanguages.forEach(addLanguage);
    return entries;
  }, [formState.input_language, normalizedTargetLanguages]);

  const playVoicePreview = useCallback(
    async (languageCode: string, languageLabel: string) => {
      const trimmedCode = languageCode.trim();
      if (!trimmedCode) {
        return;
      }

      const effectiveVoice = formState.voice_overrides[trimmedCode] ?? formState.selected_voice;
      const sampleText = sampleSentenceFor(trimmedCode, languageLabel);

      setVoicePreviewError((previous) => {
        const next = { ...previous };
        delete next[trimmedCode];
        return next;
      });
      cleanupPreviewAudio();
      setVoicePreviewStatus((previous) => ({ ...previous, [trimmedCode]: 'loading' }));

      try {
        const previewBlob = await synthesizeVoicePreview({
          text: sampleText,
          language: trimmedCode,
          voice: effectiveVoice
        });
        const previewUrl = URL.createObjectURL(previewBlob);
        const audio = new Audio(previewUrl);
        previewAudioRef.current = { audio, url: previewUrl, code: trimmedCode };
        audio.onended = () => {
          setVoicePreviewStatus((previous) => ({ ...previous, [trimmedCode]: 'idle' }));
          cleanupPreviewAudio();
        };
        audio.onerror = () => {
          setVoicePreviewStatus((previous) => ({ ...previous, [trimmedCode]: 'idle' }));
          setVoicePreviewError((previous) => ({
            ...previous,
            [trimmedCode]: 'Audio playback failed.'
          }));
          cleanupPreviewAudio();
        };
        await audio.play();
        setVoicePreviewStatus((previous) => ({ ...previous, [trimmedCode]: 'playing' }));
      } catch (previewError) {
        cleanupPreviewAudio();
        setVoicePreviewStatus((previous) => ({ ...previous, [trimmedCode]: 'idle' }));
        const message =
          previewError instanceof Error
            ? previewError.message
            : 'Unable to generate voice preview.';
        setVoicePreviewError((previous) => ({ ...previous, [trimmedCode]: message }));
      }
    },
    [cleanupPreviewAudio, formState.selected_voice, formState.voice_overrides]
  );

  const buildVoiceOptions = useCallback(
    (languageLabel: string, languageCode: string | null): MenuOption[] => {
      const baseOptions: MenuOption[] = VOICE_OPTIONS.map((option) => ({
        value: option.value,
        label: option.label,
        description: option.description
      }));

      if (!voiceInventory || !languageCode) {
        return baseOptions;
      }

      const extras: MenuOption[] = [];
      const normalizedCode = languageCode.toLowerCase();

      const gttsMatches = voiceInventory.gtts.filter((entry) => {
        const entryCode = entry.code.toLowerCase();
        if (entryCode === normalizedCode) {
          return true;
        }
        return entryCode.startsWith(`${normalizedCode}-`) || entryCode.startsWith(`${normalizedCode}_`);
      });
      const seenGtts = new Set<string>();
      for (const entry of gttsMatches) {
        const shortCode = entry.code.split(/[-_]/)[0].toLowerCase();
        if (!shortCode || seenGtts.has(shortCode)) {
          continue;
        }
        seenGtts.add(shortCode);
        const identifier = `gTTS-${shortCode}`;
        extras.push({ value: identifier, label: `gTTS (${entry.name})`, description: 'gTTS voice' });
      }

      const macVoices = voiceInventory.macos.filter((voice) => {
        const voiceLang = voice.lang.toLowerCase();
        return (
          voiceLang === normalizedCode ||
          voiceLang.startsWith(`${normalizedCode}-`) ||
          voiceLang.startsWith(`${normalizedCode}_`)
        );
      });
      macVoices
        .slice()
        .sort((a, b) => a.name.localeCompare(b.name))
        .forEach((voice) => {
          extras.push({
            value: formatMacOSVoiceIdentifier(voice),
            label: formatMacOSVoiceLabel(voice),
            description: 'macOS system voice'
          });
        });

      const merged = new Map<string, MenuOption>();
      for (const option of [...baseOptions, ...extras]) {
        if (!option.value) {
          continue;
        }
        if (!merged.has(option.value)) {
          merged.set(option.value, option);
        }
      }
      return Array.from(merged.values());
    },
    [voiceInventory]
  );

  const refreshFiles = useCallback(async () => {
    if (isGeneratedSource) {
      setIsLoadingFiles(false);
      setFileOptions(null);
      return;
    }
    setIsLoadingFiles(true);
    try {
      const response = await fetchPipelineFiles();
      setFileOptions(response);
      setFileDialogError(null);
    } catch (fetchError) {
      const message =
        fetchError instanceof Error ? fetchError.message : 'Unable to load available files.';
      setFileDialogError(message);
      setFileOptions(null);
    } finally {
      setIsLoadingFiles(false);
    }
  }, [isGeneratedSource]);

  const handleDeleteEbook = useCallback(
    async (entry: PipelineFileEntry) => {
      const confirmed =
        typeof window === 'undefined'
          ? true
          : window.confirm(`Delete ${entry.name}? This action cannot be undone.`);
      if (!confirmed) {
        return;
      }

      try {
        await deletePipelineEbook(entry.path);
        setFileDialogError(null);
        setFormState((previous) => {
          if (previous.input_file !== entry.path) {
            return previous;
          }
          const derivedBase = deriveBaseOutputName(entry.name);
          const nextBase =
            forcedBaseOutputFile ??
            (previous.base_output_file === derivedBase ? '' : previous.base_output_file);
          return {
            ...previous,
            input_file: '',
            base_output_file: nextBase,
            book_metadata: '{}'
          };
        });
        prefillAppliedRef.current = null;
        await refreshFiles();
      } catch (deleteError) {
        const message =
          deleteError instanceof Error
            ? deleteError.message
            : 'Unable to delete selected ebook.';
        setFileDialogError(message);
      }
    },
    [refreshFiles, forcedBaseOutputFile]
  );

  const processFileUpload = useCallback(
    async (file: File) => {
      setUploadError(null);
      setRecentUploadName(null);

      const filename = file.name || 'uploaded.epub';
      if (!filename.toLowerCase().endsWith('.epub')) {
        setUploadError('Only EPUB files can be imported.');
        return;
      }

      setIsUploadingFile(true);
      try {
        const entry = await uploadEpubFile(file);
        handleInputFileChange(entry.path);
        setRecentUploadName(entry.name);
        await refreshFiles();
      } catch (uploadFailure) {
        const message =
          uploadFailure instanceof Error
            ? uploadFailure.message
            : 'Unable to upload EPUB file.';
        setUploadError(message);
      } finally {
        setIsUploadingFile(false);
      }
    },
    [handleInputFileChange, refreshFiles]
  );

  const handleDropzoneDragOver = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      if (!isDraggingFile) {
        setIsDraggingFile(true);
      }
    },
    [isDraggingFile]
  );

  const handleDropzoneDragLeave = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDraggingFile(false);
  }, []);

  const handleDropzoneDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      setIsDraggingFile(false);

      const droppedFile = event.dataTransfer?.files?.[0];
      if (droppedFile) {
        void processFileUpload(droppedFile);
      }
    },
    [processFileUpload]
  );

  useEffect(() => {
    let cancelled = false;
    setIsLoadingVoiceInventory(true);
    fetchVoiceInventory()
      .then((inventory) => {
        if (cancelled) {
          return;
        }
        setVoiceInventory(inventory);
        setVoiceInventoryError(null);
      })
      .catch((inventoryError) => {
        if (cancelled) {
          return;
        }
        const message =
          inventoryError instanceof Error
            ? inventoryError.message
            : 'Unable to load voice inventory.';
        setVoiceInventory(null);
        setVoiceInventoryError(message);
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingVoiceInventory(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [setSharedInputLanguage, setSharedTargetLanguages]);

  useEffect(() => {
    return () => {
      cleanupPreviewAudio();
    };
  }, [cleanupPreviewAudio]);

  useEffect(() => {
    if (!isGeneratedSource) {
      return;
    }
    userEditedStartRef.current = false;
    userEditedEndRef.current = false;
    lastAutoEndSentenceRef.current = null;
    setFormState((previous) => ({
      ...previous,
      start_sentence: 1,
      end_sentence: ''
    }));
  }, [isGeneratedSource]);

  useEffect(() => {
    if (forcedBaseOutputFile === null || forcedBaseOutputFile === undefined) {
      return;
    }
    setFormState((previous) => {
      if (previous.base_output_file === forcedBaseOutputFile) {
        return previous;
      }
      return {
        ...previous,
        base_output_file: forcedBaseOutputFile
      };
    });
  }, [forcedBaseOutputFile]);

  useEffect(() => {
    void refreshFiles();
  }, [refreshFiles]);

  useEffect(() => {
    if (!fileOptions || fileOptions.ebooks.length === 0 || isGeneratedSource) {
      return;
    }
    setFormState((previous) => {
      if (previous.input_file && previous.input_file.trim()) {
        return previous;
      }
      const preferred =
        fileOptions.ebooks.find((entry) =>
          entry.name.trim().toLowerCase() === PREFERRED_SAMPLE_EBOOK
        ) || fileOptions.ebooks[0];
      const nextInput = preferred.path;
      const derivedBase = deriveBaseOutputName(preferred.name || preferred.path);
      const suggestedStart = resolveStartFromHistory(nextInput);
      userEditedStartRef.current = false;
      return {
        ...previous,
        input_file: nextInput,
        base_output_file: derivedBase || previous.base_output_file || 'book-output',
        start_sentence: suggestedStart ?? DEFAULT_FORM_STATE.start_sentence
      };
    });
  }, [fileOptions, isGeneratedSource, resolveStartFromHistory]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    try {
      const json: Record<JsonFields, Record<string, unknown>> = {
        config: parseJsonField('config', formState.config),
        environment_overrides: parseJsonField(
          'environment_overrides',
          formState.environment_overrides
        ),
        pipeline_overrides: parseJsonField('pipeline_overrides', formState.pipeline_overrides),
        book_metadata: parseJsonField('book_metadata', formState.book_metadata)
      };

      if (normalizedTargetLanguages.length === 0) {
        throw new Error('Please choose at least one target language.');
      }

      const pipelineOverrides = { ...json.pipeline_overrides };

      const threadCount = parseOptionalNumberInput(formState.thread_count);
      if (threadCount !== undefined) {
        pipelineOverrides.thread_count = threadCount;
      }

      const queueSize = parseOptionalNumberInput(formState.queue_size);
      if (queueSize !== undefined) {
        pipelineOverrides.queue_size = queueSize;
      }

      const jobMaxWorkers = parseOptionalNumberInput(formState.job_max_workers);
      if (jobMaxWorkers !== undefined) {
        pipelineOverrides.job_max_workers = jobMaxWorkers;
      }

      const slideParallelism = formState.slide_parallelism.trim();
      if (slideParallelism) {
        pipelineOverrides.slide_parallelism = slideParallelism;
      }

      const slideParallelWorkers = parseOptionalNumberInput(formState.slide_parallel_workers);
      if (slideParallelWorkers !== undefined) {
        pipelineOverrides.slide_parallel_workers = slideParallelWorkers;
      }

      const sanitizedVoiceOverrides: Record<string, string> = {};
      for (const [code, value] of Object.entries(formState.voice_overrides)) {
        if (typeof code !== 'string' || typeof value !== 'string') {
          continue;
        }
        const trimmedCode = code.trim();
        const trimmedValue = value.trim();
        if (!trimmedCode || !trimmedValue) {
          continue;
        }
        sanitizedVoiceOverrides[trimmedCode] = trimmedValue;
      }
      if (Object.keys(sanitizedVoiceOverrides).length > 0) {
        pipelineOverrides.voice_overrides = sanitizedVoiceOverrides;
      }
      if (typeof formState.audio_mode === 'string' && formState.audio_mode.trim()) {
        pipelineOverrides.audio_mode = formState.audio_mode.trim();
      }
      const audioBitrate = parseOptionalNumberInput(formState.audio_bitrate_kbps);
      if (audioBitrate !== undefined) {
        pipelineOverrides.audio_bitrate_kbps = Math.max(32, Math.trunc(audioBitrate));
      }
      if (formState.add_images) {
        if (typeof formState.image_style_template === 'string' && formState.image_style_template.trim()) {
          pipelineOverrides.image_style_template = formState.image_style_template.trim();
        }

        pipelineOverrides.image_prompt_batching_enabled = Boolean(formState.image_prompt_batching_enabled);
        const rawBatchSize = Number(formState.image_prompt_batch_size);
        const normalizedBatchSize = Number.isFinite(rawBatchSize) ? Math.trunc(rawBatchSize) : 10;
        pipelineOverrides.image_prompt_batch_size = Math.min(50, Math.max(1, normalizedBatchSize));

        const rawPromptPlanBatchSize = Number(formState.image_prompt_plan_batch_size);
        const normalizedPromptPlanBatchSize = Number.isFinite(rawPromptPlanBatchSize)
          ? Math.trunc(rawPromptPlanBatchSize)
          : 50;
        pipelineOverrides.image_prompt_plan_batch_size = Math.min(50, Math.max(1, normalizedPromptPlanBatchSize));

        const rawContext = Number(formState.image_prompt_context_sentences);
        const normalizedContext = Number.isFinite(rawContext) ? Math.trunc(rawContext) : 0;
        pipelineOverrides.image_prompt_context_sentences = Math.min(50, Math.max(0, normalizedContext));
        pipelineOverrides.image_seed_with_previous_image = Boolean(formState.image_seed_with_previous_image);
        pipelineOverrides.image_blank_detection_enabled = Boolean(formState.image_blank_detection_enabled);

        const normalizedImageBaseUrls = await resolveImageBaseUrlsForSubmission(
          formState.image_api_base_urls
        );
        pipelineOverrides.image_api_base_urls = normalizedImageBaseUrls;
        pipelineOverrides.image_api_base_url = normalizedImageBaseUrls[0] ?? '';

        const imageConcurrency = parseOptionalNumberInput(formState.image_concurrency);
        if (imageConcurrency !== undefined) {
          pipelineOverrides.image_concurrency = Math.max(1, Math.trunc(imageConcurrency));
        }

        const imageTimeout = parseOptionalNumberInput(formState.image_api_timeout_seconds);
        if (imageTimeout !== undefined) {
          pipelineOverrides.image_api_timeout_seconds = Math.max(1, imageTimeout);
        }

        const imageWidth = parseOptionalNumberInput(formState.image_width);
        if (imageWidth !== undefined) {
          pipelineOverrides.image_width = Math.max(64, Math.trunc(imageWidth));
        }

        const imageHeight = parseOptionalNumberInput(formState.image_height);
        if (imageHeight !== undefined) {
          pipelineOverrides.image_height = Math.max(64, Math.trunc(imageHeight));
        }

        const imageSteps = parseOptionalNumberInput(formState.image_steps);
        if (imageSteps !== undefined) {
          pipelineOverrides.image_steps = Math.max(1, Math.trunc(imageSteps));
        }

        const imageCfgScale = parseOptionalNumberInput(formState.image_cfg_scale);
        if (imageCfgScale !== undefined) {
          pipelineOverrides.image_cfg_scale = Math.max(0, imageCfgScale);
        }

        pipelineOverrides.image_sampler_name = formState.image_sampler_name;
      }

      const configOverrides = { ...json.config };
      const metadataBookTitle = normalizeTextValue(json.book_metadata?.['book_title']);
      const metadataBookAuthor = normalizeTextValue(json.book_metadata?.['book_author']);
      const metadataBookYear = normalizeTextValue(json.book_metadata?.['book_year']);
      const metadataBookSummary = normalizeTextValue(json.book_metadata?.['book_summary']);
      const metadataCoverFile = normalizeTextValue(json.book_metadata?.['book_cover_file']);
      if (metadataBookTitle) {
        configOverrides['book_title'] = metadataBookTitle;
      }
      if (metadataBookAuthor) {
        configOverrides['book_author'] = metadataBookAuthor;
      }
      if (metadataBookYear) {
        configOverrides['book_year'] = metadataBookYear;
      }
      if (metadataBookSummary) {
        configOverrides['book_summary'] = metadataBookSummary;
      }
      if (metadataCoverFile) {
        configOverrides['book_cover_file'] = metadataCoverFile;
      }
      const selectedModel = formState.ollama_model.trim();
      if (selectedModel) {
        pipelineOverrides.ollama_model = selectedModel;
      }

      const chapterRange =
        chapterSelectionMode === 'chapters' ? chapterSelection : null;
      if (!isGeneratedSource && chapterSelectionMode === 'chapters' && !chapterRange) {
        throw new Error('Select at least one chapter.');
      }
      const normalizedStartSentence = isGeneratedSource
        ? 1
        : chapterRange
        ? chapterRange.startSentence
        : Math.max(1, Math.trunc(Number(formState.start_sentence)));
      if (!Number.isFinite(normalizedStartSentence)) {
        throw new Error('Start sentence must be a valid number.');
      }
      const normalizedEndSentence = isGeneratedSource
        ? null
        : chapterRange
        ? chapterRange.endSentence
        : parseEndSentenceInput(
            formState.end_sentence,
            normalizedStartSentence,
            implicitEndOffsetThreshold
          );
      const resolvedBaseOutput = (forcedBaseOutputFile ?? formState.base_output_file).trim();
      const trimmedInputFile = formState.input_file.trim();
      const fallbackInputFile = resolvedBaseOutput || 'generated-book';
      const resolvedInputFile =
        trimmedInputFile || (isGeneratedSource ? `${fallbackInputFile}.epub` : trimmedInputFile);

      const payload: PipelineRequestPayload = {
        config: configOverrides,
        environment_overrides: json.environment_overrides,
        pipeline_overrides: pipelineOverrides,
        inputs: {
          input_file: resolvedInputFile,
          base_output_file: resolvedBaseOutput,
          input_language: formState.input_language.trim(),
          target_languages: normalizedTargetLanguages,
          sentences_per_output_file: Number(formState.sentences_per_output_file),
          start_sentence: normalizedStartSentence,
          end_sentence: normalizedEndSentence,
          stitch_full: formState.stitch_full,
          generate_audio: formState.generate_audio,
          audio_mode: formState.audio_mode.trim(),
          audio_bitrate_kbps: audioBitrate !== undefined ? Math.max(32, Math.trunc(audioBitrate)) : null,
          written_mode: formState.written_mode.trim(),
          selected_voice: formState.selected_voice.trim(),
          voice_overrides: sanitizedVoiceOverrides,
          output_html: formState.output_html,
          output_pdf: formState.output_pdf,
          generate_video: formState.generate_video,
          add_images: formState.add_images,
          include_transliteration: formState.include_transliteration,
          tempo: Number(formState.tempo),
          book_metadata: json.book_metadata
        }
      };

      await onSubmit(payload);
    } catch (submissionError) {
      const message =
        submissionError instanceof Error
          ? submissionError.message
          : 'Unable to submit pipeline request';
      setError(message);
    }
  };

  const headerTitle = sectionMeta[activeTab]?.title ?? 'Submit a book job';
  const headerDescription =
    sectionMeta[activeTab]?.description ??
    'Provide the input file, target languages, and any overrides to enqueue a new ebook processing job.';
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
  if (!isGeneratedSource && chapterSelectionMode === 'chapters' && !chapterSelection) {
    missingRequirements.push('a chapter selection');
  }
  const targetLanguageSummary =
    normalizedTargetLanguages.length > 0
      ? normalizedTargetLanguages.map((language) => formatLanguageWithFlag(language) || language).join(', ')
      : 'None selected';
  const inputSummaryValue =
    isGeneratedSource && !formState.input_file.trim()
      ? `${formState.base_output_file.trim() || 'generated-book'}.epub`
      : formState.input_file;
  const isSubmitDisabled = isSubmitting || missingRequirements.length > 0;
  const submitText = submitLabel ?? 'Submit job';
  const hasMissingRequirements = missingRequirements.length > 0;
  const outputFormats =
    [
      formState.output_html ? 'HTML' : null,
      formState.output_pdf ? 'PDF' : null,
      formState.generate_audio ? 'Audio' : null,
      formState.add_images ? 'Images' : null,
      formState.generate_video ? 'Video' : null
    ]
      .filter(Boolean)
      .join(', ') || 'Default';
  const missingRequirementText = formatList(missingRequirements);
  const canBrowseFiles = Boolean(fileOptions);
  const displayStartSentence =
    chapterSelectionMode === 'chapters' && chapterSelection
      ? chapterSelection.startSentence
      : formState.start_sentence;
  const displayEndSentence =
    chapterSelectionMode === 'chapters' && chapterSelection
      ? String(chapterSelection.endSentence)
      : formState.end_sentence;

  const renderSection = (section: BookNarrationFormSection) => {
    switch (section) {
      case 'source':
        return (
          customSourceSection ?? (
            <BookNarrationSourceSection
              key="source"
              headingId="pipeline-card-source"
              title={sectionMeta.source.title}
              description={sectionMeta.source.description}
              inputFile={formState.input_file}
              baseOutputFile={formState.base_output_file}
              onInputFileChange={handleInputFileChange}
              onBaseOutputFileChange={(value) => handleChange('base_output_file', value)}
              onBrowseClick={(dialogType) => setActiveFileDialog(dialogType)}
              canBrowseFiles={canBrowseFiles}
              isLoadingFiles={isLoadingFiles}
              fileDialogError={fileDialogError}
              isDraggingFile={isDraggingFile}
              isUploadingFile={isUploadingFile}
              onDropzoneDragOver={handleDropzoneDragOver}
              onDropzoneDragLeave={handleDropzoneDragLeave}
              onDropzoneDrop={handleDropzoneDrop}
              onUploadFile={processFileUpload}
              uploadError={uploadError}
              recentUploadName={recentUploadName}
              configOverrides={formState.config}
              environmentOverrides={formState.environment_overrides}
              pipelineOverrides={formState.pipeline_overrides}
              bookMetadata={formState.book_metadata}
              onConfigOverridesChange={(value) => handleChange('config', value)}
              onEnvironmentOverridesChange={(value) => handleChange('environment_overrides', value)}
              onPipelineOverridesChange={(value) => handleChange('pipeline_overrides', value)}
              onBookMetadataChange={(value) => handleChange('book_metadata', value)}
              showAdvancedOverrides={false}
              disableBaseOutput={isGeneratedSource || Boolean(forcedBaseOutputFile)}
              showOutputPathControls={showOutputPathControls}
            />
          )
        );
      case 'metadata':
        return (
          <BookMetadataSection
            key="metadata"
            headingId="pipeline-card-metadata"
            title={sectionMeta.metadata.title}
            description={sectionMeta.metadata.description}
            metadataSourceName={metadataSourceName}
            metadataLookupQuery={metadataLookupQuery}
            metadataPreview={metadataPreview}
            metadataLoading={metadataLoading}
            metadataError={metadataError}
            bookMetadataJson={formState.book_metadata}
            cachedCoverDataUrl={cachedCoverDataUrl}
            onMetadataLookupQueryChange={(value) => setMetadataLookupQuery(value)}
            onLookupMetadata={performMetadataLookup}
            onClearMetadata={handleClearMetadata}
            onBookMetadataJsonChange={(value) => handleChange('book_metadata', value)}
          />
        );
      case 'language':
        return (
          <BookNarrationLanguageSection
            key="language"
            headingId="pipeline-card-language"
            title={sectionMeta.language.title}
            description={sectionMeta.language.description}
            inputLanguage={formState.input_language}
            targetLanguages={formState.target_languages}
            customTargetLanguages={formState.custom_target_languages}
            ollamaModel={formState.ollama_model}
            llmModels={availableLlmModels}
            llmModelsLoading={isLoadingLlmModels}
            llmModelsError={llmModelError}
            sentencesPerOutputFile={formState.sentences_per_output_file}
            startSentence={displayStartSentence}
            endSentence={displayEndSentence}
            stitchFull={formState.stitch_full}
            disableProcessingWindow={isGeneratedSource}
            processingMode={chapterSelectionMode}
            chapterOptions={chapterOptions}
            selectedChapterIds={selectedChapterIds}
            chapterSummary={chapterSelectionSummary || undefined}
            chaptersLoading={chaptersLoading}
            chaptersError={chaptersError}
            chaptersDisabled={chaptersDisabled}
            estimatedAudioDurationLabel={estimatedAudioDurationLabel}
            onProcessingModeChange={handleChapterModeChange}
            onChapterToggle={handleChapterToggle}
            onChapterClear={handleChapterClear}
            onInputLanguageChange={(value) => handleChange('input_language', value)}
            onTargetLanguagesChange={(value) => handleChange('target_languages', value)}
            onCustomTargetLanguagesChange={(value) => handleChange('custom_target_languages', value)}
            onOllamaModelChange={(value) => handleChange('ollama_model', value)}
            onSentencesPerOutputFileChange={(value) =>
              handleChange('sentences_per_output_file', value)
            }
            onStartSentenceChange={(value) => handleChange('start_sentence', value)}
            onEndSentenceChange={(value) => handleChange('end_sentence', value)}
            onStitchFullChange={(value) => handleChange('stitch_full', value)}
          />
        );
      case 'output':
        return (
          <BookNarrationOutputSection
            key="output"
            headingId="pipeline-card-output"
            title={sectionMeta.output.title}
            description={sectionMeta.output.description}
            generateAudio={formState.generate_audio}
            audioMode={formState.audio_mode}
            audioBitrateKbps={formState.audio_bitrate_kbps}
            selectedVoice={formState.selected_voice}
            writtenMode={formState.written_mode}
            outputHtml={formState.output_html}
            outputPdf={formState.output_pdf}
            includeTransliteration={formState.include_transliteration}
            tempo={formState.tempo}
            generateVideo={formState.generate_video}
            availableAudioModes={availableAudioModes}
            availableAudioQualities={AUDIO_QUALITY_OPTIONS}
            availableVoices={availableVoices}
            availableWrittenModes={availableWrittenModes}
            languagesForOverride={languagesForOverride}
            voiceOverrides={formState.voice_overrides}
            voicePreviewStatus={voicePreviewStatus}
            voicePreviewError={voicePreviewError}
            isLoadingVoiceInventory={isLoadingVoiceInventory}
            voiceInventoryError={voiceInventoryError}
            buildVoiceOptions={buildVoiceOptions}
            onGenerateAudioChange={(value) => handleChange('generate_audio', value)}
            onAudioModeChange={(value) => handleChange('audio_mode', value)}
            onAudioBitrateChange={(value) => handleChange('audio_bitrate_kbps', value)}
            onSelectedVoiceChange={(value) => handleChange('selected_voice', value)}
            onVoiceOverrideChange={updateVoiceOverride}
            onWrittenModeChange={(value) => handleChange('written_mode', value)}
            onOutputHtmlChange={(value) => handleChange('output_html', value)}
            onOutputPdfChange={(value) => handleChange('output_pdf', value)}
            onIncludeTransliterationChange={(value) =>
              handleChange('include_transliteration', value)
            }
            onTempoChange={(value) => handleChange('tempo', value)}
            onGenerateVideoChange={(value) => handleChange('generate_video', value)}
            onPlayVoicePreview={playVoicePreview}
          />
        );
      case 'images':
        return (
          <BookNarrationImageSection
            key="images"
            headingId="pipeline-card-images"
            title={sectionMeta.images.title}
            description={sectionMeta.images.description}
            addImages={formState.add_images}
            imageStyleTemplate={formState.image_style_template}
            imagePromptBatchingEnabled={formState.image_prompt_batching_enabled}
            imagePromptBatchSize={formState.image_prompt_batch_size}
            imagePromptPlanBatchSize={formState.image_prompt_plan_batch_size}
            imagePromptContextSentences={formState.image_prompt_context_sentences}
            imageSeedWithPreviousImage={formState.image_seed_with_previous_image}
            imageBlankDetectionEnabled={formState.image_blank_detection_enabled}
            imageApiBaseUrls={formState.image_api_base_urls}
            imageConcurrency={formState.image_concurrency}
            imageWidth={formState.image_width}
            imageHeight={formState.image_height}
            imageSteps={formState.image_steps}
            imageCfgScale={formState.image_cfg_scale}
            imageSamplerName={formState.image_sampler_name}
            imageApiTimeoutSeconds={formState.image_api_timeout_seconds}
            onAddImagesChange={(value) => handleChange('add_images', value)}
            onImageStyleTemplateChange={(value) => handleChange('image_style_template', value)}
            onImagePromptBatchingEnabledChange={(value) => handleChange('image_prompt_batching_enabled', value)}
            onImagePromptBatchSizeChange={(value) => handleChange('image_prompt_batch_size', value)}
            onImagePromptPlanBatchSizeChange={(value) => handleChange('image_prompt_plan_batch_size', value)}
            onImagePromptContextSentencesChange={(value) =>
              handleChange('image_prompt_context_sentences', value)
            }
            onImageSeedWithPreviousImageChange={(value) =>
              handleChange('image_seed_with_previous_image', value)
            }
            onImageBlankDetectionEnabledChange={(value) =>
              handleChange('image_blank_detection_enabled', value)
            }
            onImageApiBaseUrlsChange={(value) => handleChange('image_api_base_urls', value)}
            onImageConcurrencyChange={(value) => handleChange('image_concurrency', value)}
            onImageWidthChange={(value) => handleChange('image_width', value)}
            onImageHeightChange={(value) => handleChange('image_height', value)}
            onImageStepsChange={(value) => handleChange('image_steps', value)}
            onImageCfgScaleChange={(value) => handleChange('image_cfg_scale', value)}
            onImageSamplerNameChange={(value) => handleChange('image_sampler_name', value)}
            onImageApiTimeoutSecondsChange={(value) =>
              handleChange('image_api_timeout_seconds', value)
            }
          />
        );
		      case 'performance':
		        return (
		          <BookNarrationPerformanceSection
		            key="performance"
		            headingId="pipeline-card-performance"
		            title={sectionMeta.performance.title}
		            description={sectionMeta.performance.description}
		            threadCount={formState.thread_count}
		            queueSize={formState.queue_size}
		            jobMaxWorkers={formState.job_max_workers}
		            slideParallelism={formState.slide_parallelism}
		            slideParallelWorkers={formState.slide_parallel_workers}
		            onThreadCountChange={(value) => handleChange('thread_count', value)}
		            onQueueSizeChange={(value) => handleChange('queue_size', value)}
		            onJobMaxWorkersChange={(value) => handleChange('job_max_workers', value)}
		            onSlideParallelismChange={(value) => handleChange('slide_parallelism', value)}
		            onSlideParallelWorkersChange={(value) => handleChange('slide_parallel_workers', value)}
		          />
		        );
      case 'submit':
      default:
        return null;
    }
  };

  return (
    <div className="pipeline-settings">
      {showInfoHeader ? (
        <>
          <h2>{headerTitle}</h2>
          <p>{headerDescription}</p>
        </>
      ) : null}
      <form className="pipeline-form" onSubmit={handleSubmit} noValidate>
        <div className="pipeline-step-bar">
          <div className="pipeline-step-tabs" role="tablist" aria-label="Pipeline steps">
            {tabSections.map((section) => {
              const meta = sectionMeta[section];
              const isActive = activeTab === section;
              return (
                <button
                  type="button"
                  key={section}
                  className={`pipeline-step-tab ${isActive ? 'is-active' : ''}`}
                  onClick={() => handleSectionChange(section)}
                  aria-selected={isActive}
                  role="tab"
                >
                  <span className="pipeline-step-tab__label">{meta.title}</span>
                </button>
              );
            })}
          </div>
          <div className="pipeline-step-actions">
            <button type="submit" disabled={isSubmitDisabled}>
              {isSubmitting ? 'Submitting…' : submitText}
            </button>
          </div>
        </div>
        {hasMissingRequirements ? (
          <div className="form-callout form-callout--warning" role="status">
            Provide {missingRequirementText} before submitting.
          </div>
        ) : null}
        {error || externalError ? (
          <div className="alert" role="alert">
            {error ?? externalError}
          </div>
        ) : null}
        <div className="pipeline-section-panel">{renderSection(activeTab)}</div>
      </form>
      {activeFileDialog && fileOptions ? (
        <FileSelectionDialog
          title={activeFileDialog === 'input' ? 'Select ebook file' : 'Select output path'}
          description={
            activeFileDialog === 'input'
              ? 'Choose an EPUB file from the configured books directory.'
              : 'Select an existing output file or directory as the base path.'
          }
          files={activeFileDialog === 'input' ? fileOptions.ebooks : fileOptions.outputs}
          onSelect={(path) => {
            if (activeFileDialog === 'input') {
              handleInputFileChange(path);
            } else {
              handleChange('base_output_file', path);
            }
            setActiveFileDialog(null);
          }}
          onClose={() => setActiveFileDialog(null)}
          onDelete={
            activeFileDialog === 'input'
              ? (entry) => {
                  void handleDeleteEbook(entry);
                }
              : undefined
          }
        />
      ) : null}
    </div>
  );

}

export default BookNarrationForm;
