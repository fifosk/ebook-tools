import type { ProgressEventPayload } from '../../api/dtos';
import { formatDurationLabel } from '../../utils/timeFormatters';
import { formatProgressStageLabel, resolveProgressStage } from '../../utils/progressEvents';

type JobProgressHealthSummaryProps = {
  event: ProgressEventPayload | undefined;
  isActive: boolean;
};

export function JobProgressHealthSummary({
  event,
  isActive,
}: JobProgressHealthSummaryProps) {
  if (!isActive || !event) {
    return null;
  }

  const stage = formatProgressStageLabel(resolveProgressStage(event)) ?? 'Active';
  const elapsed = formatDurationLabel(event.snapshot.elapsed);
  const eta = event.snapshot.eta !== null ? formatDurationLabel(event.snapshot.eta) : null;
  const parts = [`${stage}`, `elapsed ${elapsed}`];
  if (eta) {
    parts.push(`ETA ${eta}`);
  }

  return (
    <div className="notice notice--info job-health-summary" role="status">
      <strong>Job health</strong>
      <span>{parts.join(' | ')}</span>
    </div>
  );
}
