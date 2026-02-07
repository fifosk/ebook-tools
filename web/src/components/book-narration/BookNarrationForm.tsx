import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from 'react';
import { PipelineStatusResponse } from '../../api/dtos';
import {
  AUDIO_MODE_OPTIONS,
  AUDIO_QUALITY_OPTIONS,
  MenuOption,
  VOICE_OPTIONS,
  WRITTEN_MODE_OPTIONS
} from '../../constants/menuOptions';
import { resolveLanguageCode } from '../../constants/languageCodes';
import { formatLanguageWithFlag } from '../../utils/languages';
import { loadCachedMediaMetadataJson } from '../../utils/mediaMetadataCache';
import { useLanguagePreferences } from '../../context/LanguageProvider';
import FileSelectionDialog from '../FileSelectionDialog';
import { useBookNarrationVoices } from './useBookNarrationVoices';
import { useBookNarrationMetadata } from './useBookNarrationMetadata';
import { useBookNarrationFiles } from './useBookNarrationFiles';
import { useBookNarrationSubmit } from './useBookNarrationSubmit';
import { BookNarrationFormSections } from './BookNarrationFormSections';
import { useBookNarrationChapters } from './useBookNarrationChapters';
import { useBookNarrationLlmModels } from './useBookNarrationLlmModels';
import { useBookNarrationDefaults } from './useBookNarrationDefaults';
import type {
  BookNarrationFormProps,
  BookNarrationFormSection,
  FormState
} from './bookNarrationFormTypes';
import {
  BOOK_NARRATION_SECTION_META,
  BOOK_NARRATION_TAB_SECTIONS,
  DEFAULT_FORM_STATE,
  IMAGE_DEFAULT_FIELDS
} from './bookNarrationFormDefaults';
import {
  areLanguageArraysEqual,
  deriveBaseOutputName,
  formatList,
  normalizeImagePromptPipeline,
  normalizeSingleTargetLanguages
} from './bookNarrationFormUtils';

