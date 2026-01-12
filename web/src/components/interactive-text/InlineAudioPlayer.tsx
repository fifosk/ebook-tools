import type { Ref } from 'react';
import PlayerCore, { type PlayerCoreHandle, type PlayerCoreProps } from '../../player/PlayerCore';

interface InlineAudioPlayerProps {
  audioUrl: string | null;
  noAudioAvailable: boolean;
  collapsed: boolean;
  showControls?: boolean;
  playerRef: Ref<PlayerCoreHandle>;
  mediaRef?: PlayerCoreProps['mediaRef'];
  onPlay?: PlayerCoreProps['onPlay'];
  onPause?: PlayerCoreProps['onPause'];
  onLoadedMetadata?: PlayerCoreProps['onLoadedMetadata'];
  onTimeUpdate?: PlayerCoreProps['onTimeUpdate'];
  onEnded?: PlayerCoreProps['onEnded'];
  onSeeked?: PlayerCoreProps['onSeeked'];
  onSeeking?: PlayerCoreProps['onSeeking'];
  onWaiting?: PlayerCoreProps['onWaiting'];
  onStalled?: PlayerCoreProps['onStalled'];
  onPlaying?: PlayerCoreProps['onPlaying'];
  onRateChange?: PlayerCoreProps['onRateChange'];
}

export function InlineAudioPlayer({
  audioUrl,
  noAudioAvailable,
  collapsed,
  showControls = true,
  playerRef,
  mediaRef,
  onPlay,
  onPause,
  onLoadedMetadata,
  onTimeUpdate,
  onEnded,
  onSeeked,
  onSeeking,
  onWaiting,
  onStalled,
  onPlaying,
  onRateChange,
}: InlineAudioPlayerProps) {
  if (audioUrl) {
    if (!showControls) {
      return (
        <PlayerCore
          ref={playerRef}
          className="player-panel__interactive-audio-hidden"
          mediaRef={mediaRef}
          src={audioUrl ?? undefined}
          id="main-audio"
          controls={false}
          preload="metadata"
          onPlay={onPlay}
          onPause={onPause}
          onLoadedMetadata={onLoadedMetadata}
          onTimeUpdate={onTimeUpdate}
          onEnded={onEnded}
          onSeeked={onSeeked}
          onSeeking={onSeeking}
          onWaiting={onWaiting}
          onStalled={onStalled}
          onPlaying={onPlaying}
          onRateChange={onRateChange}
        />
      );
    }
    return (
      <div
        className={[
          'player-panel__interactive-audio',
          collapsed ? 'player-panel__interactive-audio--collapsed' : null,
        ]
          .filter(Boolean)
          .join(' ')}
        aria-hidden={collapsed ? 'true' : undefined}
      >
        <span className="player-panel__interactive-label">Synchronized audio</span>
        <div className="player-panel__interactive-audio-controls">
          <PlayerCore
            ref={playerRef}
            mediaRef={mediaRef}
            src={audioUrl ?? undefined}
            id="main-audio"
            controls
            preload="metadata"
            onPlay={onPlay}
            onPause={onPause}
            onLoadedMetadata={onLoadedMetadata}
            onTimeUpdate={onTimeUpdate}
            onEnded={onEnded}
            onSeeked={onSeeked}
            onSeeking={onSeeking}
            onWaiting={onWaiting}
            onStalled={onStalled}
            onPlaying={onPlaying}
            onRateChange={onRateChange}
          />
        </div>
      </div>
    );
  }
  if (noAudioAvailable && showControls) {
    return (
      <div className="player-panel__interactive-no-audio" role="status">
        Matching audio has not been generated for this selection yet.
      </div>
    );
  }
  return null;
}
