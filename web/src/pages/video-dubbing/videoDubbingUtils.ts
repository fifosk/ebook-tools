import type {
  JobParameterSnapshot,
  MacOSVoice,
  VoiceInventoryResponse,
  YoutubeInlineSubtitleStream,
  YoutubeDubRequest,
  YoutubeNasSubtitle,
  YoutubeNasVideo
} from '../../api/dtos';
import type { JobState } from '../../components/JobList';
import { resolveLanguageName } from '../../constants/languageCodes';
import { VOICE_OPTIONS } from '../../constants/menuOptions';
import { resolveSubtitleLanguageLabel } from '../../utils/subtitles';

export function basenameFromPath(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return '';
  }
  const normalized = trimmed.replace(/\\\\/g, '/');
  const parts = normalized.split('/');
  return parts.length ? parts[parts.length - 1] : trimmed;
}

export function coerceRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

export type VideoDubbingMetadataDraftUpdater = (draft: Record<string, unknown>) => void;

export function updateVideoDubbingMediaMetadataDraft(
  current: Record<string, unknown> | null,
  updater: VideoDubbingMetadataDraftUpdater
): Record<string, unknown> {
  const next: Record<string, unknown> = current ? { ...current } : {};
  updater(next);
  return next;
}

export function updateVideoDubbingMediaMetadataSection(
  current: Record<string, unknown> | null,
  sectionKey: string,
  updater: VideoDubbingMetadataDraftUpdater
): Record<string, unknown> {
  return updateVideoDubbingMediaMetadataDraft(current, (draft) => {
    const currentSection = coerceRecord(draft[sectionKey]);
    const nextSection: Record<string, unknown> = currentSection ? { ...currentSection } : {};
    updater(nextSection);
    draft[sectionKey] = nextSection;
  });
}

export function mergeTvMetadataPreviewWithPreservedYoutubeMetadata(
  current: Record<string, unknown> | null,
  mediaMetadata: Record<string, unknown> | null | undefined
): Record<string, unknown> | null {
  const preservedYoutube = current ? coerceRecord(current['youtube']) : null;
  const next = mediaMetadata ? { ...mediaMetadata } : null;
  if (next && preservedYoutube && !('youtube' in next)) {
    next['youtube'] = { ...preservedYoutube };
  }
  return next;
}

export function hasYoutubeMetadataTitle(mediaMetadata: Record<string, unknown> | null): boolean {
  const youtube = mediaMetadata ? coerceRecord(mediaMetadata['youtube']) : null;
  const title = typeof youtube?.['title'] === 'string' ? youtube['title'].trim() : '';
  return title.length > 0;
}

export function normalizeTextValue(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const cleaned = value.trim();
  return cleaned.length > 0 ? cleaned : null;
}

