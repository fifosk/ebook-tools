import { useEffect } from 'react';
import PlayerPanel from '../components/PlayerPanel';
import { useLiveMedia } from '../hooks/useLiveMedia';
import type { LibraryOpenInput, MediaSelectionRequest } from '../types/player';

export interface JobDetailProps {
  jobId: string | null | undefined;
  onVideoPlaybackStateChange?: (isPlaying: boolean) => void;
  bookMetadata?: Record<string, unknown> | null;
  onOpenLibraryItem?: (item: LibraryOpenInput) => void;
  selectionRequest?: MediaSelectionRequest | null;
}

export default function JobDetail({ jobId, onVideoPlaybackStateChange, bookMetadata = null, onOpenLibraryItem, selectionRequest = null }: JobDetailProps) {
  const normalisedJobId = jobId ?? null;
  const { media, chunks, isComplete, isLoading, error } = useLiveMedia(normalisedJobId, {
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
        chunks={chunks}
        mediaComplete={isComplete}
        isLoading={isLoading}
        error={error}
        bookMetadata={bookMetadata}
        onVideoPlaybackStateChange={onVideoPlaybackStateChange}
        onOpenLibraryItem={onOpenLibraryItem}
        selectionRequest={selectionRequest}
      />
    </section>
  );
}
