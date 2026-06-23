import type { SubtitleJobResultPayload } from '../../api/dtos';
import type { JobState } from '../../components/JobList';
import { resolveSubtitleDownloadUrl } from '../../api/client';
import { getStatusGlyph } from '../../utils/status';
import { extractSubtitleFile, formatSubtitleRetryCounts } from './subtitleJobUtils';

type SubtitleDetails = NonNullable<SubtitleJobResultPayload['subtitle']>;

export type SubtitleJobPresentation = {
  assEmphasisLabel: number | null;
  assFontSizeLabel: number | null;
  batchSetting: number | null;
  canMoveToLibrary: boolean;
  completed: number;
  directUrl: string | null;
  endTimeLabel: string | null;
  event: JobState['latestEvent'] | NonNullable<JobState['status']['latest_event']> | null;
  originalLanguageLabel: string | null;
  outputFormatLabel: string | null;
  resolvedName: string;
  showOriginalSetting: boolean | null;
  stage: string | null;
  statusGlyph: ReturnType<typeof getStatusGlyph>;
  startTimeLabel: string | null;
  total: number | null;
  translationBatchSetting: number | null;
  translationLanguage: string | null;
  translationRetries: string | null;
  transliterationRetries: string | null;
  updatedAt: string | null;
  workerSetting: number | null;
};

export function buildSubtitleJobPresentation(
  job: JobState,
  subtitleDetails: SubtitleDetails | undefined,
  canRequestMoveToLibrary: boolean
): SubtitleJobPresentation {
  const subtitleMetadata = recordOrNull(subtitleDetails?.metadata);
  const statusFile = extractSubtitleFile(job.status);
  const metadataDownloadUrl = stringOrNull(subtitleMetadata?.['download_url']);
  const resolvedRelativePath = resolveRelativePath(
    job.jobId,
    statusFile?.relativePath ?? stringOrNull(subtitleDetails?.relative_path),
    stringOrNull(subtitleDetails?.output_path)
  );
  const resultOutputPath = trimToNull(stringOrNull(subtitleDetails?.output_path));
  const resolvedName =
    statusFile?.name ??
    filenameFromPath(resolvedRelativePath) ??
    filenameFromPath(resultOutputPath) ??
    'subtitle';
  const directUrl =
    statusFile?.url ??
    metadataDownloadUrl ??
    (resolvedRelativePath ? resolveSubtitleDownloadUrl(job.jobId, resolvedRelativePath) : null);
  const event = job.latestEvent ?? job.status.latest_event ?? null;
  const retrySummary = recordOrNull(job.status.retry_summary);
  const subtitleMetadataFromStatus = extractStatusSubtitleMetadata(job);
  const audiobookToggleValue =
    subtitleMetadataFromStatus?.['generate_audio_book'] ?? subtitleMetadata?.['generate_audio_book'];
  const isNarratedSubtitleJob = parseBooleanOn(audiobookToggleValue);
  const isLibraryCandidate =
    job.status.status === 'completed' ||
    (job.status.status === 'paused' && job.status.media_completed === true);

  return {
    assEmphasisLabel: numberOrNull(subtitleMetadata?.['ass_emphasis_scale']),
    assFontSizeLabel: numberOrNull(subtitleMetadata?.['ass_font_size']),
    batchSetting: numberOrNull(subtitleMetadata?.['batch_size']),
    canMoveToLibrary:
      canRequestMoveToLibrary && job.canManage && isNarratedSubtitleJob && isLibraryCandidate,
    completed: event?.snapshot.completed ?? 0,
    directUrl,
    endTimeLabel: stringOrNull(subtitleMetadata?.['end_time_offset_label']),
    event,
    originalLanguageLabel: stringOrNull(subtitleMetadata?.['original_language']),
    outputFormatLabel: uppercaseStringOrNull(subtitleMetadata?.['output_format']),
    resolvedName,
    showOriginalSetting: parseBooleanUnlessExplicitlyOff(subtitleMetadata?.['show_original']),
    stage: stringOrNull(event?.metadata?.stage),
    statusGlyph: getStatusGlyph(job.status.status),
    startTimeLabel: stringOrNull(subtitleMetadata?.['start_time_offset_label']),
    total: event?.snapshot.total ?? null,
    translationBatchSetting: numberOrNull(subtitleMetadata?.['translation_batch_size']),
    translationLanguage: stringOrNull(subtitleMetadata?.['target_language']),
    translationRetries: formatSubtitleRetryCounts(recordNumberCounts(retrySummary?.['translation'])),
    transliterationRetries: formatSubtitleRetryCounts(recordNumberCounts(retrySummary?.['transliteration'])),
    updatedAt: job.status.completed_at
      || job.status.started_at
      || (event ? new Date(event.timestamp * 1000).toISOString() : null),
    workerSetting: numberOrNull(subtitleMetadata?.['workers'])
  };
}

function extractStatusSubtitleMetadata(job: JobState): Record<string, unknown> | null {
  const rawResult = recordOrNull(job.status.result);
  const subtitleSection = recordOrNull(rawResult?.['subtitle']);
  return recordOrNull(subtitleSection?.['metadata']);
}

function resolveRelativePath(
  jobId: string,
  rawRelativePath: string | null,
  rawOutputPath: string | null
): string | null {
  const directRelativePath = trimToNull(rawRelativePath);
  if (directRelativePath) {
    return directRelativePath;
  }
  const outputPath = trimToNull(rawOutputPath);
  if (!outputPath) {
    return null;
  }
  const normalisedOutput = outputPath.replace(/\\\\/g, '/');
  const marker = `/${jobId}/`;
  const markerIndex = normalisedOutput.indexOf(marker);
  if (markerIndex < 0) {
    return null;
  }
  return trimToNull(normalisedOutput.slice(markerIndex + marker.length));
}

function filenameFromPath(path: string | null): string | null {
  return path ? path.split(/[\\\\/]/).filter(Boolean).pop() ?? null : null;
}

function uppercaseStringOrNull(value: unknown): string | null {
  const text = stringOrNull(value);
  return text ? text.toUpperCase() : null;
}

function stringOrNull(value: unknown): string | null {
  return typeof value === 'string' ? trimToNull(value) : null;
}

function trimToNull(value: string | null | undefined): string | null {
  const trimmed = value?.trim() ?? '';
  return trimmed ? trimmed : null;
}

function numberOrNull(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value.trim());
    return Number.isNaN(parsed) ? null : parsed;
  }
  return null;
}

function parseBooleanUnlessExplicitlyOff(value: unknown): boolean | null {
  if (typeof value === 'boolean') {
    return value;
  }
  if (typeof value === 'string') {
    return !['false', '0', 'no', 'off'].includes(value.trim().toLowerCase());
  }
  return null;
}

function parseBooleanOn(value: unknown): boolean {
  if (typeof value === 'boolean') {
    return value;
  }
  if (typeof value === 'string') {
    return ['true', '1', 'yes', 'on'].includes(value.trim().toLowerCase());
  }
  return false;
}

function recordOrNull(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : null;
}

function recordNumberCounts(value: unknown): Record<string, number> | null {
  const record = recordOrNull(value);
  if (!record) {
    return null;
  }
  const counts: Record<string, number> = {};
  for (const [key, count] of Object.entries(record)) {
    if (typeof count === 'number') {
      counts[key] = count;
    }
  }
  return counts;
}
