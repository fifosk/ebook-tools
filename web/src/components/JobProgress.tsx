import { useCallback, useEffect, useMemo, useState } from 'react';
import { usePipelineEvents } from '../hooks/usePipelineEvents';
import {
  PipelineJobStatus,
  PipelineStatusResponse,
  ProgressEventPayload
} from '../api/dtos';
import { buildStorageUrl } from '../api/client';

const TERMINAL_STATES: PipelineJobStatus[] = ['completed', 'failed', 'cancelled'];

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
  | { type: 'storage'; path: string }
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

  const lower = normalised.toLowerCase();
  const markers: Array<{ token: string; dropToken: boolean }> = [
    { token: '/storage/', dropToken: true },
    { token: '/output/', dropToken: false },
    { token: '/runtime/', dropToken: false },
    { token: '/books/', dropToken: false }
  ];

  for (const marker of markers) {
    const index = lower.indexOf(marker.token);
    if (index >= 0) {
      if (marker.dropToken) {
        return normalised.slice(index + marker.token.length).replace(/^\/+/, '');
      }
      return normalised.slice(index + 1).replace(/^\/+/, '');
    }
  }

  return normalised.replace(/^[A-Za-z]:/, '').replace(/^\/+/, '');
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
    return null;
  }
  return { type: 'storage', path: relative };
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
  isMutating = false
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
  const coverUrl = useMemo(() => {
    if (!coverAsset) {
      return null;
    }
    if (coverAsset.type === 'external') {
      return coverAsset.url;
    }
    try {
      return buildStorageUrl(coverAsset.path);
    } catch (error) {
      console.warn('Unable to build storage URL for cover image', error);
      return null;
    }
  }, [coverAsset]);
  const [coverFailed, setCoverFailed] = useState(false);
  useEffect(() => {
    setCoverFailed(false);
  }, [coverUrl, bookMetadata]);
  const handleCoverError = useCallback(() => {
    setCoverFailed(true);
  }, []);
  const handleCoverRetry = useCallback(() => {
    setCoverFailed(false);
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

  const canPause = !isTerminal && statusValue !== 'paused';
  const canResume = statusValue === 'paused';
  const canCancel = !isTerminal;
  const canDelete = isTerminal;

  return (
    <div className="job-card" aria-live="polite">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '0.75rem',
          flexWrap: 'wrap'
        }}
      >
        <div style={{ flexGrow: 1 }}>
          <h3 style={{ marginTop: 0 }}>Job {jobId}</h3>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
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
      <div style={{ marginTop: '1rem' }}>
        <h4>Book metadata</h4>
        <div className="metadata-cover-preview">
          {coverUrl && !coverFailed ? (
            <img src={coverUrl} alt={coverAltText} onError={handleCoverError} />
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
              const normalized = normalizeMetadataValue(value);
              if (!normalized) {
                return null;
              }
              return (
                <div key={key} className="metadata-grid__row">
                  <dt>{formatMetadataLabel(key)}</dt>
                  <dd>{normalized}</dd>
                </div>
              );
            })}
          </dl>
        ) : (
          <p style={{ marginTop: 0 }}>Metadata is not available yet.</p>
        )}
        <button
          type="button"
          className="link-button"
          onClick={onReload}
          disabled={isReloading || isMutating}
          aria-busy={isReloading || isMutating}
          style={{ marginTop: '0.5rem' }}
        >
          {isReloading ? 'Reloading…' : 'Reload metadata'}
        </button>
      </div>
      {status?.result ? (
        <details style={{ marginTop: '1rem' }}>
          <summary>View pipeline result payload</summary>
          <pre style={{ overflowX: 'auto' }}>{JSON.stringify(status.result, null, 2)}</pre>
        </details>
      ) : null}
    </div>
  );
}

export default JobProgress;
