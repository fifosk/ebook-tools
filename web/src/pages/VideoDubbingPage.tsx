import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  discoverAcquisitionCandidates,
  fetchAcquisitionProviders,
  generateYoutubeDub,
  saveCreationTemplate
} from '../api/client';
import type {
  AcquisitionCandidate,
  AcquisitionDiscoveryResponse,
  AcquisitionProvider,
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
import {
  buildVideoDubbingGeneratePayload,
  buildVideoDubbingTemplatePayload,
  canExtractEmbeddedSubtitles,
  extractVideoDubbingTemplateFormState,
  filterPlayableSubtitles,
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

type VideoDiscoveryProvider = 'nas_video' | 'youtube_search';

function findProvider(providers: AcquisitionProvider[], providerId: string): AcquisitionProvider | null {
  return providers.find((provider) => provider.id === providerId) ?? null;
}

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
  const [videoDiscoveryProvider, setVideoDiscoveryProvider] = useState<VideoDiscoveryProvider>('nas_video');
  const [discoveryQuery, setDiscoveryQuery] = useState('');
  const [discoveryResponse, setDiscoveryResponse] = useState<AcquisitionDiscoveryResponse | null>(null);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);
  const [isDiscoveringVideos, setIsDiscoveringVideos] = useState(false);
  const [acquisitionProviders, setAcquisitionProviders] = useState<AcquisitionProvider[]>([]);
  const [acquisitionProviderError, setAcquisitionProviderError] = useState<string | null>(null);
  const appliedTemplateRef = useRef<string | null>(null);
  const pendingTemplateMetadataRef = useRef<Record<string, unknown> | null>(null);
  const [templateMetadataApplyKey, setTemplateMetadataApplyKey] = useState(0);

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
  const youtubeSearchProvider = useMemo(
    () => findProvider(acquisitionProviders, 'youtube_search'),
    [acquisitionProviders]
  );
  const isYoutubeSearchAvailable = youtubeSearchProvider?.available !== false;
  const youtubeSearchUnavailableMessage =
    youtubeSearchProvider && !youtubeSearchProvider.available
      ? `${youtubeSearchProvider.label} is ${youtubeSearchProvider.status.replace('_', ' ')}. Configure the YouTube Data API key to search videos, or use NAS videos.`
      : null;

  const discoveredVideoCandidates = useMemo(() => {
    return (discoveryResponse?.candidates ?? []).filter((candidate) => {
      if (candidate.provider !== videoDiscoveryProvider) {
        return false;
      }
      if (candidate.provider === 'youtube_search') {
        const metadataYoutubeUrl = candidate.metadata['youtube_url'];
        return Boolean(candidate.source_url?.trim() || (typeof metadataYoutubeUrl === 'string' && metadataYoutubeUrl.trim()));
      }
      return Boolean(candidate.local_path);
    });
  }, [discoveryResponse, videoDiscoveryProvider]);

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
    void refreshAcquisitionProviders();
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
  }, [ensureTargetLanguage, playableSubtitles, selectedSubtitlePath, selectedVideo]);

  const handleSelectVideo = useCallback((video: YoutubeNasVideo) => {
    setSelectedVideoPath(video.path);
    const defaultSubtitle = resolveDefaultSubtitle(video);
    setSelectedSubtitlePath(defaultSubtitle?.path ?? null);
    ensureTargetLanguage(defaultSubtitle?.language);
  }, [ensureTargetLanguage]);

  const handleDiscoverVideos = useCallback(async () => {
    if (videoDiscoveryProvider === 'youtube_search' && !isYoutubeSearchAvailable) {
      setDiscoveryError(youtubeSearchUnavailableMessage ?? 'YouTube search is not available on this backend.');
      setDiscoveryResponse(null);
      return;
    }
    setIsDiscoveringVideos(true);
    setDiscoveryError(null);
    try {
      const response = await discoverAcquisitionCandidates({
        mediaKind: 'video',
        provider: videoDiscoveryProvider,
        query: discoveryQuery,
        limit: 25
      });
      setDiscoveryResponse(response);
    } catch (error) {
      const message =
        error instanceof Error ? error.message || 'Unable to discover video sources.' : 'Unable to discover video sources.';
      setDiscoveryError(message);
    } finally {
      setIsDiscoveringVideos(false);
    }
  }, [discoveryQuery, isYoutubeSearchAvailable, videoDiscoveryProvider, youtubeSearchUnavailableMessage]);

  const refreshAcquisitionProviders = useCallback(async () => {
    setAcquisitionProviderError(null);
    try {
      const response = await fetchAcquisitionProviders();
      setAcquisitionProviders(response.providers ?? []);
    } catch (error) {
      const message =
        error instanceof Error ? error.message || 'Unable to load discovery providers.' : 'Unable to load discovery providers.';
      setAcquisitionProviderError(message);
    }
  }, []);

  const handleDiscoveryProviderChange = useCallback((provider: VideoDiscoveryProvider) => {
    setVideoDiscoveryProvider(provider);
    setDiscoveryResponse(null);
    setDiscoveryError(null);
  }, []);

  const handleSelectDiscoveryCandidate = useCallback((candidate: AcquisitionCandidate) => {
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
      setStatusMessage(`Selected YouTube discovery result ${candidate.title}. Review metadata before downloading or dubbing.`);
      return;
    }

    const localPath = candidate.local_path?.trim();
    if (!localPath) {
      return;
    }
    const libraryVideo = videos.find((video) => video.path === localPath);
    if (libraryVideo) {
      handleSelectVideo(libraryVideo);
      setStatusMessage(`Selected discovered video ${libraryVideo.filename}.`);
      return;
    }
    setSelectedVideoPath(localPath);
    setSelectedSubtitlePath(candidate.subtitles[0]?.path ?? null);
    setStatusMessage('Selected a discovered video path. Refresh the NAS library if the video row is not visible yet.');
  }, [
    handleSelectVideo,
    performYoutubeMetadataLookup,
    setMetadataSection,
    setSelectedSubtitlePath,
    setSelectedVideoPath,
    setYoutubeLookupSourceName,
    videos
  ]);

  const handleSelectSubtitle = useCallback((path: string) => {
    setSelectedSubtitlePath(path);
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
      const saved = await saveCreationTemplate(buildVideoDubbingTemplatePayload(result.payload));
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
          discoveryQuery={discoveryQuery}
          discoveryCandidates={discoveredVideoCandidates}
          discoveryError={discoveryError}
          acquisitionProviderError={acquisitionProviderError}
          youtubeSearchUnavailableMessage={youtubeSearchUnavailableMessage}
          isYoutubeSearchAvailable={isYoutubeSearchAvailable}
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