export type { BookNarrationFormSection } from './bookNarrationFormTypes';

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
      const defaultPromptPipeline = normalizeImagePromptPipeline(imageDefaults.image_prompt_pipeline);
      if (
        defaultPromptPipeline &&
        !edited.has('image_prompt_pipeline') &&
        state.image_prompt_pipeline !== defaultPromptPipeline
      ) {
        merge({ image_prompt_pipeline: defaultPromptPipeline });
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
  const {
    voiceInventoryError,
    isLoadingVoiceInventory,
    voicePreviewStatus,
    voicePreviewError,
    playVoicePreview,
    buildVoiceOptions
  } = useBookNarrationVoices({
    selectedVoice: formState.selected_voice,
    voiceOverrides: formState.voice_overrides
  });
  const { availableLlmModels, llmModelError, isLoadingLlmModels } = useBookNarrationLlmModels();
  const [error, setError] = useState<string | null>(null);
  const prefillAppliedRef = useRef<string | null>(null);
  const prefillParametersRef = useRef<string | null>(null);
  const recentJobsRef = useRef<PipelineStatusResponse[] | null>(recentJobs ?? null);
  const userEditedStartRef = useRef<boolean>(false);
  const userEditedInputRef = useRef<boolean>(false);
  const userEditedEndRef = useRef<boolean>(false);
  const userEditedFieldsRef = useRef<Set<keyof FormState>>(new Set<keyof FormState>());
  const defaultsAppliedRef = useRef<boolean>(false);
  const lastAutoEndSentenceRef = useRef<string | null>(null);

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
  const {
    chapterSelectionMode,
    chapterOptions,
    selectedChapterIds,
    chapterSelection,
    chapterSelectionSummary,
    chaptersLoading,
    chaptersError,
    chaptersDisabled,
    estimatedAudioDurationLabel,
    handleChapterModeChange,
    handleChapterToggle,
    handleChapterClear,
    displayStartSentence,
    displayEndSentence
  } = useBookNarrationChapters({
    inputFile: formState.input_file,
    startSentence: formState.start_sentence,
    endSentence: formState.end_sentence,
    isGeneratedSource,
    implicitEndOffsetThreshold: implicitEndOffsetThreshold ?? null,
    normalizedInputPath: normalizedInputForBookMetadataCache
  });
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

  const {
    metadataSourceName,
    metadataLookupQuery,
    setMetadataLookupQuery,
    metadataPreview,
    metadataLoading,
    metadataError,
    cachedCoverDataUrl,
    performMetadataLookup,
    handleClearMetadata
  } = useBookNarrationMetadata({
    isGeneratedSource,
    activeTab,
    inputFile: formState.input_file,
    mediaMetadataJson: formState.book_metadata,
    normalizedInputPath: normalizedInputForBookMetadataCache,
    normalizePath,
    setFormState,
    markUserEditedField
  });
  const {
    fileOptions,
    fileDialogError,
    isLoadingFiles,
    activeFileDialog,
    setActiveFileDialog,
    isDraggingFile,
    isUploadingFile,
    uploadError,
    recentUploadName,
    handleInputFileChange,
    handleDeleteEbook,
    processFileUpload,
    handleDropzoneDragOver,
    handleDropzoneDragLeave,
    handleDropzoneDrop
  } = useBookNarrationFiles({
    isGeneratedSource,
    forcedBaseOutputFile,
    markUserEditedField,
    normalizePath,
    resolveStartFromHistory,
    setFormState,
    prefillAppliedRef,
    userEditedStartRef,
    userEditedInputRef,
    userEditedEndRef,
    lastAutoEndSentenceRef
  });

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
    const cachedBookMetadata = normalizedInput ? loadCachedMediaMetadataJson(normalizedInput) : null;
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
        translation_provider: translationProvider,
        translation_batch_size: translationBatchSize,
        transliteration_mode: transliterationMode,
        transliteration_model: transliterationModel,
        add_images: addImages,
        voice_overrides: voiceOverrides
      };
      return preserveUserEditedFields(previous, next);
    });
  }, [prefillParameters, forcedBaseOutputFile, preserveUserEditedFields]);

  useBookNarrationDefaults({
    formState,
    isGeneratedSource,
    forcedBaseOutputFile,
    recentJobs,
    resolveLatestJobSelection,
    resolveStartFromHistory,
    applyImageDefaults,
    preserveUserEditedFields,
    defaultsAppliedRef,
    userEditedFieldsRef,
    userEditedImageDefaultsRef,
    userEditedInputRef,
    userEditedStartRef,
    userEditedEndRef,
    lastAutoEndSentenceRef,
    setFormState,
    sharedInputLanguage,
    sharedTargetLanguages,
    setSharedInputLanguage,
    setSharedTargetLanguages
  });

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

  const { handleSubmit } = useBookNarrationSubmit({
    formState,
    normalizedTargetLanguages,
    chapterSelectionMode,
    chapterSelection: chapterSelection ? {
      startSentence: chapterSelection.startSentence,
      endSentence: chapterSelection.endSentence
    } : null,
    isGeneratedSource,
    forcedBaseOutputFile,
    implicitEndOffsetThreshold: implicitEndOffsetThreshold ?? null,
    onSubmit,
    setError
  });

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
      formState.add_images ? 'Images' : null
    ]
      .filter(Boolean)
      .join(', ') || 'Default';
  const missingRequirementText = formatList(missingRequirements);
  const canBrowseFiles = Boolean(fileOptions);
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
        <div className="pipeline-section-panel">
          <BookNarrationFormSections
            section={activeTab}
            sectionMeta={sectionMeta}
            customSourceSection={customSourceSection}
            formState={formState}
            handleChange={handleChange}
            handleInputFileChange={handleInputFileChange}
            setActiveFileDialog={setActiveFileDialog}
            canBrowseFiles={canBrowseFiles}
            isLoadingFiles={isLoadingFiles}
            fileDialogError={fileDialogError}
            isDraggingFile={isDraggingFile}
            isUploadingFile={isUploadingFile}
            uploadError={uploadError}
            recentUploadName={recentUploadName}
            onDropzoneDragOver={handleDropzoneDragOver}
            onDropzoneDragLeave={handleDropzoneDragLeave}
            onDropzoneDrop={handleDropzoneDrop}
            onUploadFile={processFileUpload}
            metadataSourceName={metadataSourceName}
            metadataLookupQuery={metadataLookupQuery}
            metadataPreview={metadataPreview}
            metadataLoading={metadataLoading}
            metadataError={metadataError}
            cachedCoverDataUrl={cachedCoverDataUrl}
            onMetadataLookupQueryChange={(value) => setMetadataLookupQuery(value)}
            onLookupMetadata={performMetadataLookup}
            onClearMetadata={handleClearMetadata}
            availableLlmModels={availableLlmModels}
            isLoadingLlmModels={isLoadingLlmModels}
            llmModelError={llmModelError}
            displayStartSentence={displayStartSentence}
            displayEndSentence={displayEndSentence}
            chapterSelectionMode={chapterSelectionMode}
            chapterOptions={chapterOptions}
            selectedChapterIds={selectedChapterIds}
            chapterSelectionSummary={chapterSelectionSummary}
            chaptersLoading={chaptersLoading}
            chaptersError={chaptersError}
            chaptersDisabled={chaptersDisabled}
            estimatedAudioDurationLabel={estimatedAudioDurationLabel}
            onProcessingModeChange={handleChapterModeChange}
            onChapterToggle={handleChapterToggle}
            onChapterClear={handleChapterClear}
            availableAudioModes={availableAudioModes}
            availableAudioQualities={AUDIO_QUALITY_OPTIONS}
            availableVoices={availableVoices}
            availableWrittenModes={availableWrittenModes}
            languagesForOverride={languagesForOverride}
            voicePreviewStatus={voicePreviewStatus}
            voicePreviewError={voicePreviewError}
            isLoadingVoiceInventory={isLoadingVoiceInventory}
            voiceInventoryError={voiceInventoryError}
            buildVoiceOptions={buildVoiceOptions}
            onVoiceOverrideChange={updateVoiceOverride}
            onPlayVoicePreview={playVoicePreview}
            showOutputPathControls={showOutputPathControls}
            isGeneratedSource={isGeneratedSource}
            forcedBaseOutputFile={forcedBaseOutputFile}
          />
        </div>
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
