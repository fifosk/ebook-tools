import type { ProgressEventPayload } from '../../api/dtos';
import type { ProgressCount } from './jobProgressUtils';

type JobProgressLatestSectionProps = {
  event: ProgressEventPayload | undefined;
  latestPlayableEvent?: ProgressEventPayload;
  playableProgress: ProgressCount | null;
};

export function JobProgressLatestSection({
  event,
  latestPlayableEvent,
  playableProgress,
}: JobProgressLatestSectionProps) {
  if (!event) {
    return <p>No progress events received yet.</p>;
  }

  return (
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
            {playableProgress
              ? `${playableProgress.completed}${playableProgress.total !== null ? ` / ${playableProgress.total}` : ''}`
              : `${event.snapshot.completed}${event.snapshot.total !== null ? ` / ${event.snapshot.total}` : ''}`}
          </span>
        </div>
        <div className="progress-metric">
          <strong>Speed</strong>
          <span>
            {latestPlayableEvent?.snapshot
              ? `${latestPlayableEvent.snapshot.speed.toFixed(2)} items/s`
              : `${event.snapshot.speed.toFixed(2)} items/s`}
          </span>
        </div>
        <div className="progress-metric">
          <strong>Elapsed</strong>
          <span>{event.snapshot.elapsed.toFixed(2)} s</span>
        </div>
        <div className="progress-metric">
          <strong>ETA</strong>
          <span>
            {latestPlayableEvent?.snapshot?.eta !== null && latestPlayableEvent?.snapshot?.eta !== undefined
              ? `${latestPlayableEvent.snapshot.eta.toFixed(2)} s`
              : event.snapshot.eta !== null
                ? `${event.snapshot.eta.toFixed(2)} s`
                : (
                    <>
                      &mdash;
                    </>
                  )}
          </span>
        </div>
      </div>
      {event.error ? <div className="alert">{event.error}</div> : null}
    </div>
  );
}
