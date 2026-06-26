import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  generateYoutubeDub,
  saveCreationTemplate
} from '../api/client';
import type {
  AcquisitionCandidate,
  CreationTemplateEntry,
  YoutubeNasVideo,
  JobParameterSnapshot
} from '../api/dtos';
import type { JobState } from '../components/JobList';
import { useLanguagePreferences } from '../context/LanguageProvider';
import {
  resolveSubtitleLanguageCandidate,
  resolveSubtitleLanguageLabel
} from '../utils/subtitles';
import VideoDubbingJobsPanel from './video-dubbing/VideoDubbingJobsPanel';
import VideoMetadataPanel from './video-dubbing/VideoMetadataPanel';
import VideoDubbingOptionsPanel from './video-dubbing/VideoDubbingOptionsPanel';
import VideoSourcePanel from './video-dubbing/VideoSourcePanel';
import VideoDubbingTabs from './video-dubbing/VideoDubbingTabs';
import VideoDubbingTuningPanel from './video-dubbing/VideoDubbingTuningPanel';
import { CreateIntakeStatusCallout } from '../components/create-intake/CreateIntakeStatusCallout';
import { useCreateIntakeStatus } from '../components/create-intake/useCreateIntakeStatus';
import type { VideoDubbingTab } from './video-dubbing/videoDubbingTypes';
import { useVideoDubbingSelectionState } from './video-dubbing/useVideoDubbingSelectionState';
import { useVideoDubbingMetadata } from './video-dubbing/useVideoDubbingMetadata';
import { useVideoDubbingLanguageState } from './video-dubbing/useVideoDubbingLanguageState';
import { useVideoDubbingVoiceState } from './video-dubbing/useVideoDubbingVoiceState';
import { useVideoDubbingModelState } from './video-dubbing/useVideoDubbingModelState';
import { useVideoDubbingOutputState } from './video-dubbing/useVideoDubbingOutputState';
import { useVideoDubbingSubtitleExtraction } from './video-dubbing/useVideoDubbingSubtitleExtraction';
import { useVideoDubbingLibraryState } from './video-dubbing/useVideoDubbingLibraryState';
import { useVideoDubbingAcquisitionProviders } from './video-dubbing/useVideoDubbingAcquisitionProviders';
import { useVideoDubbingDownloadStation } from './video-dubbing/useVideoDubbingDownloadStation';
import { useVideoDubbingDiscoverySearch } from './video-dubbing/useVideoDubbingDiscoverySearch';
import {
  buildVideoDubbingGeneratePayload,
  buildVideoDubbingTemplatePayload,
  canExtractEmbeddedSubtitles,
  extractVideoDubbingTemplateFormState,
  filterPlayableSubtitles,
  isDownloadStationHandoffCandidate,
  makeVideoDiscoveryTemplateState,
  resolveVideoDubPrefill,
  resolveDefaultSubtitle,
  resolveSubtitleNotice,
  resolveVideoDubbingMetadataSourceName
} from './video-dubbing/videoDubbingUtils';
import styles from './VideoDubbingPage.module.css';

