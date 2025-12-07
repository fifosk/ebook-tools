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
  fetchPipelineDefaults,
  deleteYoutubeVideo
} from '../api/client';
import type {
  YoutubeNasLibraryResponse,
  YoutubeNasVideo,
  YoutubeNasSubtitle,
  YoutubeInlineSubtitleStream,
  VoiceInventoryResponse,
  JobParameterSnapshot
} from '../api/dtos';
import type { MacOSVoice } from '../api/dtos';
import type { JobState } from '../components/JobList';
import { VOICE_OPTIONS } from '../constants/menuOptions';
import { resolveLanguageName } from '../constants/languageCodes';
import { useLanguagePreferences } from '../context/LanguageProvider';
import {
  buildLanguageOptions,
  normalizeLanguageLabel,
  preferLanguageLabel,
  resolveLanguageCode
} from '../utils/languages';
import { subtitleLanguageDetail } from '../utils/subtitles';
import styles from './YoutubeDubPage.module.css';

const DEFAULT_VIDEO_DIR = '/Volumes/Data/Download/DStation';
const DEFAULT_LLM_MODEL = 'kimi-k2:1t-cloud';
const RESOLUTION_OPTIONS = [
  { value: 320, label: '320p (lighter)' },
  { value: 480, label: '480p (default)' },
  { value: 720, label: '720p' }
];

type Props = {
  jobs: JobState[];
  onJobCreated: (jobId: string) => void;
  onSelectJob: (jobId: string) => void;
  onOpenJobMedia?: (jobId: string) => void;
  prefillParameters?: JobParameterSnapshot | null;
};

function formatMacOSVoiceIdentifier(voice: MacOSVoice): string {
  const quality = voice.quality ? voice.quality : 'Default';
  const genderSuffix = voice.gender ? ` - ${voice.gender}` : '';
  return `${voice.name} - ${voice.lang} - (${quality})${genderSuffix}`;
}

function formatMacOSVoiceLabel(voice: MacOSVoice): string {
  const descriptors: string[] = [voice.lang];
  if (voice.gender) {
    descriptors.push(voice.gender);
  }
  if (voice.quality) {
    descriptors.push(voice.quality);
  }
  const meta = descriptors.length > 0 ? ` (${descriptors.join(', ')})` : '';
  return `${voice.name}${meta}`;
}

function sampleSentenceFor(languageCode: string, fallbackLabel: string): string {
  const resolvedName = resolveLanguageName(languageCode) ?? fallbackLabel ?? '';
  const display = resolvedName || 'this language';
  return `Sample narration for ${display}.`;
}

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return '0 B';
  }
  const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB'];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  const precision = size >= 10 || unitIndex === 0 ? 0 : 1;
  return `${size.toFixed(precision)} ${units[unitIndex]}`;
}

function formatDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function formatDateShort(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleDateString();
}

function subtitleLabel(sub: YoutubeNasSubtitle): string {
  const language = sub.language ? `(${sub.language})` : '';
  return `${sub.format.toUpperCase()} ${language}`.trim();
}

function subtitleStreamLabel(stream: YoutubeInlineSubtitleStream): string {
  const normalized = stream.language ? stream.language : '';
  const friendlyName = normalized ? resolveLanguageName(normalized) || normalized : 'Unknown language';
  const titleSuffix = stream.title ? ` – ${stream.title}` : '';
  return `${friendlyName}${titleSuffix}`;
}

function videoSourceLabel(video: YoutubeNasVideo): string {
  const source = (video.source || '').toLowerCase();
  if (source === 'nas_video') {
    return 'NAS video';
  }
  if (source === 'youtube') {
    return 'YouTube download';
  }
  if (!source) {
    return 'YouTube download';
  }
  return source.charAt(0).toUpperCase() + source.slice(1);
}

function videoSourceBadge(video: YoutubeNasVideo): { icon: string; label: string; title: string } {
  const source = (video.source || '').toLowerCase();
  if (source === 'nas_video') {
    return { icon: '🗃', label: 'NAS', title: 'NAS video' };
  }
  if (source === 'youtube') {
    return { icon: '📺', label: 'YT', title: 'YouTube download' };
  }
  return { icon: '📦', label: 'SRC', title: videoSourceLabel(video) };
}

