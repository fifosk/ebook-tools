import type {
  YoutubeInlineSubtitleStream,
  YoutubeNasSubtitle,
  YoutubeNasVideo
} from '../../api/dtos';
import type { JobState } from '../../components/JobList';
import { resolveLanguageName } from '../../constants/languageCodes';
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
