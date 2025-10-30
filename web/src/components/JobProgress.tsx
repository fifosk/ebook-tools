import { useCallback, useEffect, useMemo, useState } from 'react';
import { usePipelineEvents } from '../hooks/usePipelineEvents';
import {
  PipelineJobStatus,
  PipelineStatusResponse,
  ProgressEventPayload
} from '../api/dtos';
import { buildStorageUrl } from '../api/client';

const TERMINAL_STATES: PipelineJobStatus[] = ['completed', 'failed', 'cancelled'];
const FALLBACK_COVER_URL = '/assets/default-cover.png';

type Props = {
  jobId: string;
  status: PipelineStatusResponse | undefined;
  latestEvent: ProgressEventPayload | undefined;
  onEvent: (event: ProgressEventPayload) => void;
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
  onDelete: () => void;
  onReload: () => void;
  isReloading?: boolean;
  isMutating?: boolean;
  canManage: boolean;
};

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

const METADATA_LABELS: Record<string, string> = {
  book_title: 'Title',
  book_author: 'Author',
  book_year: 'Publication year',
  book_summary: 'Summary',
  book_cover_file: 'Cover file'
};

const TUNING_LABELS: Record<string, string> = {
  hardware_profile: 'Hardware profile',
  detected_cpu_cores: 'Detected CPU cores',
  detected_memory_gib: 'Detected memory (GiB)',
  pipeline_mode: 'Pipeline mode enabled',
  thread_count: 'Translation threads',
  translation_pool_workers: 'Translation pool workers',
  translation_pool_mode: 'Worker pool mode',
  queue_size: 'Translation queue size',
  job_worker_slots: 'Job worker slots',
  job_max_workers: 'Configured job workers',
  slide_parallelism: 'Slide parallelism',
  slide_parallel_workers: 'Slide workers'
};

const TUNING_ORDER: string[] = [
  'hardware_profile',
  'detected_cpu_cores',
  'detected_memory_gib',
  'pipeline_mode',
  'thread_count',
  'translation_pool_workers',
  'translation_pool_mode',
  'queue_size',
  'job_worker_slots',
  'job_max_workers',
  'slide_parallelism',
  'slide_parallel_workers'
];

function formatMetadataLabel(key: string): string {
  return METADATA_LABELS[key] ?? key.replace(/_/g, ' ');
}

function normalizeMetadataValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '';
  }
  if (typeof value === 'string') {
    return value.trim();
  }
  return String(value);
}

function formatTuningLabel(key: string): string {
  return TUNING_LABELS[key] ?? key.replace(/_/g, ' ');
}

function formatTuningValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '';
  }
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      return value.toString();
    }
    return Number.isInteger(value) ? value.toString() : value.toFixed(1);
  }
  if (typeof value === 'string') {
    return value;
  }
  return JSON.stringify(value);
}

type CoverAsset =
  | { type: 'external'; url: string }
  | { type: 'storage'; path: string; raw: string }
  | null;

function isExternalAsset(path: string): boolean {
  const lower = path.trim().toLowerCase();
  return lower.startsWith('http://') || lower.startsWith('https://') || lower.startsWith('data:');
}

function normaliseStoragePath(path: string): string {
  const normalised = path.replace(/\\/g, '/').trim();
  if (!normalised) {
    return '';
  }

  const withoutDrive = normalised.replace(/^[A-Za-z]:/, '');
  const segments = withoutDrive
    .split('/')
    .map((segment) => segment.trim())
    .filter((segment) => segment.length > 0);

  if (segments.length === 0) {
    return '';
  }

  const lowered = segments.map((segment) => segment.toLowerCase());
  const runtimeIndex = lowered.lastIndexOf('runtime');
  if (runtimeIndex >= 0) {
    return segments.slice(runtimeIndex).join('/');
  }

  const booksIndex = lowered.lastIndexOf('books');
  if (booksIndex >= 0) {
    return segments.slice(booksIndex).join('/');
  }

  const storageIndex = lowered.indexOf('storage');
  if (storageIndex >= 0 && storageIndex + 1 < segments.length) {
    return segments.slice(storageIndex + 1).join('/');
  }

  const outputIndex = lowered.indexOf('output');
  if (outputIndex >= 0 && outputIndex + 1 < segments.length) {
    return segments.slice(outputIndex + 1).join('/');
  }

  return segments.join('/');
}

