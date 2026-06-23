import {
  DEFAULT_LANGUAGE_FLAG,
  resolveLanguageFlag,
  resolveLanguageName,
} from '../../constants/languageCodes';
import { getStatusGlyph } from '../../utils/status';
import { getJobTypeGlyph, isTvSeriesMetadata } from '../../utils/jobGlyphs';
import { resolveProgressStage } from '../../utils/progressEvents';
import { coerceNumber } from '../job-progress/jobProgressUtils';
import type { JobState } from '../JobList';
import { coerceRecord, readNestedValue } from '../player-panel/helpers';

const SIDEBAR_STAGE_GLYPHS: Record<string, { icon: string; tooltip: string }> = {
  'stitching.start': { icon: '🧵', tooltip: 'Stitching batches' },
  'stitching.done': { icon: '🧵', tooltip: 'Stitching complete' },
  'nas.mirror.start': { icon: '🗄️', tooltip: 'Copying stitched output to NAS' },
  'nas.mirror.done': { icon: '🗄️', tooltip: 'NAS copy complete' },
};

export function isPipelineView(view: unknown): boolean {
  return typeof view === 'string' && view.startsWith('pipeline:');
}

function resolveSubtitleMetadata(status: JobState['status']): Record<string, unknown> | null {
  if (status.job_type !== 'subtitle') {
    return null;
  }
  const rawResult = status.result as Record<string, unknown> | null;
  if (!rawResult) {
    return null;
  }
  const subtitleSection = rawResult['subtitle'];
  if (!subtitleSection || typeof subtitleSection !== 'object') {
    return null;
  }
  const metadata = (subtitleSection as Record<string, unknown>)['metadata'];
  return metadata && typeof metadata === 'object' ? (metadata as Record<string, unknown>) : null;
}

function resolveSubtitleTargetLanguage(status: JobState['status']): string | null {
  if (status.job_type !== 'subtitle') {
    return null;
  }
  const metadata = resolveSubtitleMetadata(status);
  if (!metadata) {
    return null;
  }
  const target = (metadata as Record<string, unknown>)['target_language'];
  return typeof target === 'string' && target.trim() ? target.trim() : null;
}

export function resolveSidebarLanguage(job: JobState): { label: string; tooltip?: string; flag?: string } {
  const parameters = job.status.parameters;
  const rawLanguages = parameters?.target_languages;
  const firstLanguage =
    Array.isArray(rawLanguages) && rawLanguages.length > 0
      ? rawLanguages.find((value) => typeof value === 'string' && value.trim().length > 0)
      : null;
  const singleLanguage = (() => {
    const raw =
      parameters && typeof parameters === 'object'
        ? (parameters as Record<string, unknown>)['target_language']
        : null;
    return typeof raw === 'string' ? raw.trim() : null;
  })();
  const normalized =
    Array.isArray(rawLanguages) && rawLanguages.length > 0
      ? rawLanguages
          .map((value) => (typeof value === 'string' ? value.trim() : ''))
          .filter((value) => value.length > 0)
      : [];
  if (singleLanguage) {
    normalized.push(singleLanguage);
  }
  const resolvedLanguages = normalized.map((language) => resolveLanguageName(language) ?? language);

  if (resolvedLanguages.length > 0) {
    return {
      label:
        resolvedLanguages.length > 1
          ? `${resolvedLanguages[0]} +${resolvedLanguages.length - 1}`
          : resolvedLanguages[0],
      tooltip: resolvedLanguages.join(', '),
      flag: resolveLanguageFlag(firstLanguage ?? singleLanguage ?? resolvedLanguages[0]) ?? DEFAULT_LANGUAGE_FLAG,
    };
  }

  const fallback = resolveSubtitleTargetLanguage(job.status);
  if (fallback) {
    const resolved = resolveLanguageName(fallback) ?? fallback;
    return { label: resolved, flag: resolveLanguageFlag(fallback) ?? DEFAULT_LANGUAGE_FLAG };
  }

  return { label: `Job ${job.jobId}` };
}

