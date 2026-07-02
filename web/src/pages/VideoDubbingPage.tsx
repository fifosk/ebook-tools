import { useCallback } from 'react';
import type {
  CreationTemplateEntry,
  JobParameterSnapshot
} from '../api/dtos';
import type { JobState } from '../components/JobList';
import { useLanguagePreferences } from '../context/LanguageProvider';
import VideoDubbingJobsPanel from './video-dubbing/VideoDubbingJobsPanel';
import VideoMetadataPanel from './video-dubbing/VideoMetadataPanel';
import VideoDubbingOptionsPanel from './video-dubbing/VideoDubbingOptionsPanel';
import VideoSourcePanel from './video-dubbing/VideoSourcePanel';
import VideoDubbingFeedbackPanel from './video-dubbing/VideoDubbingFeedbackPanel';
import VideoDubbingTabs from './video-dubbing/VideoDubbingTabs';
import VideoDubbingTuningPanel from './video-dubbing/VideoDubbingTuningPanel';
import { useCreateIntakeStatus } from '../components/create-intake/useCreateIntakeStatus';
import { useVideoDubbingSelectionState } from './video-dubbing/useVideoDubbingSelectionState';
import { useVideoDubbingMetadata } from './video-dubbing/useVideoDubbingMetadata';
import { useVideoDubbingLanguageState } from './video-dubbing/useVideoDubbingLanguageState';
import { useVideoDubbingVoiceState } from './video-dubbing/useVideoDubbingVoiceState';
import { useVideoDubbingModelState } from './video-dubbing/useVideoDubbingModelState';
import { useVideoDubbingOutputState } from './video-dubbing/useVideoDubbingOutputState';
import { useVideoDubbingSubtitleExtraction } from './video-dubbing/useVideoDubbingSubtitleExtraction';
import { useVideoDubbingLibraryActions } from './video-dubbing/useVideoDubbingLibraryActions';
import { useVideoDubbingLibraryState } from './video-dubbing/useVideoDubbingLibraryState';
import { useVideoDubbingDownloadStation } from './video-dubbing/useVideoDubbingDownloadStation';
import { useVideoDubbingDownloadStationCompletion } from './video-dubbing/useVideoDubbingDownloadStationCompletion';
import { useVideoDubbingDiscoveryController } from './video-dubbing/useVideoDubbingDiscoveryController';
import { useVideoDubbingJobActions } from './video-dubbing/useVideoDubbingJobActions';
import { useVideoDubbingCreationTemplate } from './video-dubbing/useVideoDubbingCreationTemplate';
import { useVideoDubbingSourceSelection } from './video-dubbing/useVideoDubbingSourceSelection';
import { useVideoDubbingResolvedSelection } from './video-dubbing/useVideoDubbingResolvedSelection';
import {
  useVideoDubbingInitialRefresh,
  useVideoDubbingPageState
} from './video-dubbing/useVideoDubbingPageState';
import styles from './VideoDubbingPage.module.css';

type Props = {
  jobs: JobState[];
  onJobCreated: (jobId: string) => void;
  onSelectJob: (jobId: string) => void;
  onOpenJobMedia?: (jobId: string) => void;
  prefillParameters?: JobParameterSnapshot | null;
  creationTemplate?: CreationTemplateEntry | null;
  creationTemplateError?: string | null;
  creationTemplateHandoffSource?: string | null;
  isLoadingCreationTemplate?: boolean;
};

