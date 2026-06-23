import { useEffect } from 'react';
import PlayerPanel from '../components/PlayerPanel';
import YoutubeDubPlayer from '../components/YoutubeDubPlayer';
import { useLiveMedia } from '../hooks/useLiveMedia';
import type { PipelineMediaDiagnostics } from '../api/dtos';
import type { LibraryOpenInput, MediaSelectionRequest } from '../types/player';

export interface JobDetailProps {
  jobId: string | null | undefined;
  jobType?: string | null;
  onVideoPlaybackStateChange?: (isPlaying: boolean) => void;
  onPlaybackStateChange?: (isPlaying: boolean) => void;
  onFullscreenChange?: (isFullscreen: boolean) => void;
  mediaMetadata?: Record<string, unknown> | null;
  onOpenLibraryItem?: (item: LibraryOpenInput) => void;
  selectionRequest?: MediaSelectionRequest | null;
}

function MediaDiagnosticsStrip({ diagnostics }: { diagnostics: PipelineMediaDiagnostics | null }) {
  if (!diagnostics) {
    return null;
  }

  const missingCount =
    diagnostics.chunksWithoutMetadata +
    diagnostics.filesWithoutUrl +
    diagnostics.filesWithoutSize;
  const state = missingCount > 0 ? 'warning' : 'ready';
  const timingLabel =
    diagnostics.chunkCount > 0
      ? `${diagnostics.chunksWithTiming}/${diagnostics.chunkCount}`
      : String(diagnostics.chunksWithTiming);

  return (
    <dl className="media-diagnostics" data-state={state} aria-label="Media diagnostics">
      <div className="media-diagnostics__item">
        <dt>Files</dt>
        <dd>{diagnostics.mediaFileCount}</dd>
      </div>
      <div className="media-diagnostics__item">
        <dt>Chunks</dt>
        <dd>{diagnostics.chunkCount}</dd>
      </div>
      <div className="media-diagnostics__item">
        <dt>Audio</dt>
        <dd>{diagnostics.chunksWithAudio}</dd>
      </div>
      <div className="media-diagnostics__item">
        <dt>Timing</dt>
        <dd>{timingLabel}</dd>
      </div>
      <div className="media-diagnostics__item">
        <dt>Images</dt>
        <dd>{diagnostics.chunksWithImages}</dd>
      </div>
      {missingCount > 0 ? (
        <div className="media-diagnostics__item media-diagnostics__item--warning">
          <dt>Gaps</dt>
          <dd>{missingCount}</dd>
        </div>
      ) : null}
    </dl>
  );
}

export default function JobDetail({
  jobId,
  jobType = null,
  onVideoPlaybackStateChange,
  onPlaybackStateChange,
  onFullscreenChange,
  mediaMetadata = null,
  onOpenLibraryItem,
  selectionRequest = null
}: JobDetailProps) {
  const normalisedJobId = jobId ?? null;
  const { media, chunks, diagnostics, isComplete, isLoading, error } = useLiveMedia(normalisedJobId, {
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
      <div className="job-detail" role="region" aria-label="Job detail">
        <div className="job-detail__placeholder">
          Select a job to explore generated text, audio, and video segments.
        </div>
      </div>
    );
  }

  const isYoutubeDub = (jobType ?? '').toLowerCase() === 'youtube_dub';

  return (
    <div className="job-detail" role="region" aria-label={`Job ${normalisedJobId} detail`}>
      <MediaDiagnosticsStrip diagnostics={diagnostics} />
      {isYoutubeDub ? (
        <YoutubeDubPlayer
          jobId={normalisedJobId}
          media={media}
          mediaComplete={isComplete}
          isLoading={isLoading}
          error={error}
          jobType={jobType ?? null}
          onPlaybackStateChange={onPlaybackStateChange}
          onVideoPlaybackStateChange={onVideoPlaybackStateChange}
          onFullscreenChange={onFullscreenChange}
        />
      ) : (
        <PlayerPanel
          jobId={normalisedJobId}
          jobType={jobType}
          media={media}
          chunks={chunks}
          mediaComplete={isComplete}
          isLoading={isLoading}
          error={error}
          mediaMetadata={mediaMetadata}
          onVideoPlaybackStateChange={onVideoPlaybackStateChange}
          onPlaybackStateChange={onPlaybackStateChange}
          onFullscreenChange={onFullscreenChange}
          onOpenLibraryItem={onOpenLibraryItem}
          selectionRequest={selectionRequest}
        />
      )}
    </div>
  );
}
