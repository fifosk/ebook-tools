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
  deleteYoutubeVideo
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
import type { MacOSVoice } from '../api/dtos';
import type { JobState } from '../components/JobList';
import { VOICE_OPTIONS } from '../constants/menuOptions';
import EmojiIcon from '../components/EmojiIcon';
import LanguageSelect from '../components/LanguageSelect';
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
  resolveSubtitleFlag,
  resolveSubtitleLanguageCandidate,
  resolveSubtitleLanguageLabel,
  subtitleLanguageDetail
} from '../utils/subtitles';
import styles from './YoutubeDubPage.module.css';

const DEFAULT_VIDEO_DIR = '/Volumes/Data/Download/DStation';
const DEFAULT_LLM_MODEL = 'kimi-k2:1t-cloud';
const STORAGE_KEYS = {
  baseDir: 'ebookTools.youtubeDub.baseDir',
  selectedVideoPath: 'ebookTools.youtubeDub.selectedVideoPath',
  selectedSubtitlePath: 'ebookTools.youtubeDub.selectedSubtitlePath'
} as const;
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

type YoutubeDubTab = 'videos' | 'options' | 'metadata' | 'jobs';
type YoutubeMetadataSection = 'tv' | 'youtube';

function basenameFromPath(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return '';
  }
  const normalized = trimmed.replace(/\\/g, '/');
  const parts = normalized.split('/');
  return parts.length ? parts[parts.length - 1] : trimmed;
}

function coerceRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function normalizeTextValue(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const cleaned = value.trim();
  return cleaned.length > 0 ? cleaned : null;
}

function formatEpisodeCode(season: unknown, episode: unknown): string | null {
  if (typeof season !== 'number' || typeof episode !== 'number') {
    return null;
  }
  if (!Number.isFinite(season) || !Number.isFinite(episode)) {
    return null;
  }
  const seasonInt = Math.trunc(season);
  const episodeInt = Math.trunc(episode);
  if (seasonInt <= 0 || episodeInt <= 0) {
    return null;
  }
  return `S${seasonInt.toString().padStart(2, '0')}E${episodeInt.toString().padStart(2, '0')}`;
}

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

function formatCount(value: unknown): string | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return null;
  }
  try {
    return new Intl.NumberFormat().format(Math.trunc(value));
  } catch {
    return `${Math.trunc(value)}`;
  }
}

