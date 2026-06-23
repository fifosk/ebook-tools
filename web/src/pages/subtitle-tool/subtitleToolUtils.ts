import type { JobState } from '../../components/JobList';
import type { SubtitleSourceEntry } from '../../api/dtos';
import { normalizeLanguageLabel } from '../../utils/languages';
import { subtitleFormatFromPath } from '../../utils/subtitles';
import type { SubtitleOutputFormat, SubtitleSourceMode } from './subtitleToolTypes';

export { resolveSubtitlePrefillValues } from './subtitlePrefillUtils';
export type { SubtitlePrefillValues } from './subtitlePrefillUtils';
export {
  buildSubtitleSubmitFormData,
  formatTimecodeFromSeconds,
  normalizeLanguageInput,
  normalizeSubtitleTimecodeInput,
  resolveSubtitleSubmitValues
} from './subtitleSubmitUtils';
export type {
  ResolvedSubtitleSubmitValues,
  SubtitleSubmitFormDataInput,
  SubtitleSubmitInput,
  SubtitleSubmitResolution
} from './subtitleSubmitUtils';

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

export type SubtitleMetadataDraftUpdater = (draft: Record<string, unknown>) => void;

export function updateSubtitleMediaMetadataDraft(
  current: Record<string, unknown> | null,
  updater: SubtitleMetadataDraftUpdater
): Record<string, unknown> {
  const next: Record<string, unknown> = current ? { ...current } : {};
  updater(next);
  return next;
}

export function updateSubtitleMediaMetadataSection(
  current: Record<string, unknown> | null,
  sectionKey: string,
  updater: SubtitleMetadataDraftUpdater
): Record<string, unknown> {
  return updateSubtitleMediaMetadataDraft(current, (draft) => {
    const currentSection = coerceRecord(draft[sectionKey]);
    const nextSection: Record<string, unknown> = currentSection ? { ...currentSection } : {};
    updater(nextSection);
    draft[sectionKey] = nextSection;
  });
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

export type SubtitleLanguageDefaults = {
  fetchedLanguages: string[];
  inputLanguage: string | null;
};

export function resolveSubtitleLanguageDefaults(
  config: Record<string, unknown> | null | undefined,
  currentInputLanguage: string
): SubtitleLanguageDefaults {
  const targetLanguages = Array.isArray(config?.['target_languages'])
    ? (config['target_languages'] as unknown[])
    : [];
  const fetchedLanguages = targetLanguages
    .map((language) => (typeof language === 'string' ? normalizeLanguageLabel(language) : ''))
    .filter((language) => language.length > 0);
  const defaultInput = normalizeLanguageLabel(
    typeof config?.['input_language'] === 'string' ? config['input_language'] : ''
  );
  return {
    fetchedLanguages,
    inputLanguage: defaultInput && !currentInputLanguage ? defaultInput : null
  };
}

export function resolveSubtitleSourceFormat(entry: SubtitleSourceEntry | null | undefined): string {
  if (!entry) {
    return '';
  }
  return (entry.format || subtitleFormatFromPath(entry.path) || '').toLowerCase();
}

export function isAssSubtitleSelection(
  sourceMode: SubtitleSourceMode,
  selectedSourceEntry: SubtitleSourceEntry | null | undefined
): boolean {
  return sourceMode === 'existing' && resolveSubtitleSourceFormat(selectedSourceEntry) === 'ass';
}

export function resolveSubtitleMetadataSourceName(input: {
  sourceMode: SubtitleSourceMode;
  uploadFileName?: string | null;
  selectedSourceName?: string | null;
  selectedSourcePath: string;
}): string {
  if (input.sourceMode === 'upload') {
    return input.uploadFileName ?? '';
  }
  return input.selectedSourceName ?? (input.selectedSourcePath ? basenameFromPath(input.selectedSourcePath) : '');
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
      const leftWeight = resolveSubtitleSourceFormat(left.entry) === 'ass' ? 1 : 0;
      const rightWeight = resolveSubtitleSourceFormat(right.entry) === 'ass' ? 1 : 0;
      if (leftWeight !== rightWeight) {
        return leftWeight - rightWeight;
      }
      return left.index - right.index;
    })
    .map(({ entry }) => entry);
}

export function pickLatestSubtitleSource(sources: SubtitleSourceEntry[]): string {
  const preferred = sources.filter((item) => resolveSubtitleSourceFormat(item) !== 'ass');
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

export function resolveSubtitleSourceSelectionAfterRefresh({
  sources,
  currentSelection,
  resetSelection,
}: {
  sources: SubtitleSourceEntry[];
  currentSelection: string;
  resetSelection: boolean;
}): string {
  if (!resetSelection && currentSelection && sources.some((entry) => entry.path === currentSelection)) {
    return currentSelection;
  }
  return pickLatestSubtitleSource(sources);
}

export function selectMissingCompletedSubtitleJobs<T>(
  jobs: JobState[],
  jobResults: Record<string, T>
): JobState[] {
  return jobs.filter(
    (job) =>
      job.status.job_type === 'subtitle' &&
      job.status.status === 'completed' &&
      jobResults[job.jobId] === undefined
  );
}

export function sortSubtitleJobsNewestFirst(jobs: JobState[]): JobState[] {
  return [...jobs].sort((a, b) => {
    const left = new Date(a.status.created_at).getTime();
    const right = new Date(b.status.created_at).getTime();
    return right - left;
  });
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
