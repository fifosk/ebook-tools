import type { JobState } from '../../components/JobList';

export { resolveSubtitleLanguageDefaults } from './subtitleLanguageDefaultsUtils';
export type { SubtitleLanguageDefaults } from './subtitleLanguageDefaultsUtils';
export { resolveSubtitlePrefillValues } from './subtitlePrefillUtils';
export type { SubtitlePrefillValues } from './subtitlePrefillUtils';
export {
  basenameFromPath,
  isAssSubtitleSelection,
  pickLatestSubtitleSource,
  resolveSubtitleMetadataSourceName,
  resolveSubtitleSourceFormat,
  resolveSubtitleSourceSelectionAfterRefresh,
  sortSubtitleSourcesForSelection
} from './subtitleSourceUtils';
export { formatSubmittedSubtitleSummary } from './subtitleSubmitFeedbackUtils';
export type { SubmittedSubtitleSummary } from './subtitleSubmitFeedbackUtils';
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
