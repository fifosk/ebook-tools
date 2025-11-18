import { DragEvent, FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  MacOSVoice,
  PipelineFileBrowserResponse,
  PipelineFileEntry,
  PipelineRequestPayload,
  VoiceInventoryResponse
} from '../api/dtos';
import {
  fetchPipelineDefaults,
  fetchPipelineFiles,
  fetchVoiceInventory,
  fetchLlmModels,
  deletePipelineEbook,
  synthesizeVoicePreview,
  uploadEpubFile
} from '../api/client';
import {
  AUDIO_MODE_OPTIONS,
  MenuOption,
  VOICE_OPTIONS,
  WRITTEN_MODE_OPTIONS
} from '../constants/menuOptions';
import { resolveLanguageCode, resolveLanguageName } from '../constants/languageCodes';
import { useLanguagePreferences } from '../context/LanguageProvider';
import PipelineSourceSection from './PipelineSourceSection';
import PipelineLanguageSection from './PipelineLanguageSection';
import PipelineOutputSection from './PipelineOutputSection';
import PipelinePerformanceSection from './PipelinePerformanceSection';
import PipelineSubmitSection from './PipelineSubmitSection';
import FileSelectionDialog from './FileSelectionDialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/Tabs';

const SAMPLE_SENTENCES: Record<string, string> = {
  en: 'Hello from ebook-tools! This is a sample narration.',
  es: 'Hola desde ebook-tools. Esta es una frase de ejemplo.',
  fr: 'Bonjour de ebook-tools. Ceci est une phrase exemple.',
  ar: 'مرحبا من منصة ebook-tools.',
  ja: 'ebook-tools からのサンプル文です。'
};

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

function sampleSentenceFor(languageCode: string, fallbackLabel: string): string {
  const normalized = languageCode.trim().toLowerCase();
  if (normalized && SAMPLE_SENTENCES[normalized]) {
    return SAMPLE_SENTENCES[normalized];
  }
  const resolvedName = resolveLanguageName(languageCode) ?? fallbackLabel;
  const displayName = resolvedName || 'this language';
  return `Sample narration for ${displayName}.`;
}
export type PipelineFormSection =
  | 'source'
  | 'language'
  | 'output'
  | 'performance'
  | 'submit';

type Props = {
  onSubmit: (payload: PipelineRequestPayload) => Promise<void> | void;
  isSubmitting?: boolean;
  activeSection?: PipelineFormSection;
  externalError?: string | null;
  prefillInputFile?: string | null;
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
  selected_voice: 'macOS-auto',
  voice_overrides: {},
  output_html: true,
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
  'language',
  'output',
  'performance',
  'submit'
];

