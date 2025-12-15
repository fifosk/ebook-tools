import { useEffect, useMemo } from 'react';
import PlayerPanel from '../components/PlayerPanel';
import YoutubeDubPlayer from '../components/YoutubeDubPlayer';
import { useLibraryMedia } from '../hooks/useLibraryMedia';
import JobDetail from './JobDetail';
import type { LibraryOpenInput, MediaSelectionRequest } from '../types/player';

export type PlayerContext =
  | { type: 'job'; jobId: string; jobType?: string | null }
  | {
      type: 'library';
      jobId: string;
      itemType?: 'book' | 'video' | 'narrated_subtitle' | null;
      bookMetadata: Record<string, unknown> | null;
    };

interface PlayerViewProps {
  context: PlayerContext | null;
  jobBookMetadata?: Record<string, unknown> | null;
  onVideoPlaybackStateChange?: (isPlaying: boolean) => void;
  onPlaybackStateChange?: (isPlaying: boolean) => void;
  onFullscreenChange?: (isFullscreen: boolean) => void;
  onOpenLibraryItem?: (item: LibraryOpenInput) => void;
  onBackToLibrary?: (payload: { jobId: string; itemType: 'book' | 'video' | 'narrated_subtitle' | null }) => void;
  selectionRequest?: MediaSelectionRequest | null;
}

export default function PlayerView({
  context,
  jobBookMetadata = null,
  onVideoPlaybackStateChange,
  onPlaybackStateChange,
  onFullscreenChange,
  onOpenLibraryItem,
  onBackToLibrary,
  selectionRequest = null
}: PlayerViewProps) {
  if (!context) {
    return (
      <div className="job-detail" role="region" aria-label="Player">
        <div className="job-detail__placeholder">
          Select a job or library book to open the player.
        </div>
      </div>
    );
  }

  if (context.type === 'job') {
    return (
      <JobDetail
        jobId={context.jobId}
        jobType={context.jobType}
        onVideoPlaybackStateChange={onVideoPlaybackStateChange}
        onPlaybackStateChange={onPlaybackStateChange}
        onFullscreenChange={onFullscreenChange}
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

  const isVideoItem = useMemo(() => {
    if ((context.itemType ?? null) === 'video') {
      return true;
    }
    const hasVideoMedia = media.video.length > 0;
    const hasInteractiveChunks = chunks.some(
      (chunk) =>
        (Array.isArray(chunk.sentences) && chunk.sentences.length > 0) ||
        (typeof chunk.sentenceCount === 'number' && chunk.sentenceCount > 0),
    );
    return hasVideoMedia && !hasInteractiveChunks;
  }, [chunks, context.itemType, media.video]);

  return (
    <div className="job-detail" role="region" aria-label={`Player for library job ${context.jobId}`}>
      {isVideoItem ? (
        <YoutubeDubPlayer
          jobId={context.jobId}
          media={media}
          mediaComplete={isComplete}
          isLoading={isLoading}
          error={error}
          onPlaybackStateChange={onPlaybackStateChange}
          onVideoPlaybackStateChange={onVideoPlaybackStateChange}
          onFullscreenChange={onFullscreenChange}
          showBackToLibrary
          onBackToLibrary={
            onBackToLibrary
              ? () => {
                  onBackToLibrary({ jobId: context.jobId, itemType: context.itemType ?? null });
                }
              : undefined
          }
        />
      ) : (
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
          onFullscreenChange={onFullscreenChange}
          origin="library"
          showBackToLibrary
          onBackToLibrary={
            onBackToLibrary
              ? () => {
                  onBackToLibrary({ jobId: context.jobId, itemType: context.itemType ?? null });
                }
              : undefined
          }
          onOpenLibraryItem={onOpenLibraryItem}
          selectionRequest={selectionRequest}
        />
      )}
    </div>
  );
}
