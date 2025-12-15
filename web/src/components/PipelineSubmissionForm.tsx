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
} from '../api/dtos';
import {
  fetchPipelineDefaults,
  fetchPipelineFiles,
  fetchVoiceInventory,
  fetchLlmModels,
  deletePipelineEbook,
  synthesizeVoicePreview,
  uploadEpubFile,
  uploadCoverFile,
  lookupBookOpenLibraryMetadataPreview,
  withBase
} from '../api/client';
import {
  AUDIO_MODE_OPTIONS,
  MenuOption,
  VOICE_OPTIONS,
  WRITTEN_MODE_OPTIONS
} from '../constants/menuOptions';
import { resolveLanguageCode, resolveLanguageName } from '../constants/languageCodes';
import { formatLanguageWithFlag } from '../utils/languages';
import { sampleSentenceFor } from '../utils/sampleSentences';
import { useLanguagePreferences } from '../context/LanguageProvider';
import PipelineSourceSection from './PipelineSourceSection';
import PipelineLanguageSection from './PipelineLanguageSection';
import PipelineOutputSection from './PipelineOutputSection';
import PipelinePerformanceSection from './PipelinePerformanceSection';
import FileSelectionDialog from './FileSelectionDialog';

const PREFERRED_SAMPLE_EBOOK = 'test-agatha-poirot-30sentences.epub';