export const PIPELINE_SECTION_META: Record<PipelineFormSection, { title: string; description: string }> = {
  source: {
    title: 'Source material',
    description: 'Select the EPUB to ingest and where generated files should be written.'
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
  externalError = null,
  prefillInputFile = null
}: Props) {
  const {
    inputLanguage: sharedInputLanguage,
    setInputLanguage: setSharedInputLanguage,
    targetLanguages: sharedTargetLanguages,
    setTargetLanguages: setSharedTargetLanguages
  } = useLanguagePreferences();
  const [formState, setFormState] = useState<FormState>(() => ({
    ...DEFAULT_FORM_STATE,
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

  const tabSections: PipelineFormSection[] = ['source', 'language', 'output', 'performance'];
  const [activeTab, setActiveTab] = useState<PipelineFormSection>(() => {
    if (activeSection && tabSections.includes(activeSection)) {
      return activeSection;
    }
    return 'source';
  });
  const isSubmitSection = activeSection === 'submit';

  useEffect(() => {
    if (activeSection && tabSections.includes(activeSection)) {
      setActiveTab(activeSection);
    }
  }, [activeSection]);

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
    setFormState((previous) => {
      if (previous.input_file === normalizedPrefill) {
        return previous;
      }
      const previousDerivedBase = deriveBaseOutputName(previous.input_file);
      const nextDerivedBase = deriveBaseOutputName(normalizedPrefill);
      const shouldUpdateBase =
        !previous.base_output_file || previous.base_output_file === previousDerivedBase;
      return {
        ...previous,
        input_file: normalizedPrefill,
        base_output_file: shouldUpdateBase ? nextDerivedBase : previous.base_output_file,
        book_metadata: '{}'
      };
    });
    prefillAppliedRef.current = normalizedPrefill;
  }, [prefillInputFile]);

  useEffect(() => {
    let cancelled = false;
    const loadDefaults = async () => {
      try {
        const defaults = await fetchPipelineDefaults();
        if (cancelled) {
          return;
        }
        const config = defaults?.config ?? {};
        setFormState((previous) => applyConfigDefaults(previous, config));
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
  }, [setSharedInputLanguage, setSharedTargetLanguages]);

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

  const handleChange = <K extends keyof FormState>(key: K, value: FormState[K]) => {
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
    setFormState((previous) => {
      if (previous.input_file === value) {
        return previous;
      }
      const previousDerivedBase = deriveBaseOutputName(previous.input_file);
      const nextDerivedBase = deriveBaseOutputName(value);
      const shouldUpdateBase =
        !previous.base_output_file ||
        previous.base_output_file === previousDerivedBase;
      return {
        ...previous,
        input_file: value,
        base_output_file: shouldUpdateBase ? nextDerivedBase : previous.base_output_file,
        book_metadata: '{}'
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
  }, []);

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
            previous.base_output_file === derivedBase ? '' : previous.base_output_file;
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
    [refreshFiles]
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
    void refreshFiles();
  }, [refreshFiles]);

  useEffect(() => {
    if (!fileOptions || fileOptions.ebooks.length === 0) {
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
      return {
        ...previous,
        input_file: nextInput,
        base_output_file: derivedBase || previous.base_output_file || 'book-output'
      };
    });
  }, [fileOptions]);

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
        configOverrides.ollama_model = selectedModel;
      }

      const payload: PipelineRequestPayload = {
        config: configOverrides,
        environment_overrides: json.environment_overrides,
        pipeline_overrides: pipelineOverrides,
        inputs: {
          input_file: formState.input_file,
          base_output_file: formState.base_output_file,
          input_language: formState.input_language,
          target_languages: normalizedTargetLanguages,
          sentences_per_output_file: Number(formState.sentences_per_output_file),
          start_sentence: Number(formState.start_sentence),
          end_sentence: formState.end_sentence ? Number(formState.end_sentence) : null,
          stitch_full: formState.stitch_full,
          generate_audio: formState.generate_audio,
          audio_mode: formState.audio_mode,
          written_mode: formState.written_mode,
          selected_voice: formState.selected_voice,
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

  const headerTitle = activeSection ? PIPELINE_SECTION_META[activeSection].title : 'Submit a Pipeline Job';
  const headerDescription = activeSection
    ? PIPELINE_SECTION_META[activeSection].description
    : 'Provide the input file, target languages, and any overrides to enqueue a new ebook processing job.';
  const missingRequirements: string[] = [];
  if (!formState.input_file.trim()) {
    missingRequirements.push('an input EPUB');
  }
  if (!formState.base_output_file.trim()) {
    missingRequirements.push('a base output path');
  }
  if (normalizedTargetLanguages.length === 0) {
    missingRequirements.push('at least one target language');
  }
  const targetLanguageSummary =
    normalizedTargetLanguages.length > 0 ? normalizedTargetLanguages.join(', ') : 'None selected';
  const isSubmitDisabled = isSubmitting || missingRequirements.length > 0;
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
          <PipelineSourceSection
            key="source"
            headingId="pipeline-card-source"
            title={PIPELINE_SECTION_META.source.title}
            description={PIPELINE_SECTION_META.source.description}
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
          />
        );
      case 'language':
        return (
          <PipelineLanguageSection
            key="language"
            headingId="pipeline-card-language"
            title={PIPELINE_SECTION_META.language.title}
            description={PIPELINE_SECTION_META.language.description}
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
            title={PIPELINE_SECTION_META.output.title}
            description={PIPELINE_SECTION_META.output.description}
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
            title={PIPELINE_SECTION_META.performance.title}
            description={PIPELINE_SECTION_META.performance.description}
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
        return (
          <PipelineSubmitSection
            key="submit"
            headingId="pipeline-card-submit"
            title={PIPELINE_SECTION_META.submit.title}
            description={PIPELINE_SECTION_META.submit.description}
            missingRequirements={missingRequirements}
            missingRequirementText={missingRequirementText}
            isSubmitSection={isSubmitSection}
            error={error}
            externalError={externalError}
            inputFile={formState.input_file}
            baseOutputFile={formState.base_output_file}
            inputLanguage={formState.input_language}
            targetLanguageSummary={targetLanguageSummary}
            outputFormats={outputFormats}
            isSubmitting={isSubmitting}
            isSubmitDisabled={isSubmitDisabled}
          />
        );
    }
  };

  return (
    <section className="pipeline-settings">
      <h2>{headerTitle}</h2>
      <p>{headerDescription}</p>
      <form className="pipeline-form" onSubmit={handleSubmit} noValidate>
      <Tabs
        className="pipeline-tabs"
        value={activeTab}
        onValueChange={(next) => setActiveTab(next as PipelineFormSection)}
      >
        <TabsList className="pipeline-tabs__list">
          {tabSections.map((section) => (
            <TabsTrigger key={section} value={section} className="pipeline-tabs__trigger">
              <span className="pipeline-tabs__trigger-title">
                {PIPELINE_SECTION_META[section].title}
              </span>
              <span className="pipeline-tabs__trigger-description">
                {PIPELINE_SECTION_META[section].description}
              </span>
            </TabsTrigger>
          ))}
        </TabsList>
        {tabSections.map((section) => (
          <TabsContent
            key={section}
            value={section}
            className="pipeline-tabs__content"
          >
            {renderSection(section)}
          </TabsContent>
        ))}
      </Tabs>
      {renderSection('submit')}
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
    </section>
  );

}

export default PipelineSubmissionForm;
