import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  fetchYoutubeLibrary,
  fetchVoiceInventory,
  generateYoutubeDub,
  lookupSubtitleTvMetadataPreview,
  lookupYoutubeVideoMetadataPreview,
  synthesizeVoicePreview,
  fetchSubtitleModels,
  fetchInlineSubtitleStreams,
  extractInlineSubtitles,
  deleteNasSubtitle,
  fetchPipelineDefaults,
  deleteYoutubeVideo,
  clearTvMetadataCache,
  clearYoutubeMetadataCache
} from '../api/client';
import type {
  YoutubeNasLibraryResponse,
  YoutubeNasVideo,
  YoutubeNasSubtitle,
  YoutubeInlineSubtitleStream,
  VoiceInventoryResponse,
  JobParameterSnapshot,
  SubtitleTvMetadataPreviewResponse,
  YoutubeVideoMetadataPreviewResponse
} from '../api/dtos';
import type { JobState } from '../components/JobList';
import { VOICE_OPTIONS } from '../constants/menuOptions';
import { resolveLanguageName } from '../constants/languageCodes';
import { useLanguagePreferences } from '../context/LanguageProvider';
import { sampleSentenceFor } from '../utils/sampleSentences';
import {
  buildLanguageOptions,
  normalizeLanguageLabel,
  preferLanguageLabel,
  resolveLanguageCode,
  sortLanguageLabelsByName
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
import {
  DEFAULT_LLM_MODEL,
  DEFAULT_TRANSLATION_BATCH_SIZE,
  DEFAULT_VIDEO_DIR,
  VIDEO_DUB_STORAGE_KEYS
} from './video-dubbing/videoDubbingConfig';
import type { VideoDubbingTab, VideoMetadataSection } from './video-dubbing/videoDubbingTypes';
import {
  basenameFromPath,
  coerceRecord,
  formatMacOSVoiceIdentifier,
  formatMacOSVoiceLabel,
  formatOffsetLabel,
  parseOffsetSeconds,
  resolveDefaultSubtitle
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
  const [baseDir, setBaseDir] = useState(() => {
    if (typeof window === 'undefined') {
      return DEFAULT_VIDEO_DIR;
    }
    try {
      const stored = window.localStorage.getItem(VIDEO_DUB_STORAGE_KEYS.baseDir);
      return stored && stored.trim() ? stored.trim() : DEFAULT_VIDEO_DIR;
    } catch {
      return DEFAULT_VIDEO_DIR;
    }
  });
  const [library, setLibrary] = useState<YoutubeNasLibraryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<VideoDubbingTab>('videos');

  const [selectedVideoPath, setSelectedVideoPath] = useState<string | null>(() => {
    if (typeof window === 'undefined') {
      return null;
    }
    try {
      const stored = window.localStorage.getItem(VIDEO_DUB_STORAGE_KEYS.selectedVideoPath);
      return stored && stored.trim() ? stored.trim() : null;
    } catch {
      return null;
    }
  });
  const [selectedSubtitlePath, setSelectedSubtitlePath] = useState<string | null>(() => {
    if (typeof window === 'undefined') {
      return null;
    }
    try {
      const stored = window.localStorage.getItem(VIDEO_DUB_STORAGE_KEYS.selectedSubtitlePath);
      return stored && stored.trim() ? stored.trim() : null;
    } catch {
      return null;
    }
  });
  const selectedVideoPathRef = useRef<string | null>(selectedVideoPath);
  const selectedSubtitlePathRef = useRef<string | null>(selectedSubtitlePath);

  const [voice, setVoice] = useState('gTTS');
  const [targetLanguage, setTargetLanguage] = useState<string>(
    normalizeLanguageLabel(primaryTargetLanguage ?? '')
  );
  const [fetchedLanguages, setFetchedLanguages] = useState<string[]>([]);
  const [startOffset, setStartOffset] = useState('');
  const [endOffset, setEndOffset] = useState('');
  const [originalMixPercent, setOriginalMixPercent] = useState(5);
  const [flushSentences, setFlushSentences] = useState(10);
  const [translationBatchSize, setTranslationBatchSize] = useState(DEFAULT_TRANSLATION_BATCH_SIZE);
  const [targetHeight, setTargetHeight] = useState(480);
  const [preserveAspectRatio, setPreserveAspectRatio] = useState(true);
  const [llmModel, setLlmModel] = useState(DEFAULT_LLM_MODEL);
  const [transliterationModel, setTransliterationModel] = useState('');
  const [translationProvider, setTranslationProvider] = useState('llm');
  const [transliterationMode, setTransliterationMode] = useState('default');
  const [splitBatches, setSplitBatches] = useState(true);
  const [stitchBatches, setStitchBatches] = useState(true);
  const [includeTransliteration, setIncludeTransliteration] = useState(true);
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

  useEffect(() => {
    selectedVideoPathRef.current = selectedVideoPath;
    if (typeof window !== 'undefined') {
      try {
        if (selectedVideoPath) {
          window.localStorage.setItem(VIDEO_DUB_STORAGE_KEYS.selectedVideoPath, selectedVideoPath);
        } else {
          window.localStorage.removeItem(VIDEO_DUB_STORAGE_KEYS.selectedVideoPath);
        }
      } catch {
        // ignore storage errors
      }
    }
  }, [selectedVideoPath]);

  useEffect(() => {
    selectedSubtitlePathRef.current = selectedSubtitlePath;
    if (typeof window !== 'undefined') {
      try {
        if (selectedSubtitlePath) {
          window.localStorage.setItem(VIDEO_DUB_STORAGE_KEYS.selectedSubtitlePath, selectedSubtitlePath);
        } else {
          window.localStorage.removeItem(VIDEO_DUB_STORAGE_KEYS.selectedSubtitlePath);
        }
      } catch {
        // ignore storage errors
      }
    }
  }, [selectedSubtitlePath]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    try {
      window.localStorage.setItem(VIDEO_DUB_STORAGE_KEYS.baseDir, baseDir);
    } catch {
      // ignore storage errors
    }
  }, [baseDir]);


  const applyTargetLanguage = useCallback(
    (language: string) => {
      const normalized = normalizeLanguageLabel(language);
      setTargetLanguage(normalized);
      if (normalized) {
        setPrimaryTargetLanguage(normalized);
      }
    },
    [setPrimaryTargetLanguage]
  );

  const ensureTargetLanguage = useCallback(
    (language?: string | null) => {
      if (targetLanguage) {
        return;
      }
      const normalized = normalizeLanguageLabel(language);
      if (normalized) {
        setTargetLanguage(normalized);
        setPrimaryTargetLanguage(normalized);
      }
    },
    [setPrimaryTargetLanguage, targetLanguage]
  );

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
    if (!selectedVideo) {
      return [];
    }
    return selectedVideo.subtitles.filter((sub) => ['ass', 'srt', 'vtt', 'sub'].includes(sub.format.toLowerCase()));
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
  const metadataSourceName = useMemo(() => {
    if (selectedSubtitle?.filename) {
      return selectedSubtitle.filename;
    }
    if (selectedSubtitle?.path) {
      return basenameFromPath(selectedSubtitle.path);
    }
    if (selectedVideo?.filename) {
      return selectedVideo.filename;
    }
    if (selectedVideo?.path) {
      return basenameFromPath(selectedVideo.path);
    }
    return '';
  }, [selectedSubtitle, selectedVideo]);
  const [metadataLookupSourceName, setMetadataLookupSourceName] = useState<string>('');
  const [metadataPreview, setMetadataPreview] = useState<SubtitleTvMetadataPreviewResponse | null>(null);
  const [mediaMetadataDraft, setMediaMetadataDraft] = useState<Record<string, unknown> | null>(null);
  const [metadataLoading, setMetadataLoading] = useState<boolean>(false);
  const [metadataError, setMetadataError] = useState<string | null>(null);
  const metadataLookupIdRef = useRef<number>(0);
  const [metadataSection, setMetadataSection] = useState<VideoMetadataSection>('tv');
  const [youtubeLookupSourceName, setYoutubeLookupSourceName] = useState<string>('');
  const [youtubeMetadataPreview, setYoutubeMetadataPreview] = useState<YoutubeVideoMetadataPreviewResponse | null>(null);
  const [youtubeMetadataLoading, setYoutubeMetadataLoading] = useState<boolean>(false);
  const [youtubeMetadataError, setYoutubeMetadataError] = useState<string | null>(null);
  const youtubeLookupIdRef = useRef<number>(0);
  const updateMediaMetadataDraft = useCallback((updater: (draft: Record<string, unknown>) => void) => {
    setMediaMetadataDraft((current) => {
      const next: Record<string, unknown> = current ? { ...current } : {};
      updater(next);
      return next;
    });
  }, []);
  const updateMediaMetadataSection = useCallback(
    (sectionKey: string, updater: (section: Record<string, unknown>) => void) => {
      updateMediaMetadataDraft((draft) => {
        const currentSection = coerceRecord(draft[sectionKey]);
        const nextSection: Record<string, unknown> = currentSection ? { ...currentSection } : {};
        updater(nextSection);
        draft[sectionKey] = nextSection;
      });
    },
    [updateMediaMetadataDraft]
  );
  const performMetadataLookup = useCallback(async (sourceName: string, force: boolean) => {
    const normalized = sourceName.trim();
    if (!normalized) {
      setMetadataPreview(null);
      setMediaMetadataDraft(null);
      setMetadataError(null);
      setMetadataLoading(false);
      return;
    }
    const requestId = metadataLookupIdRef.current + 1;
    metadataLookupIdRef.current = requestId;
    setMetadataLoading(true);
    setMetadataError(null);
    try {
      const payload = await lookupSubtitleTvMetadataPreview({ source_name: normalized, force });
      if (metadataLookupIdRef.current !== requestId) {
        return;
      }
      setMetadataPreview(payload);
      setMediaMetadataDraft((current) => {
        const preservedYoutube =
          current && typeof current === 'object' && !Array.isArray(current)
            ? coerceRecord((current as Record<string, unknown>)['youtube'])
            : null;
        const next = payload.media_metadata ? { ...payload.media_metadata } : null;
        if (next && preservedYoutube && !('youtube' in next)) {
          next['youtube'] = { ...preservedYoutube };
        }
        return next;
      });
    } catch (error) {
      if (metadataLookupIdRef.current !== requestId) {
        return;
      }
      const message = error instanceof Error ? error.message : 'Unable to lookup TV metadata.';
      setMetadataError(message);
      setMetadataPreview(null);
      setMediaMetadataDraft(null);
    } finally {
      if (metadataLookupIdRef.current === requestId) {
        setMetadataLoading(false);
      }
    }
  }, []);

  const performYoutubeMetadataLookup = useCallback(
    async (sourceName: string, force: boolean) => {
      const normalized = sourceName.trim();
      if (!normalized) {
        setYoutubeMetadataPreview(null);
        setYoutubeMetadataError(null);
        setYoutubeMetadataLoading(false);
        updateMediaMetadataDraft((draft) => {
          delete draft['youtube'];
        });
        return;
      }

      const requestId = youtubeLookupIdRef.current + 1;
      youtubeLookupIdRef.current = requestId;
      setYoutubeMetadataLoading(true);
      setYoutubeMetadataError(null);
      try {
        const payload = await lookupYoutubeVideoMetadataPreview({ source_name: normalized, force });
        if (youtubeLookupIdRef.current !== requestId) {
          return;
        }
        setYoutubeMetadataPreview(payload);
        if (payload.youtube_metadata) {
          updateMediaMetadataDraft((draft) => {
            draft['youtube'] = { ...payload.youtube_metadata };
          });
        } else {
          updateMediaMetadataDraft((draft) => {
            delete draft['youtube'];
          });
        }
      } catch (error) {
        if (youtubeLookupIdRef.current !== requestId) {
          return;
        }
        const message = error instanceof Error ? error.message : 'Unable to lookup YouTube metadata.';
        setYoutubeMetadataError(message);
        setYoutubeMetadataPreview(null);
        updateMediaMetadataDraft((draft) => {
          delete draft['youtube'];
        });
      } finally {
        if (youtubeLookupIdRef.current === requestId) {
          setYoutubeMetadataLoading(false);
        }
      }
    },
    [updateMediaMetadataDraft]
  );

  useEffect(() => {
    const normalized = metadataSourceName.trim();
    setMetadataLookupSourceName(normalized);
    setYoutubeLookupSourceName(normalized);
    if (!normalized) {
      setMetadataPreview(null);
      setMediaMetadataDraft(null);
      setMetadataError(null);
      setMetadataLoading(false);
      setYoutubeMetadataPreview(null);
      setYoutubeMetadataError(null);
      setYoutubeMetadataLoading(false);
      return;
    }
    void performMetadataLookup(normalized, false);
  }, [metadataSourceName, performMetadataLookup]);

  useEffect(() => {
    if (activeTab !== 'metadata' || metadataSection !== 'youtube') {
      return;
    }
    const normalized = youtubeLookupSourceName.trim();
    if (!normalized) {
      return;
    }
    const youtube = mediaMetadataDraft ? coerceRecord(mediaMetadataDraft['youtube']) : null;
    const hasTitle = youtube && typeof youtube['title'] === 'string' && (youtube['title'] as string).trim();
    if (hasTitle) {
      return;
    }
    if (youtubeMetadataLoading) {
      return;
    }
    void performYoutubeMetadataLookup(normalized, false);
  }, [
    activeTab,
    mediaMetadataDraft,
    metadataSection,
    performYoutubeMetadataLookup,
    youtubeLookupSourceName,
    youtubeMetadataLoading
  ]);
  const languageOptions = useMemo(
    () =>
      buildLanguageOptions({
        fetchedLanguages,
        preferredLanguages: [targetLanguage, subtitleLanguageLabel, primaryTargetLanguage]
      }),
    [fetchedLanguages, primaryTargetLanguage, subtitleLanguageLabel, targetLanguage]
  );
  const sortedLanguageOptions = useMemo(() => sortLanguageLabelsByName(languageOptions), [languageOptions]);
  const canExtractEmbedded = useMemo(() => {
    if (!selectedVideo) {
      return false;
    }
    const lower = selectedVideo.path.toLowerCase();
    return lower.endsWith('.mkv') || lower.endsWith('.mp4') || lower.endsWith('.mov') || lower.endsWith('.m4v');
  }, [selectedVideo]);
  const extractableStreams = useMemo(
    () => availableSubtitleStreams.filter((stream) => stream.can_extract),
    [availableSubtitleStreams]
  );
  const targetLanguageCode = useMemo(() => {
    const preferredLabel = preferLanguageLabel([targetLanguage, subtitleLanguageLabel, primaryTargetLanguage]);
    const fallback = subtitleLanguageCode || '';
    return resolveLanguageCode(preferredLabel || fallback);
  }, [primaryTargetLanguage, subtitleLanguageCode, subtitleLanguageLabel, targetLanguage]);

  const handleRefresh = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    setStatusMessage(null);
    try {
      const response = await fetchYoutubeLibrary(baseDir.trim() || undefined);
      setLibrary(response);
      setBaseDir(response.base_dir || baseDir);
      if (response.videos.length > 0) {
        const prefilledVideoPath =
          prefillParameters?.input_file && typeof prefillParameters.input_file === 'string'
            ? prefillParameters.input_file.trim()
            : prefillParameters?.video_path && typeof prefillParameters.video_path === 'string'
              ? prefillParameters.video_path.trim()
              : null;
        const prefilledSubtitlePath =
          prefillParameters?.subtitle_path && typeof prefillParameters.subtitle_path === 'string'
            ? prefillParameters.subtitle_path.trim()
            : null;
        const previousSelectedVideoPath = prefilledVideoPath || selectedVideoPathRef.current;
        const previousSelectedSubtitlePath = prefilledSubtitlePath || selectedSubtitlePathRef.current;
        const nextVideo =
          response.videos.find((video) => video.path === previousSelectedVideoPath) ?? response.videos[0];
        setSelectedVideoPath(nextVideo.path);
        const subtitleCandidates = nextVideo.subtitles.filter((sub) =>
          ['ass', 'srt', 'vtt', 'sub'].includes(sub.format.toLowerCase())
        );
        const keepExistingSubtitle =
          previousSelectedVideoPath === nextVideo.path &&
          !!previousSelectedSubtitlePath &&
          subtitleCandidates.some((sub) => sub.path === previousSelectedSubtitlePath);
        const resolvedSubtitle = keepExistingSubtitle
          ? subtitleCandidates.find((sub) => sub.path === previousSelectedSubtitlePath) ?? null
          : resolveDefaultSubtitle(nextVideo) ?? subtitleCandidates[0] ?? null;
        setSelectedSubtitlePath(resolvedSubtitle?.path ?? null);
        ensureTargetLanguage(resolvedSubtitle?.language);
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
      let fallbackLanguage: string | null = null;
      try {
        await deleteYoutubeVideo({ video_path: video.path });
        let nextSelectedPath = selectedVideoPath;
        let nextSubtitle = selectedSubtitlePath;
        setLibrary((prev) => {
          if (!prev) {
            return prev;
          }
          const remaining = prev.videos.filter((entry) => entry.path !== video.path);
          if (nextSelectedPath === video.path) {
            const fallback = remaining[0];
            nextSelectedPath = fallback ? fallback.path : null;
            const resolvedFallback = fallback ? resolveDefaultSubtitle(fallback) : null;
            fallbackLanguage = resolvedFallback?.language ?? null;
            nextSubtitle = resolvedFallback?.path ?? null;
          }
          return { ...prev, videos: remaining };
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
    let cancelled = false;
    const loadDefaults = async () => {
      try {
        const defaults = await fetchPipelineDefaults();
        if (cancelled) {
          return;
        }
        const config = defaults?.config ?? {};
        const targetLanguages = Array.isArray(config['target_languages'])
          ? (config['target_languages'] as unknown[])
          : [];
        const normalised = targetLanguages
          .map((language) => (typeof language === 'string' ? normalizeLanguageLabel(language) : ''))
          .filter((language) => language.length > 0);
        if (normalised.length > 0) {
          setFetchedLanguages(normalised);
          if (!primaryTargetLanguage) {
            setPrimaryTargetLanguage(normalised[0]);
          }
        }
      } catch (error) {
        console.warn('Unable to load pipeline defaults for dubbing languages', error);
      }
    };

    void loadDefaults();
    return () => {
      cancelled = true;
    };
  }, [primaryTargetLanguage, setPrimaryTargetLanguage]);

  useEffect(() => {
    if (targetLanguage) {
      return;
    }
    const fallback = preferLanguageLabel([subtitleLanguageLabel, primaryTargetLanguage, languageOptions[0]]);
    if (fallback) {
      applyTargetLanguage(fallback);
    }
  }, [applyTargetLanguage, languageOptions, primaryTargetLanguage, subtitleLanguageLabel, targetLanguage]);

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
    if (!prefillParameters) {
      return;
    }
    if (prefillParameters.input_file && typeof prefillParameters.input_file === 'string') {
      setSelectedVideoPath(prefillParameters.input_file.trim());
    } else if (prefillParameters.video_path && typeof prefillParameters.video_path === 'string') {
      setSelectedVideoPath(prefillParameters.video_path.trim());
    }
    if (prefillParameters.subtitle_path && typeof prefillParameters.subtitle_path === 'string') {
      setSelectedSubtitlePath(prefillParameters.subtitle_path.trim());
    }
    const targets = Array.isArray(prefillParameters.target_languages)
      ? prefillParameters.target_languages
          .map((entry) => (typeof entry === 'string' ? entry.trim() : ''))
          .filter((entry) => entry.length > 0)
      : [];
    if (targets.length > 0) {
      applyTargetLanguage(targets[0]);
    }
    if (prefillParameters.selected_voice && typeof prefillParameters.selected_voice === 'string') {
      setVoice(prefillParameters.selected_voice.trim());
    }
    if (
      typeof prefillParameters.start_time_offset_seconds === 'number' &&
      Number.isFinite(prefillParameters.start_time_offset_seconds)
    ) {
      setStartOffset(formatOffsetLabel(prefillParameters.start_time_offset_seconds));
    }
    if (
      typeof prefillParameters.end_time_offset_seconds === 'number' &&
      Number.isFinite(prefillParameters.end_time_offset_seconds)
    ) {
      setEndOffset(formatOffsetLabel(prefillParameters.end_time_offset_seconds));
    }
    if (
      typeof prefillParameters.original_mix_percent === 'number' &&
      Number.isFinite(prefillParameters.original_mix_percent)
    ) {
      setOriginalMixPercent(prefillParameters.original_mix_percent);
    } else {
      setOriginalMixPercent(5);
    }
    if (
      typeof prefillParameters.flush_sentences === 'number' &&
      Number.isFinite(prefillParameters.flush_sentences)
    ) {
      setFlushSentences(prefillParameters.flush_sentences);
    }
    if (
      typeof prefillParameters.translation_batch_size === 'number' &&
      Number.isFinite(prefillParameters.translation_batch_size)
    ) {
      setTranslationBatchSize(prefillParameters.translation_batch_size);
    }
    if (
      typeof prefillParameters.target_height === 'number' &&
      Number.isFinite(prefillParameters.target_height)
    ) {
      setTargetHeight(prefillParameters.target_height);
    } else {
      setTargetHeight(480);
    }
    if (typeof prefillParameters.preserve_aspect_ratio === 'boolean') {
      setPreserveAspectRatio(prefillParameters.preserve_aspect_ratio);
    } else {
      setPreserveAspectRatio(true);
    }
    if (typeof prefillParameters.split_batches === 'boolean') {
      setSplitBatches(prefillParameters.split_batches);
    } else {
      setSplitBatches(true);
    }
    if (prefillParameters.llm_model && typeof prefillParameters.llm_model === 'string') {
      setLlmModel(prefillParameters.llm_model.trim());
    }
    if (prefillParameters.translation_provider && typeof prefillParameters.translation_provider === 'string') {
      setTranslationProvider(prefillParameters.translation_provider.trim());
    }
    if (prefillParameters.transliteration_mode && typeof prefillParameters.transliteration_mode === 'string') {
      setTransliterationMode(prefillParameters.transliteration_mode.trim());
    }
    if (prefillParameters.transliteration_model && typeof prefillParameters.transliteration_model === 'string') {
      setTransliterationModel(prefillParameters.transliteration_model.trim());
    }
    if (typeof prefillParameters.include_transliteration === 'boolean') {
      setIncludeTransliteration(prefillParameters.include_transliteration);
    } else {
      setIncludeTransliteration(true);
    }
  }, [applyTargetLanguage, formatOffsetLabel, prefillParameters]);

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

  const resolveDefaultStreamLanguages = useCallback((streams: YoutubeInlineSubtitleStream[]): Set<string> => {
    const extractable = streams.filter((stream) => stream.can_extract);
    const next = new Set<string>();
    const english = extractable.find(
      (stream) => (stream.language ?? '').toLowerCase().startsWith('en') && stream.language
    );
    if (english?.language) {
      next.add(english.language);
    } else if (extractable.length === 1 && extractable[0].language) {
      next.add(extractable[0].language);
    }
    return next;
  }, []);

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
        setStatusMessage(
          count > 0
            ? `Extracted ${count} subtitle ${count === 1 ? 'track' : 'tracks'} from ${selectedVideo.filename}.`
            : 'No subtitle streams found to extract.'
        );
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

  const handleClearTvMetadata = useCallback(async () => {
    // Clear frontend state first
    setMetadataPreview(null);
    setMediaMetadataDraft(null);
    setMetadataError(null);

    // Clear backend cache for a fresh lookup
    const query = metadataLookupSourceName.trim();
    if (query) {
      try {
        await clearTvMetadataCache(query);
      } catch {
        // Ignore cache clear failures - frontend state is already cleared
      }
    }
  }, [metadataLookupSourceName]);

  const handleClearYoutubeMetadata = useCallback(async () => {
    // Clear frontend state first
    setYoutubeMetadataPreview(null);
    setYoutubeMetadataError(null);
    updateMediaMetadataDraft((draft) => {
      delete draft['youtube'];
    });

    // Clear backend cache for a fresh lookup
    const query = metadataLookupSourceName.trim();
    if (query) {
      try {
        await clearYoutubeMetadataCache(query);
      } catch {
        // Ignore cache clear failures - frontend state is already cleared
      }
    }
  }, [metadataLookupSourceName, updateMediaMetadataDraft]);

  const handleGenerate = useCallback(async () => {
    if (!selectedVideo || !selectedSubtitle) {
      setGenerateError('Choose a video and an ASS subtitle before generating audio.');
      return;
    }
    let parsedStart = 0;
    let parsedEnd: number | undefined;
    try {
      parsedStart = parseOffsetSeconds(startOffset);
      parsedEnd = endOffset.trim() ? parseOffsetSeconds(endOffset) : undefined;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Offsets must be in seconds or HH:MM:SS format.';
      setGenerateError(message);
      return;
    }
    if (parsedEnd !== undefined && parsedEnd <= parsedStart) {
      setGenerateError('End offset must be greater than start offset.');
      return;
    }
    setIsGenerating(true);
    setGenerateError(null);
    setStatusMessage(null);
    try {
      const response = await generateYoutubeDub({
        video_path: selectedVideo.path,
        subtitle_path: selectedSubtitle.path,
        media_metadata: mediaMetadataDraft ?? undefined,
        source_language: subtitleLanguageLabel || subtitleLanguageCode || undefined,
        target_language: targetLanguageCode || undefined,
        voice: voice.trim() || 'gTTS',
        start_time_offset: startOffset.trim() || undefined,
        end_time_offset: endOffset.trim() || undefined,
        original_mix_percent: originalMixPercent,
        flush_sentences: flushSentences,
        llm_model: llmModel || undefined,
        translation_provider: translationProvider || undefined,
        translation_batch_size: translationBatchSize,
        transliteration_mode: transliterationMode || undefined,
        transliteration_model: transliterationModel || undefined,
        split_batches: splitBatches,
        stitch_batches: stitchBatches,
        include_transliteration: includeTransliteration,
        target_height: targetHeight,
        preserve_aspect_ratio: preserveAspectRatio
      });
      setStatusMessage(`Dub job submitted as ${response.job_id}. Track progress below.`);
      onJobCreated(response.job_id);
      setActiveTab('jobs');
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
    mediaMetadataDraft,
    onJobCreated,
    parseOffsetSeconds
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
    if (!selectedVideo) {
      return 'Select a video to see subtitles.';
    }
    if (playableSubtitles.length === 0) {
      return 'No subtitles were found next to this video.';
    }
    return null;
  }, [playableSubtitles, selectedVideo]);

  const availableVoiceOptions = useMemo(() => {
    const base = VOICE_OPTIONS.map((option) => ({
      value: option.value,
      label: option.label
    }));
    if (!voiceInventory) {
      return base;
    }
    const targetCode = (targetLanguageCode || '').toLowerCase();
    const macVoices = voiceInventory.macos
      .filter((voice) => {
        if (!targetCode) {
          return true;
        }
        return voice.lang.toLowerCase().startsWith(targetCode);
      })
      .map((voice) => ({
        value: formatMacOSVoiceIdentifier(voice),
        label: formatMacOSVoiceLabel(voice)
      }));
    const merged = new Map<string, { value: string; label: string }>();
    [...base, ...macVoices].forEach((entry) => merged.set(entry.value, entry));
    return Array.from(merged.values()).sort((a, b) => a.label.localeCompare(b.label));
  }, [targetLanguageCode, voiceInventory]);

  const canGenerate = Boolean(selectedVideo && selectedSubtitle && !isGenerating);

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
