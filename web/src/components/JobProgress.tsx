import { useMemo } from 'react';
import { usePipelineEvents } from '../hooks/usePipelineEvents';
import {
  PipelineJobStatus,
  PipelineStatusResponse,
  ProgressEventPayload
} from '../api/dtos';

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
  const metadata = status?.result?.book_metadata ?? {};
  const metadataEntries = Object.entries(metadata).filter(([, value]) => {
    const normalized = normalizeMetadataValue(value);
    return normalized.length > 0;
  });
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