function resolveDefaultSubtitle(video: YoutubeNasVideo | null): YoutubeNasSubtitle | null {
  if (!video) {
    return null;
  }
  const candidates = video.subtitles.filter((sub) => ['ass', 'srt', 'vtt', 'sub'].includes(sub.format.toLowerCase()));
  if (!candidates.length) {
    return null;
  }
  const english = candidates.find((sub) => (sub.language ?? '').toLowerCase().startsWith('en'));
  return english ?? candidates[0];
}

function resolveOutputPath(job: JobState): string | null {
  const generated = job.status.generated_files;
  if (generated && typeof generated === 'object') {
    const record = generated as Record<string, unknown>;
    const files = record['files'];
    if (Array.isArray(files)) {
      for (const entry of files) {
        if (!entry || typeof entry !== 'object') {
          continue;
        }
        const file = entry as Record<string, unknown>;
        if (typeof file.path === 'string' && file.path.trim()) {
          return file.path.trim();
        }
      }
    }
  }
  const result = job.status.result;
  if (result && typeof result === 'object') {
    const section = (result as Record<string, unknown>)['youtube_dub'];
    if (section && typeof section === 'object' && typeof (section as Record<string, unknown>).output_path === 'string') {
      const pathValue = (section as Record<string, unknown>).output_path as string;
      return pathValue.trim() || null;
    }
  }
  return null;
}

function formatJobLabel(job: JobState): string {
  const parameters = job.status.parameters;
  const languages = parameters?.target_languages ?? [];
  const target = Array.isArray(languages) && languages.length > 0 ? languages[0] : null;
  if (typeof target === 'string' && target.trim()) {
    return target.trim();
  }
  const videoPath = parameters?.video_path ?? parameters?.input_file;
  if (videoPath && typeof videoPath === 'string' && videoPath.trim()) {
    const parts = videoPath.split('/');
    return parts[parts.length - 1] || videoPath;
  }
  return job.jobId;
}

