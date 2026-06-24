import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  fetchYoutubeLibrary,
  fetchVoiceInventory,
  generateYoutubeDub,
  synthesizeVoicePreview,
  fetchSubtitleModels,
  fetchInlineSubtitleStreams,
  extractInlineSubtitles,
  deleteNasSubtitle,
  deleteYoutubeVideo
} from '../api/client';
import { fetchBookCreationOptions } from '../api/createBook';
import type {
  YoutubeNasLibraryResponse,
  YoutubeNasVideo,
  YoutubeNasSubtitle,
  YoutubeInlineSubtitleStream,
  VoiceInventoryResponse,
  JobParameterSnapshot
} from '../api/dtos';
import type { JobState } from '../components/JobList';
import { resolveLanguageName } from '../constants/languageCodes';
import { useLanguagePreferences } from '../context/LanguageProvider';
import { sampleSentenceFor } from '../utils/sampleSentences';
import {
  preferLanguageLabel,
  resolveLanguageCode
} from '../utils/languages';
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
import {
  DEFAULT_FLUSH_SENTENCES,
  DEFAULT_LLM_MODEL,
  DEFAULT_ORIGINAL_MIX_PERCENT,
  DEFAULT_PRESERVE_ASPECT_RATIO,
  DEFAULT_SPLIT_BATCHES,
  DEFAULT_STITCH_BATCHES,
  DEFAULT_TARGET_HEIGHT,
  DEFAULT_TRANSLATION_BATCH_SIZE
} from './video-dubbing/videoDubbingConfig';
import type { VideoDubbingTab } from './video-dubbing/videoDubbingTypes';
import { useVideoDubbingSelectionState } from './video-dubbing/useVideoDubbingSelectionState';
import { useVideoDubbingMetadata } from './video-dubbing/useVideoDubbingMetadata';
import { useVideoDubbingLanguageState } from './video-dubbing/useVideoDubbingLanguageState';
import {
  buildVideoDubbingGeneratePayload,
  buildVoiceOptions,
  canExtractEmbeddedSubtitles,
  filterPlayableSubtitles,
  formatSubtitleExtractionStatus,
  resolveVideoDubPrefill,
  resolveDefaultStreamLanguages,
  resolveDefaultSubtitle,
  resolveSelectionAfterVideoDelete,
  resolveSubtitleNotice,
  resolveVideoDubbingSelection,
  resolveVideoDubbingMetadataSourceName
} from './video-dubbing/videoDubbingUtils';
import styles from './VideoDubbingPage.module.css';

