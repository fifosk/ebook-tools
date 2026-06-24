import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from 'react';
import type { FormEvent } from 'react';
import { PipelineStatusResponse } from '../../api/dtos';
import { saveCreationTemplate } from '../../api/client';
import {
  AUDIO_MODE_OPTIONS,
  AUDIO_QUALITY_OPTIONS,
  MenuOption,
  VOICE_OPTIONS,
  WRITTEN_MODE_OPTIONS
} from '../../constants/menuOptions';
import { loadCachedMediaMetadataJson } from '../../utils/mediaMetadataCache';
import { useLanguagePreferences } from '../../context/LanguageProvider';
import { useBookNarrationVoices } from './useBookNarrationVoices';
import { useBookNarrationMetadata } from './useBookNarrationMetadata';
import { useBookNarrationFiles } from './useBookNarrationFiles';
import { useBookNarrationSubmit } from './useBookNarrationSubmit';
import { BookNarrationFormSections } from './BookNarrationFormSections';
import { useBookNarrationChapters } from './useBookNarrationChapters';
import { useBookNarrationLlmModels } from './useBookNarrationLlmModels';
import { useBookNarrationDefaults } from './useBookNarrationDefaults';
import { useCreateIntakeStatus } from '../create-intake/useCreateIntakeStatus';
import { BookNarrationStepBar } from './BookNarrationStepBar';
import { BookNarrationSubmitStatus } from './BookNarrationSubmitStatus';
import { BookNarrationFileDialog } from './BookNarrationFileDialog';
import { buildBookNarrationTemplatePayload } from './bookNarrationTemplates';
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
  applyBookNarrationImageDefaults,
  applyBookNarrationPrefillParameters,
  deriveBaseOutputName,
  formatList,
  normalizeBookNarrationPath,
  normalizeTargetLanguages,
  preserveBookNarrationUserEditedFields,
  resolveLatestBookNarrationJobSelection,
  resolveLatestBookNarrationJobSettings,
  resolveBookNarrationMissingRequirements,
  resolveBookNarrationVoiceOverrideLanguages,
  resolveBookNarrationSectionMeta,
  resolveStartFromNarrationHistory,
  targetLanguageFieldsFromLanguages
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
  defaultImageSettings = null,
  defaultPipelineSettings = null,
  supportedInputLanguages = null,
  supportedTargetLanguages = null
}: BookNarrationFormProps) {
  const isGeneratedSource = sourceMode === 'generated';
  const imageDefaults = defaultImageSettings ?? null;
  const userEditedImageDefaultsRef = useRef<Set<keyof FormState>>(new Set());
  const {
    inputLanguage: sharedInputLanguage,
    setInputLanguage: setSharedInputLanguage,
    targetLanguages: sharedTargetLanguages,
    setTargetLanguages: setSharedTargetLanguages,
    enableLookupCache: sharedEnableLookupCache,
    setEnableLookupCache: setSharedEnableLookupCache
  } = useLanguagePreferences();
  const hasPrefillAddImages = typeof prefillParameters?.add_images === 'boolean';
  const initialTargetLanguageFields = targetLanguageFieldsFromLanguages(
    sharedTargetLanguages.length > 0
      ? sharedTargetLanguages
      : DEFAULT_FORM_STATE.target_languages
  );
  const applyImageDefaults = useCallback(
    (state: FormState): FormState => {
      return applyBookNarrationImageDefaults({
        state,
        imageDefaults,
        editedFields: userEditedImageDefaultsRef.current,
        allowAddImagesDefault: !hasPrefillAddImages
      });
    },
    [hasPrefillAddImages, imageDefaults]
  );
  const [formState, setFormState] = useState<FormState>(() => ({
    ...DEFAULT_FORM_STATE,
    base_output_file: forcedBaseOutputFile ?? DEFAULT_FORM_STATE.base_output_file,
    input_language: sharedInputLanguage ?? DEFAULT_FORM_STATE.input_language,
    target_languages: initialTargetLanguageFields.target_languages.length > 0
      ? initialTargetLanguageFields.target_languages
      : [...DEFAULT_FORM_STATE.target_languages],
    custom_target_languages: initialTargetLanguageFields.custom_target_languages,
    enable_lookup_cache:
      typeof sharedEnableLookupCache === 'boolean'
        ? sharedEnableLookupCache
        : DEFAULT_FORM_STATE.enable_lookup_cache
  }));
  const {
    intakeStatus,
    isLoadingIntakeStatus,
    isIntakeAtCapacity,
    refreshIntakeStatus,
  } = useCreateIntakeStatus();
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
  const [templateStatus, setTemplateStatus] = useState<string | null>(null);
  const [templateError, setTemplateError] = useState<string | null>(null);
  const [isSavingTemplate, setIsSavingTemplate] = useState(false);
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
    return resolveBookNarrationSectionMeta(BOOK_NARRATION_SECTION_META, sectionOverrides);
  }, [sectionOverrides]);

  useEffect(() => {
    recentJobsRef.current = recentJobs ?? null;
  }, [recentJobs]);
  const normalizePath = useCallback(
    (value: string | null | undefined): string | null => normalizeBookNarrationPath(value),
    []
  );
  const resolveStartFromHistory = useCallback(
    (inputPath: string): number | null => {
      return resolveStartFromNarrationHistory(inputPath, recentJobsRef.current);
    },
    []
  );
  const markUserEditedField = useCallback((key: keyof FormState) => {
    userEditedFieldsRef.current.add(key);
  }, []);
  const preserveUserEditedFields = useCallback((previous: FormState, next: FormState): FormState => {
    return preserveBookNarrationUserEditedFields(previous, next, userEditedFieldsRef.current);
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
    return resolveLatestBookNarrationJobSelection(recentJobsRef.current);
  }, []);

  /**
   * Pick up source language, target languages and lookup-cache preference from
   * the most recent book job in the user's history. Mirrors how start_sentence
   * is prefilled from the last job on the same input file — only here the
   * match is "most recent book job" regardless of input_file. Returns null
   * when no usable job exists or none of the relevant fields are populated,
   * so the caller falls back to whatever defaults are already in place.
   */
  const resolveLatestJobSettings = useCallback((): {
    inputLanguage: string | null;
    targetLanguages: string[] | null;
    enableLookupCache: boolean | null;
  } | null => {
    return resolveLatestBookNarrationJobSettings(recentJobsRef.current);
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
      const next = applyBookNarrationPrefillParameters(previous, prefillParameters, forcedBaseOutputFile);
      return preserveUserEditedFields(previous, next);
    });
  }, [prefillParameters, forcedBaseOutputFile, preserveUserEditedFields]);

  useBookNarrationDefaults({
    formState,
    isGeneratedSource,
    forcedBaseOutputFile,
    recentJobs,
    resolveLatestJobSelection,
    resolveLatestJobSettings,
    resolveStartFromHistory,
    applyImageDefaults,
    defaultPipelineSettings,
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
    setSharedTargetLanguages,
    setSharedEnableLookupCache
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
    if (key === 'custom_target_languages') {
      markUserEditedField('target_languages');
    }
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
      const manualTargets = formState.custom_target_languages
        .split(/[,\n]/)
        .map((language) => language.trim())
        .filter(Boolean);
      const normalized = normalizeTargetLanguages([...(value as string[]), ...manualTargets]);
      if (!areLanguageArraysEqual(sharedTargetLanguages, normalized)) {
        setSharedTargetLanguages(normalized);
      }
    } else if (key === 'custom_target_languages' && typeof value === 'string') {
      const manualTargets = value
        .split(/[,\n]/)
        .map((language) => language.trim())
        .filter(Boolean);
      const normalized = normalizeTargetLanguages([...formState.target_languages, ...manualTargets]);
      if (!areLanguageArraysEqual(sharedTargetLanguages, normalized)) {
        setSharedTargetLanguages(normalized);
      }
    } else if (key === 'enable_lookup_cache' && typeof value === 'boolean') {
      setSharedEnableLookupCache(value);
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
      .split(/[,\n]/)
      .map((language) => language.trim())
      .filter(Boolean);
    return normalizeTargetLanguages([...formState.target_languages, ...manualTargets]);
  }, [formState.custom_target_languages, formState.target_languages]);

  const languagesForOverride = useMemo(() => {
    return resolveBookNarrationVoiceOverrideLanguages(
      formState.input_language,
      normalizedTargetLanguages
    );
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

  const handleSaveTemplate = useCallback(async () => {
    setTemplateStatus(null);
    setTemplateError(null);
    setIsSavingTemplate(true);
    try {
      const payload = buildBookNarrationTemplatePayload({
        formState,
        normalizedTargetLanguages,
        sourceMode,
        activeSection: activeTab
      });
      const saved = await saveCreationTemplate(payload);
      setTemplateStatus(`Saved template "${saved.name}".`);
    } catch (saveError) {
      const message =
        saveError instanceof Error
          ? saveError.message
          : 'Unable to save creation template.';
      setTemplateError(message);
    } finally {
      setIsSavingTemplate(false);
    }
  }, [activeTab, formState, normalizedTargetLanguages, sourceMode]);

  const handleSubmitAndRefreshIntake = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      const didSubmit = await handleSubmit(event);
      if (didSubmit) {
        await refreshIntakeStatus();
      }
    },
    [handleSubmit, refreshIntakeStatus]
  );

  const headerTitle = sectionMeta[activeTab]?.title ?? 'Submit a book job';
  const headerDescription =
    sectionMeta[activeTab]?.description ??
    'Provide the input file, target languages, and any overrides to enqueue a new ebook processing job.';
  const missingRequirements = resolveBookNarrationMissingRequirements({
    formState,
    normalizedTargetLanguages,
    isGeneratedSource,
    chapterSelectionMode,
    hasChapterSelection: Boolean(chapterSelection)
  });
  const isSubmitDisabled = isSubmitting || missingRequirements.length > 0 || isIntakeAtCapacity;
  const submitText = submitLabel ?? 'Submit job';
  const hasMissingRequirements = missingRequirements.length > 0;
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
      <form className="pipeline-form" onSubmit={handleSubmitAndRefreshIntake} noValidate>
        <BookNarrationStepBar
          tabSections={tabSections}
          sectionMeta={sectionMeta}
          activeTab={activeTab}
          onSectionChange={handleSectionChange}
          isSubmitDisabled={isSubmitDisabled}
          isSubmitting={isSubmitting}
          submitText={submitText}
          isSavingTemplate={isSavingTemplate}
          onSaveTemplate={handleSaveTemplate}
        />
        <BookNarrationSubmitStatus
          intakeStatus={intakeStatus}
          isLoadingIntakeStatus={isLoadingIntakeStatus}
          hasMissingRequirements={hasMissingRequirements}
          missingRequirementText={missingRequirementText}
          error={error}
          externalError={externalError}
          templateStatus={templateStatus}
          templateError={templateError}
        />
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
            supportedInputLanguages={supportedInputLanguages}
            supportedTargetLanguages={supportedTargetLanguages}
          />
        </div>
      </form>
      <BookNarrationFileDialog
        activeFileDialog={activeFileDialog}
        fileOptions={fileOptions}
        onInputFileSelect={handleInputFileChange}
        onOutputPathSelect={(path) => handleChange('base_output_file', path)}
        onClose={() => setActiveFileDialog(null)}
        onDeleteEbook={(entry) => {
          void handleDeleteEbook(entry);
        }}
      />
    </div>
  );

}

export default BookNarrationForm;