type Props = {
  jobs: JobState[];
  onJobCreated: (jobId: string) => void;
  onSelectJob: (jobId: string) => void;
  onOpenJobMedia?: (jobId: string) => void;
  prefillParameters?: JobParameterSnapshot | null;
  creationTemplate?: CreationTemplateEntry | null;
  creationTemplateError?: string | null;
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
    selectedSubtitlePathRef
  } = useVideoDubbingSelectionState();
  const [activeTab, setActiveTab] = useState<VideoDubbingTab>('videos');

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

  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [templateStatus, setTemplateStatus] = useState<string | null>(null);
  const [templateError, setTemplateError] = useState<string | null>(null);
  const [isSavingTemplate, setIsSavingTemplate] = useState(false);
  const [selectedVideoDiscoveryTemplateState, setSelectedVideoDiscoveryTemplateState] =
    useState<Record<string, unknown> | null>(null);
  const appliedTemplateRef = useRef<string | null>(null);
  const pendingTemplateMetadataRef = useRef<Record<string, unknown> | null>(null);
  const [templateMetadataApplyKey, setTemplateMetadataApplyKey] = useState(0);
  const clearSelectedVideoDiscoveryTemplate = useCallback(() => {
    setSelectedVideoDiscoveryTemplateState(null);
  }, []);
  const {
    videoDiscoveryProvider,
    discoveryQuery,
    setDiscoveryQuery,
    discoveryError,
    setDiscoveryError,
    isDiscoveringVideos,
    discoveredVideoCandidates,
    discoverVideos,
    handleDiscoveryProviderChange: changeDiscoveryProvider
  } = useVideoDubbingDiscoverySearch({
    onClearSelectedDiscoveryTemplate: clearSelectedVideoDiscoveryTemplate
  });

  const {
    library,
    isLoading,
    loadError,
    deletingVideoPath,
    refreshLibrary,
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
  const selectedVideo = useMemo(
    () => videos.find((video) => video.path === selectedVideoPath) ?? null,
    [videos, selectedVideoPath]
  );
  const playableSubtitles = useMemo(() => {
    return filterPlayableSubtitles(selectedVideo);
  }, [selectedVideo]);
  const selectedSubtitle = useMemo(
    () => playableSubtitles.find((sub) => sub.path === selectedSubtitlePath) ?? null,
    [playableSubtitles, selectedSubtitlePath]
  );
  const subtitleLanguageLabel = useMemo(
    () =>
      resolveSubtitleLanguageLabel(
        selectedSubtitle?.language,
        selectedSubtitle?.path,
        selectedSubtitle?.filename
      ),
    [selectedSubtitle]
  );
  const subtitleLanguageCode = useMemo(
    () =>
      resolveSubtitleLanguageCandidate(
        selectedSubtitle?.language,
        selectedSubtitle?.path,
        selectedSubtitle?.filename
      ),
    [selectedSubtitle]
  );
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
  const metadataSourceName = useMemo(() => {
    return resolveVideoDubbingMetadataSourceName({
      subtitle: selectedSubtitle,
      video: selectedVideo
    });
  }, [selectedSubtitle, selectedVideo]);
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
  const canExtractEmbedded = useMemo(() => {
    return canExtractEmbeddedSubtitles(selectedVideo);
  }, [selectedVideo]);
  const {
    acquisitionProviderError,
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
  } = useVideoDubbingAcquisitionProviders(videoDiscoveryProvider);
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
    onClearSelectedDiscoveryTemplate: clearSelectedVideoDiscoveryTemplate
  });

  const handleRefresh = useCallback(async () => {
    const language = await refreshLibrary();
    ensureTargetLanguage(language);
  }, [ensureTargetLanguage, refreshLibrary]);

  const handleDeleteVideo = useCallback(
    async (video: YoutubeNasVideo) => {
      const language = await deleteVideo(video);
      ensureTargetLanguage(language);
    },
    [deleteVideo, ensureTargetLanguage]
  );

  useEffect(() => {
    void handleRefresh();
  }, []);

  useEffect(() => {
    const prefill = resolveVideoDubPrefill(prefillParameters);
    if (!prefill) {
      return;
    }
    if (prefill.videoPath) {
      setSelectedVideoPath(prefill.videoPath);
    }
    if (prefill.subtitlePath) {
      setSelectedSubtitlePath(prefill.subtitlePath);
    }
    if (prefill.targetLanguage) {
      applyTargetLanguage(prefill.targetLanguage);
    }
    if (prefill.voice !== undefined) {
      setVoice(prefill.voice);
    }
    if (prefill.llmModel) {
      setLlmModel(prefill.llmModel);
    }
    if (prefill.translationProvider) {
      setTranslationProvider(prefill.translationProvider);
    }
    if (prefill.transliterationMode) {
      setTransliterationMode(prefill.transliterationMode);
    }
    if (prefill.transliterationModel) {
      setTransliterationModel(prefill.transliterationModel);
    }
  }, [applyTargetLanguage, prefillParameters]);

  useEffect(() => {
    if (prefillParameters || creationTemplate) {
      return;
    }
    applyPipelineDefaults(pipelineDefaults);
  }, [applyPipelineDefaults, creationTemplate, pipelineDefaults, prefillParameters]);

  useEffect(() => {
    if (!creationTemplate) {
      appliedTemplateRef.current = null;
      return;
    }
    const applyKey = `${creationTemplate.id}:${creationTemplate.updated_at}`;
    if (appliedTemplateRef.current === applyKey) {
      return;
    }
    const applied = extractVideoDubbingTemplateFormState(creationTemplate);
    if (!applied) {
      setTemplateStatus(null);
      setTemplateError(`Template "${creationTemplate.name}" is not compatible with Video Dubbing.`);
      appliedTemplateRef.current = applyKey;
      return;
    }

    setSelectedVideoDiscoveryTemplateState(applied.discoveryState ?? null);
    if (applied.videoPath) setSelectedVideoPath(applied.videoPath);
    if (applied.subtitlePath) setSelectedSubtitlePath(applied.subtitlePath);
    if (applied.targetLanguage) applyTargetLanguage(applied.targetLanguage);
    if (applied.voice !== undefined) setVoice(applied.voice);
    if (applied.startOffset !== undefined) setStartOffset(applied.startOffset);
    if (applied.endOffset !== undefined) setEndOffset(applied.endOffset);
    if (applied.originalMixPercent !== undefined) setOriginalMixPercent(applied.originalMixPercent);
    if (applied.flushSentences !== undefined) setFlushSentences(applied.flushSentences);
    if (applied.translationBatchSize !== undefined) setTranslationBatchSize(applied.translationBatchSize);
    if (applied.targetHeight !== undefined) setTargetHeight(applied.targetHeight);
    if (applied.preserveAspectRatio !== undefined) setPreserveAspectRatio(applied.preserveAspectRatio);
    if (applied.splitBatches !== undefined) setSplitBatches(applied.splitBatches);
    if (applied.stitchBatches !== undefined) setStitchBatches(applied.stitchBatches);
    if (applied.llmModel) setLlmModel(applied.llmModel);
    if (applied.translationProvider) setTranslationProvider(applied.translationProvider);
    if (applied.transliterationMode) setTransliterationMode(applied.transliterationMode);
    if (applied.transliterationModel) setTransliterationModel(applied.transliterationModel);
    if (applied.includeTransliteration !== undefined) setIncludeTransliteration(applied.includeTransliteration);
    if (applied.enableLookupCache !== undefined) setEnableLookupCache(applied.enableLookupCache);
    if (applied.mediaMetadataDraft) {
      pendingTemplateMetadataRef.current = applied.mediaMetadataDraft;
      setTemplateMetadataApplyKey((current) => current + 1);
    }
    setTemplateError(null);
    setTemplateStatus(`Applied template "${creationTemplate.name}".`);
    appliedTemplateRef.current = applyKey;
  }, [
    applyTargetLanguage,
    creationTemplate,
    setEnableLookupCache,
    setEndOffset,
    setFlushSentences,
    setIncludeTransliteration,
    setLlmModel,
    setOriginalMixPercent,
    setPreserveAspectRatio,
    setSelectedSubtitlePath,
    setSelectedVideoPath,
    setSplitBatches,
    setStartOffset,
    setStitchBatches,
    setTargetHeight,
    setTranslationBatchSize,
    setTranslationProvider,
    setTransliterationMode,
    setTransliterationModel,
    setVoice
  ]);

  useEffect(() => {
    const metadata = pendingTemplateMetadataRef.current;
    if (!metadata) {
      return;
    }
    pendingTemplateMetadataRef.current = null;
    updateMediaMetadataDraft((draft) => {
      Object.keys(draft).forEach((key) => {
        delete draft[key];
      });
      Object.assign(draft, metadata);
    });
  }, [metadataSourceName, templateMetadataApplyKey, updateMediaMetadataDraft]);

  useEffect(() => {
    if (selectedVideoPath && !selectedVideo) {
      return;
    }
    if (playableSubtitles.length === 0) {
      setSelectedSubtitlePath(null);
      return;
    }
    const current = playableSubtitles.find((sub) => sub.path === selectedSubtitlePath);
    if (current) {
      return;
    }
    const defaultSubtitle = resolveDefaultSubtitle(selectedVideo) ?? playableSubtitles[0];
    setSelectedSubtitlePath(defaultSubtitle?.path ?? null);
    ensureTargetLanguage(defaultSubtitle?.language);
  }, [ensureTargetLanguage, playableSubtitles, selectedSubtitlePath, selectedVideo, selectedVideoPath]);

  const handleSelectVideo = useCallback((video: YoutubeNasVideo) => {
    setSelectedVideoDiscoveryTemplateState(null);
    setSelectedVideoPath(video.path);
    const defaultSubtitle = resolveDefaultSubtitle(video);
    setSelectedSubtitlePath(defaultSubtitle?.path ?? null);
    ensureTargetLanguage(defaultSubtitle?.language);
  }, [ensureTargetLanguage]);

  const handleDiscoverVideos = useCallback(async () => {
    await discoverVideos({
      isDiscoveryProviderAvailable: isSelectedVideoDiscoveryProviderAvailable,
      unavailableMessage: selectedVideoDiscoveryProviderUnavailableMessage
    });
  }, [
    discoverVideos,
    isSelectedVideoDiscoveryProviderAvailable,
    selectedVideoDiscoveryProviderUnavailableMessage
  ]);

  const handleDiscoveryProviderChange = useCallback((provider: string) => {
    setDownloadStationCandidate(null);
    changeDiscoveryProvider(provider);
  }, [changeDiscoveryProvider, setDownloadStationCandidate]);

  const handleSelectDiscoveryCandidate = useCallback((candidate: AcquisitionCandidate) => {
    const templateState = (selectedVideoPath?: string | null, selectedSubtitlePath?: string | null) =>
      makeVideoDiscoveryTemplateState(candidate, {
        selectedProvider: videoDiscoveryProvider,
        query: discoveryQuery,
        selectedVideoPath,
        selectedSubtitlePath
      });
    if (candidate.provider === 'youtube_search') {
      const metadataYoutubeUrl = candidate.metadata['youtube_url'];
      const sourceUrl =
        candidate.source_url?.trim() ||
        (typeof metadataYoutubeUrl === 'string' ? metadataYoutubeUrl.trim() : '');
      if (!sourceUrl) {
        setDiscoveryError('Selected YouTube result does not include a reviewable URL.');
        return;
      }
      setYoutubeLookupSourceName(sourceUrl);
      setMetadataSection('youtube');
      setActiveTab('metadata');
      void performYoutubeMetadataLookup(sourceUrl, false);
      setSelectedVideoDiscoveryTemplateState(templateState(null, null));
      setStatusMessage(`Selected YouTube discovery result ${candidate.title}. Review metadata before downloading or dubbing.`);
      return;
    }

    if (candidate.provider === 'newznab_torznab') {
      if (isDownloadStationHandoffCandidate(candidate)) {
        setDownloadStationCandidate(candidate);
        setDownloadStationSourceUri('');
      }
      setSelectedVideoDiscoveryTemplateState(templateState(null, null));
      setStatusMessage(`Selected indexer result ${candidate.title}. Confirm lawful access before any downloader handoff.`);
      return;
    }

    const localPath = candidate.local_path?.trim();
    if (!localPath) {
      return;
    }
    const libraryVideo = videos.find((video) => video.path === localPath);
    if (libraryVideo) {
      const defaultSubtitle = resolveDefaultSubtitle(libraryVideo);
      handleSelectVideo(libraryVideo);
      setSelectedVideoDiscoveryTemplateState(templateState(libraryVideo.path, defaultSubtitle?.path ?? null));
      setStatusMessage(`Selected discovered video ${libraryVideo.filename}.`);
      return;
    }
    setSelectedVideoPath(localPath);
    const selectedSubtitlePath = candidate.subtitles[0]?.path ?? null;
    setSelectedSubtitlePath(selectedSubtitlePath);
    setSelectedVideoDiscoveryTemplateState(templateState(localPath, selectedSubtitlePath));
    setStatusMessage('Selected a discovered video path. Refresh the NAS library if the video row is not visible yet.');
  }, [
    discoveryQuery,
    handleSelectVideo,
    performYoutubeMetadataLookup,
    setMetadataSection,
    setDownloadStationSourceUri,
    setSelectedSubtitlePath,
    setSelectedVideoPath,
    setYoutubeLookupSourceName,
    videoDiscoveryProvider,
    videos
  ]);

  const handleSelectSubtitle = useCallback((path: string) => {
    setSelectedSubtitlePath(path);
    setSelectedVideoDiscoveryTemplateState((current) => current ? { ...current, selected_subtitle_path: path } : current);
    const match = playableSubtitles.find((sub) => sub.path === path);
    ensureTargetLanguage(match?.language);
  }, [ensureTargetLanguage, playableSubtitles]);

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

  const handleGenerate = useCallback(async () => {
    if (isIntakeAtCapacity) {
      setGenerateError('Job queue is at capacity. Wait for pending jobs to clear before creating a dubbed video.');
      return;
    }
    const result = buildVideoDubbingGeneratePayload({
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
    });
    if (!result.payload) {
      setGenerateError(result.error);
      return;
    }
    setIsGenerating(true);
    setGenerateError(null);
    setStatusMessage(null);
    try {
      const response = await generateYoutubeDub(result.payload);
      setStatusMessage(`Dub job submitted as ${response.job_id}. Track progress below.`);
      onJobCreated(response.job_id);
      setActiveTab('jobs');
      await refreshIntakeStatus();
    } catch (error) {
      const message =
        error instanceof Error ? error.message || 'Unable to generate dubbed video.' : 'Unable to generate dubbed video.';
      setGenerateError(message);
    } finally {
      setIsGenerating(false);
    }
  }, [
    selectedVideo,
    selectedSubtitle,
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
    mediaMetadataDraft,
    onJobCreated,
    isIntakeAtCapacity,
    refreshIntakeStatus
  ]);

  const handleSaveTemplate = useCallback(async () => {
    const result = buildVideoDubbingGeneratePayload({
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
    });
    if (!result.payload) {
      setTemplateError(result.error);
      setTemplateStatus(null);
      return;
    }

    setIsSavingTemplate(true);
    setTemplateError(null);
    setTemplateStatus(null);
    try {
      const saved = await saveCreationTemplate(buildVideoDubbingTemplatePayload(result.payload, selectedVideoDiscoveryTemplateState));
      setTemplateStatus(`Saved template "${saved.name}". Apple Create can apply it from YouTube Dub.`);
    } catch (error) {
      const message =
        error instanceof Error ? error.message || 'Unable to save video template.' : 'Unable to save video template.';
      setTemplateError(message);
    } finally {
      setIsSavingTemplate(false);
    }
  }, [
    selectedVideo,
    selectedSubtitle,
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
    mediaMetadataDraft
  ]);

  const subtitleNotice = useMemo(() => {
    return resolveSubtitleNotice(selectedVideo, playableSubtitles);
  }, [playableSubtitles, selectedVideo]);

  const canGenerate = Boolean(selectedVideo && selectedSubtitle && !isGenerating && !isIntakeAtCapacity);

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

      {statusMessage ? <p className={styles.success}>{statusMessage}</p> : null}
      {generateError ? <p className={styles.error}>{generateError}</p> : null}
      {isLoadingCreationTemplate ? <p className={styles.success}>Loading saved template...</p> : null}
      {templateStatus ? <p className={styles.success}>{templateStatus}</p> : null}
      {creationTemplateError ?? templateError ? (
        <p className={styles.error}>{creationTemplateError ?? templateError}</p>
      ) : null}
      <CreateIntakeStatusCallout status={intakeStatus} isLoading={isLoadingIntakeStatus} />

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
