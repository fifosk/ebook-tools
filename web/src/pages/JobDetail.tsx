import { useEffect } from 'react';
import PlayerPanel from '../components/PlayerPanel';
import { useLiveMedia } from '../hooks/useLiveMedia';

export interface JobDetailProps {
  jobId: string | null | undefined;
  onVideoPlaybackStateChange?: (isPlaying: boolean) => void;
  bookMetadata?: Record<string, unknown> | null;
}

export default function JobDetail({ jobId, onVideoPlaybackStateChange, bookMetadata = null }: JobDetailProps) {
  const normalisedJobId = jobId ?? null;
  const { media, isLoading, error } = useLiveMedia(normalisedJobId, {
    enabled: Boolean(normalisedJobId),
  });

  useEffect(() => {
    if (!normalisedJobId) {
      onVideoPlaybackStateChange?.(false);
    }

    return () => {
      onVideoPlaybackStateChange?.(false);
    };
  }, [normalisedJobId, onVideoPlaybackStateChange]);

  if (!normalisedJobId) {
    return (
      <section className="job-detail" aria-label="Job detail">
        <div className="job-detail__placeholder">
          Select a job to explore generated text, audio, and video segments.
        </div>
      </section>
    );
  }

  return (
    <section className="job-detail" aria-label={`Job ${normalisedJobId} detail`}>
      <PlayerPanel
        jobId={normalisedJobId}
        media={media}
        isLoading={isLoading}
        error={error}
        bookMetadata={bookMetadata}
        onVideoPlaybackStateChange={onVideoPlaybackStateChange}
      />
    </section>
  );
}
