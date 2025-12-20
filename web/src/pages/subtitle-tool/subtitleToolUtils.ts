import type { JobState } from '../../components/JobList';

export function formatSubtitleRetryCounts(counts?: Record<string, number> | null): string | null {
  if (!counts) {
    return null;
  }
  const parts = Object.entries(counts)
    .filter(([, count]) => typeof count === 'number' && count > 0)
    .sort((a, b) => {
      const delta = (b[1] || 0) - (a[1] || 0);
      return delta !== 0 ? delta : a[0].localeCompare(b[0]);
    })
    .map(([reason, count]) => `${reason} (${count})`);
  return parts.length ? parts.join(', ') : null;
}

export function extractSubtitleFile(status: JobState['status']): {
  name: string;
  relativePath: string | null;
  url: string | null;
} | null {
  const generated = status.generated_files;
  if (!generated || typeof generated !== 'object') {
    return null;
  }
  const record = generated as Record<string, unknown>;
  const files = record.files;
  if (!Array.isArray(files)) {
    return null;
  }
  for (const entry of files) {
    if (!entry || typeof entry !== 'object') {
      continue;
    }
    const file = entry as Record<string, unknown>;
    const type = typeof file.type === 'string' ? file.type : undefined;
    if ((type ?? '').toLowerCase() !== 'subtitle') {
      continue;
    }
    const name = typeof file.name === 'string' ? file.name : 'subtitle';
    const relativePath = typeof file.relative_path === 'string' ? file.relative_path : null;
    const url = typeof file.url === 'string' ? file.url : null;
    return { name, relativePath, url };
  }
  return null;
}

export function basenameFromPath(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return '';
  }
  const normalized = trimmed.replace(/\\/g, '/');
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

export function normalizeLanguageInput(value: string): string {
  return value.trim() || '';
}

type ParsedTimecode = {
  seconds: number;
  normalized: string;
};

function parseAbsoluteTimecode(value: string): ParsedTimecode | null {
  const trimmed = value.trim();
  const match = trimmed.match(/^(\\d+):(\\d{1,2})(?::(\\d{1,2}))?$/);
  if (!match) {
    return null;
  }
  const [, primary, secondary, tertiary] = match;
  const first = Number(primary);
  const second = Number(secondary);
  const third = typeof tertiary === 'string' ? Number(tertiary) : null;

  if ([first, second, third ?? 0].some((component) => !Number.isInteger(component) || component < 0)) {
    return null;
  }
  if (third !== null) {
    if (second >= 60 || third >= 60) {
      return null;
    }
    const hours = first;
    const minutes = second;
    const seconds = third;
    const normalized = [hours, minutes, seconds]
      .map((component) => component.toString().padStart(2, '0'))
      .join(':');
    return {
      seconds: hours * 3600 + minutes * 60 + seconds,
      normalized
    };
  }

  if (second >= 60) {
    return null;
  }
  const minutes = first;
  const seconds = second;
  return {
    seconds: minutes * 60 + seconds,
    normalized: `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
  };
}

function formatRelativeDuration(totalSeconds: number): string {
  const clamped = Math.max(0, Math.floor(totalSeconds));
  if (clamped >= 3600) {
    const hours = Math.floor(clamped / 3600);
    const remainder = clamped % 3600;
    const minutes = Math.floor(remainder / 60);
    const seconds = remainder % 60;
    return [hours, minutes, seconds].map((component) => component.toString().padStart(2, '0')).join(':');
  }
  const minutes = Math.floor(clamped / 60);
  const seconds = clamped % 60;
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

function parseRelativeTimecode(value: string): ParsedTimecode | null {
  const trimmed = value.trim();
  if (/^\\d+$/.test(trimmed)) {
    const minutes = Number(trimmed);
    if (!Number.isInteger(minutes) || minutes < 0) {
      return null;
    }
    const totalSeconds = minutes * 60;
    return {
      seconds: totalSeconds,
      normalized: formatRelativeDuration(totalSeconds)
    };
  }
  const absolute = parseAbsoluteTimecode(trimmed);
  if (!absolute) {
    return null;
  }
  return {
    seconds: absolute.seconds,
    normalized: formatRelativeDuration(absolute.seconds)
  };
}

export function normalizeSubtitleTimecodeInput(
  value: string,
  options: { allowRelative?: boolean; emptyValue?: string } = {}
): string | null {
  const { allowRelative = false, emptyValue = '' } = options;
  const trimmed = value.trim();
  if (!trimmed) {
    return emptyValue;
  }
  if (allowRelative && trimmed.startsWith('+')) {
    const relative = parseRelativeTimecode(trimmed.slice(1));
    if (!relative) {
      return null;
    }
    return `+${relative.normalized}`;
  }
  const absolute = parseAbsoluteTimecode(trimmed);
  if (!absolute) {
    return null;
  }
  return absolute.normalized;
}

export function formatTimecodeFromSeconds(value: number | null | undefined): string {
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
