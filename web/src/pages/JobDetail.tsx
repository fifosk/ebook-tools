import { useEffect } from 'react';
import PlayerPanel from '../components/PlayerPanel';
import YoutubeDubPlayer from '../components/YoutubeDubPlayer';
import { useLiveMedia } from '../hooks/useLiveMedia';
import type { LibraryOpenInput, MediaSelectionRequest } from '../types/player';

export interface JobDetailProps {
  jobId: string | null | undefined;
  jobType?: string | null;
  onVideoPlaybackStateChange?: (isPlaying: boolean) => void;
  onPlaybackStateChange?: (isPlaying: boolean) => void;
  onFullscreenChange?: (isFullscreen: boolean) => void;
  bookMetadata?: Record<string, unknown> | null;
  onOpenLibraryItem?: (item: LibraryOpenInput) => void;
  selectionRequest?: MediaSelectionRequest | null;
}

export default function JobDetail({
  jobId,
  jobType = null,
  onVideoPlaybackStateChange,
  onPlaybackStateChange,
  onFullscreenChange,
  bookMetadata = null,
  onOpenLibraryItem,
  selectionRequest = null
}: JobDetailProps) {
  const normalisedJobId = jobId ?? null;
  const { media, chunks, isComplete, isLoading, error } = useLiveMedia(normalisedJobId, {
    enabled: Boolean(normalisedJobId),
  });

  useEffect(() => {
    if (!normalisedJobId) {
      onVideoPlaybackStateChange?.(false);
      onPlaybackStateChange?.(false);
    }

    return () => {
      onVideoPlaybackStateChange?.(false);
      onPlaybackStateChange?.(false);
    };
  }, [normalisedJobId, onPlaybackStateChange, onVideoPlaybackStateChange]);

  if (!normalisedJobId) {
    return (
      <section className="job-detail" aria-label="Job detail">
        <div className="job-detail__placeholder">
          Select a job to explore generated text, audio, and video segments.
        </div>
      </section>
    );
  }

  const isYoutubeDub = (jobType ?? '').toLowerCase() === 'youtube_dub';

  return (
    <section className="job-detail" aria-label={`Job ${normalisedJobId} detail`}>
      {isYoutubeDub ? (
        <YoutubeDubPlayer
          jobId={normalisedJobId}
          media={media}
          mediaComplete={isComplete}
          isLoading={isLoading}
          error={error}
          onPlaybackStateChange={onPlaybackStateChange}
          onVideoPlaybackStateChange={onVideoPlaybackStateChange}
          onFullscreenChange={onFullscreenChange}
        />
      ) : (
        <PlayerPanel
          jobId={normalisedJobId}
          media={media}
          chunks={chunks}
          mediaComplete={isComplete}
          isLoading={isLoading}
          error={error}
          bookMetadata={bookMetadata}
          onVideoPlaybackStateChange={onVideoPlaybackStateChange}
          onPlaybackStateChange={onPlaybackStateChange}
          onFullscreenChange={onFullscreenChange}
          onOpenLibraryItem={onOpenLibraryItem}
          selectionRequest={selectionRequest}
        />
      )}
    </section>
  );
}
