import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from 'react';
import type { FormEvent } from 'react';
import type { AcquisitionCandidate, PipelineStatusResponse } from '../../api/dtos';
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
import type { BookNarrationSourcePanel } from './BookNarrationSourceSection';
import { useBookNarrationChapters } from './useBookNarrationChapters';
import { useBookNarrationLlmModels } from './useBookNarrationLlmModels';
import { useBookNarrationDefaults } from './useBookNarrationDefaults';
import { useBookNarrationSectionState } from './useBookNarrationSectionState';
import { useCreateIntakeStatus } from '../create-intake/useCreateIntakeStatus';
import { BookNarrationStepBar } from './BookNarrationStepBar';
import { BookNarrationSubmitStatus } from './BookNarrationSubmitStatus';
import { BookNarrationFileDialog } from './BookNarrationFileDialog';
import { BookNarrationDiscoveryDialog } from './BookNarrationDiscoveryDialog';
import { useBookNarrationDiscovery } from './useBookNarrationDiscovery';
import { filterBookNarrationDiscoveryCandidates } from './bookNarrationDiscoveryProviders';
import {
  buildBookDiscoveryTemplateState,
  buildBookNarrationTemplatePayload,
  buildSparseBookDiscoveryTemplateState,
  extractBookNarrationTemplateFormState
} from './bookNarrationTemplates';
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
  applyBookNarrationPrefillInputFile,
  applyBookNarrationPrefillParameters,
  applyBookNarrationVoiceOverride,
  buildBookNarrationInitialFormState,
  normalizeBookNarrationPath,
  normalizeTargetLanguages,
  preserveBookNarrationUserEditedFields,
  resolveLatestBookNarrationJobSelection,
  resolveLatestBookNarrationJobSettings,
  resolveBookNarrationSubmitPresentation,
  resolveBookNarrationSharedPreferenceUpdate,
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
  creationTemplate = null,
  creationTemplateError = null,
  isLoadingCreationTemplate = false,
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
  supportedTargetLanguages = null,
  sentenceSplitterOptions = null,
  templatePayloadExtras = null
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
  const [formState, setFormState] = useState<FormState>(() => buildBookNarrationInitialFormState({
    forcedBaseOutputFile,
    sharedInputLanguage,
    sharedTargetLanguages,
    sharedEnableLookupCache,
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
  const [activeSourcePanel, setActiveSourcePanel] =
    useState<BookNarrationSourcePanel>('source');
  const [selectedDiscoveryTemplateState, setSelectedDiscoveryTemplateState] =
    useState<Record<string, unknown> | null>(null);
  const prefillAppliedRef = useRef<string | null>(null);
  const prefillParametersRef = useRef<string | null>(null);
  const creationTemplateAppliedRef = useRef<string | null>(null);
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
  const { activeTab, handleSectionChange } = useBookNarrationSectionState({
    activeSection,
    tabSections,
    onSectionChange
  });

  const {
    metadataSourceName,
    metadataLookupQuery,
    setMetadataLookupQuery,
    metadataPreview,
    metadataLoading,
    metadataError,
    cachedCoverDataUrl,
    performMetadataLookup,
    applyDiscoveryMetadataCandidate,
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
  const {
    acquiringCandidateId,
    activeDiscoveryDialog,
    discoveryProvider,
    discoveryQuery,
    discoveryResponse,
    discoveryError,
    isDiscovering,
    isLoadingProviders,
    providerError,
    providers,
    providerOptions,
    selectedProviderUnavailableMessage,
    acquireDiscoveryCandidate,
    changeDiscoveryProvider,
    closeDiscoveryDialog,
    discoverInternetArchiveCandidatesForCandidate,
    openDiscoveryDialog,
    runDiscoverySearch,
    selectDiscoveryCandidate,
    setDiscoveryQuery
  } = useBookNarrationDiscovery({ isGeneratedSource });

  const discoveryCandidates = useMemo(() => filterBookNarrationDiscoveryCandidates(
    discoveryResponse,
    discoveryProvider,
    providers
  ), [discoveryProvider, discoveryResponse, providers]);

  const mergedTemplatePayloadExtras = useMemo(() => {
    const discoveryState = selectedDiscoveryTemplateState
      ?? (sourceMode === 'upload'
        ? buildSparseBookDiscoveryTemplateState({
          provider: discoveryProvider,
          query: discoveryQuery
        })
        : null);
    if (!discoveryState) {
      return templatePayloadExtras;
    }
    return {
      ...(templatePayloadExtras ?? {}),
      discovery_state: discoveryState
    };
  }, [discoveryProvider, discoveryQuery, selectedDiscoveryTemplateState, sourceMode, templatePayloadExtras]);

  useEffect(() => {
    const selectedPath =
      typeof selectedDiscoveryTemplateState?.selected_path === 'string'
        ? selectedDiscoveryTemplateState.selected_path
        : null;
    if (!selectedPath) {
      return;
    }
    if (formState.input_file && formState.input_file !== selectedPath) {
      setSelectedDiscoveryTemplateState(null);
    }
  }, [formState.input_file, selectedDiscoveryTemplateState]);

  const handleDiscoveryCandidateSelect = useCallback((candidate: AcquisitionCandidate) => {
    void (async () => {
      const selection = (await selectDiscoveryCandidate(candidate))
        ?? (candidate.capabilities.includes('acquire')
          ? await acquireDiscoveryCandidate(candidate)
          : null);
      if (selection?.selectedPath) {
        setSelectedDiscoveryTemplateState(buildBookDiscoveryTemplateState(candidate, {
          query: discoveryQuery,
          provider: discoveryProvider,
          selectedPath: selection.selectedPath,
          preparedMetadata: selection.preparedMetadata
        }));
        handleInputFileChange(selection.selectedPath);
        closeDiscoveryDialog();
        return;
      }
      if (!candidate.capabilities.includes('acquire')) {
        const handledArchiveBridge = await discoverInternetArchiveCandidatesForCandidate(candidate);
        if (handledArchiveBridge) {
          return;
        }
      }
      if (!candidate.capabilities.includes('acquire') && applyDiscoveryMetadataCandidate(candidate)) {
        setSelectedDiscoveryTemplateState(buildBookDiscoveryTemplateState(candidate, {
          query: discoveryQuery,
          provider: discoveryProvider
        }));
        handleSectionChange('metadata');
        closeDiscoveryDialog();
      }
    })();
  }, [
    acquireDiscoveryCandidate,
    applyDiscoveryMetadataCandidate,
    closeDiscoveryDialog,
    discoverInternetArchiveCandidatesForCandidate,
    discoveryProvider,
    discoveryQuery,
    handleInputFileChange,
    handleSectionChange,
    selectDiscoveryCandidate
  ]);

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
    const suggestedStart = resolveStartFromHistory(normalizedPrefill);
    setFormState((previous) => {
      return applyBookNarrationPrefillInputFile({
        previous,
        inputFile: normalizedPrefill,
        forcedBaseOutputFile,
        cachedBookMetadata,
        suggestedStartSentence: suggestedStart
      });
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

  useEffect(() => {
    if (!creationTemplate) {
      creationTemplateAppliedRef.current = null;
      return;
    }
    const applyKey = `${creationTemplate.id}:${creationTemplate.updated_at}:${sourceMode}`;
    if (creationTemplateAppliedRef.current === applyKey) {
      return;
    }
    const applied = extractBookNarrationTemplateFormState(creationTemplate, sourceMode);
    if (!applied) {
      setTemplateStatus(null);
      setTemplateError(`Template "${creationTemplate.name}" is not compatible with this book job.`);
      creationTemplateAppliedRef.current = applyKey;
      return;
    }

    const appliedFormState: Partial<FormState> = { ...applied.formState };
    setSelectedDiscoveryTemplateState(applied.discoveryState);
    setActiveSourcePanel(applied.discoveryState ? 'discovery' : 'source');
    if (Array.isArray(appliedFormState.target_languages)) {
      const targetLanguageFields = targetLanguageFieldsFromLanguages(
        normalizeTargetLanguages(appliedFormState.target_languages)
      );
      appliedFormState.target_languages = targetLanguageFields.target_languages;
      appliedFormState.custom_target_languages = targetLanguageFields.custom_target_languages;
    }

    userEditedStartRef.current = 'start_sentence' in appliedFormState;
    userEditedInputRef.current = 'input_file' in appliedFormState || 'base_output_file' in appliedFormState;
    userEditedEndRef.current = 'end_sentence' in appliedFormState;
    lastAutoEndSentenceRef.current = null;
    for (const key of Object.keys(appliedFormState) as (keyof FormState)[]) {
      userEditedFieldsRef.current.add(key);
      if (IMAGE_DEFAULT_FIELDS.has(key)) {
        userEditedImageDefaultsRef.current.add(key);
      }
    }

    if (Array.isArray(appliedFormState.target_languages)) {
      const normalizedTargets = normalizeTargetLanguages([
        ...appliedFormState.target_languages,
        ...(appliedFormState.custom_target_languages ?? '')
          .split(/[,\n]/)
          .map((language) => language.trim())
          .filter(Boolean)
      ]);
      if (!areLanguageArraysEqual(sharedTargetLanguages, normalizedTargets)) {
        setSharedTargetLanguages(normalizedTargets);
      }
    }
    if (typeof appliedFormState.input_language === 'string') {
      setSharedInputLanguage(appliedFormState.input_language);
    }
    if (typeof appliedFormState.enable_lookup_cache === 'boolean') {
      setSharedEnableLookupCache(appliedFormState.enable_lookup_cache);
    }
    setFormState((previous) => ({
      ...previous,
      ...appliedFormState,
      base_output_file:
        forcedBaseOutputFile ??
        appliedFormState.base_output_file ??
        previous.base_output_file
    }));
    if (applied.activeSection) {
      handleSectionChange(applied.activeSection);
    }
    setTemplateError(null);
    setTemplateStatus(`Applied template "${creationTemplate.name}".`);
    creationTemplateAppliedRef.current = applyKey;
  }, [
    creationTemplate,
    forcedBaseOutputFile,
    handleSectionChange,
    setSharedEnableLookupCache,
    setSharedInputLanguage,
    setSharedTargetLanguages,
    sharedTargetLanguages,
    sourceMode
  ]);

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

    const sharedPreferenceUpdate = resolveBookNarrationSharedPreferenceUpdate({
      key,
      value,
      formState,
      sharedTargetLanguages
    });
    if (sharedPreferenceUpdate?.inputLanguage !== undefined) {
      setSharedInputLanguage(sharedPreferenceUpdate.inputLanguage);
    }
    if (sharedPreferenceUpdate?.targetLanguages !== undefined) {
      setSharedTargetLanguages(sharedPreferenceUpdate.targetLanguages);
    }
    if (sharedPreferenceUpdate?.enableLookupCache !== undefined) {
      setSharedEnableLookupCache(sharedPreferenceUpdate.enableLookupCache);
    }
  };

  const updateVoiceOverride = useCallback((languageCode: string, voiceValue: string) => {
    if (!languageCode.trim()) {
      return;
    }
    markUserEditedField('voice_overrides');
    setFormState((previous) => {
      return applyBookNarrationVoiceOverride(previous, languageCode, voiceValue);
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
        activeSection: activeTab,
        payloadExtras: mergedTemplatePayloadExtras
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
  }, [activeTab, formState, mergedTemplatePayloadExtras, normalizedTargetLanguages, sourceMode]);

  const handleSubmitAndRefreshIntake = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      const didSubmit = await handleSubmit(event);
      if (didSubmit) {
        await refreshIntakeStatus();
      }
    },
    [handleSubmit, refreshIntakeStatus]
  );

  const submitPresentation = resolveBookNarrationSubmitPresentation({
    activeSection: activeTab,
    sectionMeta,
    formState,
    normalizedTargetLanguages,
    isGeneratedSource,
    chapterSelectionMode,
    hasChapterSelection: Boolean(chapterSelection),
    isSubmitting,
    isIntakeAtCapacity,
    submitLabel
  });
  const effectiveTemplateStatus =
    isLoadingCreationTemplate ? 'Loading saved template...' : templateStatus;
  const effectiveTemplateError = creationTemplateError ?? templateError;
  const canBrowseFiles = Boolean(fileOptions);
  return (
    <div className="pipeline-settings">
      {showInfoHeader ? (
        <>
          <h2>{submitPresentation.headerTitle}</h2>
          <p>{submitPresentation.headerDescription}</p>
        </>
      ) : null}
      <form className="pipeline-form" onSubmit={handleSubmitAndRefreshIntake} noValidate>
        <BookNarrationStepBar
          tabSections={tabSections}
          sectionMeta={sectionMeta}
          activeTab={activeTab}
          onSectionChange={handleSectionChange}
          isSubmitDisabled={submitPresentation.isSubmitDisabled}
          isSubmitting={isSubmitting}
          submitText={submitPresentation.submitText}
          isSavingTemplate={isSavingTemplate}
          onSaveTemplate={handleSaveTemplate}
        />
        <BookNarrationSubmitStatus
          intakeStatus={intakeStatus}
          isLoadingIntakeStatus={isLoadingIntakeStatus}
          hasMissingRequirements={submitPresentation.hasMissingRequirements}
          missingRequirementText={submitPresentation.missingRequirementText}
          error={error}
          externalError={externalError}
          templateStatus={effectiveTemplateStatus}
          templateError={effectiveTemplateError}
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
            onDiscoverClick={openDiscoveryDialog}
            canDiscoverFiles={!isGeneratedSource}
            isDiscoveringFiles={isDiscovering}
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
            activeSourcePanel={activeSourcePanel}
            onActiveSourcePanelChange={setActiveSourcePanel}
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
            sentenceSplitterOptions={sentenceSplitterOptions}
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
      <BookNarrationDiscoveryDialog
        active={activeDiscoveryDialog}
        provider={discoveryProvider}
        query={discoveryQuery}
        candidates={discoveryCandidates}
        policyNotes={discoveryResponse?.policy_notes ?? []}
        providersQueried={discoveryResponse?.providers_queried ?? []}
        isLoading={isDiscovering}
        isLoadingProviders={isLoadingProviders}
        acquiringCandidateId={acquiringCandidateId}
        providerOptions={providerOptions}
        error={discoveryError}
        providerError={providerError}
        selectedProviderUnavailableMessage={selectedProviderUnavailableMessage}
        onProviderChange={changeDiscoveryProvider}
        onQueryChange={setDiscoveryQuery}
        onSearch={(query) => {
          void runDiscoverySearch(query);
        }}
        onSelect={handleDiscoveryCandidateSelect}
        onClose={closeDiscoveryDialog}
      />
    </div>
  );

}

export default BookNarrationForm;