function normalizeLabel(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function filenameStem(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const normalized = value.trim();
  if (!normalized) {
    return null;
  }
  const basename = normalized.split(/[/\\]/).pop() ?? normalized;
  const parts = basename.split('.');
  if (parts.length > 1) {
    parts.pop();
  }
  const stem = parts.join('.');
  return stem || basename;
}

function truncateLabel(label: string, maxLength = 28): string {
  if (label.length <= maxLength) {
    return label;
  }
  return `${label.slice(0, Math.max(1, maxLength - 1))}…`;
}

function resolveMetadataTitle(metadata: Record<string, unknown> | null | undefined): string | null {
  if (!metadata) {
    return null;
  }
  return (
    normalizeLabel(metadata['job_label']) ||
    normalizeLabel(metadata['jobLabel']) ||
    normalizeLabel(metadata['book_title']) ||
    normalizeLabel(metadata['title']) ||
    normalizeLabel(metadata['book_name']) ||
    normalizeLabel(metadata['name']) ||
    normalizeLabel(metadata['book_topic']) ||
    normalizeLabel(metadata['topic'])
  );
}

function resolveBookLabel(job: JobState): string | null {
  const status = job.status as JobState['status'] & { job_label?: string | null };
  const explicit = normalizeLabel(status.job_label ?? (status as unknown as Record<string, unknown>)['jobLabel']);
  const parameters = status.parameters as Record<string, unknown> | null | undefined;
  const paramMetadata =
    parameters &&
    typeof parameters === 'object' &&
    typeof (parameters['media_metadata'] ?? parameters['book_metadata']) === 'object'
      ? ((parameters['media_metadata'] ?? parameters['book_metadata']) as Record<string, unknown>)
      : null;
  const baseOutput =
    parameters && typeof parameters === 'object' ? (parameters['base_output_file'] as string | null | undefined) : null;
  const inputFile =
    parameters && typeof parameters === 'object' ? (parameters['input_file'] as string | null | undefined) : null;
  const result = status.result as Record<string, unknown> | null;
  const resultMetadata =
    result && typeof result === 'object'
      ? typeof (result['media_metadata'] ?? result['book_metadata']) === 'object'
        ? ((result['media_metadata'] ?? result['book_metadata']) as Record<string, unknown>)
        : typeof result['metadata'] === 'object'
          ? (result['metadata'] as Record<string, unknown>)
          : null
      : null;
  const pipelineConfig =
    result && typeof result === 'object' && typeof result['pipeline_config'] === 'object'
      ? (result['pipeline_config'] as Record<string, unknown>)
      : null;

  return (
    explicit ||
    resolveMetadataTitle(paramMetadata) ||
    resolveMetadataTitle(pipelineConfig) ||
    resolveMetadataTitle(resultMetadata) ||
    filenameStem(baseOutput ?? undefined) ||
    filenameStem(inputFile ?? undefined)
  );
}

function resolveSubtitleLabel(job: JobState): string | null {
  const status = job.status as JobState['status'] & { job_label?: string | null; jobLabel?: string | null };
  const explicit = normalizeLabel(status.job_label ?? (status as unknown as Record<string, unknown>)['jobLabel']);
  if (explicit) {
    return explicit;
  }
  const metadata = resolveSubtitleMetadata(job.status);
  const metaName =
    normalizeLabel(metadata?.['input_file']) ||
    normalizeLabel(metadata?.['source']) ||
    normalizeLabel(metadata?.['subtitle_name']);
  if (metaName) {
    return filenameStem(metaName);
  }
  const parameters = job.status.parameters as Record<string, unknown> | null | undefined;
  const subtitlePath =
    parameters && typeof parameters === 'object' ? (parameters['subtitle_path'] as string | null | undefined) : null;
  if (subtitlePath) {
    return filenameStem(subtitlePath);
  }
  return null;
}

function resolveVideoLabel(job: JobState): string | null {
  const result = job.status.result as Record<string, unknown> | null;
  if (result && typeof result === 'object') {
    const dub = result['youtube_dub'];
    if (dub && typeof dub === 'object') {
      const dubMetadata = dub as Record<string, unknown>;
      const videoPath =
        normalizeLabel(dubMetadata['video_path']) ||
        normalizeLabel(dubMetadata['source_subtitle_path']) ||
        normalizeLabel(dubMetadata['subtitle_path']);
      if (videoPath) {
        return filenameStem(videoPath);
      }
    }
  }
  const parameters = job.status.parameters as Record<string, unknown> | null | undefined;
  const videoPath =
    parameters && typeof parameters === 'object' ? (parameters['video_path'] as string | null | undefined) : null;
  const subtitlePath =
    parameters && typeof parameters === 'object' ? (parameters['subtitle_path'] as string | null | undefined) : null;
  return filenameStem(videoPath ?? undefined) ?? filenameStem(subtitlePath ?? undefined);
}

export function resolveSidebarLabel(job: JobState): { label: string; tooltip: string } {
  let candidate: string | null = null;
  switch (job.status.job_type) {
    case 'pipeline':
    case 'book':
      candidate = resolveBookLabel(job);
      break;
    case 'subtitle':
      candidate = resolveSubtitleLabel(job);
      break;
    case 'youtube_dub':
      candidate = resolveVideoLabel(job);
      break;
    default:
      candidate = resolveBookLabel(job) ?? resolveSubtitleLabel(job) ?? resolveVideoLabel(job);
      break;
  }
  if (!candidate) {
    const fallbackLanguage = resolveSidebarLanguage(job);
    candidate = fallbackLanguage.label ?? `Job ${job.jobId}`;
  }
  const normalized = candidate.trim();
  const truncated = truncateLabel(normalized);
  return { label: truncated, tooltip: normalized };
}

export function resolveSidebarStatus(value: string): { icon: string; tooltip: string } {
  const glyph = getStatusGlyph(value);
  return { icon: glyph.icon, tooltip: glyph.label };
}

export function resolveSidebarStage(job: JobState): { icon: string; tooltip: string } | null {
  const event = job.latestEvent ?? job.status.latest_event ?? null;
  const metadata = event?.metadata;
  if (!metadata || typeof metadata !== 'object') {
    return null;
  }
  const stageRaw = (metadata as Record<string, unknown>)['stage'];
  const stage = typeof stageRaw === 'string' ? stageRaw.trim() : '';
  if (!stage) {
    return null;
  }
  return SIDEBAR_STAGE_GLYPHS[stage] ?? null;
}

function resolveJobTvMetadata(job: JobState): Record<string, unknown> | null {
  const payload = job.status?.result ?? null;
  if (!payload || typeof payload !== 'object') {
    const parameters = job.status?.parameters ?? null;
    if (parameters && typeof parameters === 'object') {
      return coerceRecord((parameters as Record<string, unknown>)['media_metadata']);
    }
    return null;
  }
  const record = payload as Record<string, unknown>;
  const candidate =
    readNestedValue(record, ['youtube_dub', 'media_metadata']) ??
    readNestedValue(record, ['subtitle', 'metadata', 'media_metadata']) ??
    readNestedValue(record, ['result', 'youtube_dub', 'media_metadata']) ??
    readNestedValue(record, ['result', 'subtitle', 'metadata', 'media_metadata']) ??
    readNestedValue(record, ['request', 'media_metadata']) ??
    readNestedValue(record, ['media_metadata']) ??
    (job.status?.parameters && typeof job.status.parameters === 'object'
      ? (job.status.parameters as Record<string, unknown>)['media_metadata']
      : null) ??
    null;
  return coerceRecord(candidate);
}

export function resolveJobGlyph(job: JobState): { icon: string; label: string; variant?: 'youtube' | 'tv' } {
  const tvMetadata = resolveJobTvMetadata(job);
  const isTvSeries = isTvSeriesMetadata(tvMetadata);
  return getJobTypeGlyph(job.status.job_type, { isTvSeries });
}

export function resolveSidebarProgress(job: JobState): number | null {
  if (!job.status || job.status.status !== 'running') {
    return null;
  }

  const playableEvent = job.latestPlayableEvent ?? null;
  if (playableEvent?.snapshot) {
    const { completed, total } = playableEvent.snapshot;
    if (
      typeof completed === 'number' &&
      typeof total === 'number' &&
      Number.isFinite(completed) &&
      Number.isFinite(total) &&
      total > 0
    ) {
      const ratio = completed / total;
      if (Number.isFinite(ratio) && ratio >= 0) {
        return Math.min(100, Math.max(0, Math.round(ratio * 100)));
      }
    }
  }

  const generated = coerceRecord(job.status.generated_files);
  const mediaBatchStats = generated ? coerceRecord(generated['media_batch_stats']) : null;
  if (mediaBatchStats) {
    const itemsCompleted = coerceNumber(mediaBatchStats['items_completed']);
    const itemsTotal = coerceNumber(mediaBatchStats['items_total']);
    if (
      typeof itemsCompleted === 'number' &&
      typeof itemsTotal === 'number' &&
      Number.isFinite(itemsCompleted) &&
      Number.isFinite(itemsTotal) &&
      itemsTotal > 0
    ) {
      const ratio = itemsCompleted / itemsTotal;
      if (Number.isFinite(ratio) && ratio >= 0) {
        return Math.min(100, Math.max(0, Math.round(ratio * 100)));
      }
    }
  }

  const preferredEvent = job.latestMediaEvent ?? null;
  const fallbackEvent = job.latestEvent ?? job.status.latest_event ?? null;
  const fallbackStage = resolveProgressStage(fallbackEvent);
  const isTranslationStage = fallbackStage === 'translation';
  const event = preferredEvent ?? (!isTranslationStage ? fallbackEvent : null);
  const snapshot = event?.snapshot;
  if (!snapshot) {
    return null;
  }
  const { completed, total } = snapshot;
  if (
    typeof completed !== 'number' ||
    typeof total !== 'number' ||
    !Number.isFinite(completed) ||
    !Number.isFinite(total) ||
    total <= 0
  ) {
    return null;
  }
  const ratio = completed / total;
  if (!Number.isFinite(ratio) || ratio < 0) {
    return null;
  }
  return Math.min(100, Math.max(0, Math.round(ratio * 100)));
}

export function resolveImageWaitStatus(job: JobState): { icon: string; tooltip: string; percent: number | null } | null {
  const stats = job.status.image_generation ?? null;
  if (!stats || !stats.enabled) {
    return null;
  }
  if (job.status.status !== 'running') {
    return null;
  }
  const expected = stats.expected;
  const generated = stats.generated;
  const sentenceTotal = stats.sentence_total;
  if (
    typeof expected !== 'number' ||
    !Number.isFinite(expected) ||
    expected <= 0 ||
    typeof generated !== 'number' ||
    !Number.isFinite(generated) ||
    typeof sentenceTotal !== 'number' ||
    !Number.isFinite(sentenceTotal)
  ) {
    return null;
  }
  const event = job.latestEvent ?? job.status.latest_event ?? null;
  const completed = event?.snapshot?.completed;
  if (typeof completed !== 'number' || !Number.isFinite(completed)) {
    return null;
  }
  if (completed < sentenceTotal) {
    return null;
  }
  if (generated >= expected) {
    return null;
  }
  const percent =
    typeof stats.percent === 'number' && Number.isFinite(stats.percent)
      ? stats.percent
      : Math.round((generated / expected) * 100);
  return {
    icon: '🖼️',
    tooltip: `Waiting for images (${generated}/${expected})`,
    percent,
  };
}