function formatDurationSeconds(value: unknown): string | null {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) {
    return null;
  }
  const total = Math.trunc(value);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function subtitleLabel(sub: YoutubeNasSubtitle): string {
  const language = resolveSubtitleLanguageLabel(sub.language, sub.path, sub.filename);
  const languageSuffix = language ? `(${language})` : '';
  return `${sub.format.toUpperCase()} ${languageSuffix}`.trim();
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
  const [baseDir, setBaseDir] = useState(() => {
    if (typeof window === 'undefined') {
      return DEFAULT_VIDEO_DIR;
    }
    try {
      const stored = window.localStorage.getItem(STORAGE_KEYS.baseDir);
      return stored && stored.trim() ? stored.trim() : DEFAULT_VIDEO_DIR;
    } catch {
      return DEFAULT_VIDEO_DIR;
    }
  });
  const [library, setLibrary] = useState<YoutubeNasLibraryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<YoutubeDubTab>('videos');

  const [selectedVideoPath, setSelectedVideoPath] = useState<string | null>(() => {
    if (typeof window === 'undefined') {
      return null;
    }
    try {
      const stored = window.localStorage.getItem(STORAGE_KEYS.selectedVideoPath);
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
      const stored = window.localStorage.getItem(STORAGE_KEYS.selectedSubtitlePath);
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
  const [targetHeight, setTargetHeight] = useState(480);
  const [preserveAspectRatio, setPreserveAspectRatio] = useState(true);
  const [llmModel, setLlmModel] = useState(DEFAULT_LLM_MODEL);
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
          window.localStorage.setItem(STORAGE_KEYS.selectedVideoPath, selectedVideoPath);
        } else {
          window.localStorage.removeItem(STORAGE_KEYS.selectedVideoPath);
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
          window.localStorage.setItem(STORAGE_KEYS.selectedSubtitlePath, selectedSubtitlePath);
        } else {
          window.localStorage.removeItem(STORAGE_KEYS.selectedSubtitlePath);
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
      window.localStorage.setItem(STORAGE_KEYS.baseDir, baseDir);
    } catch {
      // ignore storage errors
    }
  }, [baseDir]);

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
  const [metadataSection, setMetadataSection] = useState<YoutubeMetadataSection>('tv');
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
        media_metadata: mediaMetadataDraft ?? undefined,
        target_language: targetLanguageCode || undefined,
        voice: voice.trim() || 'gTTS',
        start_time_offset: startOffset.trim() || undefined,
        end_time_offset: endOffset.trim() || undefined,
        original_mix_percent: originalMixPercent,
        flush_sentences: flushSentences,
        llm_model: llmModel || undefined,
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
    targetLanguageCode,
    voice,
    startOffset,
    endOffset,
    originalMixPercent,
    flushSentences,
    llmModel,
    splitBatches,
    stitchBatches,
    includeTransliteration,
    targetHeight,
    preserveAspectRatio,
    mediaMetadataDraft,
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
      <div className={styles.tabsRow}>
        <div className={styles.tabs} role="tablist" aria-label="Dubbed video tabs">
          <button
            type="button"
            role="tab"
            className={`${styles.tabButton} ${activeTab === 'videos' ? styles.tabButtonActive : ''}`}
            aria-selected={activeTab === 'videos'}
            onClick={() => setActiveTab('videos')}
          >
            Source <span className={styles.sectionCount}>{videos.length}</span>
          </button>
          <button
            type="button"
            role="tab"
            className={`${styles.tabButton} ${activeTab === 'metadata' ? styles.tabButtonActive : ''}`}
            aria-selected={activeTab === 'metadata'}
            onClick={() => setActiveTab('metadata')}
          >
            Metadata
          </button>
          <button
            type="button"
            role="tab"
            className={`${styles.tabButton} ${activeTab === 'options' ? styles.tabButtonActive : ''}`}
            aria-selected={activeTab === 'options'}
            onClick={() => setActiveTab('options')}
          >
            Options
          </button>
          <button
            type="button"
            role="tab"
            className={`${styles.tabButton} ${activeTab === 'jobs' ? styles.tabButtonActive : ''}`}
            aria-selected={activeTab === 'jobs'}
            onClick={() => setActiveTab('jobs')}
          >
            Jobs <span className={styles.sectionCount}>{jobs.length}</span>
          </button>
        </div>
        <div className={styles.tabsActions}>
          <button className={styles.primaryButton} type="button" onClick={() => void handleGenerate()} disabled={!canGenerate}>
            {isGenerating ? 'Rendering…' : 'Generate dubbed video'}
          </button>
        </div>
      </div>

      {statusMessage ? <p className={styles.success}>{statusMessage}</p> : null}
      {generateError ? <p className={styles.error}>{generateError}</p> : null}

      {activeTab === 'videos' ? (
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
                    {video.subtitles.length === 0 ? (
                      <span className={`${styles.pill} ${styles.pillMeta} ${styles.pillMuted}`}>No subtitles</span>
                    ) : (
                      video.subtitles.map((sub) => (
                        <span
                          key={sub.path}
                          className={`${styles.pill} ${styles.pillMeta} ${
                            sub.format.toLowerCase() === 'ass' ? styles.pillAss : styles.pillMuted
                          }`}
                          aria-label={subtitleLabel(sub)}
                          title={subtitleLabel(sub)}
                        >
                          <EmojiIcon
                            emoji={resolveSubtitleFlag(sub.language, sub.path, sub.filename)}
                            className={styles.pillFlag}
                          />
                          <span>{(sub.format ?? '').toUpperCase()}</span>
                        </span>
                      ))
                    )}
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
	                                        <span
	                                          className={`${styles.pill} ${styles.pillMuted}`}
	                                          title={subtitleLanguageDetail(sub.language, sub.path, sub.filename)}
	                                          aria-label={subtitleLanguageDetail(sub.language, sub.path, sub.filename)}
	                                        >
	                                          <EmojiIcon
	                                            emoji={resolveSubtitleFlag(sub.language, sub.path, sub.filename)}
	                                            className={styles.pillFlag}
	                                          />
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
                </div>
              </label>
            );
          })}
        </div>
      </section>
      ) : null}

      {activeTab === 'options' ? (
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
	            <LanguageSelect
	              value={targetLanguage}
	              options={sortedLanguageOptions}
	              onChange={applyTargetLanguage}
	              className={styles.input}
	            />
	            <p className={styles.fieldHint}>
	              Matches the Subtitles page list; we will convert it to the correct language code automatically.
	            </p>
	          </label>
          <label className={styles.field}>
            <span>Voice / audio mode</span>
            <div className={styles.voiceRow}>
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
              <button
                className={styles.secondaryButton}
                type="button"
                onClick={() => void handlePreviewVoice()}
                disabled={isPreviewing}
              >
                {isPreviewing ? 'Playing…' : 'Play sample'}
              </button>
            </div>
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
              checked={stitchBatches}
              onChange={(event) => setStitchBatches(event.target.checked)}
              disabled={!splitBatches}
            />
            <span>Stitch batches into a single final MP4 (default on)</span>
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
          {isLoadingVoices ? <p className={styles.status}>Loading voices…</p> : null}
          {voiceInventoryError ? <p className={styles.error}>{voiceInventoryError}</p> : null}
          {previewError ? <p className={styles.error}>{previewError}</p> : null}
        </div>
      </section>
      ) : null}

      {activeTab === 'metadata' ? (
      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Metadata loader</h2>
            <p className={styles.cardHint}>
              {metadataSection === 'tv'
                ? 'Load TV episode metadata from TVMaze (no API key) and edit it before submitting the job.'
                : 'Load YouTube video metadata via yt-dlp (no API key) using the video id in brackets.'}
            </p>
          </div>
          <div className={styles.tabs} role="tablist" aria-label="Metadata sections">
            <button
              type="button"
              role="tab"
              className={`${styles.tabButton} ${metadataSection === 'tv' ? styles.tabButtonActive : ''}`}
              aria-selected={metadataSection === 'tv'}
              onClick={() => setMetadataSection('tv')}
            >
              TVMaze
            </button>
            <button
              type="button"
              role="tab"
              className={`${styles.tabButton} ${metadataSection === 'youtube' ? styles.tabButtonActive : ''}`}
              aria-selected={metadataSection === 'youtube'}
              onClick={() => setMetadataSection('youtube')}
            >
              YouTube
            </button>
          </div>
        </div>

        {!metadataSourceName ? (
          <p className={styles.status}>Select a video/subtitle to load metadata.</p>
        ) : (
          <>
            {metadataSection === 'tv' ? (
              <>
                {metadataError ? <div className="alert" role="alert">{metadataError}</div> : null}
                <div className={styles.controlRow}>
                  <label style={{ minWidth: 'min(32rem, 100%)' }}>
                    Lookup filename
                    <input
                      type="text"
                      className={styles.input}
                      value={metadataLookupSourceName}
                      onChange={(event) => setMetadataLookupSourceName(event.target.value)}
                    />
                  </label>
                  <button
                    type="button"
                    className={styles.secondaryButton}
                    onClick={() => void performMetadataLookup(metadataLookupSourceName, false)}
                    disabled={!metadataLookupSourceName.trim() || metadataLoading}
                    aria-busy={metadataLoading}
                  >
                    {metadataLoading ? 'Looking up…' : 'Lookup'}
                  </button>
                  <button
                    type="button"
                    className={styles.secondaryButton}
                    onClick={() => void performMetadataLookup(metadataLookupSourceName, true)}
                    disabled={!metadataLookupSourceName.trim() || metadataLoading}
                    aria-busy={metadataLoading}
                  >
                    Refresh
                  </button>
                  <button
                    type="button"
                    className={styles.secondaryButton}
                    onClick={() => {
                      setMetadataPreview(null);
                      setMediaMetadataDraft(null);
                      setMetadataError(null);
                    }}
                    disabled={metadataLoading}
                  >
                    Clear
                  </button>
                </div>

                {metadataLoading ? <p className={styles.status}>Loading metadata…</p> : null}
                {!metadataLoading && metadataPreview ? (
                  (() => {
                const media = coerceRecord(mediaMetadataDraft);
                const show = media ? coerceRecord(media['show']) : null;
                const episode = media ? coerceRecord(media['episode']) : null;
                const errorMessage = normalizeTextValue(media ? media['error'] : null);
                const showName = normalizeTextValue(show ? show['name'] : null);
                const episodeName = normalizeTextValue(episode ? episode['name'] : null);
                const seasonNumber = typeof episode?.season === 'number' ? episode.season : null;
                const episodeNumber = typeof episode?.number === 'number' ? episode.number : null;
                const episodeCode = formatEpisodeCode(seasonNumber, episodeNumber);
                const airdate = normalizeTextValue(episode ? episode['airdate'] : null);
                const episodeUrl = normalizeTextValue(episode ? episode['url'] : null);
                const jobLabel = normalizeTextValue(media ? media['job_label'] : null);

                const showImage = show ? coerceRecord(show['image']) : null;
                const showImageMedium = normalizeTextValue(showImage ? showImage['medium'] : null);
                const showImageOriginal = normalizeTextValue(showImage ? showImage['original'] : null);
                const showImageUrl = showImageMedium ?? showImageOriginal;
                const showImageLink = showImageOriginal ?? showImageMedium;
                const episodeImage = episode ? coerceRecord(episode['image']) : null;
                const episodeImageMedium = normalizeTextValue(episodeImage ? episodeImage['medium'] : null);
                const episodeImageOriginal = normalizeTextValue(episodeImage ? episodeImage['original'] : null);
                const episodeImageUrl = episodeImageMedium ?? episodeImageOriginal;
                const episodeImageLink = episodeImageOriginal ?? episodeImageMedium;

                return (
                  <>
                    {showImageUrl || episodeImageUrl ? (
                      <div className="tv-metadata-media" aria-label="TV images">
                        {showImageUrl ? (
                          <a
                            href={showImageLink ?? showImageUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="tv-metadata-media__poster"
                          >
                            <img
                              src={showImageUrl}
                              alt={showName ? `${showName} poster` : 'Show poster'}
                              loading="lazy"
                              decoding="async"
                            />
                          </a>
                        ) : null}
                        {episodeImageUrl ? (
                          <a
                            href={episodeImageLink ?? episodeImageUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="tv-metadata-media__still"
                          >
                            <img
                              src={episodeImageUrl}
                              alt={episodeName ? `${episodeName} still` : 'Episode still'}
                              loading="lazy"
                              decoding="async"
                            />
                          </a>
                        ) : null}
                      </div>
                    ) : null}

                    <dl className="metadata-grid">
                      <div className="metadata-grid__row">
                        <dt>Source</dt>
                        <dd>{metadataPreview.source_name ?? metadataSourceName}</dd>
                      </div>
                      {metadataPreview.parsed ? (
                        <div className="metadata-grid__row">
                          <dt>Parsed</dt>
                          <dd>
                            {metadataPreview.parsed.series}{' '}
                            {formatEpisodeCode(metadataPreview.parsed.season, metadataPreview.parsed.episode) ?? ''}
                          </dd>
                        </div>
                      ) : null}
                      {showName ? (
                        <div className="metadata-grid__row">
                          <dt>Show</dt>
                          <dd>{showName}</dd>
                        </div>
                      ) : null}
                      {episodeCode || episodeName ? (
                        <div className="metadata-grid__row">
                          <dt>Episode</dt>
                          <dd>
                            {episodeCode ? `${episodeCode}${episodeName ? ` — ${episodeName}` : ''}` : episodeName}
                          </dd>
                        </div>
                      ) : null}
                      {airdate ? (
                        <div className="metadata-grid__row">
                          <dt>Airdate</dt>
                          <dd>{airdate}</dd>
                        </div>
                      ) : null}
                      {episodeUrl ? (
                        <div className="metadata-grid__row">
                          <dt>TVMaze</dt>
                          <dd>
                            <a href={episodeUrl} target="_blank" rel="noopener noreferrer">
                              Open episode page
                            </a>
                          </dd>
                        </div>
                      ) : null}
                      {errorMessage ? (
                        <div className="metadata-grid__row">
                          <dt>Status</dt>
                          <dd>{errorMessage}</dd>
                        </div>
                      ) : null}
                    </dl>

                    <fieldset className="metadata-fieldset">
                      <legend>Edit metadata</legend>
                      <div className="metadata-fieldset__fields">
                        <label>
                          Job label
                          <input
                            type="text"
                            value={jobLabel ?? ''}
                            onChange={(event) => {
                              const value = event.target.value;
                              updateMediaMetadataDraft((draft) => {
                                const trimmed = value.trim();
                                if (trimmed) {
                                  draft['job_label'] = trimmed;
                                } else {
                                  delete draft['job_label'];
                                }
                              });
                            }}
                          />
                        </label>
                        <label>
                          Show
                          <input
                            type="text"
                            value={showName ?? ''}
                            onChange={(event) => {
                              const value = event.target.value;
                              updateMediaMetadataSection('show', (section) => {
                                const trimmed = value.trim();
                                if (trimmed) {
                                  section['name'] = trimmed;
                                } else {
                                  delete section['name'];
                                }
                              });
                            }}
                          />
                        </label>
                        <label>
                          Season
                          <input
                            type="number"
                            min={1}
                            value={seasonNumber ?? ''}
                            onChange={(event) => {
                              const raw = event.target.value;
                              updateMediaMetadataSection('episode', (section) => {
                                if (!raw.trim()) {
                                  delete section['season'];
                                  return;
                                }
                                const parsed = Number(raw);
                                if (!Number.isFinite(parsed) || parsed <= 0) {
                                  return;
                                }
                                section['season'] = Math.trunc(parsed);
                              });
                            }}
                          />
                        </label>
                        <label>
                          Episode
                          <input
                            type="number"
                            min={1}
                            value={episodeNumber ?? ''}
                            onChange={(event) => {
                              const raw = event.target.value;
                              updateMediaMetadataSection('episode', (section) => {
                                if (!raw.trim()) {
                                  delete section['number'];
                                  return;
                                }
                                const parsed = Number(raw);
                                if (!Number.isFinite(parsed) || parsed <= 0) {
                                  return;
                                }
                                section['number'] = Math.trunc(parsed);
                              });
                            }}
                          />
                        </label>
                        <label>
                          Episode title
                          <input
                            type="text"
                            value={episodeName ?? ''}
                            onChange={(event) => {
                              const value = event.target.value;
                              updateMediaMetadataSection('episode', (section) => {
                                const trimmed = value.trim();
                                if (trimmed) {
                                  section['name'] = trimmed;
                                } else {
                                  delete section['name'];
                                }
                              });
                            }}
                          />
                        </label>
                        <label>
                          Airdate
                          <input
                            type="text"
                            value={airdate ?? ''}
                            onChange={(event) => {
                              const value = event.target.value;
                              updateMediaMetadataSection('episode', (section) => {
                                const trimmed = value.trim();
                                if (trimmed) {
                                  section['airdate'] = trimmed;
                                } else {
                                  delete section['airdate'];
                                }
                              });
                            }}
                            placeholder="YYYY-MM-DD"
                          />
                        </label>
                      </div>
                    </fieldset>

                    {media ? (
                      <details>
                        <summary>Raw payload</summary>
                        <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(media, null, 2)}</pre>
                      </details>
                    ) : null}
                  </>
                );
              })()
                ) : null}

                {!metadataLoading && !metadataPreview ? <p className={styles.status}>Metadata is not available yet.</p> : null}
              </>
            ) : null}

            {metadataSection === 'youtube' ? (
              <>
                {youtubeMetadataError ? <div className="alert" role="alert">{youtubeMetadataError}</div> : null}
                <div className={styles.controlRow}>
                  <label style={{ minWidth: 'min(32rem, 100%)' }}>
                    Lookup video id / filename
                    <input
                      type="text"
                      className={styles.input}
                      value={youtubeLookupSourceName}
                      onChange={(event) => setYoutubeLookupSourceName(event.target.value)}
                      placeholder="Example: Title [dQw4w9WgXcQ].mp4"
                    />
                  </label>
                  <button
                    type="button"
                    className={styles.secondaryButton}
                    onClick={() => void performYoutubeMetadataLookup(youtubeLookupSourceName, false)}
                    disabled={!youtubeLookupSourceName.trim() || youtubeMetadataLoading}
                    aria-busy={youtubeMetadataLoading}
                  >
                    {youtubeMetadataLoading ? 'Looking up…' : 'Lookup'}
                  </button>
                  <button
                    type="button"
                    className={styles.secondaryButton}
                    onClick={() => void performYoutubeMetadataLookup(youtubeLookupSourceName, true)}
                    disabled={!youtubeLookupSourceName.trim() || youtubeMetadataLoading}
                    aria-busy={youtubeMetadataLoading}
                  >
                    Refresh
                  </button>
                  <button
                    type="button"
                    className={styles.secondaryButton}
                    onClick={() => {
                      setYoutubeMetadataPreview(null);
                      setYoutubeMetadataError(null);
                      updateMediaMetadataDraft((draft) => {
                        delete draft['youtube'];
                      });
                    }}
                    disabled={youtubeMetadataLoading}
                  >
                    Clear
                  </button>
                </div>

                {youtubeMetadataLoading ? <p className={styles.status}>Loading metadata…</p> : null}
                {!youtubeMetadataLoading && youtubeMetadataPreview ? (
                  (() => {
                    const youtube = mediaMetadataDraft ? coerceRecord(mediaMetadataDraft['youtube']) : null;
                    const title = normalizeTextValue(youtube ? youtube['title'] : null);
                    const channel =
                      normalizeTextValue(youtube ? youtube['channel'] : null) ??
                      normalizeTextValue(youtube ? youtube['uploader'] : null);
                    const webpageUrl = normalizeTextValue(youtube ? youtube['webpage_url'] : null);
                    const thumbnailUrl = normalizeTextValue(youtube ? youtube['thumbnail'] : null);
                    const summary = normalizeTextValue(youtube ? youtube['summary'] : null);
                    const description = normalizeTextValue(youtube ? youtube['description'] : null);
                    const views = formatCount(youtube ? youtube['view_count'] : null);
                    const likes = formatCount(youtube ? youtube['like_count'] : null);
                    const uploaded = normalizeTextValue(youtube ? youtube['upload_date'] : null);
                    const duration = formatDurationSeconds(youtube ? youtube['duration_seconds'] : null);
                    const errorMessage = normalizeTextValue(youtube ? youtube['error'] : null);
                    const rawPayload = youtube ? youtube['raw_payload'] : null;

                    return (
                      <>
                        {thumbnailUrl ? (
                          <div className="tv-metadata-media" aria-label="YouTube thumbnail">
                            <a
                              href={webpageUrl ?? thumbnailUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="tv-metadata-media__still"
                            >
                              <img
                                src={thumbnailUrl}
                                alt={title ? `${title} thumbnail` : 'YouTube thumbnail'}
                                loading="lazy"
                                decoding="async"
                              />
                            </a>
                          </div>
                        ) : null}

                        <dl className="metadata-grid">
                          <div className="metadata-grid__row">
                            <dt>Source</dt>
                            <dd>{youtubeMetadataPreview.source_name ?? youtubeLookupSourceName}</dd>
                          </div>
                          {youtubeMetadataPreview.parsed ? (
                            <div className="metadata-grid__row">
                              <dt>Video id</dt>
                              <dd>{youtubeMetadataPreview.parsed.video_id}</dd>
                            </div>
                          ) : null}
                          {title ? (
                            <div className="metadata-grid__row">
                              <dt>Title</dt>
                              <dd>{title}</dd>
                            </div>
                          ) : null}
                          {channel ? (
                            <div className="metadata-grid__row">
                              <dt>Channel</dt>
                              <dd>{channel}</dd>
                            </div>
                          ) : null}
                          {duration ? (
                            <div className="metadata-grid__row">
                              <dt>Duration</dt>
                              <dd>{duration}</dd>
                            </div>
                          ) : null}
                          {uploaded ? (
                            <div className="metadata-grid__row">
                              <dt>Uploaded</dt>
                              <dd>{uploaded}</dd>
                            </div>
                          ) : null}
                          {views ? (
                            <div className="metadata-grid__row">
                              <dt>Views</dt>
                              <dd>{views}{likes ? ` · 👍 ${likes}` : ''}</dd>
                            </div>
                          ) : null}
                          {webpageUrl ? (
                            <div className="metadata-grid__row">
                              <dt>Link</dt>
                              <dd>
                                <a href={webpageUrl} target="_blank" rel="noopener noreferrer">
                                  Open on YouTube
                                </a>
                              </dd>
                            </div>
                          ) : null}
                          {errorMessage ? (
                            <div className="metadata-grid__row">
                              <dt>Status</dt>
                              <dd>{errorMessage}</dd>
                            </div>
                          ) : null}
                        </dl>

                        {summary ? <p className={styles.status}>{summary}</p> : null}
                        {description ? (
                          <details>
                            <summary>Description</summary>
                            <pre style={{ whiteSpace: 'pre-wrap' }}>{description}</pre>
                          </details>
                        ) : null}
                        {rawPayload ? (
                          <details>
                            <summary>Raw payload</summary>
                            <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(rawPayload, null, 2)}</pre>
                          </details>
                        ) : null}
                      </>
                    );
                  })()
                ) : null}

                {!youtubeMetadataLoading && !youtubeMetadataPreview ? (
                  <p className={styles.status}>Metadata is not available yet.</p>
                ) : null}
              </>
            ) : null}
          </>
        )}
      </section>
      ) : null}

      {activeTab === 'jobs' ? (
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
      ) : null}
    </div>
  );
}
