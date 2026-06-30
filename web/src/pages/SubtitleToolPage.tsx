import { useMemo } from 'react';
import type { JobState } from '../components/JobList';
import type { CreationTemplateEntry, JobParameterSnapshot } from '../api/dtos';
import SubtitleToolTabContent from './subtitle-tool/SubtitleToolTabContent';
import SubtitleToolTabs from './subtitle-tool/SubtitleToolTabs';
import { CreateIntakeStatusCallout } from '../components/create-intake/CreateIntakeStatusCallout';
import { useCreateIntakeStatus } from '../components/create-intake/useCreateIntakeStatus';
import {
  DEFAULT_START_TIME,
  DEFAULT_SUBTITLE_SOURCE_DIRECTORY
} from './subtitle-tool/subtitleToolConfig';
import { useSubtitleJobResults } from './subtitle-tool/useSubtitleJobResults';
import { useSubtitleCreationDefaults } from './subtitle-tool/useSubtitleCreationDefaults';
import { useSubtitleCreationTemplate } from './subtitle-tool/useSubtitleCreationTemplate';
import { useSubtitleLanguageState } from './subtitle-tool/useSubtitleLanguageState';
import { useSubtitleModels } from './subtitle-tool/useSubtitleModels';
import { useSubtitlePrefill } from './subtitle-tool/useSubtitlePrefill';
import { useSubtitleProcessingOptions } from './subtitle-tool/useSubtitleProcessingOptions';
import { useSubtitleShowOriginalPreference } from './subtitle-tool/useSubtitleShowOriginalPreference';
import { useSubtitleSourceMode } from './subtitle-tool/useSubtitleSourceMode';
import { useSubtitleSources } from './subtitle-tool/useSubtitleSources';
import { useSubtitleSubmit } from './subtitle-tool/useSubtitleSubmit';
import { useSubtitleSubmitFeedback } from './subtitle-tool/useSubtitleSubmitFeedback';
import { useSubtitleSubmitStatus } from './subtitle-tool/useSubtitleSubmitStatus';
import { useSubtitleTabState } from './subtitle-tool/useSubtitleTabState';
import { useSubtitleTemplateActions } from './subtitle-tool/useSubtitleTemplateActions';
import { useSubtitleTvMetadata } from './subtitle-tool/useSubtitleTvMetadata';
import { buildHandoffPayloadExtras } from '../utils/creationTemplatePayloadExtras';
import styles from './SubtitleToolPage.module.css';

const SUBTITLE_SUBMIT_FORM_ID = 'subtitle-submit-form';

type Props = {
  subtitleJobs: JobState[];
  onJobCreated: (jobId: string) => void;
  onSelectJob: (jobId: string) => void;
  onMoveToLibrary?: (jobId: string) => void;
  prefillParameters?: JobParameterSnapshot | null;
  creationTemplate?: CreationTemplateEntry | null;
  creationTemplateError?: string | null;
  creationTemplateHandoffSource?: string | null;
  isLoadingCreationTemplate?: boolean;
  refreshSignal?: number;
};