export default function YoutubeDubPage({
  jobs,
  onJobCreated,
  onSelectJob,
  onOpenJobMedia,
  prefillParameters = null
}: Props) {
  const { primaryTargetLanguage, setPrimaryTargetLanguage } = useLanguagePreferences();
  const [baseDir, setBaseDir] = useState(DEFAULT_VIDEO_DIR);
  const [library, setLibrary] = useState<YoutubeNasLibraryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selectedVideoPath, setSelectedVideoPath] = useState<string | null>(null);
  const [selectedSubtitlePath, setSelectedSubtitlePath] = useState<string | null>(null);

  const [voice, setVoice] = useState('gTTS');
  const [targetLanguage, setTargetLanguage] = useState<string>(
    normalizeLanguageLabel(primaryTargetLanguage ?? '')
  );
  const [fetchedLanguages, setFetchedLanguages] = useState<string[]>([]);
  const [startOffset, setStartOffset] = useState('');
  const [endOffset, setEndOffset] = useState('');
  const [originalMixPercent, setOriginalMixPercent] = useState(5);
  const [flushSentences, setFlushSentences] = useState(10);
  const [targetHeight, setTargetHeight] = useState(480);
  const [preserveAspectRatio, setPreserveAspectRatio] = useState(true);
  const [llmModel, setLlmModel] = useState(DEFAULT_LLM_MODEL);
  const [splitBatches, setSplitBatches] = useState(true);
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

  const parseOffset = useCallback((value: string): number => {
    const trimmed = value.trim();
    if (!trimmed) {
      return 0;
    }
    const segments = trimmed.split(':');
    const parseNumber = (token: string) => {
      if (!/^\d+(\.\d+)?$/.test(token)) {
        throw new Error('Offsets must be numbers or timecodes like HH:MM:SS');
      }
      return parseFloat(token);
    };
    if (segments.length === 1) {
      const seconds = parseNumber(segments[0]);
      if (seconds < 0) throw new Error('Offsets must be non-negative');
      return seconds;
    }
    if (segments.length > 3) {
      throw new Error('Use MM:SS or HH:MM:SS for timecodes');
    }
    const [hStr, mStr, sStr] =
      segments.length === 3 ? segments : ['0', segments[0], segments[1]];
    const hours = parseNumber(hStr);
    const minutes = parseNumber(mStr);
    const seconds = parseNumber(sStr);
    if (minutes >= 60 || seconds >= 60) {
      throw new Error('Minutes and seconds must be between 0 and 59');
    }
    return hours * 3600 + minutes * 60 + seconds;
  }, []);

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
  const formatOffset = useCallback((value: number | null | undefined): string => {
    if (value === null || value === undefined || !Number.isFinite(value) || value < 0) {
      return '';
    }
    const totalSeconds = Math.floor(value);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    if (hours > 0) {
      return [hours, minutes, seconds].map((component) => component.toString().padStart(2, '0')).join(':');
    }
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }, []);

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
    () => normalizeLanguageLabel(selectedSubtitle?.language ?? ''),
    [selectedSubtitle]
  );
  const languageOptions = useMemo(
    () =>
      buildLanguageOptions({
        fetchedLanguages,
        preferredLanguages: [targetLanguage, subtitleLanguageLabel, primaryTargetLanguage]
      }),
    [fetchedLanguages, primaryTargetLanguage, subtitleLanguageLabel, targetLanguage]
  );
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
    const fallback = selectedSubtitle?.language ?? '';
    return resolveLanguageCode(preferredLabel || fallback);
  }, [primaryTargetLanguage, selectedSubtitle, subtitleLanguageLabel, targetLanguage]);

  const handleRefresh = useCallback(async () => {
    setIsLoading(true);
      setLoadError(null);
      setStatusMessage(null);
      try {
        const response = await fetchYoutubeLibrary(baseDir.trim() || undefined);
        setLibrary(response);
        setBaseDir(response.base_dir || baseDir);
        if (response.videos.length > 0) {
          const existingSelection = response.videos.find((video) => video.path === selectedVideoPath);
          const nextVideo = existingSelection ?? response.videos[0];
          setSelectedVideoPath(nextVideo.path);
          const defaultSubtitle = resolveDefaultSubtitle(nextVideo);
          setSelectedSubtitlePath(defaultSubtitle?.path ?? null);
          ensureTargetLanguage(defaultSubtitle?.language);
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
  }, [baseDir, ensureTargetLanguage, selectedVideoPath]);

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
  }, [handleRefresh]);

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
      setStartOffset(formatOffset(prefillParameters.start_time_offset_seconds));
    }
    if (
      typeof prefillParameters.end_time_offset_seconds === 'number' &&
      Number.isFinite(prefillParameters.end_time_offset_seconds)
    ) {
      setEndOffset(formatOffset(prefillParameters.end_time_offset_seconds));
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
    if (typeof prefillParameters.include_transliteration === 'boolean') {
      setIncludeTransliteration(prefillParameters.include_transliteration);
    } else {
      setIncludeTransliteration(true);
    }
  }, [applyTargetLanguage, formatOffset, prefillParameters]);

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

  const handleGenerate = useCallback(async () => {
    if (!selectedVideo || !selectedSubtitle) {
      setGenerateError('Choose a video and an ASS subtitle before generating audio.');
      return;
    }
    let parsedStart = 0;
    let parsedEnd: number | undefined;
    try {
      parsedStart = parseOffset(startOffset);
      parsedEnd = endOffset.trim() ? parseOffset(endOffset) : undefined;
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
        target_language: targetLanguageCode || undefined,
        voice: voice.trim() || 'gTTS',
        start_time_offset: startOffset.trim() || undefined,
        end_time_offset: endOffset.trim() || undefined,
        original_mix_percent: originalMixPercent,
        flush_sentences: flushSentences,
        llm_model: llmModel || undefined,
        split_batches: splitBatches,
        include_transliteration: includeTransliteration,
        target_height: targetHeight,
        preserve_aspect_ratio: preserveAspectRatio
      });
      setStatusMessage(`Dub job submitted as ${response.job_id}. Track progress below.`);
      onJobCreated(response.job_id);
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
    targetLanguageCode,
    voice,
    startOffset,
    endOffset,
    originalMixPercent,
    flushSentences,
    llmModel,
    splitBatches,
    includeTransliteration,
    targetHeight,
    preserveAspectRatio,
    onJobCreated,
    parseOffset
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
      <div>
        <p className={styles.kicker}>NAS dubbing</p>
        <h1 className={styles.title}>Dub downloaded videos from subtitles</h1>
        <p className={styles.subtitle}>
          Pick a downloaded YouTube video or a generic NAS video (MP4/MKV), pair it with ASS/SRT/SUB subtitles in the same folder, and render a dubbed track aligned to that timing.
        </p>
      </div>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Discovered videos</h2>
            <p className={styles.cardHint}>
              Base path: <code>{baseDir}</code>
            </p>
          </div>
          <div className={styles.controlRow}>
            <input
              className={styles.input}
              value={baseDir}
              onChange={(event) => setBaseDir(event.target.value)}
              placeholder="NAS directory"
              aria-label="YouTube NAS directory"
            />
            <button className={styles.secondaryButton} type="button" onClick={() => void handleRefresh()} disabled={isLoading}>
              {isLoading ? 'Refreshing…' : 'Refresh'}
            </button>
          </div>
        </div>
        {loadError ? <p className={styles.error}>{loadError}</p> : null}
        {isLoading && videos.length === 0 ? <p className={styles.status}>Loading videos…</p> : null}
        {!isLoading && videos.length === 0 ? (
          <p className={styles.status}>No downloaded videos found in this directory.</p>
        ) : null}
        <div className={styles.videoList}>
          {videos.map((video) => {
            const isActive = video.path === selectedVideoPath;
            const sourceBadge = videoSourceBadge(video);
            const hasLinkedJobs = (video.linked_job_ids ?? []).length > 0;
            const disableDelete = hasLinkedJobs || deletingVideoPath === video.path;
            const jobTitle = hasLinkedJobs
              ? `Linked jobs: ${(video.linked_job_ids ?? []).join(', ')}`
              : 'Delete downloaded video';
            return (
              <label key={video.path} className={`${styles.videoOption} ${isActive ? styles.videoOptionActive : ''}`}>
                <input
                  type="radio"
                  name="video"
                  value={video.path}
                  checked={isActive}
                  onChange={() => handleSelectVideo(video)}
                />
                <div className={styles.videoContent}>
                  <div className={styles.videoTitle}>{video.filename}</div>
                  <div className={styles.videoMeta}>
                    <span
                      className={`${styles.pill} ${styles.pillMeta} ${styles.pillSource}`}
                      title={`${sourceBadge.title} · ${video.folder || video.path}`}
                    >
                      <span aria-hidden="true">{sourceBadge.icon}</span>
                      <span>{sourceBadge.label}</span>
                    </span>
                    <span
                      className={`${styles.pill} ${styles.pillMeta}`}
                      title={`Size: ${formatBytes(video.size_bytes)}`}
                    >
                      <span aria-hidden="true">💾</span>
                      <span>{formatBytes(video.size_bytes)}</span>
                    </span>
                    <span
                      className={`${styles.pill} ${styles.pillMeta}`}
                      title={`Modified: ${formatDate(video.modified_at)}`}
                    >
                      <span aria-hidden="true">🕒</span>
                      <span>{formatDateShort(video.modified_at)}</span>
                    </span>
                    {hasLinkedJobs ? (
                      <span
                        className={`${styles.pill} ${styles.pillWarning}`}
                        title={`Linked jobs: ${(video.linked_job_ids ?? []).join(', ')}`}
                      >
                        🔗 {video.linked_job_ids?.length ?? 0} job
                        {(video.linked_job_ids?.length ?? 0) === 1 ? '' : 's'}
                      </span>
                    ) : null}
                  </div>
                  <div className={styles.subtitleRow} aria-label="Available subtitles">
                    {video.subtitles.length === 0 ? (
                      <span className={`${styles.pill} ${styles.pillMuted}`}>No subtitles</span>
                    ) : (
                      video.subtitles.map((sub) => (
                        <span
                          key={sub.path}
                          className={`${styles.pill} ${
                            sub.format.toLowerCase() === 'ass' ? styles.pillAss : styles.pillMuted
                          }`}
                        >
                          {subtitleLabel(sub)}
                        </span>
                      ))
                    )}
                  </div>
                  {isActive ? (
                    <div className={styles.nestedSubtitleCard} aria-label="Subtitle selection">
                      <div className={styles.nestedHeader}>
                        <h3 className={styles.cardTitle}>Subtitle selection</h3>
                        <p className={styles.cardHint}>Pick a nearby subtitle file or extract embedded tracks before dubbing.</p>
                      </div>
                      <div>
                        <h4 className={styles.sectionTitle}>Choose subtitle</h4>
                        {subtitleNotice ? <p className={styles.status}>{subtitleNotice}</p> : null}
                        <div className={styles.subtitleList}>
                          {playableSubtitles.map((sub) => {
                            const isDeleting = deletingSubtitlePath === sub.path;
                            return (
                              <div
                                key={sub.path}
                                className={`${styles.subtitleCard} ${selectedSubtitlePath === sub.path ? styles.subtitleCardActive : ''}`}
                              >
                                <label className={styles.subtitleChoice}>
                                  <input
                                    type="radio"
                                    name="subtitle"
                                    value={sub.path}
                                    checked={selectedSubtitlePath === sub.path}
                                    disabled={Boolean(deletingSubtitlePath)}
                                    onChange={() => handleSelectSubtitle(sub.path)}
                                  />
                                  <div className={styles.subtitleBody}>
                                    <div className={styles.subtitleHeaderRow}>
                                      <div className={styles.subtitleName}>{sub.filename}</div>
                                      <div className={styles.subtitleBadges} aria-label="Subtitle details">
                                        <span className={`${styles.pill} ${styles.pillFormat}`}>
                                          {sub.format.toUpperCase()}
                                        </span>
                                        <span className={`${styles.pill} ${styles.pillMuted}`}>
                                          {subtitleLanguageDetail(sub.language)}
                                        </span>
                                      </div>
                                    </div>
                                </div>
                              </label>
                              <div className={styles.subtitleActions}>
                                <button
                                  type="button"
                                  className={styles.dangerButton}
                                  onClick={() => void handleDeleteSubtitle(sub)}
                                  disabled={Boolean(deletingSubtitlePath) || isExtractingSubtitles}
                                  title={`Delete ${sub.filename}`}
                                  aria-label={`Delete ${sub.filename}`}
                                >
                                  {isDeleting ? '…' : '🗑'}
                                </button>
                              </div>
                            </div>
                            );
                          })}
                        </div>
                        {isChoosingStreams && extractableStreams.length > 0 ? (
                          <div className={styles.streamChooser}>
                            <div className={styles.streamHeader}>
                              <div className={styles.streamTitle}>Select which tracks to extract</div>
                              <p className={styles.streamHint}>Default selection prefers English when present.</p>
                            </div>
                            <div className={styles.streamList}>
                              {availableSubtitleStreams.map((stream) => {
                                const language = stream.language ?? '';
                                const selected = language ? selectedStreamLanguages.has(language) : false;
                                const disabled = !stream.can_extract || !language || isExtractingSubtitles;
                                return (
                                  <label key={`${stream.index}-${language || 'unknown'}`} className={styles.streamItem}>
                                    <input
                                      type="checkbox"
                                      disabled={disabled}
                                      checked={selected}
                                      onChange={(event) => handleToggleSubtitleStream(language, event.target.checked)}
                                    />
                                    <div className={styles.streamBody}>
                                      <div className={styles.streamLabel}>{subtitleStreamLabel(stream)}</div>
                                      <div className={styles.streamMeta}>
                                        <span>Stream #{stream.index}</span>
                                        <span aria-hidden="true">·</span>
                                        <span>{language || 'No language tag'}</span>
                                        {stream.codec ? <span className={styles.streamBadge}>{stream.codec}</span> : null}
                                        {!stream.can_extract ? (
                                          <span className={`${styles.streamBadge} ${styles.streamBadgeMuted}`}>Image-based</span>
                                        ) : null}
                                      </div>
                                      {!stream.can_extract ? (
                                        <p className={styles.streamHint}>Image-based subtitles (e.g. PGS/VobSub) need OCR.</p>
                                      ) : null}
                                      {!language ? (
                                        <p className={styles.streamHint}>
                                          No language tag detected; choose a tagged stream or extract all tracks.
                                        </p>
                                      ) : null}
                                    </div>
                                  </label>
                                );
                              })}
                            </div>
                            <div className={styles.streamActions}>
                              <button
                                className={styles.primaryButton}
                                type="button"
                                onClick={() => void handleConfirmSubtitleStreams()}
                                disabled={isExtractingSubtitles}
                              >
                                {isExtractingSubtitles ? 'Extracting…' : 'Extract selected tracks'}
                              </button>
                              <button
                                className={styles.secondaryButton}
                                type="button"
                                onClick={() => {
                                  setIsChoosingStreams(false);
                                  setAvailableSubtitleStreams([]);
                                }}
                                disabled={isExtractingSubtitles}
                              >
                                Cancel
                              </button>
                              <button
                                className={styles.secondaryButton}
                                type="button"
                                onClick={() => void performSubtitleExtraction(undefined)}
                                disabled={isExtractingSubtitles}
                              >
                                Extract all text tracks
                              </button>
                            </div>
                          </div>
                        ) : null}
                        <p className={styles.fieldHint}>
                          Pulls subtitle streams from the selected video (writes .srt files next to it).
                        </p>
                        {extractError ? <p className={styles.error}>{extractError}</p> : null}
                      </div>
                    </div>
                  ) : null}
                  <div className={styles.videoActions}>
                    <button
                      type="button"
                      className={`${styles.pill} ${styles.pillMeta} ${styles.pillAction}`}
                      onClick={(event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        if (!isActive) {
                          return;
                        }
                        void handleExtractSubtitles();
                      }}
                      disabled={
                        !isActive ||
                        !canExtractEmbedded ||
                        isExtractingSubtitles ||
                        isLoadingStreams ||
                        Boolean(deletingSubtitlePath)
                      }
                      title="Inspect and extract subtitle streams from this video"
                      aria-label="Inspect and extract subtitle streams from this video"
                    >
                      ⬇️
                    </button>
                    <button
                      type="button"
                      className={`${styles.pill} ${styles.pillMeta} ${styles.pillAction}`}
                      onClick={(event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        void handleDeleteVideo(video);
                      }}
                      disabled={disableDelete}
                      title={jobTitle}
                      aria-label={jobTitle}
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              </label>
            );
          })}
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Dubbing options</h2>
            <p className={styles.cardHint}>Translate, pick voices, and tune rendering before you submit.</p>
          </div>
        </div>
        <div className={styles.formFields}>
          <label className={styles.field}>
            <span>Translation language</span>
            <select className={styles.input} value={targetLanguage} onChange={(event) => applyTargetLanguage(event.target.value)}>
              {languageOptions.map((language) => (
                <option key={language} value={language}>
                  {language}
                </option>
              ))}
            </select>
            <p className={styles.fieldHint}>
              Matches the Subtitles page list; we will convert it to the correct language code automatically.
            </p>
          </label>
          <label className={styles.field}>
            <span>Voice / audio mode</span>
            <select
              className={styles.input}
              value={voice}
              onChange={(event) => setVoice(event.target.value)}
              disabled={availableVoiceOptions.length === 0 && isLoadingVoices}
            >
              {availableVoiceOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
              {availableVoiceOptions.length === 0 ? <option value={voice}>{voice || 'gTTS'}</option> : null}
            </select>
            <p className={styles.fieldHint}>Switch between macOS voices, gTTS, or other configured modes.</p>
          </label>
          <p className={styles.fieldHint}>
            Audio pacing follows the subtitle timing automatically for each sentence.
          </p>
          <label className={styles.field}>
            <span>Translation model</span>
            <select
              className={styles.input}
              value={llmModel}
              onChange={(event) => setLlmModel(event.target.value)}
              disabled={isLoadingModels}
            >
              {[...(llmModels.length ? llmModels : [DEFAULT_LLM_MODEL])].map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
            <p className={styles.fieldHint}>Model used when translating subtitles before TTS (defaults to kimi).</p>
            {isLoadingModels ? <p className={styles.status}>Loading models…</p> : null}
            {modelError ? <p className={styles.error}>{modelError}</p> : null}
          </label>
          <label className={styles.field}>
            <span>Target resolution</span>
            <select className={styles.input} value={targetHeight} onChange={(event) => setTargetHeight(Number(event.target.value))}>
              {RESOLUTION_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <p className={styles.fieldHint}>Downscale dubbed batches to this height (480p default for NAS playback).</p>
          </label>
          <label className={styles.fieldCheckbox}>
            <input
              type="checkbox"
              checked={preserveAspectRatio}
              onChange={(event) => setPreserveAspectRatio(event.target.checked)}
            />
            <span>Keep original aspect ratio (recommended)</span>
          </label>
          <label className={styles.field}>
            <span>Flush interval (sentences)</span>
            <div className={styles.rangeRow}>
              <input
                className={styles.input}
                type="number"
                min={1}
                step={1}
                value={flushSentences}
                onChange={(event) => setFlushSentences(Math.max(1, Number(event.target.value)))}
              />
              <span className={styles.rangeValue}>{flushSentences} sentences</span>
            </div>
            <p className={styles.fieldHint}>Write out/append the video every N sentences (default 10).</p>
          </label>
          <label className={styles.fieldCheckbox}>
            <input
              type="checkbox"
              checked={splitBatches}
              onChange={(event) => setSplitBatches(event.target.checked)}
            />
            <span>Create separate video per batch (adds start-end sentence to filename)</span>
          </label>
          <label className={styles.fieldCheckbox}>
            <input
              type="checkbox"
              checked={includeTransliteration}
              onChange={(event) => setIncludeTransliteration(event.target.checked)}
            />
            <span>Include transliteration subtitle track (default on for non-Latin targets)</span>
          </label>
          <label className={styles.field}>
            <span>Original audio mix</span>
            <div className={styles.rangeRow}>
              <input
                className={styles.rangeInput}
                type="range"
                min={0}
                max={100}
                step={5}
                value={originalMixPercent}
                onChange={(event) => setOriginalMixPercent(Number(event.target.value))}
              />
              <span className={styles.rangeValue}>{originalMixPercent}% original</span>
            </div>
            <p className={styles.fieldHint}>
              Amount of the original track to keep under the dub (default 5%).
            </p>
          </label>
          <div className={styles.field}>
            <span>Clip window (seconds)</span>
            <div className={styles.clipInputs}>
              <input
                className={styles.input}
                type="text"
                value={startOffset}
                onChange={(event) => setStartOffset(event.target.value)}
                placeholder="Start (e.g., 45 or 00:45)"
              />
              <input
                className={styles.input}
                type="text"
                value={endOffset}
                onChange={(event) => setEndOffset(event.target.value)}
                placeholder="End (e.g., 01:30)"
              />
            </div>
            <p className={styles.fieldHint}>Leave blank to dub the entire video. Use offsets to render a short slice.</p>
          </div>
        </div>
        <div className={styles.actions}>
          <button className={styles.primaryButton} type="button" onClick={() => void handleGenerate()} disabled={!canGenerate}>
            {isGenerating ? 'Rendering…' : 'Generate dubbed video'}
          </button>
          <button
            className={styles.secondaryButton}
            type="button"
            onClick={() => void handlePreviewVoice()}
            disabled={isPreviewing}
          >
            {isPreviewing ? 'Playing…' : 'Play sample'}
          </button>
          {isLoadingVoices ? <p className={styles.status}>Loading voices…</p> : null}
          {voiceInventoryError ? <p className={styles.error}>{voiceInventoryError}</p> : null}
          {previewError ? <p className={styles.error}>{previewError}</p> : null}
          {statusMessage ? <p className={styles.success}>{statusMessage}</p> : null}
          {generateError ? <p className={styles.error}>{generateError}</p> : null}
        </div>
      </section>
      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Dubbing jobs</h2>
            <p className={styles.cardHint}>Monitor active and recent dubbing tasks.</p>
          </div>
        </div>
        {jobs.length === 0 ? (
          <p className={styles.status}>No dubbing jobs submitted yet.</p>
        ) : (
          <div className={styles.jobList}>
            {[...jobs]
              .sort((a, b) => new Date(b.status.created_at).getTime() - new Date(a.status.created_at).getTime())
              .map((job) => {
                const statusValue = job.status?.status ?? 'pending';
                const outputPath = resolveOutputPath(job);
                return (
                  <div key={job.jobId} className={styles.jobRow}>
                    <div>
                      <div className={styles.jobTitle}>
                        <span className={styles.jobBadge}>{statusValue}</span>
                        <span>{formatJobLabel(job)}</span>
                      </div>
                      <div className={styles.jobMeta}>
                        <span>Job {job.jobId}</span>
                        {outputPath ? (
                          <>
                            <span aria-hidden="true">•</span>
                            <span className={styles.jobPath}>{outputPath}</span>
                          </>
                        ) : null}
                      </div>
                    </div>
                    <div className={styles.jobActions}>
                      <button
                        type="button"
                        className={styles.primaryButton}
                        onClick={() => (onOpenJobMedia ? onOpenJobMedia(job.jobId) : onSelectJob(job.jobId))}
                      >
                        Play media
                      </button>
                      <button
                        type="button"
                        className={styles.secondaryButton}
                        onClick={() => onSelectJob(job.jobId)}
                      >
                        View progress
                      </button>
                    </div>
                  </div>
                );
              })}
          </div>
        )}
      </section>
    </div>
  );
}
