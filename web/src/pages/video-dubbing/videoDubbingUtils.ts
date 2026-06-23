import type {
  MacOSVoice,
  VoiceInventoryResponse,
  YoutubeInlineSubtitleStream,
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
  const candidates = video.subtitles.filter((sub) => ['ass', 'srt', 'vtt', 'sub'].includes(sub.format.toLowerCase()));
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
    if (!/^\\d+(\\.\\d+)?$/.test(token)) {
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