type Props = {
  jobs: JobState[];
  onJobCreated: (jobId: string) => void;
  onSelectJob: (jobId: string) => void;
  onOpenJobMedia?: (jobId: string) => void;
  prefillParameters?: JobParameterSnapshot | null;
};
export default function VideoDubbingPage({
  jobs,
  onJobCreated,
  onSelectJob,
  onOpenJobMedia,
  prefillParameters = null
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
  const [library, setLibrary] = useState<YoutubeNasLibraryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<VideoDubbingTab>('videos');

  const [voice, setVoice] = useState('gTTS');
  const [startOffset, setStartOffset] = useState('');
  const [endOffset, setEndOffset] = useState('');
  const [originalMixPercent, setOriginalMixPercent] = useState(DEFAULT_ORIGINAL_MIX_PERCENT);
  const [flushSentences, setFlushSentences] = useState(DEFAULT_FLUSH_SENTENCES);
  const [translationBatchSize, setTranslationBatchSize] = useState(DEFAULT_TRANSLATION_BATCH_SIZE);
  const [targetHeight, setTargetHeight] = useState(DEFAULT_TARGET_HEIGHT);
  const [preserveAspectRatio, setPreserveAspectRatio] = useState(DEFAULT_PRESERVE_ASPECT_RATIO);
  const [llmModel, setLlmModel] = useState(DEFAULT_LLM_MODEL);
  const [transliterationModel, setTransliterationModel] = useState('');
  const [translationProvider, setTranslationProvider] = useState('llm');
  const [transliterationMode, setTransliterationMode] = useState('default');
  const [splitBatches, setSplitBatches] = useState(DEFAULT_SPLIT_BATCHES);
  const [stitchBatches, setStitchBatches] = useState(DEFAULT_STITCH_BATCHES);
  const [includeTransliteration, setIncludeTransliteration] = useState(true);
  const [enableLookupCache, setEnableLookupCache] = useState(true);
  const [voiceInventory, setVoiceInventory] = useState<VoiceInventoryResponse | null>(null);
  const [voiceInventoryError, setVoiceInventoryError] = useState<string | null>(null);
  const [isLoadingVoices, setIsLoadingVoices] = useState(false);
  const [llmModels, setLlmModels] = useState<string[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [modelError, setModelError] = useState<string | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const previewAudioRef = useRef<{ audio: HTMLAudioElement; url: string } | null>(null);

  const cleanupPreviewAudio = useCallback(() => {
    if (previewAudioRef.current) {
      previewAudioRef.current.audio.pause();
      URL.revokeObjectURL(previewAudioRef.current.url);
      previewAudioRef.current = null;
    }
  }, []);

  const applyYoutubeDubDefaults = useCallback(
    (defaults: Awaited<ReturnType<typeof fetchBookCreationOptions>>['youtube_dub_defaults']) => {
      if (!defaults) {
        return;
      }
      setOriginalMixPercent((current) =>
        current === DEFAULT_ORIGINAL_MIX_PERCENT ? defaults.original_mix_percent : current
      );
      setFlushSentences((current) =>
        current === DEFAULT_FLUSH_SENTENCES ? defaults.flush_sentences : current
      );
      setTranslationBatchSize((current) =>
        current === DEFAULT_TRANSLATION_BATCH_SIZE ? defaults.translation_batch_size : current
      );
      setTargetHeight((current) =>
        current === DEFAULT_TARGET_HEIGHT ? defaults.target_height : current
      );
      setPreserveAspectRatio((current) =>
        current === DEFAULT_PRESERVE_ASPECT_RATIO ? defaults.preserve_aspect_ratio : current
      );
      setSplitBatches((current) =>
        current === DEFAULT_SPLIT_BATCHES ? defaults.split_batches : current
      );
      setStitchBatches((current) =>
        current === DEFAULT_STITCH_BATCHES ? defaults.stitch_batches : current
      );
    },
    []
  );

  useEffect(() => {
    if (prefillParameters) {
      return undefined;
    }
    let cancelled = false;
    const loadCreationDefaults = async () => {
      try {
        const options = await fetchBookCreationOptions();
        if (!cancelled) {
          applyYoutubeDubDefaults(options.youtube_dub_defaults);
        }
      } catch (error) {
        if (!cancelled) {
          console.warn('Unable to load YouTube dubbing creation defaults', error);
        }
      }
    };
    void loadCreationDefaults();
    return () => {
      cancelled = true;
    };
  }, [applyYoutubeDubDefaults, prefillParameters]);

  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isExtractingSubtitles, setIsExtractingSubtitles] = useState(false);
  const [deletingSubtitlePath, setDeletingSubtitlePath] = useState<string | null>(null);
  const [deletingVideoPath, setDeletingVideoPath] = useState<string | null>(null);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [availableSubtitleStreams, setAvailableSubtitleStreams] = useState<YoutubeInlineSubtitleStream[]>([]);
  const [selectedStreamLanguages, setSelectedStreamLanguages] = useState<Set<string>>(new Set());
  const [isChoosingStreams, setIsChoosingStreams] = useState(false);
  const [isLoadingStreams, setIsLoadingStreams] = useState(false);

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
  const extractableStreams = useMemo(
    () => availableSubtitleStreams.filter((stream) => stream.can_extract),
    [availableSubtitleStreams]
  );

  const handleRefresh = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    setStatusMessage(null);
    try {
      const response = await fetchYoutubeLibrary(baseDir.trim() || undefined);
      setLibrary(response);
      setBaseDir(response.base_dir || baseDir);
      if (response.videos.length > 0) {
        const prefill = resolveVideoDubPrefill(prefillParameters);
        const selection = resolveVideoDubbingSelection({
          videos: response.videos,
          preferredVideoPath: prefill?.videoPath || selectedVideoPathRef.current,
          preferredSubtitlePath: prefill?.subtitlePath || selectedSubtitlePathRef.current,
        });
        setSelectedVideoPath(selection.videoPath);
        setSelectedSubtitlePath(selection.subtitlePath);
        ensureTargetLanguage(selection.subtitle?.language);
      } else {
        setSelectedVideoPath(null);
        setSelectedSubtitlePath(null);
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message || 'Unable to load NAS videos.' : 'Unable to load NAS videos.';
      setLoadError(message);
    } finally {
      setIsLoading(false);
    }
  }, [baseDir, ensureTargetLanguage, prefillParameters]);

  const handleDeleteVideo = useCallback(
    async (video: YoutubeNasVideo) => {
      if (video.linked_job_ids && video.linked_job_ids.length > 0) {
        return;
      }
      const targetFolder = video.folder || video.path;
      const confirmed = window.confirm(
        `Delete the folder "${targetFolder}" and all dubbed outputs/subtitles inside it? This will remove the downloaded video and any generated artifacts.`
      );
      if (!confirmed) {
        return;
      }
      setDeletingVideoPath(video.path);
      setLoadError(null);
      try {
        await deleteYoutubeVideo({ video_path: video.path });
        let nextSelectedPath = selectedVideoPath;
        let nextSubtitle = selectedSubtitlePath;
        let fallbackLanguage: string | null = null;
        setLibrary((prev) => {
          if (!prev) {
            return prev;
          }
          const selection = resolveSelectionAfterVideoDelete({
            videos: prev.videos,
            deletedVideoPath: video.path,
            selectedVideoPath: nextSelectedPath,
            selectedSubtitlePath: nextSubtitle,
          });
          nextSelectedPath = selection.selectedVideoPath;
          nextSubtitle = selection.selectedSubtitlePath;
          fallbackLanguage = selection.fallbackLanguage;
          return { ...prev, videos: selection.videos };
        });
        setSelectedVideoPath(nextSelectedPath);
        setSelectedSubtitlePath(nextSubtitle);
        ensureTargetLanguage(fallbackLanguage);
      } catch (error) {
        const message =
          error instanceof Error ? error.message || 'Unable to delete video.' : 'Unable to delete video.';
        setLoadError(message);
      } finally {
        setDeletingVideoPath(null);
      }
    },
    [ensureTargetLanguage, selectedSubtitlePath, selectedVideoPath]
  );

  useEffect(() => {
    void handleRefresh();
  }, []);

  useEffect(() => {
    setAvailableSubtitleStreams([]);
    setSelectedStreamLanguages(new Set());
    setIsChoosingStreams(false);
    setDeletingSubtitlePath(null);
  }, [selectedVideoPath]);

  useEffect(() => {
    return () => cleanupPreviewAudio();
  }, [cleanupPreviewAudio]);

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
    if (prefill.startOffset !== undefined) {
      setStartOffset(prefill.startOffset);
    }
    if (prefill.endOffset !== undefined) {
      setEndOffset(prefill.endOffset);
    }
    setOriginalMixPercent(prefill.originalMixPercent);
    if (prefill.flushSentences !== undefined) {
      setFlushSentences(prefill.flushSentences);
    }
    if (prefill.translationBatchSize !== undefined) {
      setTranslationBatchSize(prefill.translationBatchSize);
    }
    setTargetHeight(prefill.targetHeight);
    setPreserveAspectRatio(prefill.preserveAspectRatio);
    setSplitBatches(prefill.splitBatches);
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
    setIncludeTransliteration(prefill.includeTransliteration);
  }, [applyTargetLanguage, prefillParameters]);

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

  useEffect(() => {
    let cancelled = false;
    const loadModels = async () => {
      setIsLoadingModels(true);
      setModelError(null);
      try {
        const models = await fetchSubtitleModels();
        if (cancelled) return;
        setLlmModels(models);
        if (!llmModel && models.length > 0) {
          setLlmModel(models.includes(DEFAULT_LLM_MODEL) ? DEFAULT_LLM_MODEL : models[0]);
        }
      } catch (error) {
        if (cancelled) return;
        const message =
          error instanceof Error ? error.message || 'Unable to load translation models.' : 'Unable to load translation models.';
        setModelError(message);
      } finally {
        if (!cancelled) {
          setIsLoadingModels(false);
        }
      }
    };
    void loadModels();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadVoices = async () => {
      setIsLoadingVoices(true);
      setVoiceInventoryError(null);
      try {
        const inventory = await fetchVoiceInventory();
        if (cancelled) {
          return;
        }
        setVoiceInventory(inventory);
      } catch (error) {
        if (cancelled) {
          return;
        }
        const message =
          error instanceof Error ? error.message || 'Unable to load voices.' : 'Unable to load voices.';
        setVoiceInventoryError(message);
      } finally {
        if (!cancelled) {
          setIsLoadingVoices(false);
        }
      }
    };
    void loadVoices();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSelectVideo = useCallback((video: YoutubeNasVideo) => {
    setSelectedVideoPath(video.path);
    const defaultSubtitle = resolveDefaultSubtitle(video);
    setSelectedSubtitlePath(defaultSubtitle?.path ?? null);
    ensureTargetLanguage(defaultSubtitle?.language);
  }, [ensureTargetLanguage]);

  const handleSelectSubtitle = useCallback((path: string) => {
    setSelectedSubtitlePath(path);
    const match = playableSubtitles.find((sub) => sub.path === path);
    ensureTargetLanguage(match?.language);
  }, [ensureTargetLanguage, playableSubtitles]);

  const handleDeleteSubtitle = useCallback(
    async (subtitle: YoutubeNasSubtitle) => {
      if (!selectedVideo) {
        return;
      }
      const confirmed =
        typeof window === 'undefined' ||
        window.confirm(
          `Delete ${subtitle.filename}? This removes the subtitle and any mirrored HTML transcript copies.`,
        );
      if (!confirmed) {
        return;
      }
      setExtractError(null);
      setStatusMessage(null);
      setDeletingSubtitlePath(subtitle.path);
      try {
        await deleteNasSubtitle(selectedVideo.path, subtitle.path);
        await handleRefresh();
        setSelectedVideoPath(selectedVideo.path);
        if (selectedSubtitlePath === subtitle.path) {
          setSelectedSubtitlePath(null);
        }
        setStatusMessage(`Deleted ${subtitle.filename}`);
      } catch (error) {
        const message =
          error instanceof Error ? error.message || 'Unable to delete subtitle.' : 'Unable to delete subtitle.';
        setExtractError(message);
      } finally {
        setDeletingSubtitlePath(null);
      }
    },
    [handleRefresh, selectedSubtitlePath, selectedVideo]
  );

  const performSubtitleExtraction = useCallback(
    async (languages?: string[]) => {
      if (!selectedVideo) {
        return;
      }
      setIsExtractingSubtitles(true);
      setExtractError(null);
      setStatusMessage(null);
      try {
        const response = await extractInlineSubtitles(selectedVideo.path, languages);
        const count = response.extracted?.length ?? 0;
        setStatusMessage(formatSubtitleExtractionStatus(count, selectedVideo.filename));
        await handleRefresh();
        setSelectedVideoPath(selectedVideo.path);
        setAvailableSubtitleStreams([]);
        setSelectedStreamLanguages(new Set());
      } catch (error) {
        const message =
          error instanceof Error ? error.message || 'Unable to extract subtitles.' : 'Unable to extract subtitles.';
        setExtractError(message);
      } finally {
        setIsExtractingSubtitles(false);
      }
    },
    [handleRefresh, selectedVideo]
  );

  const handleExtractSubtitles = useCallback(async () => {
    if (!selectedVideo) {
      return;
    }
    setIsLoadingStreams(true);
    setIsChoosingStreams(false);
    setExtractError(null);
    setStatusMessage(null);
    try {
      const response = await fetchInlineSubtitleStreams(selectedVideo.path);
      const streams = response.streams ?? [];
      setAvailableSubtitleStreams(streams);
      const extractable = streams.filter((stream) => stream.can_extract);
      const defaults = resolveDefaultStreamLanguages(streams);
      setSelectedStreamLanguages(defaults);
      if (extractable.length === 0) {
        setExtractError(
          'No text-based subtitle streams were found. Image-based subtitle tracks cannot be extracted automatically.'
        );
        return;
      }
      if (extractable.length === 1) {
        const languages = Array.from(defaults).filter(Boolean);
        await performSubtitleExtraction(languages.length > 0 ? languages : undefined);
        return;
      }
      setIsChoosingStreams(true);
    } catch (error) {
      const message =
        error instanceof Error ? error.message || 'Unable to inspect subtitle streams.' : 'Unable to inspect subtitle streams.';
      setExtractError(message);
    } finally {
      setIsLoadingStreams(false);
    }
  }, [performSubtitleExtraction, resolveDefaultStreamLanguages, selectedVideo]);

  const handleToggleSubtitleStream = useCallback((language: string, enabled: boolean) => {
    if (!language) {
      return;
    }
    setSelectedStreamLanguages((previous) => {
      const next = new Set(previous);
      if (enabled) {
        next.add(language);
      } else {
        next.delete(language);
      }
      return next;
    });
  }, []);

  const handleConfirmSubtitleStreams = useCallback(async () => {
    if (!selectedVideo) {
      return;
    }
    if (availableSubtitleStreams.length > 1 && selectedStreamLanguages.size === 0) {
      setExtractError('Select at least one subtitle language to extract.');
      return;
    }
    setIsChoosingStreams(false);
    const languages = Array.from(selectedStreamLanguages).filter(Boolean);
    await performSubtitleExtraction(languages.length > 0 ? languages : undefined);
  }, [availableSubtitleStreams.length, performSubtitleExtraction, selectedVideo, selectedStreamLanguages]);

  const handleCancelStreamSelection = useCallback(() => {
    setIsChoosingStreams(false);
    setAvailableSubtitleStreams([]);
  }, []);

  const handleExtractAllStreams = useCallback(() => {
    void performSubtitleExtraction(undefined);
  }, [performSubtitleExtraction]);

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

  const handlePreviewVoice = useCallback(async () => {
    const languageCode = targetLanguageCode || resolveLanguageCode(subtitleLanguageLabel) || '';
    if (!languageCode) {
      setPreviewError('Choose a translation language before previewing.');
      return;
    }
    const languageLabel = preferLanguageLabel([
      targetLanguage,
      subtitleLanguageLabel,
      resolveLanguageName(languageCode),
      languageCode
    ]);
    setPreviewError(null);
    setIsPreviewing(true);
    cleanupPreviewAudio();
    try {
      const blob = await synthesizeVoicePreview({
        text: sampleSentenceFor(languageCode, languageLabel || languageCode),
        language: languageCode,
        voice: voice.trim() || undefined
      });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      previewAudioRef.current = { audio, url };
      audio.onended = () => {
        setIsPreviewing(false);
        cleanupPreviewAudio();
      };
      audio.onerror = () => {
        setIsPreviewing(false);
        setPreviewError('Audio playback failed.');
        cleanupPreviewAudio();
      };
      await audio.play();
    } catch (error) {
      setIsPreviewing(false);
      setPreviewError(error instanceof Error ? error.message : 'Unable to preview voice.');
      cleanupPreviewAudio();
    }
  }, [cleanupPreviewAudio, subtitleLanguageLabel, targetLanguage, targetLanguageCode, voice]);

  const subtitleNotice = useMemo(() => {
    return resolveSubtitleNotice(selectedVideo, playableSubtitles);
  }, [playableSubtitles, selectedVideo]);

  const availableVoiceOptions = useMemo(
    () => buildVoiceOptions(voiceInventory, targetLanguageCode),
    [targetLanguageCode, voiceInventory]
  );

  const canGenerate = Boolean(selectedVideo && selectedSubtitle && !isGenerating && !isIntakeAtCapacity);

  return (
    <div className={styles.container}>
      <VideoDubbingTabs
        activeTab={activeTab}
        videoCount={videos.length}
        jobCount={jobs.length}
        isGenerating={isGenerating}
        canGenerate={canGenerate}
        onTabChange={setActiveTab}
        onGenerate={() => void handleGenerate()}
      />

      {statusMessage ? <p className={styles.success}>{statusMessage}</p> : null}
      {generateError ? <p className={styles.error}>{generateError}</p> : null}
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
          onSelectVideo={handleSelectVideo}
          onSelectSubtitle={handleSelectSubtitle}
          onDeleteVideo={(video) => void handleDeleteVideo(video)}
          onDeleteSubtitle={(subtitle) => void handleDeleteSubtitle(subtitle)}
          onExtractSubtitles={() => void handleExtractSubtitles()}
          onToggleSubtitleStream={handleToggleSubtitleStream}
          onConfirmSubtitleStreams={() => void handleConfirmSubtitleStreams()}
          onCancelStreamSelection={handleCancelStreamSelection}
          onExtractAllStreams={handleExtractAllStreams}
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
          onPreviewVoice={() => void handlePreviewVoice()}
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
