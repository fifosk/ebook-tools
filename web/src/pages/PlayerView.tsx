import { useEffect } from 'react';
import PlayerPanel from '../components/PlayerPanel';
import { useLibraryMedia } from '../hooks/useLibraryMedia';
import JobDetail from './JobDetail';
import type { LibraryOpenInput, MediaSelectionRequest } from '../types/player';

export type PlayerContext =
  | { type: 'job'; jobId: string }
  | { type: 'library'; jobId: string; bookMetadata: Record<string, unknown> | null };

interface PlayerViewProps {
  context: PlayerContext | null;
  jobBookMetadata?: Record<string, unknown> | null;
  onVideoPlaybackStateChange?: (isPlaying: boolean) => void;
  onPlaybackStateChange?: (isPlaying: boolean) => void;
  onOpenLibraryItem?: (item: LibraryOpenInput) => void;
  selectionRequest?: MediaSelectionRequest | null;
}

export default function PlayerView({
  context,
  jobBookMetadata = null,
  onVideoPlaybackStateChange,
  onPlaybackStateChange,
  onOpenLibraryItem,
  selectionRequest = null
}: PlayerViewProps) {
  if (!context) {
    return (
      <section className="job-detail" aria-label="Player">
        <div className="job-detail__placeholder">
          Select a job or library book to open the player.
        </div>
      </section>
    );
  }

  if (context.type === 'job') {
    return (
      <JobDetail
        jobId={context.jobId}
        onVideoPlaybackStateChange={onVideoPlaybackStateChange}
        onPlaybackStateChange={onPlaybackStateChange}
        bookMetadata={jobBookMetadata}
        onOpenLibraryItem={onOpenLibraryItem}
        selectionRequest={selectionRequest}
      />
    );
  }

  const { media, chunks, isComplete, isLoading, error } = useLibraryMedia(context.jobId);

  useEffect(() => {
    onVideoPlaybackStateChange?.(false);
    onPlaybackStateChange?.(false);
    return () => {
      onVideoPlaybackStateChange?.(false);
      onPlaybackStateChange?.(false);
    };
  }, [context.jobId, onPlaybackStateChange, onVideoPlaybackStateChange]);

  return (
    <section className="job-detail" aria-label={`Player for library job ${context.jobId}`}>
      <PlayerPanel
        jobId={context.jobId}
        media={media}
        chunks={chunks}
        mediaComplete={isComplete}
        isLoading={isLoading}
        error={error}
        bookMetadata={context.bookMetadata ?? null}
        onVideoPlaybackStateChange={onVideoPlaybackStateChange}
        onPlaybackStateChange={onPlaybackStateChange}
        origin="library"
        onOpenLibraryItem={onOpenLibraryItem}
        selectionRequest={selectionRequest}
      />
    </section>
  );
}
