import PlayerPanel from '../components/PlayerPanel';
import { useLiveMedia } from '../hooks/useLiveMedia';

export interface JobDetailProps {
  jobId: string | null | undefined;
}

export default function JobDetail({ jobId }: JobDetailProps) {
  const normalisedJobId = jobId ?? null;
  const { media, isLoading, error } = useLiveMedia(normalisedJobId, {
    enabled: Boolean(normalisedJobId),
  });

  if (!normalisedJobId) {
    return (
      <section className="job-detail" aria-label="Job detail">
        <p>No job selected.</p>
      </section>
    );
  }

  return (
    <section className="job-detail" aria-label={`Job ${normalisedJobId} detail`}>
      <PlayerPanel jobId={normalisedJobId} media={media} isLoading={isLoading} error={error} />
    </section>
  );
}
