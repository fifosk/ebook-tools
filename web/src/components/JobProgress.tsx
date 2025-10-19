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

export function JobProgress({ jobId, status, latestEvent, onEvent }: Props) {
  const isTerminal = useMemo(() => {
    if (!status) {
      return false;
    }
    return TERMINAL_STATES.includes(status.status);
  }, [status]);

  usePipelineEvents(jobId, !isTerminal, onEvent);

  const event = latestEvent ?? status?.latest_event ?? undefined;

  return (
    <div className="job-card" aria-live="polite">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <h3 style={{ marginTop: 0 }}>Job {jobId}</h3>
        <span className="job-status" data-state={status?.status ?? 'pending'}>
          {status?.status ?? 'pending'}
        </span>
      </div>
      <p>
        <strong>Created:</strong> {formatDate(status?.created_at ?? null)}
        <br />
        <strong>Started:</strong> {formatDate(status?.started_at)}
        <br />
        <strong>Completed:</strong> {formatDate(status?.completed_at)}
      </p>
      {status?.error ? <div className="alert">{status.error}</div> : null}
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