function capitalize(value: string): string {
  if (!value) {
    return value;
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function normalizeIsbnCandidate(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const cleaned = value.replace(/[^0-9Xx]/g, '').toUpperCase();
  if (cleaned.length === 10 || cleaned.length === 13) {
    return cleaned;
  }
  return null;
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
export type PipelineFormSection =
  | 'source'
  | 'metadata'
  | 'language'
  | 'output'
  | 'performance'
  | 'submit';

type Props = {
  onSubmit: (payload: PipelineRequestPayload) => Promise<void> | void;
  isSubmitting?: boolean;
  activeSection?: PipelineFormSection;
  onSectionChange?: (section: PipelineFormSection) => void;
  externalError?: string | null;
  prefillInputFile?: string | null;
  prefillParameters?: JobParameterSnapshot | null;
  recentJobs?: PipelineStatusResponse[] | null;
  sourceMode?: 'upload' | 'generated';
  submitLabel?: string;
  forcedBaseOutputFile?: string | null;
  customSourceSection?: ReactNode;
  implicitEndOffsetThreshold?: number | null;
  sectionOverrides?: Partial<Record<PipelineFormSection, { title: string; description: string }>>;
  showInfoHeader?: boolean;
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
  written_mode: string;
  selected_voice: string;
  voice_overrides: Record<string, string>;
  output_html: boolean;
  output_pdf: boolean;
  generate_video: boolean;
  include_transliteration: boolean;
  tempo: number;
  thread_count: string;
  queue_size: string;
  job_max_workers: string;
  slide_parallelism: string;
  slide_parallel_workers: string;
  config: string;
  environment_overrides: string;
  pipeline_overrides: string;
  book_metadata: string;
};

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
  written_mode: '4',
  selected_voice: 'gTTS',
  voice_overrides: {},
  output_html: false,
  output_pdf: false,
  generate_video: false,
  include_transliteration: true,
  tempo: 1,
  thread_count: '',
  queue_size: '',
  job_max_workers: '',
  slide_parallelism: '',
  slide_parallel_workers: '',
  config: '{}',
  environment_overrides: '{}',
  pipeline_overrides: '{}',
  book_metadata: '{}'
};

const SECTION_ORDER: PipelineFormSection[] = [
  'source',
  'metadata',
  'language',
  'output',
  'performance',
  'submit'
];

const PIPELINE_TAB_SECTIONS: PipelineFormSection[] = ['source', 'metadata', 'language', 'output', 'performance'];

export const PIPELINE_SECTION_META: Record<PipelineFormSection, { title: string; description: string }> = {
  source: {
    title: 'Source material',
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
    description: 'Control narration voices, written formats, and other presentation options.'
  },
  performance: {
    title: 'Performance tuning',
    description: 'Adjust concurrency and orchestration parameters to fit your environment.'
  },
  submit: {
    title: 'Submit pipeline job',
    description: 'Review the configured settings and enqueue the job for processing.'
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function coerceRecord(value: unknown): Record<string, unknown> | null {
  return isRecord(value) ? value : null;
}

function normalizeTextValue(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function basenameFromPath(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return '';
  }
  const parts = trimmed.split(/[/\\]/);
  return parts[parts.length - 1] || trimmed;
}

function resolveCoverPreviewUrlFromCoverFile(coverFile: string | null): string | null {
  const trimmed = coverFile?.trim() ?? '';
  if (!trimmed) {
    return null;
  }
  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }

  const normalised = trimmed.replace(/\\/g, '/');
  const storagePrefix = '/storage/covers/';
  const storageIndex = normalised.lastIndexOf(storagePrefix);
  if (storageIndex >= 0) {
    return withBase(normalised.slice(storageIndex));
  }
  const storageRelativeIndex = normalised.lastIndexOf('storage/covers/');
  if (storageRelativeIndex >= 0) {
    return withBase(`/${normalised.slice(storageRelativeIndex)}`);
  }

  const filename = basenameFromPath(normalised);
  if (!filename) {
    return null;
  }
  return withBase(`/storage/covers/${encodeURIComponent(filename)}`);
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
    next.target_languages = normalized;
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

function parseJsonField(label: JsonFields, value: string): Record<string, unknown> {
  if (!value.trim()) {
    return {};
  }

  try {
    const parsed = JSON.parse(value);
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      throw new Error(`${label} must be an object`);
    }
    return parsed as Record<string, unknown>;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Invalid JSON for ${label}: ${message}`);
  }
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

export function PipelineSubmissionForm({
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
  showInfoHeader = true
}: Props) {
  const isGeneratedSource = sourceMode === 'generated';
  const {
    inputLanguage: sharedInputLanguage,
    setInputLanguage: setSharedInputLanguage,
    targetLanguages: sharedTargetLanguages,
    setTargetLanguages: setSharedTargetLanguages
  } = useLanguagePreferences();
  const [formState, setFormState] = useState<FormState>(() => ({
    ...DEFAULT_FORM_STATE,
    base_output_file: forcedBaseOutputFile ?? DEFAULT_FORM_STATE.base_output_file,
    input_language: sharedInputLanguage ?? DEFAULT_FORM_STATE.input_language,
    target_languages:
      sharedTargetLanguages.length > 0
        ? [...sharedTargetLanguages]
        : [...DEFAULT_FORM_STATE.target_languages]
  }));
  const [error, setError] = useState<string | null>(null);
  const [fileOptions, setFileOptions] = useState<PipelineFileBrowserResponse | null>(null);
  const [fileDialogError, setFileDialogError] = useState<string | null>(null);
  const [isLoadingFiles, setIsLoadingFiles] = useState<boolean>(true);
  const [activeFileDialog, setActiveFileDialog] = useState<'input' | 'output' | null>(null);
  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [recentUploadName, setRecentUploadName] = useState<string | null>(null);
  const coverUploadInputRef = useRef<HTMLInputElement | null>(null);
  const [coverUploadCandidate, setCoverUploadCandidate] = useState<File | null>(null);
  const [isUploadingCover, setIsUploadingCover] = useState(false);
  const [coverUploadError, setCoverUploadError] = useState<string | null>(null);
  const [isCoverDragActive, setIsCoverDragActive] = useState(false);
  const [coverPreviewRefreshKey, setCoverPreviewRefreshKey] = useState(0);
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

  const sectionMeta = useMemo(() => {
    const base: Record<PipelineFormSection, { title: string; description: string }> = {
      ...PIPELINE_SECTION_META
    };
    for (const [key, override] of Object.entries(sectionOverrides)) {
      if (!override) {
        continue;
      }
      const sectionKey = key as PipelineFormSection;
      base[sectionKey] = { ...PIPELINE_SECTION_META[sectionKey], ...override };
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

  const tabSections: PipelineFormSection[] = PIPELINE_TAB_SECTIONS;
  const [activeTab, setActiveTab] = useState<PipelineFormSection>(() => {
    if (activeSection && tabSections.includes(activeSection)) {
      return activeSection;
    }
    return 'source';
  });

  const handleSectionChange = useCallback(
    (section: PipelineFormSection) => {
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
        book_metadata: '{}',
        start_sentence: suggestedStart ?? DEFAULT_FORM_STATE.start_sentence
      };
    });
    prefillAppliedRef.current = normalizedPrefill;
  }, [prefillInputFile, resolveStartFromHistory, forcedBaseOutputFile]);

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
      const voiceOverrides =
        prefillParameters.voice_overrides && typeof prefillParameters.voice_overrides === 'object'
          ? { ...prefillParameters.voice_overrides }
          : previous.voice_overrides;

      return {
        ...previous,
        input_file: inputFile,
        base_output_file: forcedBaseOutputFile ?? baseOutputFile,
        input_language: inputLanguage,
        target_languages: targetLanguages,
        custom_target_languages: '',
        start_sentence: startSentence,
        end_sentence: endSentence,
        sentences_per_output_file: sentencesPerOutput,
        audio_mode: audioMode,
        selected_voice: selectedVoice,
        tempo,
        include_transliteration: includeTransliteration,
        voice_overrides: voiceOverrides
      };
    });
  }, [prefillParameters, forcedBaseOutputFile]);

  useEffect(() => {
    let cancelled = false;
    const loadDefaults = async () => {
      try {
        const defaults = await fetchPipelineDefaults();
        if (cancelled) {
          return;
        }
        const config = defaults?.config ?? {};
        userEditedStartRef.current = false;
        userEditedInputRef.current = false;
        userEditedEndRef.current = false;
        lastAutoEndSentenceRef.current = null;
        setFormState((previous) => {
          const next = applyConfigDefaults(previous, config);
          const suggestedStart = resolveStartFromHistory(next.input_file);
          const baseOutput = forcedBaseOutputFile ?? next.base_output_file;
          if (suggestedStart !== null) {
            return { ...next, start_sentence: suggestedStart, base_output_file: baseOutput };
          }
          return { ...next, base_output_file: baseOutput };
        });
        const inputLanguage = typeof config['input_language'] === 'string' ? config['input_language'] : null;
        if (inputLanguage) {
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
        if (targetLanguages.length > 0) {
          setSharedTargetLanguages(targetLanguages);
        }
      } catch (defaultsError) {
        console.warn('Unable to load pipeline defaults', defaultsError);
      }
    };
    void loadDefaults();
    return () => {
      cancelled = true;
    };
  }, [resolveStartFromHistory, setSharedInputLanguage, setSharedTargetLanguages, forcedBaseOutputFile]);

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
    if (key === 'start_sentence') {
      userEditedStartRef.current = true;
    } else if (key === 'end_sentence') {
      userEditedEndRef.current = true;
      lastAutoEndSentenceRef.current = null;
    } else if (key === 'base_output_file') {
      if (forcedBaseOutputFile !== null && forcedBaseOutputFile !== undefined) {
        return;
      }
      userEditedInputRef.current = true;
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
      if (!areLanguageArraysEqual(sharedTargetLanguages, nextLanguages)) {
        setSharedTargetLanguages(nextLanguages);
      }
    }
  };

  const updateVoiceOverride = useCallback((languageCode: string, voiceValue: string) => {
    const trimmedCode = languageCode.trim();
    if (!trimmedCode) {
      return;
    }
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
  }, []);

  const handleInputFileChange = (value: string) => {
    setRecentUploadName(null);
    setUploadError(null);
    userEditedStartRef.current = false;
    userEditedInputRef.current = true;
    userEditedEndRef.current = false;
    lastAutoEndSentenceRef.current = null;
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
        book_metadata: '{}',
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
    return Array.from(new Set([...formState.target_languages, ...manualTargets]));
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

      const configOverrides = { ...json.config };
      const selectedModel = formState.ollama_model.trim();
      if (selectedModel) {
        pipelineOverrides.ollama_model = selectedModel;
      }

      const normalizedStartSentence = isGeneratedSource
        ? 1
        : Math.max(1, Math.trunc(Number(formState.start_sentence)));
      if (!Number.isFinite(normalizedStartSentence)) {
        throw new Error('Start sentence must be a valid number.');
      }
      const normalizedEndSentence = isGeneratedSource
        ? null
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
          written_mode: formState.written_mode.trim(),
          selected_voice: formState.selected_voice.trim(),
          voice_overrides: sanitizedVoiceOverrides,
          output_html: formState.output_html,
          output_pdf: formState.output_pdf,
          generate_video: formState.generate_video,
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

  const headerTitle = sectionMeta[activeTab]?.title ?? 'Submit a Pipeline Job';
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
      formState.generate_video ? 'Video' : null
    ]
      .filter(Boolean)
      .join(', ') || 'Default';
  const missingRequirementText = formatList(missingRequirements);
  const canBrowseFiles = Boolean(fileOptions);

  const renderSection = (section: PipelineFormSection) => {
    switch (section) {
      case 'source':
        return (
          customSourceSection ?? (
            <PipelineSourceSection
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
            />
          )
        );
      case 'metadata': {
        let parsedMetadata: Record<string, unknown> | null = null;
        let parsedError: string | null = null;
        try {
          parsedMetadata = parseJsonField('book_metadata', formState.book_metadata);
        } catch (error) {
          parsedMetadata = null;
          parsedError = error instanceof Error ? error.message : String(error);
        }

        const jobLabel = normalizeTextValue(parsedMetadata?.['job_label']);
        const bookTitle = normalizeTextValue(parsedMetadata?.['book_title']);
        const bookAuthor = normalizeTextValue(parsedMetadata?.['book_author']);
        const bookYear = normalizeTextValue(parsedMetadata?.['book_year']);
        const isbn =
          normalizeTextValue(parsedMetadata?.['isbn']) || normalizeTextValue(parsedMetadata?.['book_isbn']);
        const summary = normalizeTextValue(parsedMetadata?.['book_summary']);
        const coverUrl = normalizeTextValue(parsedMetadata?.['cover_url']);
        const coverFile = normalizeTextValue(parsedMetadata?.['book_cover_file']);
        const openlibraryWorkUrl = normalizeTextValue(parsedMetadata?.['openlibrary_work_url']);
        const openlibraryBookUrl = normalizeTextValue(parsedMetadata?.['openlibrary_book_url']);
        const openlibraryLink = openlibraryBookUrl || openlibraryWorkUrl;
        const isbnQuery = normalizeIsbnCandidate(isbn);
        const resolvedLookupQuery = (isbnQuery ?? metadataLookupQuery).trim();

        const lookup = metadataPreview ? coerceRecord(metadataPreview.book_metadata_lookup) : null;
        const storedLookup = parsedMetadata ? coerceRecord(parsedMetadata['book_metadata_lookup']) : null;
        const rawPayload = lookup ?? storedLookup;
        const lookupBook = lookup ? coerceRecord(lookup['book']) : null;
        const lookupError = normalizeTextValue(lookup?.['error']);
        const lookupCoverUrl =
          normalizeTextValue(lookupBook?.['cover_url']) || normalizeTextValue(lookup?.['cover_url']);
        const lookupCoverFile =
          normalizeTextValue(lookupBook?.['cover_file']) || normalizeTextValue(lookup?.['cover_file']);
        const coverPreviewUrl =
          resolveCoverPreviewUrlFromCoverFile(coverFile) ||
          resolveCoverPreviewUrlFromCoverFile(lookupCoverFile) ||
          lookupCoverUrl ||
          coverUrl;
        const coverPreviewUrlWithRefresh =
          coverPreviewUrl && coverPreviewUrl.includes('/storage/covers/')
            ? `${coverPreviewUrl}${coverPreviewUrl.includes('?') ? '&' : '?'}v=${coverPreviewRefreshKey}`
            : coverPreviewUrl;
        const coverDropzoneClassName = [
          'file-dropzone',
          'cover-dropzone',
          isCoverDragActive ? 'file-dropzone--dragging' : '',
          isUploadingCover ? 'file-dropzone--uploading' : ''
        ]
          .filter(Boolean)
          .join(' ');

        const updateBookMetadata = (updater: (draft: Record<string, unknown>) => void) => {
          setFormState((previous) => {
            let draft: Record<string, unknown> = {};
            try {
              draft = parseJsonField('book_metadata', previous.book_metadata);
            } catch {
              draft = {};
            }
            const next = { ...draft };
            updater(next);
            const nextJson = JSON.stringify(next, null, 2);
            if (nextJson === previous.book_metadata) {
              return previous;
            }
            return { ...previous, book_metadata: nextJson };
          });
        };

        const performCoverUpload = async (candidate: File | null) => {
          if (!candidate || isUploadingCover) {
            return;
          }
          setCoverUploadCandidate(candidate);
          setIsUploadingCover(true);
          setCoverUploadError(null);
          try {
            const entry = await uploadCoverFile(candidate);
            updateBookMetadata((draft) => {
              draft['book_cover_file'] = entry.path;
            });
            setCoverPreviewRefreshKey((previous) => previous + 1);
          } catch (error) {
            const message = error instanceof Error ? error.message : 'Unable to upload cover image.';
            setCoverUploadError(message);
          } finally {
            setIsUploadingCover(false);
            setCoverUploadCandidate(null);
            setIsCoverDragActive(false);
            if (coverUploadInputRef.current) {
              coverUploadInputRef.current.value = '';
            }
          }
        };

        return (
          <section className="pipeline-card" aria-labelledby="pipeline-card-metadata">
            <header className="pipeline-card__header">
              <h3 id="pipeline-card-metadata">{sectionMeta.metadata.title}</h3>
              <p>{sectionMeta.metadata.description}</p>
            </header>

            {metadataError ? (
              <div className="alert" role="alert">
                {metadataError}
              </div>
            ) : null}

            <div className="metadata-loader-row">
              <label style={{ marginBottom: 0 }}>
                Lookup query
                <input
                  type="text"
                  value={metadataLookupQuery}
                  onChange={(event) => setMetadataLookupQuery(event.target.value)}
                  placeholder={
                    metadataSourceName ? metadataSourceName : 'Title, ISBN, or filename (ISBN field preferred)'
                  }
                />
              </label>
              <div className="metadata-loader-actions">
                <button
                  type="button"
                  className="link-button"
                  onClick={() => void performMetadataLookup(resolvedLookupQuery, false)}
                  disabled={!resolvedLookupQuery || metadataLoading}
                  aria-busy={metadataLoading}
                >
                  {metadataLoading ? 'Looking up…' : 'Lookup'}
                </button>
                <button
                  type="button"
                  className="link-button"
                  onClick={() => void performMetadataLookup(resolvedLookupQuery, true)}
                  disabled={!resolvedLookupQuery || metadataLoading}
                  aria-busy={metadataLoading}
                >
                  Refresh
                </button>
                <button
                  type="button"
                  className="link-button"
                  onClick={() => {
                    setMetadataPreview(null);
                    setMetadataError(null);
                    setMetadataLoading(false);
                    setFormState((previous) => ({ ...previous, book_metadata: '{}' }));
                  }}
                  disabled={metadataLoading}
                >
                  Clear
                </button>
              </div>
            </div>

            {!metadataSourceName && !metadataLookupQuery.trim() ? (
              <p className="form-help-text" role="status">
                Select an EPUB file in the Source tab to load metadata.
              </p>
            ) : null}

            {metadataLoading ? (
              <p className="form-help-text" role="status">
                Loading metadata…
              </p>
            ) : null}

            <div className="book-metadata-cover" aria-label="Book cover">
              {coverPreviewUrl ? (
                openlibraryLink ? (
                  <a href={openlibraryLink} target="_blank" rel="noopener noreferrer">
                    <img
                      src={coverPreviewUrlWithRefresh ?? undefined}
                      alt={bookTitle ? `Cover for ${bookTitle}` : 'Book cover'}
                      loading="lazy"
                      decoding="async"
                    />
                  </a>
                ) : (
                  <img
                    src={coverPreviewUrlWithRefresh ?? undefined}
                    alt={bookTitle ? `Cover for ${bookTitle}` : 'Book cover'}
                    loading="lazy"
                    decoding="async"
                  />
                )
              ) : (
                <div className="book-metadata-cover__placeholder" aria-hidden="true">
                  No cover
                </div>
              )}
              <div
                className={coverDropzoneClassName}
                onDragOver={(event) => {
                  if (isUploadingCover) {
                    return;
                  }
                  event.preventDefault();
                  setIsCoverDragActive(true);
                }}
                onDragLeave={() => setIsCoverDragActive(false)}
                onDrop={(event) => {
                  if (isUploadingCover) {
                    return;
                  }
                  event.preventDefault();
                  setIsCoverDragActive(false);
                  const file = event.dataTransfer.files?.[0] ?? null;
                  void performCoverUpload(file);
                }}
                aria-busy={isUploadingCover}
              >
                <label>
                  <strong>Upload cover</strong>
                  <span>
                    {isUploadingCover
                      ? 'Uploading…'
                      : coverUploadCandidate
                        ? coverUploadCandidate.name
                        : 'Drop image here or click to browse (saved as 600×900 JPG)'}
                  </span>
                </label>
                <input
                  ref={coverUploadInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={(event) => {
                    const file = event.target.files?.[0] ?? null;
                    setCoverUploadError(null);
                    void performCoverUpload(file);
                  }}
                  disabled={isUploadingCover}
                />
              </div>
            </div>

            {coverUploadError ? (
              <p className="form-help-text form-help-text--error" role="alert">
                Cover upload failed: {coverUploadError}
              </p>
            ) : null}

            {bookTitle || bookAuthor || bookYear || isbn || openlibraryLink || coverUrl || coverFile ? (
              <dl className="metadata-grid">
                {jobLabel ? (
                  <div className="metadata-grid__row">
                    <dt>Label</dt>
                    <dd>{jobLabel}</dd>
                  </div>
                ) : null}
                {bookTitle ? (
                  <div className="metadata-grid__row">
                    <dt>Title</dt>
                    <dd>{bookTitle}</dd>
                  </div>
                ) : null}
                {bookAuthor ? (
                  <div className="metadata-grid__row">
                    <dt>Author</dt>
                    <dd>{bookAuthor}</dd>
                  </div>
                ) : null}
                {bookYear ? (
                  <div className="metadata-grid__row">
                    <dt>Year</dt>
                    <dd>{bookYear}</dd>
                  </div>
                ) : null}
                {isbn ? (
                  <div className="metadata-grid__row">
                    <dt>ISBN</dt>
                    <dd>{isbn}</dd>
                  </div>
                ) : null}
                {openlibraryLink ? (
                  <div className="metadata-grid__row">
                    <dt>Open Library</dt>
                    <dd>
                      <a href={openlibraryLink} target="_blank" rel="noopener noreferrer">
                        {openlibraryLink}
                      </a>
                    </dd>
                  </div>
                ) : null}
                {coverUrl ? (
                  <div className="metadata-grid__row">
                    <dt>Cover URL</dt>
                    <dd>{coverUrl}</dd>
                  </div>
                ) : null}
                {coverFile ? (
                  <div className="metadata-grid__row">
                    <dt>Cover file</dt>
                    <dd>{coverFile}</dd>
                  </div>
                ) : null}
              </dl>
            ) : null}

            {metadataPreview ? (
              <dl className="metadata-grid">
                {metadataPreview.source_name ? (
                  <div className="metadata-grid__row">
                    <dt>Source</dt>
                    <dd>{metadataPreview.source_name}</dd>
                  </div>
                ) : null}
                {metadataPreview.query?.title ? (
                  <div className="metadata-grid__row">
                    <dt>Query</dt>
                    <dd>
                      {[metadataPreview.query.title, metadataPreview.query.author, metadataPreview.query.isbn]
                        .filter(Boolean)
                        .join(' · ')}
                    </dd>
                  </div>
                ) : metadataPreview.query?.isbn ? (
                  <div className="metadata-grid__row">
                    <dt>Query</dt>
                    <dd>{metadataPreview.query.isbn}</dd>
                  </div>
                ) : null}
                {lookupError ? (
                  <div className="metadata-grid__row">
                    <dt>Status</dt>
                    <dd>{lookupError}</dd>
                  </div>
                ) : null}
              </dl>
            ) : null}

            {rawPayload ? (
              <details>
                <summary>Raw payload</summary>
                <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(rawPayload, null, 2)}</pre>
              </details>
            ) : null}

            <fieldset>
              <legend>Edit metadata</legend>
              {parsedError ? (
                <div className="notice notice--warning" role="alert">
                  Book metadata JSON is invalid: {parsedError}
                </div>
              ) : null}
              <div className="field-grid">
                <label>
                  Job label
                  <input
                    type="text"
                    value={jobLabel ?? ''}
                    onChange={(event) => {
                      const value = event.target.value;
                      updateBookMetadata((draft) => {
                        const trimmed = value.trim();
                        if (trimmed) {
                          draft['job_label'] = trimmed;
                        } else {
                          delete draft['job_label'];
                        }
                      });
                    }}
                  />
                </label>
                <label>
                  Title
                  <input
                    type="text"
                    value={bookTitle ?? ''}
                    onChange={(event) => {
                      const value = event.target.value;
                      updateBookMetadata((draft) => {
                        const trimmed = value.trim();
                        if (trimmed) {
                          draft['book_title'] = trimmed;
                        } else {
                          delete draft['book_title'];
                        }
                      });
                    }}
                  />
                </label>
                <label>
                  Author
                  <input
                    type="text"
                    value={bookAuthor ?? ''}
                    onChange={(event) => {
                      const value = event.target.value;
                      updateBookMetadata((draft) => {
                        const trimmed = value.trim();
                        if (trimmed) {
                          draft['book_author'] = trimmed;
                        } else {
                          delete draft['book_author'];
                        }
                      });
                    }}
                  />
                </label>
                <label>
                  Year
                  <input
                    type="text"
                    inputMode="numeric"
                    value={bookYear ?? ''}
                    onChange={(event) => {
                      const value = event.target.value;
                      updateBookMetadata((draft) => {
                        const trimmed = value.trim();
                        if (trimmed) {
                          draft['book_year'] = trimmed;
                        } else {
                          delete draft['book_year'];
                        }
                      });
                    }}
                  />
                </label>
                <label>
                  ISBN
                  <input
                    type="text"
                    value={isbn ?? ''}
                    onChange={(event) => {
                      const value = event.target.value;
                      updateBookMetadata((draft) => {
                        const trimmed = value.trim();
                        if (trimmed) {
                          draft['isbn'] = trimmed;
                          draft['book_isbn'] = trimmed;
                        } else {
                          delete draft['isbn'];
                          delete draft['book_isbn'];
                        }
                      });
                    }}
                  />
                </label>
                <label style={{ gridColumn: '1 / -1' }}>
                  Summary
                  <textarea
                    rows={4}
                    value={summary ?? ''}
                    onChange={(event) => {
                      const value = event.target.value;
                      updateBookMetadata((draft) => {
                        const trimmed = value.trim();
                        if (trimmed) {
                          draft['book_summary'] = trimmed;
                        } else {
                          delete draft['book_summary'];
                        }
                      });
                    }}
                  />
                </label>
                <label style={{ gridColumn: '1 / -1' }}>
                  Cover URL
                  <input
                    type="text"
                    value={coverUrl ?? ''}
                    onChange={(event) => {
                      const value = event.target.value;
                      updateBookMetadata((draft) => {
                        const trimmed = value.trim();
                        if (trimmed) {
                          draft['cover_url'] = trimmed;
                        } else {
                          delete draft['cover_url'];
                        }
                      });
                    }}
                  />
                </label>
                <label style={{ gridColumn: '1 / -1' }}>
                  Cover file (local)
                  <input
                    type="text"
                    value={coverFile ?? ''}
                    onChange={(event) => {
                      const value = event.target.value;
                      updateBookMetadata((draft) => {
                        const trimmed = value.trim();
                        if (trimmed) {
                          draft['book_cover_file'] = trimmed;
                        } else {
                          delete draft['book_cover_file'];
                        }
                      });
                    }}
                  />
                </label>
              </div>
            </fieldset>
          </section>
        );
      }
      case 'language':
        return (
          <PipelineLanguageSection
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
            startSentence={formState.start_sentence}
            endSentence={formState.end_sentence}
            stitchFull={formState.stitch_full}
            disableProcessingWindow={isGeneratedSource}
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
          <PipelineOutputSection
            key="output"
            headingId="pipeline-card-output"
            title={sectionMeta.output.title}
            description={sectionMeta.output.description}
            generateAudio={formState.generate_audio}
            audioMode={formState.audio_mode}
            selectedVoice={formState.selected_voice}
            writtenMode={formState.written_mode}
            outputHtml={formState.output_html}
            outputPdf={formState.output_pdf}
            includeTransliteration={formState.include_transliteration}
            tempo={formState.tempo}
            generateVideo={formState.generate_video}
            availableAudioModes={availableAudioModes}
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
      case 'performance':
        return (
          <PipelinePerformanceSection
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

export default PipelineSubmissionForm;