function resolveCoverAsset(metadata: Record<string, unknown>): CoverAsset {
  const rawValue = metadata['book_cover_file'];
  if (typeof rawValue !== 'string') {
    return null;
  }
  const trimmed = rawValue.trim();
  if (!trimmed) {
    return null;
  }
  if (isExternalAsset(trimmed)) {
    return { type: 'external', url: trimmed };
  }
  const relative = normaliseStoragePath(trimmed);
  if (!relative) {
    return { type: 'storage', path: '', raw: trimmed };
  }
  return { type: 'storage', path: relative, raw: trimmed };
}

function formatMetadataValue(key: string, value: unknown, coverAsset: CoverAsset): string {
  const normalized = normalizeMetadataValue(value);
  if (!normalized) {
    return '';
  }
  if (key === 'book_cover_file' && coverAsset) {
    if (coverAsset.type === 'external') {
      return coverAsset.url;
    }
    const relative = coverAsset.path.trim();
    if (relative) {
      return `storage/${relative.replace(/^\/+/, '')}`;
    }
    return coverAsset.raw || normalized;
  }
  return normalized;
}

function sortTuningEntries(entries: [string, unknown][]): [string, unknown][] {
  const order = new Map<string, number>(TUNING_ORDER.map((key, index) => [key, index]));
  return entries
    .slice()
    .sort((a, b) => {
      const rankA = order.get(a[0]) ?? Number.MAX_SAFE_INTEGER;
      const rankB = order.get(b[0]) ?? Number.MAX_SAFE_INTEGER;
      if (rankA === rankB) {
        return a[0].localeCompare(b[0]);
      }
      return rankA - rankB;
    });
}

