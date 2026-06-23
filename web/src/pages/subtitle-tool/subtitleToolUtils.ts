import type { JobState } from '../../components/JobList';
import type { JobParameterSnapshot, SubtitleSourceEntry } from '../../api/dtos';
import { subtitleFormatFromPath } from '../../utils/subtitles';
import {
  DEFAULT_START_TIME,
  MAX_ASS_EMPHASIS,
  MAX_ASS_FONT_SIZE,
  MIN_ASS_EMPHASIS,
  MIN_ASS_FONT_SIZE
} from './subtitleToolConfig';
import type { SubtitleOutputFormat, SubtitleSourceMode } from './subtitleToolTypes';

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
  const match = trimmed.match(/^(\d+):(\d{1,2})(?::(\d{1,2}))?$/);
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
  if (/^\d+$/.test(trimmed)) {
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

function normalizeOptionalText(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const cleaned = value.trim();
  return cleaned.length > 0 ? cleaned : null;
}

function normalizeFiniteNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

export type SubtitlePrefillValues = {
  targetLanguage: string | null;
  inputLanguage: string | null;
  enableTransliteration: boolean | null;
  showOriginal: boolean | null;
  workerCount: number | null;
  batchSize: number | null;
  translationBatchSize: number | null;
  startTime: string | null;
  endTime: string | null;
  selectedModel: string | null;
  translationProvider: string | null;
  transliterationMode: string | null;
  transliterationModel: string | null;
  sourcePath: string | null;
};

export function resolveSubtitlePrefillValues(
  parameters: JobParameterSnapshot | null | undefined
): SubtitlePrefillValues {
  const targetLanguages = Array.isArray(parameters?.target_languages)
    ? parameters.target_languages
        .map((entry) => (typeof entry === 'string' ? entry.trim() : ''))
        .filter((entry) => entry.length > 0)
    : [];
  const subtitlePath =
    typeof parameters?.subtitle_path === 'string' ? parameters.subtitle_path.trim() : null;
  const fallbackInputFile =
    typeof parameters?.input_file === 'string' && parameters.input_file
      ? parameters.input_file.trim()
      : null;
  const sourcePath = subtitlePath !== null ? subtitlePath : fallbackInputFile;
  return {
    targetLanguage: targetLanguages[0] ?? null,
    inputLanguage: normalizeOptionalText(parameters?.input_language),
    enableTransliteration:
      typeof parameters?.enable_transliteration === 'boolean'
        ? parameters.enable_transliteration
        : null,
    showOriginal: typeof parameters?.show_original === 'boolean' ? parameters.show_original : null,
    workerCount: normalizeFiniteNumber(parameters?.worker_count),
    batchSize: normalizeFiniteNumber(parameters?.batch_size),
    translationBatchSize: normalizeFiniteNumber(parameters?.translation_batch_size),
    startTime:
      typeof parameters?.start_time_offset_seconds === 'number'
        ? formatTimecodeFromSeconds(parameters.start_time_offset_seconds)
        : null,
    endTime:
      typeof parameters?.end_time_offset_seconds === 'number'
        ? formatTimecodeFromSeconds(parameters.end_time_offset_seconds)
        : null,
    selectedModel: normalizeOptionalText(parameters?.llm_model),
    translationProvider: normalizeOptionalText(parameters?.translation_provider),
    transliterationMode: normalizeOptionalText(parameters?.transliteration_mode),
    transliterationModel: normalizeOptionalText(parameters?.transliteration_model),
    sourcePath: sourcePath && sourcePath.length > 0 ? sourcePath : null
  };
}

export type SubtitleSubmitInput = {
  inputLanguage: string;
  targetLanguage: string;
  isAssSelection: boolean;
  sourceMode: SubtitleSourceMode;
  selectedSource: string;
  hasUploadFile: boolean;
  startTime: string;
  endTime: string;
  outputFormat: SubtitleOutputFormat;
  assFontSize: number | '';
  assEmphasis: number | '';
  selectedModel: string;
  translationProvider: string;
  transliterationMode: string;
  transliterationModel: string;
  workerCount: number | '';
  batchSize: number | '';
  translationBatchSize: number | '';
};

export type ResolvedSubtitleSubmitValues = {
  originalLanguage: string;
  targetLanguage: string;
  normalizedStartTime: string;
  normalizedEndTime: string;
  resolvedAssFontSize: number | null;
  resolvedAssEmphasis: number | null;
  selectedModel: string | null;
  translationProvider: string | null;
  transliterationMode: string | null;
  transliterationModel: string | null;
  sourcePath: string | null;
  workerCount: number | null;
  batchSize: number | null;
  translationBatchSize: number | null;
};

export type SubtitleSubmitResolution =
  | { ok: true; values: ResolvedSubtitleSubmitValues }
  | { ok: false; error: string };

export function resolveSubtitleSubmitValues(input: SubtitleSubmitInput): SubtitleSubmitResolution {
  const originalLanguage = normalizeLanguageInput(input.inputLanguage);
  if (!originalLanguage) {
    return { ok: false, error: 'Choose an original language.' };
  }
  if (input.isAssSelection) {
    return {
      ok: false,
      error: 'Generated ASS files cannot be used as sources. Choose the original SRT/VTT or upload a new subtitle.'
    };
  }
  const targetLanguage = normalizeLanguageInput(input.targetLanguage);
  if (!targetLanguage) {
    return { ok: false, error: 'Choose a target language.' };
  }
  const sourcePath = input.selectedSource.trim();
  if (input.sourceMode === 'existing' && !sourcePath) {
    return { ok: false, error: 'Select a subtitle file to process.' };
  }
  if (input.sourceMode === 'upload' && !input.hasUploadFile) {
    return { ok: false, error: 'Choose a subtitle file to upload.' };
  }

  const normalizedStartTime = normalizeSubtitleTimecodeInput(input.startTime, {
    emptyValue: DEFAULT_START_TIME
  });
  if (normalizedStartTime === null) {
    return { ok: false, error: 'Enter a valid start time in MM:SS or HH:MM:SS format.' };
  }
  const normalizedEndTime = normalizeSubtitleTimecodeInput(input.endTime, {
    allowRelative: true,
    emptyValue: ''
  });
  if (normalizedEndTime === null) {
    return { ok: false, error: 'Enter a valid end time in MM:SS, HH:MM:SS, or +offset format.' };
  }

  let resolvedAssFontSize: number | null = null;
  let resolvedAssEmphasis: number | null = null;
  if (input.outputFormat === 'ass') {
    if (typeof input.assFontSize !== 'number' || Number.isNaN(input.assFontSize)) {
      return { ok: false, error: 'Enter a numeric ASS base font size.' };
    }
    resolvedAssFontSize = Math.max(
      MIN_ASS_FONT_SIZE,
      Math.min(MAX_ASS_FONT_SIZE, Math.round(input.assFontSize))
    );

    if (typeof input.assEmphasis !== 'number' || Number.isNaN(input.assEmphasis)) {
      return { ok: false, error: 'Enter a numeric ASS emphasis scale.' };
    }
    resolvedAssEmphasis = Math.max(
      MIN_ASS_EMPHASIS,
      Math.min(MAX_ASS_EMPHASIS, Math.round(input.assEmphasis * 100) / 100)
    );
  }

  return {
    ok: true,
    values: {
      originalLanguage,
      targetLanguage,
      normalizedStartTime,
      normalizedEndTime,
      resolvedAssFontSize,
      resolvedAssEmphasis,
      selectedModel: normalizeOptionalText(input.selectedModel),
      translationProvider: normalizeOptionalText(input.translationProvider),
      transliterationMode: normalizeOptionalText(input.transliterationMode),
      transliterationModel: normalizeOptionalText(input.transliterationModel),
      sourcePath: input.sourceMode === 'existing' ? sourcePath : null,
      workerCount: typeof input.workerCount === 'number' && input.workerCount > 0 ? input.workerCount : null,
      batchSize: typeof input.batchSize === 'number' && input.batchSize > 0 ? input.batchSize : null,
      translationBatchSize:
        typeof input.translationBatchSize === 'number' && input.translationBatchSize > 0
          ? input.translationBatchSize
          : null
    }
  };
}

function subtitleSourceFormat(entry: SubtitleSourceEntry): string {
  return (entry.format || subtitleFormatFromPath(entry.path) || '').toLowerCase();
}

function parseModifiedTime(value: string | null | undefined): number {
  if (!value) {
    return 0;
  }
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

export function sortSubtitleSourcesForSelection(sources: SubtitleSourceEntry[]): SubtitleSourceEntry[] {
  return [...sources]
    .map((entry, index) => ({ entry, index }))
    .sort((left, right) => {
      const leftWeight = subtitleSourceFormat(left.entry) === 'ass' ? 1 : 0;
      const rightWeight = subtitleSourceFormat(right.entry) === 'ass' ? 1 : 0;
      if (leftWeight !== rightWeight) {
        return leftWeight - rightWeight;
      }
      return left.index - right.index;
    })
    .map(({ entry }) => entry);
}

export function pickLatestSubtitleSource(sources: SubtitleSourceEntry[]): string {
  const preferred = sources.filter((item) => subtitleSourceFormat(item) !== 'ass');
  const pool = preferred.length > 0 ? preferred : sources;
  if (pool.length === 0) {
    return '';
  }
  return pool.reduce<string>((latest, candidate) => {
    if (!latest) {
      return candidate.path;
    }
    const latestEntry = pool.find((item) => item.path === latest) ?? candidate;
    const latestTs = parseModifiedTime(latestEntry.modified_at);
    const candidateTs = parseModifiedTime(candidate.modified_at);
    if (candidateTs > latestTs) {
      return candidate.path;
    }
    if (candidateTs === latestTs && candidate.path.localeCompare(latest) < 0) {
      return candidate.path;
    }
    return latest;
  }, '');
}

export type SubmittedSubtitleSummary = {
  jobId: string;
  workerCount: number | null;
  batchSize: number | null;
  translationBatchSize: number | null;
  startTime: string;
  defaultStartTime: string;
  endTime: string | null;
  model: string | null;
  format: SubtitleOutputFormat | null;
  assFontSize: number | null;
  assEmphasis: number | null;
};

export function formatSubmittedSubtitleSummary(summary: SubmittedSubtitleSummary): string {
  const details: string[] = [];
  if (summary.workerCount) {
    details.push(`${summary.workerCount} thread${summary.workerCount === 1 ? '' : 's'}`);
  }
  if (summary.batchSize) {
    details.push(`batch size ${summary.batchSize}`);
  }
  if (summary.translationBatchSize) {
    details.push(`LLM batch ${summary.translationBatchSize}`);
  }
  if (summary.startTime && summary.startTime !== summary.defaultStartTime) {
    details.push(`starting at ${summary.startTime}`);
  }
  if (summary.endTime) {
    const display = summary.endTime.startsWith('+')
      ? `ending after ${summary.endTime.slice(1)}`
      : `ending at ${summary.endTime}`;
    details.push(display);
  }
  if (summary.model) {
    details.push(`LLM ${summary.model}`);
  }
  if (summary.format) {
    const label = summary.format === 'ass' ? 'ASS subtitles' : 'SRT subtitles';
    details.push(label);
    if (summary.format === 'ass' && summary.assFontSize) {
      details.push(`font size ${summary.assFontSize}`);
    }
    if (summary.format === 'ass' && summary.assEmphasis) {
      details.push(`scale ${summary.assEmphasis}\u00d7`);
    }
  }
  if (details.length === 0) {
    return `Submitted subtitle job ${summary.jobId} using auto-detected concurrency. Live status appears in the Jobs tab.`;
  }
  const detailText =
    details.length === 1
      ? details[0]
      : `${details.slice(0, -1).join(', ')} and ${details[details.length - 1]}`;
  return `Submitted subtitle job ${summary.jobId} using ${detailText}. Live status appears in the Jobs tab.`;
}
