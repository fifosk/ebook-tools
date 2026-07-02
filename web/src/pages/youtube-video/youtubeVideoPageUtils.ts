import type {
  AcquisitionCandidate,
  AcquisitionProvider,
  YoutubeNasVideo,
  YoutubeSubtitleKind,
  YoutubeSubtitleTrack,
  YoutubeVideoFormat
} from '../../api/dtos';
import { resolveSubtitleFlag, resolveSubtitleLanguageLabel } from '../../utils/subtitles';

export function resolveDefaultTrack(tracks: YoutubeSubtitleTrack[]): YoutubeSubtitleTrack | null {
  if (!tracks.length) {
    return null;
  }
  const lower = tracks.map((track) => ({
    track,
    language: track.language.toLowerCase()
  }));
  const manualEnglish = lower.find(
    (entry) => entry.track.kind === 'manual' && entry.language.startsWith('en')
  );
  if (manualEnglish) {
    return manualEnglish.track;
  }
  const anyEnglish = lower.find((entry) => entry.language.startsWith('en'));
  if (anyEnglish) {
    return anyEnglish.track;
  }
  const firstManual = tracks.find((track) => track.kind === 'manual');
  return firstManual ?? tracks[0];
}

export function trackKey(track: { language: string; kind: YoutubeSubtitleKind }): string {
  return `${track.language}__${track.kind}`;
}

export function describeFormat(format: YoutubeVideoFormat): string {
  const parts: string[] = [];
  if (format.resolution) {
    parts.push(format.resolution);
  }
  if (format.fps) {
    parts.push(`${format.fps} fps`);
  }
  if (format.note) {
    parts.push(format.note);
  }
  if (format.bitrate_kbps) {
    parts.push(`${Math.round(format.bitrate_kbps)} kbps`);
  }
  if (format.filesize) {
    parts.push(format.filesize);
  }
  parts.push(`itag ${format.format_id}`);
  return `mp4 • ${parts.join(' • ')}`;
}

export function isYoutubeSource(video: YoutubeNasVideo): boolean {
  return (video.source || '').toLowerCase() === 'youtube';
}

export function videoSourceBadge(video: YoutubeNasVideo): { icon: string; label: string; title: string } {
  if (isYoutubeSource(video)) {
    return { icon: '📺', label: 'YT', title: 'YouTube download' };
  }
  return { icon: '🗃️', label: 'NAS', title: 'NAS video' };
}

export function formatBytes(bytes?: number | null): string {
  if (!bytes || bytes < 0) {
    return '—';
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const units = ['KB', 'MB', 'GB', 'TB'];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value >= 10 ? value.toFixed(0) : value.toFixed(1)} ${units[unitIndex]}`;
}

export function formatDateShort(value?: string | null): string {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function formatDateLong(value?: string | null): string {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  return date.toLocaleString();
}

export function formatDurationSeconds(value?: number | null): string | null {
  if (!value || value < 0) {
    return null;
  }
  const hours = Math.floor(value / 3600);
  const minutes = Math.floor((value % 3600) / 60);
  const seconds = Math.floor(value % 60);
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

export function subtitleBadgeLabel(subtitle: YoutubeNasVideo['subtitles'][number]): string {
  const language =
    resolveSubtitleLanguageLabel(subtitle.language, subtitle.path, subtitle.filename) || '—';
  const format = subtitle.format ? subtitle.format.toUpperCase() : '';
  return `${language} ${format}`.trim();
}

export function subtitleBadgeFlag(subtitle: YoutubeNasVideo['subtitles'][number]): string {
  return resolveSubtitleFlag(subtitle.language, subtitle.path, subtitle.filename);
}

export function findProvider(providers: AcquisitionProvider[], providerId: string): AcquisitionProvider | null {
  return providers.find((provider) => provider.id === providerId) ?? null;
}

export function formatDiscoveryCandidateMeta(candidate: AcquisitionCandidate): string {
  const parts: string[] = [];
  const channel = candidate.contributors.find((value) => value.trim());
  if (channel) {
    parts.push(channel);
  }
  const duration = formatDurationSeconds(candidate.duration_seconds);
  if (duration) {
    parts.push(duration);
  }
  if (candidate.published_at) {
    parts.push(formatDateShort(candidate.published_at));
  }
  if (candidate.source_url) {
    parts.push(candidate.source_url);
  }
  if (candidate.requires_confirmation) {
    parts.push('review required');
  }
  return parts.join(' · ') || 'YouTube search result';
}