export function JobProgress({
  jobId,
  status,
  latestEvent,
  onEvent,
  onPause,
  onResume,
  onCancel,
  onDelete,
  onReload,
  isReloading = false,
  isMutating = false,
  canManage
}: Props) {
  const statusValue = status?.status ?? 'pending';
  const isTerminal = useMemo(() => {
    if (!status) {
      return false;
    }
    return TERMINAL_STATES.includes(status.status);
  }, [status]);

  usePipelineEvents(jobId, !isTerminal, onEvent);

  const event = latestEvent ?? status?.latest_event ?? undefined;
  const bookMetadata = status?.result?.book_metadata ?? null;
  const metadata = bookMetadata ?? {};
  const metadataEntries = Object.entries(metadata).filter(([, value]) => {
    const normalized = normalizeMetadataValue(value);
    return normalized.length > 0;
  });
  const coverAsset = useMemo(() => resolveCoverAsset(metadata), [metadata]);
  const coverSources = useMemo(() => {
    if (!coverAsset) {
      return [] as string[];
    }
    if (coverAsset.type === 'external') {
      return [coverAsset.url];
    }

    const sources: string[] = [];
    const unique = new Set<string>();

    const push = (candidate: string | null | undefined) => {
      const trimmed = candidate?.trim();
      if (!trimmed) {
        return;
      }
      if (unique.has(trimmed)) {
        return;
      }
      unique.add(trimmed);
      sources.push(trimmed);
    };

    const normalisedPath = coverAsset.path.trim();
    if (normalisedPath) {
      const stripped = normalisedPath.replace(/^\/+/, '');
      const isGlobalCover = stripped.startsWith('covers/');
      if (isGlobalCover) {
        push(`/storage/${stripped}`);
      } else {
        try {
          push(buildStorageUrl(stripped));
        } catch (error) {
          console.warn('Unable to build storage URL for cover image', error);
        }
        push(`/storage/${stripped}`);
        push(`/${stripped}`);
      }
    }

    const rawValue = coverAsset.raw.trim();
    if (rawValue) {
      if (isExternalAsset(rawValue)) {
        push(rawValue);
      } else if (/storage[\\/]+covers[\\/]+/i.test(rawValue)) {
        const match = rawValue.replace(/\\/g, '/').split('/storage/').pop();
        if (match) {
          const relative = match.replace(/^\/+/, '');
          push(`/storage/${relative}`);
        }
      } else if (rawValue.startsWith('/')) {
        push(rawValue);
      } else {
        push(`/${rawValue}`);
      }
    }

    return sources;
  }, [coverAsset]);
  const [coverSourceIndex, setCoverSourceIndex] = useState(0);
  const coverUrl = coverSources[coverSourceIndex] ?? null;
  const [coverFailed, setCoverFailed] = useState(false);
  useEffect(() => {
    setCoverSourceIndex(0);
    setCoverFailed(false);
  }, [coverSources, bookMetadata]);
  const handleCoverError = useCallback(() => {
    setCoverSourceIndex((currentIndex) => {
      const nextIndex = currentIndex + 1;
      if (nextIndex >= coverSources.length) {
        setCoverFailed(true);
        return currentIndex;
      }
      return nextIndex;
    });
  }, [coverSources.length]);
  const handleCoverRetry = useCallback(() => {
    setCoverFailed(false);
    setCoverSourceIndex(0);
  }, []);
  const coverAltText = useMemo(() => {
    const title = normalizeMetadataValue(metadata['book_title']);
    const author = normalizeMetadataValue(metadata['book_author']);
    if (title && author) {
      return `Cover of ${title} by ${author}`;
    }
    if (title) {
      return `Cover of ${title}`;
    }
    if (author) {
      return `Book cover for ${author}`;
    }
    return 'Book cover preview';
  }, [metadata]);
  const coverPlaceholderMessage = useMemo(() => {
    if (coverFailed) {
      return 'Cover preview could not be loaded.';
    }
    if (coverAsset) {
      return 'Cover preview is not available.';
    }
    return 'Cover image not provided yet.';
  }, [coverAsset, coverFailed]);
  const shouldShowFallbackCover = !coverUrl;
  const displayCoverUrl =
    coverUrl && !coverFailed ? coverUrl : shouldShowFallbackCover ? FALLBACK_COVER_URL : null;
  const coverErrorHandler = displayCoverUrl && displayCoverUrl === coverUrl ? handleCoverError : undefined;
  const tuningEntries = useMemo(() => {
    const tuning = status?.tuning ?? null;
    if (!tuning) {
      return [];
    }
    const filtered = Object.entries(tuning).filter(([, value]) => {
      if (value === null || value === undefined) {
        return false;
      }
      const formatted = formatTuningValue(value);
      return formatted.length > 0;
    });
    return sortTuningEntries(filtered);
  }, [status?.tuning]);
  const translations = status?.result?.written_blocks ?? [];
  const translationsUnavailable = Array.isArray(translations)
    ? translations.length > 0 && translations.every((block) => {
        if (typeof block !== 'string') {
          return false;
        }
        const cleaned = block.trim();
        return cleaned.length === 0 || cleaned.toUpperCase() === 'N/A';
      })
    : false;

  const canPause = canManage && !isTerminal && statusValue !== 'paused';
  const canResume = canManage && statusValue === 'paused';
  const canCancel = canManage && !isTerminal;
  const canDelete = canManage && isTerminal;

  return (
    <div className="job-card" aria-live="polite">
      <div className="job-card__header">
        <div className="job-card__header-title">
          <h3>Job {jobId}</h3>
        </div>
        <div className="job-card__header-actions">
          <span className="job-status" data-state={statusValue}>
            {statusValue}
          </span>
          <div className="job-actions" aria-label={`Actions for job ${jobId}`} aria-busy={isMutating}>
            {canPause ? (
              <button type="button" className="link-button" onClick={onPause} disabled={isMutating}>
                Pause
              </button>
            ) : null}
            {canResume ? (
              <button type="button" className="link-button" onClick={onResume} disabled={isMutating}>
                Resume
              </button>
            ) : null}
            {canCancel ? (
              <button type="button" className="link-button" onClick={onCancel} disabled={isMutating}>
                Cancel
              </button>
            ) : null}
            {canDelete ? (
              <button type="button" className="link-button" onClick={onDelete} disabled={isMutating}>
                Delete
              </button>
            ) : null}
          </div>
        </div>
      </div>
      <p>
        <strong>Created:</strong> {formatDate(status?.created_at ?? null)}
        <br />
        <strong>Started:</strong> {formatDate(status?.started_at)}
        <br />
        <strong>Completed:</strong> {formatDate(status?.completed_at)}
      </p>
      {status?.error ? <div className="alert">{status.error}</div> : null}
      {tuningEntries.length > 0 ? (
        <div>
          <h4>Performance tuning</h4>
          <div className="progress-grid">
            {tuningEntries.map(([key, value]) => (
              <div className="progress-metric" key={key}>
                <strong>{formatTuningLabel(key)}</strong>
                <span>{formatTuningValue(value)}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      {translationsUnavailable ? (
        <div className="alert" role="status">
          Translated content was not returned by the LLM. Verify your model configuration and try reloading once the
          metadata has been refreshed.
        </div>
      ) : null}
      {event ? (
        <div>
          <h4>Latest progress</h4>
          <div className="progress-grid">
            <div className="progress-metric">
              <strong>Event</strong>
              <span>{event.event_type}</span>
            </div>
            <div className="progress-metric">
              <strong>Completed</strong>
              <span>
                {event.snapshot.completed}
                {event.snapshot.total !== null ? ` / ${event.snapshot.total}` : ''}
              </span>
            </div>
            <div className="progress-metric">
              <strong>Speed</strong>
              <span>{event.snapshot.speed.toFixed(2)} items/s</span>
            </div>
            <div className="progress-metric">
              <strong>Elapsed</strong>
              <span>{event.snapshot.elapsed.toFixed(2)} s</span>
            </div>
            <div className="progress-metric">
              <strong>ETA</strong>
              <span>
                {event.snapshot.eta !== null ? `${event.snapshot.eta.toFixed(2)} s` : '—'}
              </span>
            </div>
          </div>
          {event.error ? <div className="alert">{event.error}</div> : null}
        </div>
      ) : (
        <p>No progress events received yet.</p>
      )}
      <div className="job-card__section">
        <h4>Book metadata</h4>
        <div className="metadata-cover-preview">
          {displayCoverUrl ? (
            <img src={displayCoverUrl} alt={coverAltText} onError={coverErrorHandler} />
          ) : (
            <div className="metadata-cover-preview__placeholder" role="status" aria-live="polite">
              <span>{coverPlaceholderMessage}</span>
              {coverFailed && coverUrl ? (
                <button type="button" className="link-button" onClick={handleCoverRetry}>
                  Retry preview
                </button>
              ) : null}
            </div>
          )}
        </div>
        {metadataEntries.length > 0 ? (
          <dl className="metadata-grid">
            {metadataEntries.map(([key, value]) => {
              const formatted = formatMetadataValue(key, value, coverAsset);
              if (!formatted) {
                return null;
              }
              return (
                <div key={key} className="metadata-grid__row">
                  <dt>{formatMetadataLabel(key)}</dt>
                  <dd>{formatted}</dd>
                </div>
              );
            })}
          </dl>
        ) : (
          <p className="job-card__metadata-empty">Metadata is not available yet.</p>
        )}
        <button
          type="button"
          className="link-button"
          onClick={onReload}
          disabled={!canManage || isReloading || isMutating}
          aria-busy={isReloading || isMutating}
          data-variant="metadata-action"
        >
          {isReloading ? 'Reloading…' : 'Reload metadata'}
        </button>
      </div>
      {status?.result ? (
        <details className="job-card__details">
          <summary>View pipeline result payload</summary>
          <pre style={{ overflowX: 'auto' }}>{JSON.stringify(status.result, null, 2)}</pre>
        </details>
      ) : null}
    </div>
  );
}

export default JobProgress;