export default function VideoDubbingPage({
  jobs,
  onJobCreated,
  onSelectJob,
  onOpenJobMedia,
  prefillParameters = null,
  creationTemplate = null,
  creationTemplateError = null,
  creationTemplateHandoffSource = null,
  isLoadingCreationTemplate = false
}: Props) {
  const { primaryTargetLanguage, setPrimaryTargetLanguage } = useLanguagePreferences();
  const {
    intakeStatus,
    isLoadingIntakeStatus,
    isIntakeAtCapacity,
    refreshIntakeStatus,
  } = useCreateIntakeStatus();
  const {
    baseDir,
    setBaseDir,
    selectedVideoPath,
    setSelectedVideoPath,
    selectedVideoPathRef,
    selectedSubtitlePath,
    setSelectedSubtitlePath,
    selectedSubtitlePathRef,
    selectedVideoDiscoveryTemplateState,
    setSelectedVideoDiscoveryTemplateState,
    clearSelectedVideoDiscoveryTemplate
  } = useVideoDubbingSelectionState();
  const {
    activeTab,
    setActiveTab,
    statusMessage,
    setStatusMessage,
    templatePayloadExtras
  } = useVideoDubbingPageState({ creationTemplateHandoffSource });

  const {
    startOffset,
    setStartOffset,
    endOffset,
    setEndOffset,
    originalMixPercent,
    setOriginalMixPercent,
    flushSentences,
    setFlushSentences,
    translationBatchSize,
    setTranslationBatchSize,
    targetHeight,
    setTargetHeight,
    preserveAspectRatio,
    setPreserveAspectRatio,
    splitBatches,
    setSplitBatches,
    stitchBatches,
    setStitchBatches,
    includeTransliteration,
    setIncludeTransliteration,
    enableLookupCache,
    setEnableLookupCache,
    pipelineDefaults
  } = useVideoDubbingOutputState({
    prefillParameters,
    hasCreationTemplate: Boolean(creationTemplate)
  });
  const {
    llmModel,
    setLlmModel,
    transliterationModel,
    setTransliterationModel,
    translationProvider,
    setTranslationProvider,
    transliterationMode,
    setTransliterationMode,
    applyPipelineDefaults,
    llmModels,
    isLoadingModels,
    modelError
  } = useVideoDubbingModelState();

  const {
    acquisitionProviderError,
    videoDiscoveryProvider,
    discoveryQuery,
    setDiscoveryQuery,
    discoveryError,
    setDiscoveryError,
    isDiscoveringVideos,
    discoveredVideoCandidates,
    discoveryPolicyNotes,
    discoverVideos: handleDiscoverVideos,
    handleDiscoveryProviderChange: changeDiscoveryProvider,
    videoDiscoveryProviderOptions,
    isYoutubeSearchAvailable,
    isDownloadStationAvailable,
    isIndexerSearchAvailable,
    isSelectedVideoDiscoveryProviderAvailable,
    youtubeSearchUnavailableMessage,
    manualDownloadsUnavailableMessage,
    downloadStationUnavailableMessage,
    indexerSearchUnavailableMessage,
    selectedVideoDiscoveryProviderUnavailableMessage
  } = useVideoDubbingDiscoveryController({
    onClearSelectedDiscoveryTemplate: clearSelectedVideoDiscoveryTemplate
  });

  const {
    library,
    isLoading,
    loadError,
    deletingVideoPath,
    refreshLibrary,
    refreshLibraryWithSelection,
    deleteVideo
  } = useVideoDubbingLibraryState({
    baseDir,
    selectedVideoPath,
    selectedSubtitlePath,
    selectedVideoPathRef,
    selectedSubtitlePathRef,
    prefillParameters,
    onBaseDirChange: setBaseDir,
    onSelectedVideoPathChange: setSelectedVideoPath,
    onSelectedSubtitlePathChange: setSelectedSubtitlePath,
    onStatusMessageChange: setStatusMessage
  });

  const videos = library?.videos ?? [];
  const {
    selectedVideo,
    playableSubtitles,
    selectedSubtitle,
    subtitleLanguageLabel,
    subtitleLanguageCode,
    metadataSourceName,
    canExtractEmbedded,
    subtitleNotice
  } = useVideoDubbingResolvedSelection({
    videos,
    selectedVideoPath,
    selectedSubtitlePath
  });
  const {
    targetLanguage,
    applyTargetLanguage,
    ensureTargetLanguage,
    sortedLanguageOptions,
    targetLanguageCode
  } = useVideoDubbingLanguageState({
    primaryTargetLanguage,
    setPrimaryTargetLanguage,
    subtitleLanguageCode,
    subtitleLanguageLabel
  });
  const {
    voice,
    setVoice,
    availableVoiceOptions,
    isLoadingVoices,
    voiceInventoryError,
    isPreviewing,
    previewError,
    previewVoice
  } = useVideoDubbingVoiceState({
    subtitleLanguageLabel,
    targetLanguage,
    targetLanguageCode
  });
  const {
    metadataSection,
    setMetadataSection,
    metadataLookupSourceName,
    setMetadataLookupSourceName,
    metadataPreview,
    metadataLoading,
    metadataError,
    youtubeLookupSourceName,
    setYoutubeLookupSourceName,
    youtubeMetadataPreview,
    youtubeMetadataLoading,
    youtubeMetadataError,
    mediaMetadataDraft,
    performMetadataLookup,
    performYoutubeMetadataLookup,
    handleClearTvMetadata,
    handleClearYoutubeMetadata,
    updateMediaMetadataDraft,
    updateMediaMetadataSection
  } = useVideoDubbingMetadata({ activeTab, metadataSourceName });

  const handleDownloadStationCompleted = useVideoDubbingDownloadStationCompletion({
    refreshLibraryWithSelection,
    onSelectedVideoPathChange: setSelectedVideoPath,
    onSelectedSubtitlePathChange: setSelectedSubtitlePath,
    onTargetLanguageEnsure: ensureTargetLanguage,
    onSelectedVideoDiscoveryTemplateStateChange: setSelectedVideoDiscoveryTemplateState
  });

  const {
    downloadStationSourceUri,
    setDownloadStationSourceUri,
    downloadStationCandidate,
    setDownloadStationCandidate,
    downloadStationDestination,
    setDownloadStationDestination,
    downloadStationConfirmed,
    setDownloadStationConfirmed,
    downloadStationJob,
    downloadStationError,
    isSubmittingDownloadStation,
    isPollingDownloadStation,
    handleDownloadStationSourceUriChange,
    submitDownloadStation,
    pollDownloadStation
  } = useVideoDubbingDownloadStation({
    isDownloadStationAvailable,
    downloadStationUnavailableMessage,
    onStatusMessageChange: setStatusMessage,
    onClearSelectedDiscoveryTemplate: clearSelectedVideoDiscoveryTemplate,
    onDownloadStationCompleted: handleDownloadStationCompleted
  });

  const { handleRefresh, handleDeleteVideo } = useVideoDubbingLibraryActions({
    refreshLibrary,
    deleteVideo,
    ensureTargetLanguage
  });

  useVideoDubbingInitialRefresh(handleRefresh);

  const handleDiscoveryProviderChange = useCallback((provider: string) => {
    setDownloadStationCandidate(null);
    changeDiscoveryProvider(provider);
  }, [changeDiscoveryProvider, setDownloadStationCandidate]);

  const {
    handleSelectVideo,
    handleSelectDiscoveryCandidate,
    handleSelectSubtitle
  } = useVideoDubbingSourceSelection({
    selectedVideoPath,
    selectedVideo,
    selectedSubtitlePath,
    playableSubtitles,
    videos,
    videoDiscoveryProvider,
    discoveryQuery,
    onSelectedVideoPathChange: setSelectedVideoPath,
    onSelectedSubtitlePathChange: setSelectedSubtitlePath,
    onSelectedVideoDiscoveryTemplateStateChange: setSelectedVideoDiscoveryTemplateState,
    onTargetLanguageEnsure: ensureTargetLanguage,
    onDiscoveryErrorChange: setDiscoveryError,
    onYoutubeLookupSourceNameChange: setYoutubeLookupSourceName,
    onMetadataSectionChange: setMetadataSection,
    onActiveTabChange: setActiveTab,
    onYoutubeMetadataLookup: performYoutubeMetadataLookup,
    onDownloadStationCandidateChange: setDownloadStationCandidate,
    onDownloadStationSourceUriChange: setDownloadStationSourceUri,
    onStatusMessageChange: setStatusMessage
  });

  const {
    isExtractingSubtitles,
    isLoadingStreams,
    isChoosingStreams,
    availableSubtitleStreams,
    selectedStreamLanguages,
    extractableStreams,
    extractError,
    deletingSubtitlePath,
    deleteSubtitle,
    inspectSubtitleStreams,
    toggleSubtitleStream,
    confirmSubtitleStreams,
    cancelStreamSelection,
    extractAllStreams
  } = useVideoDubbingSubtitleExtraction({
    selectedVideo,
    selectedSubtitlePath,
    onRefresh: handleRefresh,
    onSelectedVideoPathChange: setSelectedVideoPath,
    onSelectedSubtitlePathChange: setSelectedSubtitlePath,
    onStatusMessageChange: setStatusMessage
  });

  const {
    generateError,
    isGenerating,
    templateStatus,
    setTemplateStatus,
    templateError,
    setTemplateError,
    isSavingTemplate,
    canGenerate,
    handleGenerate,
    handleSaveTemplate
  } = useVideoDubbingJobActions({
    selectedVideo,
    selectedSubtitle,
    mediaMetadataDraft,
    subtitleLanguageLabel,
    subtitleLanguageCode,
    targetLanguageCode,
    voice,
    startOffset,
    endOffset,
    originalMixPercent,
    flushSentences,
    translationBatchSize,
    llmModel,
    translationProvider,
    transliterationMode,
    transliterationModel,
    splitBatches,
    stitchBatches,
    includeTransliteration,
    targetHeight,
    preserveAspectRatio,
    enableLookupCache,
    selectedVideoDiscoveryTemplateState,
    templatePayloadExtras,
    isIntakeAtCapacity,
    onJobCreated,
    onActiveTabChange: setActiveTab,
    onStatusMessageChange: setStatusMessage,
    refreshIntakeStatus
  });

  useVideoDubbingCreationTemplate({
    creationTemplate,
    prefillParameters,
    pipelineDefaults,
    metadataSourceName,
    applyPipelineDefaults,
    updateMediaMetadataDraft,
    setSelectedVideoDiscoveryTemplateState,
    setSelectedVideoPath,
    setSelectedSubtitlePath,
    applyTargetLanguage,
    setVoice,
    setStartOffset,
    setEndOffset,
    setOriginalMixPercent,
    setFlushSentences,
    setTranslationBatchSize,
    setTargetHeight,
    setPreserveAspectRatio,
    setSplitBatches,
    setStitchBatches,
    setLlmModel,
    setTranslationProvider,
    setTransliterationMode,
    setTransliterationModel,
    setIncludeTransliteration,
    setEnableLookupCache,
    setTemplateStatus,
    setTemplateError
  });

  return (
    <div className={styles.container}>
      <VideoDubbingTabs
        activeTab={activeTab}
        videoCount={videos.length}
        jobCount={jobs.length}
        isGenerating={isGenerating}
        isSavingTemplate={isSavingTemplate}
        canGenerate={canGenerate}
        onTabChange={setActiveTab}
        onGenerate={() => void handleGenerate()}
        onSaveTemplate={() => void handleSaveTemplate()}
      />

      <VideoDubbingFeedbackPanel
        statusMessage={statusMessage}
        generateError={generateError}
        isLoadingCreationTemplate={isLoadingCreationTemplate}
        templateStatus={templateStatus}
        creationTemplateError={creationTemplateError}
        templateError={templateError}
        intakeStatus={intakeStatus}
        isLoadingIntakeStatus={isLoadingIntakeStatus}
      />

      {activeTab === 'videos' ? (
        <VideoSourcePanel
          baseDir={baseDir}
          isLoading={isLoading}
          loadError={loadError}
          videos={videos}
          selectedVideoPath={selectedVideoPath}
          selectedSubtitlePath={selectedSubtitlePath}
          selectedVideo={selectedVideo}
          playableSubtitles={playableSubtitles}
          subtitleNotice={subtitleNotice}
          discoveryProvider={videoDiscoveryProvider}
          discoveryProviderOptions={videoDiscoveryProviderOptions}
          discoveryQuery={discoveryQuery}
          discoveryCandidates={discoveredVideoCandidates}
          discoveryError={discoveryError}
          discoveryPolicyNotes={discoveryPolicyNotes}
          acquisitionProviderError={acquisitionProviderError}
          youtubeSearchUnavailableMessage={youtubeSearchUnavailableMessage}
          manualDownloadsUnavailableMessage={manualDownloadsUnavailableMessage}
          downloadStationUnavailableMessage={downloadStationUnavailableMessage}
          isDownloadStationAvailable={isDownloadStationAvailable}
          indexerSearchUnavailableMessage={indexerSearchUnavailableMessage}
          downloadStationSourceUri={downloadStationSourceUri}
          downloadStationCandidate={downloadStationCandidate}
          downloadStationDestination={downloadStationDestination}
          downloadStationConfirmed={downloadStationConfirmed}
          downloadStationJob={downloadStationJob}
          downloadStationError={downloadStationError}
          isSubmittingDownloadStation={isSubmittingDownloadStation}
          isPollingDownloadStation={isPollingDownloadStation}
          isDiscoveryProviderAvailable={isSelectedVideoDiscoveryProviderAvailable}
          isDiscoveringVideos={isDiscoveringVideos}
          canExtractEmbedded={canExtractEmbedded}
          isExtractingSubtitles={isExtractingSubtitles}
          isLoadingStreams={isLoadingStreams}
          isChoosingStreams={isChoosingStreams}
          availableSubtitleStreams={availableSubtitleStreams}
          selectedStreamLanguages={selectedStreamLanguages}
          extractableStreams={extractableStreams}
          extractError={extractError}
          deletingSubtitlePath={deletingSubtitlePath}
          deletingVideoPath={deletingVideoPath}
          onBaseDirChange={setBaseDir}
          onRefresh={() => void handleRefresh()}
          onDiscoveryProviderChange={handleDiscoveryProviderChange}
          onDiscoveryQueryChange={setDiscoveryQuery}
          onDiscoverVideos={() => void handleDiscoverVideos()}
          onSelectDiscoveryCandidate={handleSelectDiscoveryCandidate}
          onDownloadStationSourceUriChange={handleDownloadStationSourceUriChange}
          onClearDownloadStationCandidate={() => setDownloadStationCandidate(null)}
          onDownloadStationDestinationChange={setDownloadStationDestination}
          onDownloadStationConfirmedChange={setDownloadStationConfirmed}
          onSubmitDownloadStation={() => void submitDownloadStation()}
          onPollDownloadStation={() => void pollDownloadStation()}
          onSelectVideo={handleSelectVideo}
          onSelectSubtitle={handleSelectSubtitle}
          onDeleteVideo={(video) => void handleDeleteVideo(video)}
          onDeleteSubtitle={(subtitle) => void deleteSubtitle(subtitle)}
          onExtractSubtitles={() => void inspectSubtitleStreams()}
          onToggleSubtitleStream={toggleSubtitleStream}
          onConfirmSubtitleStreams={() => void confirmSubtitleStreams()}
          onCancelStreamSelection={cancelStreamSelection}
          onExtractAllStreams={extractAllStreams}
        />
      ) : null}

      {activeTab === 'metadata' ? (
        <VideoMetadataPanel
          metadataSourceName={metadataSourceName}
          metadataSection={metadataSection}
          metadataLookupSourceName={metadataLookupSourceName}
          metadataPreview={metadataPreview}
          metadataLoading={metadataLoading}
          metadataError={metadataError}
          youtubeLookupSourceName={youtubeLookupSourceName}
          youtubeMetadataPreview={youtubeMetadataPreview}
          youtubeMetadataLoading={youtubeMetadataLoading}
          youtubeMetadataError={youtubeMetadataError}
          mediaMetadataDraft={mediaMetadataDraft}
          onMetadataSectionChange={setMetadataSection}
          onMetadataLookupSourceNameChange={setMetadataLookupSourceName}
          onYoutubeLookupSourceNameChange={setYoutubeLookupSourceName}
          onLookupMetadata={(sourceName, force) => void performMetadataLookup(sourceName, force)}
          onLookupYoutubeMetadata={(sourceName, force) => void performYoutubeMetadataLookup(sourceName, force)}
          onClearTvMetadata={handleClearTvMetadata}
          onClearYoutubeMetadata={handleClearYoutubeMetadata}
          onUpdateMediaMetadataDraft={updateMediaMetadataDraft}
          onUpdateMediaMetadataSection={updateMediaMetadataSection}
        />
      ) : null}

      {activeTab === 'options' ? (
        <VideoDubbingOptionsPanel
          targetLanguage={targetLanguage}
          sortedLanguageOptions={sortedLanguageOptions}
          voice={voice}
          availableVoiceOptions={availableVoiceOptions}
          isLoadingVoices={isLoadingVoices}
          voiceInventoryError={voiceInventoryError}
          isPreviewing={isPreviewing}
          previewError={previewError}
          llmModel={llmModel}
          transliterationModel={transliterationModel}
          llmModels={llmModels}
          isLoadingModels={isLoadingModels}
          modelError={modelError}
          translationProvider={translationProvider}
          transliterationMode={transliterationMode}
          targetHeight={targetHeight}
          preserveAspectRatio={preserveAspectRatio}
          splitBatches={splitBatches}
          stitchBatches={stitchBatches}
          includeTransliteration={includeTransliteration}
          enableLookupCache={enableLookupCache}
          originalMixPercent={originalMixPercent}
          startOffset={startOffset}
          endOffset={endOffset}
          onTargetLanguageChange={applyTargetLanguage}
          onVoiceChange={setVoice}
          onPreviewVoice={() => void previewVoice()}
          onModelChange={setLlmModel}
          onTranslationProviderChange={setTranslationProvider}
          onTransliterationModeChange={setTransliterationMode}
          onTransliterationModelChange={setTransliterationModel}
          onTargetHeightChange={setTargetHeight}
          onPreserveAspectRatioChange={setPreserveAspectRatio}
          onSplitBatchesChange={setSplitBatches}
          onStitchBatchesChange={setStitchBatches}
          onIncludeTransliterationChange={setIncludeTransliteration}
          onEnableLookupCacheChange={setEnableLookupCache}
          onOriginalMixPercentChange={setOriginalMixPercent}
          onStartOffsetChange={setStartOffset}
          onEndOffsetChange={setEndOffset}
        />
      ) : null}

      {activeTab === 'tuning' ? (
        <VideoDubbingTuningPanel
          translationBatchSize={translationBatchSize}
          flushSentences={flushSentences}
          onTranslationBatchSizeChange={setTranslationBatchSize}
          onFlushSentencesChange={setFlushSentences}
        />
      ) : null}

      {activeTab === 'jobs' ? (
        <VideoDubbingJobsPanel jobs={jobs} onSelectJob={onSelectJob} onOpenJobMedia={onOpenJobMedia} />
      ) : null}
    </div>
  );
}