export function formatEpisodeCode(season: unknown, episode: unknown): string | null {
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

export function formatMacOSVoiceIdentifier(voice: MacOSVoice): string {
  const quality = voice.quality ? voice.quality : 'Default';
  const genderSuffix = voice.gender ? ` - ${voice.gender}` : '';
  return `${voice.name} - ${voice.lang} - (${quality})${genderSuffix}`;
}

export function formatMacOSVoiceLabel(voice: MacOSVoice): string {
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

export function formatBytes(bytes: number): string {
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

export function formatDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

export function formatDateShort(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleDateString();
}

export function formatCount(value: unknown): string | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return null;
  }
  try {
    return new Intl.NumberFormat().format(Math.trunc(value));
  } catch {
    return `${Math.trunc(value)}`;
  }
}

export function formatDurationSeconds(value: unknown): string | null {
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

export function subtitleLabel(sub: YoutubeNasSubtitle): string {
  const language = resolveSubtitleLanguageLabel(sub.language, sub.path, sub.filename);
  const languageSuffix = language ? `(${language})` : '';
  return `${sub.format.toUpperCase()} ${languageSuffix}`.trim();
}

export function isPlayableSubtitle(subtitle: YoutubeNasSubtitle): boolean {
  return ['ass', 'srt', 'vtt', 'sub'].includes(subtitle.format.toLowerCase());
}

export function filterPlayableSubtitles(video: YoutubeNasVideo | null): YoutubeNasSubtitle[] {
  if (!video) {
    return [];
  }
  return video.subtitles.filter(isPlayableSubtitle);
}

export function resolveDefaultVideo(videos: YoutubeNasVideo[]): YoutubeNasVideo | null {
  return videos.find((video) => filterPlayableSubtitles(video).length > 0) ?? videos[0] ?? null;
}

export type VideoDubbingSelection = {
  video: YoutubeNasVideo | null;
  subtitle: YoutubeNasSubtitle | null;
  videoPath: string | null;
  subtitlePath: string | null;
};

export type VideoDubbingDeleteSelection = {
  videos: YoutubeNasVideo[];
  selectedVideoPath: string | null;
  selectedSubtitlePath: string | null;
  fallbackLanguage: string | null;
};

export function resolveVideoDubbingSelection({
  videos,
  preferredVideoPath,
  preferredSubtitlePath,
}: {
  videos: YoutubeNasVideo[];
  preferredVideoPath?: string | null;
  preferredSubtitlePath?: string | null;
}): VideoDubbingSelection {
  if (videos.length === 0) {
    return {
      video: null,
      subtitle: null,
      videoPath: null,
      subtitlePath: null,
    };
  }

  const selectedVideo = videos.find((video) => video.path === preferredVideoPath) ?? resolveDefaultVideo(videos);
  if (!selectedVideo) {
    return {
      video: null,
      subtitle: null,
      videoPath: null,
      subtitlePath: null,
    };
  }
  const subtitleCandidates = filterPlayableSubtitles(selectedVideo);
  const selectedSubtitle =
    preferredVideoPath === selectedVideo.path && preferredSubtitlePath
      ? subtitleCandidates.find((subtitle) => subtitle.path === preferredSubtitlePath) ?? null
      : null;
  const subtitle = selectedSubtitle ?? resolveDefaultSubtitle(selectedVideo) ?? subtitleCandidates[0] ?? null;

  return {
    video: selectedVideo,
    subtitle,
    videoPath: selectedVideo.path,
    subtitlePath: subtitle?.path ?? null,
  };
}

export function resolveSelectionAfterVideoDelete({
  videos,
  deletedVideoPath,
  selectedVideoPath,
  selectedSubtitlePath,
}: {
  videos: YoutubeNasVideo[];
  deletedVideoPath: string;
  selectedVideoPath: string | null;
  selectedSubtitlePath: string | null;
}): VideoDubbingDeleteSelection {
  const remaining = videos.filter((entry) => entry.path !== deletedVideoPath);
  if (selectedVideoPath !== deletedVideoPath) {
    return {
      videos: remaining,
      selectedVideoPath,
      selectedSubtitlePath,
      fallbackLanguage: null,
    };
  }

  const fallback = remaining[0] ?? null;
  const fallbackSubtitle = fallback ? resolveDefaultSubtitle(fallback) : null;
  return {
    videos: remaining,
    selectedVideoPath: fallback?.path ?? null,
    selectedSubtitlePath: fallbackSubtitle?.path ?? null,
    fallbackLanguage: fallbackSubtitle?.language ?? null,
  };
}

export function resolveVideoDubbingMetadataSourceName({
  subtitle,
  video,
}: {
  subtitle: YoutubeNasSubtitle | null;
  video: YoutubeNasVideo | null;
}): string {
  if (subtitle?.filename) {
    return subtitle.filename;
  }
  if (subtitle?.path) {
    return basenameFromPath(subtitle.path);
  }
  if (video?.filename) {
    return video.filename;
  }
  if (video?.path) {
    return basenameFromPath(video.path);
  }
  return '';
}

export function canExtractEmbeddedSubtitles(video: YoutubeNasVideo | null): boolean {
  if (!video) {
    return false;
  }
  const lower = video.path.toLowerCase();
  return lower.endsWith('.mkv') || lower.endsWith('.mp4') || lower.endsWith('.mov') || lower.endsWith('.m4v');
}

export function subtitleStreamLabel(stream: YoutubeInlineSubtitleStream): string {
  const normalized = stream.language ? stream.language : '';
  const friendlyName = normalized ? resolveLanguageName(normalized) || normalized : 'Unknown language';
  const titleSuffix = stream.title ? ` – ${stream.title}` : '';
  return `${friendlyName}${titleSuffix}`;
}

export function videoSourceLabel(video: YoutubeNasVideo): string {
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

export function videoSourceBadge(video: YoutubeNasVideo): { icon: string; label: string; title: string } {
  const source = (video.source || '').toLowerCase();
  if (source === 'nas_video') {
    return { icon: '🗃', label: 'NAS', title: 'NAS video' };
  }
  if (source === 'youtube') {
    return { icon: '📺', label: 'YT', title: 'YouTube download' };
  }
  return { icon: '📦', label: 'SRC', title: videoSourceLabel(video) };
}

export function resolveDefaultSubtitle(video: YoutubeNasVideo | null): YoutubeNasSubtitle | null {
  if (!video) {
    return null;
  }
  const candidates = filterPlayableSubtitles(video);
  if (!candidates.length) {
    return null;
  }
  const english = candidates.find((sub) => (sub.language ?? '').toLowerCase().startsWith('en'));
  return english ?? candidates[0];
}

export function resolveDefaultStreamLanguages(streams: YoutubeInlineSubtitleStream[]): Set<string> {
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
}

export function formatSubtitleExtractionStatus(extractedCount: number, videoFilename: string): string {
  if (extractedCount <= 0) {
    return 'No subtitle streams found to extract.';
  }
  const noun = extractedCount === 1 ? 'track' : 'tracks';
  return `Extracted ${extractedCount} subtitle ${noun} from ${videoFilename}.`;
}

export function resolveSubtitleNotice(
  selectedVideo: YoutubeNasVideo | null,
  playableSubtitles: YoutubeNasSubtitle[],
): string | null {
  if (!selectedVideo) {
    return 'Select a video to see subtitles.';
  }
  if (playableSubtitles.length === 0) {
    return 'No subtitles were found next to this video.';
  }
  return null;
}

export function buildVoiceOptions(
  voiceInventory: VoiceInventoryResponse | null,
  targetLanguageCode: string
): { value: string; label: string }[] {
  const base = VOICE_OPTIONS.map((option) => ({
    value: option.value,
    label: option.label
  }));
  if (!voiceInventory) {
    return base;
  }

  const targetCode = (targetLanguageCode || '').toLowerCase();
  const targetBase = targetCode.split(/[-_]/)[0];
  const matchesTarget = (lang: string): boolean => {
    if (!targetCode) {
      return true;
    }
    const normalized = (lang || '').toLowerCase();
    if (!normalized) {
      return false;
    }
    if (normalized === targetCode) {
      return true;
    }
    return normalized.split(/[-_]/)[0] === targetBase;
  };

  const macVoices = voiceInventory.macos
    .filter((voice) => matchesTarget(voice.lang))
    .map((voice) => ({
      value: formatMacOSVoiceIdentifier(voice),
      label: formatMacOSVoiceLabel(voice)
    }));

  const piperVoices = (voiceInventory.piper ?? [])
    .filter((voice) => matchesTarget(voice.lang))
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((voice) => ({
      value: voice.name,
      label: `Piper: ${voice.name}`
    }));

  const gttsSeen = new Set<string>();
  const gttsVoices: { value: string; label: string }[] = [];
  for (const entry of voiceInventory.gtts) {
    const entryCode = entry.code.toLowerCase();
    if (!matchesTarget(entryCode)) {
      continue;
    }
    const shortCode = entryCode.split(/[-_]/)[0];
    if (!shortCode || gttsSeen.has(shortCode)) {
      continue;
    }
    gttsSeen.add(shortCode);
    gttsVoices.push({ value: `gTTS-${shortCode}`, label: `gTTS (${entry.name})` });
  }

  const merged = new Map<string, { value: string; label: string }>();
  [...base, ...macVoices, ...piperVoices, ...gttsVoices].forEach((entry) =>
    merged.set(entry.value, entry)
  );
  return Array.from(merged.values()).sort((a, b) => a.label.localeCompare(b.label));
}

export function resolveOutputPath(job: JobState): string | null {
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

export function formatJobLabel(job: JobState): string {
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

export function parseOffsetSeconds(value: string): number {
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
}

export type VideoDubbingGeneratePayloadInput = {
  selectedVideo: YoutubeNasVideo | null;
  selectedSubtitle: YoutubeNasSubtitle | null;
  mediaMetadataDraft: Record<string, unknown> | null;
  subtitleLanguageLabel: string;
  subtitleLanguageCode: string;
  targetLanguageCode: string;
  voice: string;
  startOffset: string;
  endOffset: string;
  originalMixPercent: number;
  flushSentences: number;
  translationBatchSize: number;
  llmModel: string;
  translationProvider: string;
  transliterationMode: string;
  transliterationModel: string;
  splitBatches: boolean;
  stitchBatches: boolean;
  includeTransliteration: boolean;
  targetHeight: number;
  preserveAspectRatio: boolean;
  enableLookupCache: boolean;
};

export type VideoDubbingGeneratePayloadResult =
  | { payload: YoutubeDubRequest; error: null }
  | { payload: null; error: string };

export function buildVideoDubbingGeneratePayload({
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
}: VideoDubbingGeneratePayloadInput): VideoDubbingGeneratePayloadResult {
  if (!selectedVideo || !selectedSubtitle) {
    return {
      payload: null,
      error: 'Choose a video and an ASS subtitle before generating audio.',
    };
  }

  let parsedStart = 0;
  let parsedEnd: number | undefined;
  try {
    parsedStart = parseOffsetSeconds(startOffset);
    parsedEnd = endOffset.trim() ? parseOffsetSeconds(endOffset) : undefined;
  } catch (error) {
    return {
      payload: null,
      error: error instanceof Error ? error.message : 'Offsets must be in seconds or HH:MM:SS format.',
    };
  }
  if (parsedEnd !== undefined && parsedEnd <= parsedStart) {
    return {
      payload: null,
      error: 'End offset must be greater than start offset.',
    };
  }

  return {
    payload: {
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
      preserve_aspect_ratio: preserveAspectRatio,
      enable_lookup_cache: enableLookupCache,
    },
    error: null,
  };
}

export function formatOffsetLabel(value: number | null | undefined): string {
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
}

export type VideoDubPrefillValues = {
  videoPath?: string;
  subtitlePath?: string;
  targetLanguage?: string;
  voice?: string;
  startOffset?: string;
  endOffset?: string;
  originalMixPercent: number;
  flushSentences?: number;
  translationBatchSize?: number;
  targetHeight: number;
  preserveAspectRatio: boolean;
  splitBatches: boolean;
  stitchBatches?: boolean;
  llmModel?: string;
  translationProvider?: string;
  transliterationMode?: string;
  transliterationModel?: string;
  includeTransliteration: boolean;
  enableLookupCache?: boolean;
};

function finiteNumber(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function trimmedString(value: unknown): string | undefined {
  if (typeof value !== 'string') {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

export function resolveVideoDubPrefill(
  parameters: JobParameterSnapshot | null | undefined
): VideoDubPrefillValues | null {
  if (!parameters) {
    return null;
  }
  const targetLanguages = Array.isArray(parameters.target_languages)
    ? parameters.target_languages
        .map((entry) => trimmedString(entry))
        .filter((entry): entry is string => Boolean(entry))
    : [];

  const startSeconds = finiteNumber(parameters.start_time_offset_seconds);
  const endSeconds = finiteNumber(parameters.end_time_offset_seconds);
  return {
    videoPath: trimmedString(parameters.input_file) ?? trimmedString(parameters.video_path),
    subtitlePath: trimmedString(parameters.subtitle_path),
    targetLanguage: targetLanguages[0],
    voice: typeof parameters.selected_voice === 'string' ? parameters.selected_voice.trim() : undefined,
    startOffset: startSeconds === undefined ? undefined : formatOffsetLabel(startSeconds),
    endOffset: endSeconds === undefined ? undefined : formatOffsetLabel(endSeconds),
    originalMixPercent: finiteNumber(parameters.original_mix_percent) ?? 5,
    flushSentences: finiteNumber(parameters.flush_sentences),
    translationBatchSize: finiteNumber(parameters.translation_batch_size),
    targetHeight: finiteNumber(parameters.target_height) ?? 480,
    preserveAspectRatio:
      typeof parameters.preserve_aspect_ratio === 'boolean' ? parameters.preserve_aspect_ratio : true,
    splitBatches: typeof parameters.split_batches === 'boolean' ? parameters.split_batches : true,
    stitchBatches: typeof parameters.stitch_batches === 'boolean' ? parameters.stitch_batches : undefined,
    llmModel: trimmedString(parameters.llm_model),
    translationProvider: trimmedString(parameters.translation_provider),
    transliterationMode: trimmedString(parameters.transliteration_mode),
    transliterationModel: trimmedString(parameters.transliteration_model),
    includeTransliteration:
      typeof parameters.include_transliteration === 'boolean' ? parameters.include_transliteration : true,
    enableLookupCache:
      typeof parameters.enable_lookup_cache === 'boolean' ? parameters.enable_lookup_cache : undefined
  };
}
