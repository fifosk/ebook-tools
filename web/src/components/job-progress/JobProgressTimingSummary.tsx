import { formatDate } from './jobProgressUtils';

type JobProgressTimingSummaryProps = {
  createdAt: string | null | undefined;
  startedAt: string | null | undefined;
  completedAt: string | null | undefined;
  mediaCompleted: boolean | null;
};

export function JobProgressTimingSummary({
  createdAt,
  startedAt,
  completedAt,
  mediaCompleted,
}: JobProgressTimingSummaryProps) {
  return (
    <p>
      <strong>Created:</strong> {formatDate(createdAt ?? null)}
      <br />
      <strong>Started:</strong> {formatDate(startedAt)}
      <br />
      <strong>Completed:</strong> {formatDate(completedAt)}
      {mediaCompleted !== null ? (
        <>
          <br />
          <strong>Media finalized:</strong> {mediaCompleted ? 'Yes' : 'In progress'}
        </>
      ) : null}
    </p>
  );
}
