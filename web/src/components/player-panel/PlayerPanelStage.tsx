import type { ReactNode, RefObject, UIEvent } from 'react';
import { TabsContent } from '../ui/Tabs';
import AudioPlayer, { type AudioFile } from '../AudioPlayer';
import VideoPlayer, { type VideoFile } from '../VideoPlayer';
import InteractiveTextViewer from '../InteractiveTextViewer';
import type { LiveMediaChunk, LiveMediaItem, LiveMediaState } from '../../hooks/useLiveMedia';
import type { MediaCategory, TabDefinition } from './constants';

type PlaybackControls = {
  pause: () => void;
  play: () => void;
  ensureFullscreen?: () => void;
};

interface AudioStageProps {
  files: AudioFile[];
  activeId: string | null;
  onSelectFile: (fileId: string) => void;
  onPlaybackEnded: () => void;
  playbackPosition: number;
  onPlaybackPositionChange: (position: number) => void;
  onRegisterControls: (controls: PlaybackControls | null) => void;
  onPlaybackStateChange: (state: 'playing' | 'paused') => void;
}

interface VideoStageProps {
  files: VideoFile[];
  activeId: string | null;
  onSelectFile: (fileId: string) => void;
  onPlaybackEnded: () => void;
  playbackPosition: number;
  onPlaybackPositionChange: (position: number) => void;
  onPlaybackStateChange: (state: 'playing' | 'paused') => void;
  isTheaterMode: boolean;
  onExitTheaterMode: (reason?: 'user' | 'lost') => void;
  onRegisterControls: (controls: PlaybackControls | null) => void;
}

interface TextStageProps {
  hasTextItems: boolean;
  selectedItem: LiveMediaItem | null;
  loading: boolean;
  error: string | null;
  canRenderInteractiveViewer: boolean;
  interactiveViewerContent: string;
  interactiveViewerRaw: string;
  resolvedActiveChunk: LiveMediaChunk | null;
  inlineAudioSelection: string | null;
  inlineAudioUnavailable: boolean;
  jobId?: string | null;
  textScrollRef: RefObject<HTMLDivElement | null>;
  onScroll: (event: UIEvent<HTMLElement>) => void;
  onAudioProgress: (audioUrl: string, position: number) => void;
  getStoredAudioPosition: (audioUrl: string) => number;
  onRegisterInlineAudioControls: (controls: PlaybackControls | null) => void;
  onInlineAudioPlaybackStateChange: (state: 'playing' | 'paused') => void;
  onRequestAdvanceChunk: () => void;
  isFullscreen?: boolean;
  onRequestExitFullscreen?: () => void;
  fullscreenControls?: ReactNode;
}

interface SelectionInfo {
  title: string;
  label: string;
  timestamp: string | null;
  size: string | null;
  sentenceRange: string;
}

interface PlayerPanelStageProps {
  media: LiveMediaState;
  visibleTabs: TabDefinition[];
  selectedMediaType: MediaCategory;
  mediaComplete: boolean;
  isLoading: boolean;
  hasAnyMedia: boolean;
  emptyMediaMessage: string;
  hasInteractiveChunks: boolean;
  audio: AudioStageProps;
  video: VideoStageProps;
  text: TextStageProps;
}

export function PlayerPanelStage({
  media,
  visibleTabs,
  selectedMediaType,
  mediaComplete,
  isLoading,
  hasAnyMedia,
  emptyMediaMessage,
  hasInteractiveChunks,
  audio,
  video,
  text,
}: PlayerPanelStageProps) {
  return (
    <>
      {visibleTabs.map((tab) => {
        const isActive = tab.key === selectedMediaType;
        const tabItems = media[tab.key];
        const tabHasInteractiveContent = tab.key === 'text' && hasInteractiveChunks;
        const tabHasContent = tabItems.length > 0 || tabHasInteractiveContent;
        return (
          <TabsContent key={tab.key} value={tab.key} className="player-panel__panel">
            {!hasAnyMedia && !isLoading ? (
              <p role="status">{emptyMediaMessage}</p>
            ) : !tabHasContent ? (
              <p role="status">{tab.emptyMessage}</p>
            ) : (
              isActive ? (
                <div className="player-panel__stage">
                  {!mediaComplete ? (
                    <div className="player-panel__notice" role="status">
                      Media generation is still finishing. Newly generated files will appear automatically.
                    </div>
                  ) : null}
                  <div className="player-panel__viewer">
                    {tab.key === 'audio' ? (
                      <AudioPlayer
                        files={audio.files}
                        activeId={audio.activeId}
                        onSelectFile={audio.onSelectFile}
                        autoPlay
                        onPlaybackEnded={audio.onPlaybackEnded}
                        playbackPosition={audio.playbackPosition}
                        onPlaybackPositionChange={audio.onPlaybackPositionChange}
                        onRegisterControls={audio.onRegisterControls}
                        onPlaybackStateChange={audio.onPlaybackStateChange}
                      />
                    ) : null}
                    {tab.key === 'video' ? (
                      <VideoPlayer
                        files={video.files}
                        activeId={video.activeId}
                        onSelectFile={video.onSelectFile}
                        autoPlay
                        onPlaybackEnded={video.onPlaybackEnded}
                        playbackPosition={video.playbackPosition}
                        onPlaybackPositionChange={video.onPlaybackPositionChange}
                        onPlaybackStateChange={video.onPlaybackStateChange}
                        isTheaterMode={video.isTheaterMode}
                        onExitTheaterMode={video.onExitTheaterMode}
                        onRegisterControls={video.onRegisterControls}
                      />
                    ) : null}
                    {tab.key === 'text' ? (
                      <div className="player-panel__document">
                        {text.hasTextItems && !text.selectedItem ? (
                          <div className="player-panel__empty-viewer" role="status">
                            Select a file to preview.
                          </div>
                        ) : text.loading && text.selectedItem ? (
                          <div className="player-panel__document-status" role="status">
                            Loading document…
                          </div>
                        ) : text.error ? (
                          <div className="player-panel__document-error" role="alert">
                            {text.error}
                          </div>
                        ) : text.canRenderInteractiveViewer ? (
                          <InteractiveTextViewer
                            ref={text.textScrollRef}
                            content={text.interactiveViewerContent}
                            rawContent={text.interactiveViewerRaw}
                            chunk={text.resolvedActiveChunk}
                            activeAudioUrl={text.inlineAudioSelection}
                            noAudioAvailable={text.inlineAudioUnavailable}
                            jobId={text.jobId ?? undefined}
                            onScroll={text.onScroll}
                            onAudioProgress={text.onAudioProgress}
                            getStoredAudioPosition={text.getStoredAudioPosition}
                            onRegisterInlineAudioControls={text.onRegisterInlineAudioControls}
                            onInlineAudioPlaybackStateChange={text.onInlineAudioPlaybackStateChange}
                            onRequestAdvanceChunk={text.onRequestAdvanceChunk}
                            isFullscreen={text.isFullscreen}
                            onRequestExitFullscreen={text.onRequestExitFullscreen}
                            fullscreenControls={text.fullscreenControls}
                          />
                        ) : (
                          <div className="player-panel__document-status" role="status">
                            Interactive reader assets are still being prepared.
                          </div>
                        )}
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : null
            )}
          </TabsContent>
        );
      })}
    </>
  );
}
