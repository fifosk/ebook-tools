import { useState } from 'react';
import {
  AUDIO_MODE_OPTIONS,
  AUDIO_QUALITY_OPTIONS,
  VOICE_OPTIONS,
  WRITTEN_MODE_OPTIONS
} from '../../constants/menuOptions';
import { useLanguagePreferences } from '../../context/LanguageProvider';
import { useBookNarrationVoices } from './useBookNarrationVoices';
import { useBookNarrationMetadata } from './useBookNarrationMetadata';
import { useBookNarrationFiles } from './useBookNarrationFiles';
import { BookNarrationFormSections } from './BookNarrationFormSections';
import type { BookNarrationSourcePanel } from './BookNarrationSourceSection';
import { useBookNarrationChapters } from './useBookNarrationChapters';
import { useBookNarrationLlmModels } from './useBookNarrationLlmModels';
import { useBookNarrationDefaults } from './useBookNarrationDefaults';
import { useBookNarrationFormEditing } from './useBookNarrationFormEditing';
import { useBookNarrationSectionState } from './useBookNarrationSectionState';
import { useBookNarrationTemplateApply } from './useBookNarrationTemplateApply';
import { useBookNarrationTemplateSave } from './useBookNarrationTemplateSave';
import { useBookNarrationPrefill } from './useBookNarrationPrefill';
import { useBookNarrationSourceDefaults } from './useBookNarrationSourceDefaults';
import { useBookNarrationDiscoverySelection } from './useBookNarrationDiscoverySelection';
import { useBookNarrationHistory } from './useBookNarrationHistory';
import { useBookNarrationImageDefaults } from './useBookNarrationImageDefaults';
import { useBookNarrationNormalizedState } from './useBookNarrationNormalizedState';
import { useBookNarrationSubmitFlow } from './useBookNarrationSubmitFlow';
import { useBookNarrationWorkflowRefs } from './useBookNarrationWorkflowRefs';
import { useCreateIntakeStatus } from '../create-intake/useCreateIntakeStatus';
import { BookNarrationFormDialogs } from './BookNarrationFormDialogs';
import { BookNarrationFormShell } from './BookNarrationFormShell';
import { useBookNarrationDiscovery } from './useBookNarrationDiscovery';
import type {
  BookNarrationFormProps,
  FormState
} from './bookNarrationFormTypes';
import {
  DEFAULT_FORM_STATE
} from './bookNarrationFormDefaults';
import {
  buildBookNarrationInitialFormState,
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
  const {
    inputLanguage: sharedInputLanguage,
    setInputLanguage: setSharedInputLanguage,
    targetLanguages: sharedTargetLanguages,
    setTargetLanguages: setSharedTargetLanguages,
    enableLookupCache: sharedEnableLookupCache,
    setEnableLookupCache: setSharedEnableLookupCache
  } = useLanguagePreferences();
  const hasPrefillAddImages = typeof prefillParameters?.add_images === 'boolean';
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
  const {
    applyImageDefaults,
    userEditedImageDefaultsRef,
  } = useBookNarrationImageDefaults({
    hasPrefillAddImages,
    imageDefaults,
    setFormState,
  });
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
  const [activeSourcePanel, setActiveSourcePanel] =
    useState<BookNarrationSourcePanel>('source');
  const {
    creationTemplateAppliedRef,
    defaultsAppliedRef,
    lastAutoEndSentenceRef,
    prefillAppliedRef,
    preserveUserEditedFields,
    userEditedEndRef,
    userEditedFieldsRef,
    userEditedInputRef,
    userEditedStartRef,
  } = useBookNarrationWorkflowRefs();

  const {
    normalizePath,
    resolveLatestJobSelection,
    resolveLatestJobSettings,
    resolveStartFromHistory,
  } = useBookNarrationHistory({ recentJobs });

  const {
    normalizedInputForBookMetadataCache,
    normalizedTargetLanguages,
  } = useBookNarrationNormalizedState({
    formState,
    isGeneratedSource,
    normalizePath,
  });
  const {
    handleChange,
    languagesForOverride,
    markUserEditedField,
    updateVoiceOverride,
  } = useBookNarrationFormEditing({
    formState,
    forcedBaseOutputFile,
    lastAutoEndSentenceRef,
    normalizedTargetLanguages,
    setFormState,
    setSharedEnableLookupCache,
    setSharedInputLanguage,
    setSharedTargetLanguages,
    sharedTargetLanguages,
    userEditedEndRef,
    userEditedFieldsRef,
    userEditedImageDefaultsRef,
    userEditedInputRef,
    userEditedStartRef,
  });
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
  const {
    activeTab,
    handleSectionChange,
    sectionMeta,
    tabSections,
  } = useBookNarrationSectionState({
    activeSection,
    sectionOverrides,
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
    discoveryCandidates,
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

  const {
    handleDiscoveryCandidateSelect,
    mergedTemplatePayloadExtras,
    setSelectedDiscoveryTemplateState,
  } = useBookNarrationDiscoverySelection({
    acquireDiscoveryCandidate,
    applyDiscoveryMetadataCandidate,
    closeDiscoveryDialog,
    discoverInternetArchiveCandidatesForCandidate,
    discoveryProvider,
    discoveryQuery,
    handleInputFileChange,
    handleSectionChange,
    inputFile: formState.input_file,
    selectDiscoveryCandidate,
    sourceMode,
    templatePayloadExtras,
  });

  useBookNarrationPrefill({
    forcedBaseOutputFile,
    lastAutoEndSentenceRef,
    normalizePath,
    prefillAppliedRef,
    prefillInputFile,
    prefillParameters,
    preserveUserEditedFields,
    resolveStartFromHistory,
    setFormState,
    userEditedEndRef,
    userEditedInputRef,
    userEditedStartRef,
  });

  const {
    effectiveTemplateError,
    effectiveTemplateStatus,
    handleSaveTemplate,
    isSavingTemplate,
    setTemplateError,
    setTemplateStatus
  } = useBookNarrationTemplateSave({
    activeSection: activeTab,
    creationTemplateError,
    formState,
    isLoadingCreationTemplate,
    normalizedTargetLanguages,
    payloadExtras: mergedTemplatePayloadExtras,
    sourceMode
  });

  useBookNarrationTemplateApply({
    creationTemplate,
    creationTemplateAppliedRef,
    forcedBaseOutputFile,
    handleSectionChange,
    lastAutoEndSentenceRef,
    setActiveSourcePanel,
    setFormState,
    setSelectedDiscoveryTemplateState,
    setSharedEnableLookupCache,
    setSharedInputLanguage,
    setSharedTargetLanguages,
    setTemplateError,
    setTemplateStatus,
    sharedTargetLanguages,
    sourceMode,
    userEditedEndRef,
    userEditedFieldsRef,
    userEditedImageDefaultsRef,
    userEditedInputRef,
    userEditedStartRef,
  });

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

  useBookNarrationSourceDefaults({
    forcedBaseOutputFile,
    isGeneratedSource,
    lastAutoEndSentenceRef,
    setFormState,
    userEditedEndRef,
    userEditedStartRef,
  });

  const {
    handleSubmitAndRefreshIntake,
    submitPresentation,
  } = useBookNarrationSubmitFlow({
    activeSection: activeTab,
    sectionMeta,
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
    isSubmitting,
    isIntakeAtCapacity,
    onSubmit,
    refreshIntakeStatus,
    submitLabel,
    setError
  });
  const canBrowseFiles = Boolean(fileOptions);
  return (
    <div className="pipeline-settings">
      <BookNarrationFormShell
        showInfoHeader={showInfoHeader}
        submitPresentation={submitPresentation}
        onSubmit={handleSubmitAndRefreshIntake}
        tabSections={tabSections}
        sectionMeta={sectionMeta}
        activeTab={activeTab}
        onSectionChange={handleSectionChange}
        isSubmitting={isSubmitting}
        isSavingTemplate={isSavingTemplate}
        onSaveTemplate={handleSaveTemplate}
        intakeStatus={intakeStatus}
        isLoadingIntakeStatus={isLoadingIntakeStatus}
        error={error}
        externalError={externalError}
        templateStatus={effectiveTemplateStatus}
        templateError={effectiveTemplateError}
      >
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
            availableAudioModes={AUDIO_MODE_OPTIONS}
            availableAudioQualities={AUDIO_QUALITY_OPTIONS}
            availableVoices={VOICE_OPTIONS}
            availableWrittenModes={WRITTEN_MODE_OPTIONS}
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
      </BookNarrationFormShell>
      <BookNarrationFormDialogs
        activeFileDialog={activeFileDialog}
        fileOptions={fileOptions}
        onInputFileSelect={handleInputFileChange}
        onOutputPathSelect={(path) => handleChange('base_output_file', path)}
        onCloseFileDialog={() => setActiveFileDialog(null)}
        onDeleteEbook={handleDeleteEbook}
        activeDiscoveryDialog={activeDiscoveryDialog}
        discoveryProvider={discoveryProvider}
        discoveryQuery={discoveryQuery}
        discoveryCandidates={discoveryCandidates}
        discoveryResponse={discoveryResponse}
        discoveryError={discoveryError}
        isDiscovering={isDiscovering}
        isLoadingProviders={isLoadingProviders}
        acquiringCandidateId={acquiringCandidateId}
        providerOptions={providerOptions}
        providerError={providerError}
        selectedProviderUnavailableMessage={selectedProviderUnavailableMessage}
        onDiscoveryProviderChange={changeDiscoveryProvider}
        onDiscoveryQueryChange={setDiscoveryQuery}
        onDiscoverySearch={runDiscoverySearch}
        onDiscoverySelect={handleDiscoveryCandidateSelect}
        onCloseDiscoveryDialog={closeDiscoveryDialog}
      />
    </div>
  );

}

export default BookNarrationForm;