export default function SubtitleToolPage({
  subtitleJobs,
  onJobCreated,
  onSelectJob,
  onMoveToLibrary,
  prefillParameters = null,
  creationTemplate = null,
  creationTemplateError = null,
  creationTemplateHandoffSource = null,
  isLoadingCreationTemplate = false,
  refreshSignal = 0
}: Props) {
  const { activeTab, setActiveTab, sortedSubtitleJobs } = useSubtitleTabState(subtitleJobs);
  const {
    intakeStatus,
    isLoadingIntakeStatus,
    isIntakeAtCapacity,
    refreshIntakeStatus,
  } = useCreateIntakeStatus();
  const {
    inputLanguage,
    setInputLanguage,
    targetLanguage,
    setTargetLanguage,
    setPrimaryTargetLanguage,
    sortedLanguageOptions,
    handleInputLanguageChange,
    handleTargetLanguageChange
  } = useSubtitleLanguageState();
  const sourceDirectory = DEFAULT_SUBTITLE_SOURCE_DIRECTORY;
  const {
    sources,
    sortedSources,
    selectedSource,
    setSelectedSource,
    selectedSourceEntry,
    isLoadingSources,
    deletingSourcePath,
    sourceMessage,
    sourceError,
    refreshSources,
    handleDeleteSource
  } = useSubtitleSources({ sourceDirectory, refreshSignal });
  const {
    isSubmitting,
    submitError,
    setSubmitError,
    resetSubmitError,
    beginSubmit,
    finishSubmit,
    rejectAtCapacity,
    failSubmit
  } = useSubtitleSubmitStatus();
  const {
    sourceMode,
    uploadFile,
    isAssSelection,
    metadataSourceName,
    handleSourceModeChange,
    handleUploadFileChange,
    clearUploadFile
  } = useSubtitleSourceMode({
    selectedSource,
    selectedSourceEntry,
    onSubmitErrorReset: resetSubmitError
  });
  const {
    metadataLookupSourceName,
    setMetadataLookupSourceName,
    metadataPreview,
    metadataLoading,
    metadataError,
    mediaMetadataDraft,
    performMetadataLookup,
    handleMetadataClear,
    updateMediaMetadataDraft,
    updateMediaMetadataSection
  } = useSubtitleTvMetadata(metadataSourceName);
  const templatePayloadExtras = useMemo(
    () => buildHandoffPayloadExtras(creationTemplateHandoffSource),
    [creationTemplateHandoffSource]
  );
  const { showOriginal, setShowOriginal } = useSubtitleShowOriginalPreference();
  const {
    enableTransliteration,
    setEnableTransliteration,
    enableHighlight,
    setEnableHighlight,
    generateAudioBook,
    setGenerateAudioBook,
    outputFormat,
    setOutputFormat,
    assFontSize,
    setAssFontSize,
    assEmphasis,
    setAssEmphasis,
    mirrorToSourceDir,
    setMirrorToSourceDir,
    workerCount,
    setWorkerCount,
    batchSize,
    setBatchSize,
    translationBatchSize,
    setTranslationBatchSize,
    startTime,
    setStartTime,
    endTime,
    setEndTime,
    selectedModel,
    setSelectedModel,
    transliterationModel,
    setTransliterationModel,
    translationProvider,
    setTranslationProvider,
    transliterationMode,
    setTransliterationMode,
    applySubtitleDefaults
  } = useSubtitleProcessingOptions();
  useSubtitleCreationDefaults({
    shouldSkipDefaults: Boolean(prefillParameters || creationTemplate),
    applySubtitleDefaults
  });
  const { availableModels, modelsLoading, modelsError } = useSubtitleModels();
  const jobResults = useSubtitleJobResults(subtitleJobs);
  const { submittedSummary, recordSubmission } = useSubtitleSubmitFeedback({
    defaultStartTime: DEFAULT_START_TIME
  });
  useSubtitlePrefill({
    prefillParameters,
    setTargetLanguage,
    setPrimaryTargetLanguage,
    setInputLanguage,
    setEnableTransliteration,
    setShowOriginal,
    setWorkerCount,
    setBatchSize,
    setTranslationBatchSize,
    setStartTime,
    setEndTime,
    setSelectedModel,
    setTranslationProvider,
    setTransliterationMode,
    setTransliterationModel,
    setSelectedSource
  });

  const {
    templateStatus,
    setTemplateStatus,
    templateError,
    setTemplateError,
    isSavingTemplate,
    handleSaveTemplate
  } = useSubtitleTemplateActions({
    inputLanguage,
    targetLanguage,
    isAssSelection,
    sourceMode,
    selectedSource,
    uploadFile,
    startTime,
    endTime,
    outputFormat,
    assFontSize,
    assEmphasis,
    selectedModel,
    translationProvider,
    transliterationMode,
    transliterationModel,
    workerCount,
    batchSize,
    translationBatchSize,
    enableTransliteration,
    enableHighlight,
    showOriginal,
    generateAudioBook,
    mirrorToSourceDir,
    mediaMetadataDraft,
    templatePayloadExtras
  });

  useSubtitleCreationTemplate({
    creationTemplate,
    metadataSourceName,
    updateMediaMetadataDraft,
    handleSourceModeChange,
    setAssEmphasis,
    setAssFontSize,
    setBatchSize,
    setEnableHighlight,
    setEnableTransliteration,
    setEndTime,
    setGenerateAudioBook,
    setInputLanguage,
    setMirrorToSourceDir,
    setOutputFormat,
    setPrimaryTargetLanguage,
    setSelectedModel,
    setSelectedSource,
    setShowOriginal,
    setStartTime,
    setTargetLanguage,
    setTemplateError,
    setTemplateStatus,
    setTranslationBatchSize,
    setTranslationProvider,
    setTransliterationMode,
    setTransliterationModel,
    setWorkerCount
  });
  const { handleSubmit } = useSubtitleSubmit({
    inputLanguage,
    targetLanguage,
    isAssSelection,
    sourceMode,
    selectedSource,
    startTime,
    endTime,
    outputFormat,
    assFontSize,
    assEmphasis,
    selectedModel,
    translationProvider,
    transliterationMode,
    transliterationModel,
    workerCount,
    batchSize,
    translationBatchSize,
    enableTransliteration,
    enableHighlight,
    showOriginal,
    generateAudioBook,
    mirrorToSourceDir,
    uploadFile,
    mediaMetadataDraft,
    isIntakeAtCapacity,
    setSubmitError,
    beginSubmit,
    finishSubmit,
    rejectAtCapacity,
    failSubmit,
    recordSubmission,
    setStartTime,
    setEndTime,
    setAssFontSize,
    setAssEmphasis,
    setActiveTab,
    onJobCreated,
    clearUploadFile,
    refreshIntakeStatus
  });

  return (
    <div className={styles.container}>
      <SubtitleToolTabs
        activeTab={activeTab}
        sourceCount={sources.length}
        jobCount={sortedSubtitleJobs.length}
        isSubmitting={isSubmitting}
        isSavingTemplate={isSavingTemplate}
        isAssSelection={isAssSelection}
        isIntakeAtCapacity={isIntakeAtCapacity}
        onTabChange={setActiveTab}
        onSaveTemplate={() => void handleSaveTemplate()}
      />

      {submitError ? <div className="alert" role="alert">{submitError}</div> : null}
      {creationTemplateError ?? templateError ? (
        <div className="alert" role="alert">{creationTemplateError ?? templateError}</div>
      ) : null}
      <CreateIntakeStatusCallout status={intakeStatus} isLoading={isLoadingIntakeStatus} />
      {isLoadingCreationTemplate || templateStatus ? (
        <div className="notice notice--info" role="status">
          {isLoadingCreationTemplate ? 'Loading saved template...' : templateStatus}
        </div>
      ) : null}
      {submittedSummary ? (
        <div className="notice notice--info" role="status">
          {submittedSummary}
        </div>
      ) : null}

      <SubtitleToolTabContent
        activeTab={activeTab}
        formId={SUBTITLE_SUBMIT_FORM_ID}
        onSubmit={handleSubmit}
        sourcePanelProps={{
          sourceMode,
          sourceDirectory,
          sourceCount: sources.length,
          sortedSources,
          selectedSource,
          isLoadingSources,
          sourceError,
          sourceMessage,
          deletingSourcePath,
          isAssSelection,
          onSourceModeChange: handleSourceModeChange,
          onSelectSource: setSelectedSource,
          onRefreshSources: () => void refreshSources(),
          onDeleteSource: handleDeleteSource,
          onUploadFileChange: handleUploadFileChange
        }}
        optionsPanelProps={{
          inputLanguage,
          targetLanguage,
          sortedLanguageOptions,
          selectedModel,
          transliterationModel,
          availableModels,
          modelsLoading,
          modelsError,
          translationProvider,
          transliterationMode,
          enableTransliteration,
          enableHighlight,
          generateAudioBook,
          showOriginal,
          mirrorToSourceDir,
          outputFormat,
          assFontSize,
          assEmphasis,
          startTime,
          endTime,
          sourceDirectory,
          onInputLanguageChange: handleInputLanguageChange,
          onTargetLanguageChange: handleTargetLanguageChange,
          onModelChange: setSelectedModel,
          onTranslationProviderChange: setTranslationProvider,
          onTransliterationModeChange: setTransliterationMode,
          onTransliterationModelChange: setTransliterationModel,
          onEnableTransliterationChange: setEnableTransliteration,
          onEnableHighlightChange: setEnableHighlight,
          onGenerateAudioBookChange: setGenerateAudioBook,
          onShowOriginalChange: setShowOriginal,
          onMirrorToSourceDirChange: setMirrorToSourceDir,
          onOutputFormatChange: setOutputFormat,
          onAssFontSizeChange: setAssFontSize,
          onAssEmphasisChange: setAssEmphasis,
          onStartTimeChange: setStartTime,
          onEndTimeChange: setEndTime
        }}
        tuningPanelProps={{
          workerCount,
          batchSize,
          translationBatchSize,
          onWorkerCountChange: setWorkerCount,
          onBatchSizeChange: setBatchSize,
          onTranslationBatchSizeChange: setTranslationBatchSize
        }}
        metadataPanelProps={{
          metadataSourceName,
          metadataLookupSourceName,
          metadataPreview,
          metadataLoading,
          metadataError,
          mediaMetadataDraft,
          onLookupSourceNameChange: setMetadataLookupSourceName,
          onLookupMetadata: performMetadataLookup,
          onClearMetadata: handleMetadataClear,
          onUpdateMediaMetadataDraft: updateMediaMetadataDraft,
          onUpdateMediaMetadataSection: updateMediaMetadataSection
        }}
        jobsPanelProps={{
          jobs: sortedSubtitleJobs,
          jobResults,
          onSelectJob,
          onMoveToLibrary
        }}
      />
    </div>
  );
}
