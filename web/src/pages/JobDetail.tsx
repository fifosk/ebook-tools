import PlayerPanel from '../components/PlayerPanel';
import { useLiveMedia } from '../hooks/useLiveMedia';
import type { PipelineStatusResponse, ProgressEventPayload } from '../api/dtos';

type JobDetailProps = {
  jobId: string;
  status: PipelineStatusResponse | undefined;
  onEvent: (event: ProgressEventPayload) => void;
  isTerminal: boolean;
};

function isTerminalStatus(value: string | undefined | null): boolean {
  if (!value) {
    return false;
  }
  return value === 'completed' || value === 'failed' || value === 'cancelled';
}

export default function JobDetail({ jobId, status, onEvent, isTerminal }: JobDetailProps) {
  const { mediaFiles, progressive, isLoading, error } = useLiveMedia(jobId, {
    enabled: !isTerminal,
    onEvent
  });
  const headingId = `job-${jobId}-media`;
  const statusValue = status?.status ?? null;
  const stillGenerating = progressive || !isTerminalStatus(statusValue);

  return (
    <section aria-labelledby={headingId} className="job-detail">
      <h4 id={headingId}>Live media</h4>
      {error ? (
        <p className="alert" role="status">
          {error}
        </p>
      ) : null}
      <PlayerPanel mediaFiles={mediaFiles} isGenerating={stillGenerating} isLoading={isLoading} />
    </section>
  );
}
