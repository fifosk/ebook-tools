import type { RefObject, UIEvent } from 'react';
import { TabsContent } from '../ui/Tabs';
import AudioPlayer, { type AudioFile } from '../AudioPlayer';
import VideoPlayer, { type VideoFile } from '../VideoPlayer';
import InteractiveTextViewer from '../InteractiveTextViewer';
import type { LiveMediaChunk, LiveMediaItem, LiveMediaState } from '../../hooks/useLiveMedia';
import type { MediaCategory, TabDefinition } from './constants';

type PlaybackControls = {
  pause: () => void;
  play: () => void;
};

interface AudioStageProps {
  files: AudioFile[];
  activeId: string | null;
  onSelectFile: (fileId: string) => void;
  onPlaybackEnded: () => void;
  playbackPosition: number;
  onPlaybackPositionChange: (position: number) => void;
  onRegisterControls: (controls: PlaybackControls | null) => void;
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
  onExitTheaterMode: () => void;
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
  inlineAudioPlaylist: LiveMediaItem[];
  inlineAudioSelection: string | null;
  inlineAudioUnavailable: boolean;
  textScrollRef: RefObject<HTMLDivElement | null>;
  onScroll: (event: UIEvent<HTMLElement>) => void;
  onAudioProgress: (audioUrl: string, position: number) => void;
  getStoredAudioPosition: (audioUrl: string) => number;
  onRegisterInlineAudioControls: (controls: PlaybackControls | null) => void;
  onSelectInlineAudio: (audioUrl: string) => void;
  onRequestAdvanceChunk: () => void;
  isFullscreen?: boolean;
  onRequestExitFullscreen?: () => void;
}

interface SelectionInfo {
  title: string;
  label: string;
  timestamp: string | null;
  size: string | null;
  chunkLabel: string | null;
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
  selection: SelectionInfo;
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
  selection,
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
                            audioItems={text.inlineAudioPlaylist}
                            activeAudioUrl={text.inlineAudioSelection}
                            noAudioAvailable={text.inlineAudioUnavailable}
                            onScroll={text.onScroll}
                            onAudioProgress={text.onAudioProgress}
                            getStoredAudioPosition={text.getStoredAudioPosition}
                          onRegisterInlineAudioControls={text.onRegisterInlineAudioControls}
                          onSelectAudio={text.onSelectInlineAudio}
                          onRequestAdvanceChunk={text.onRequestAdvanceChunk}
                          isFullscreen={text.isFullscreen}
                          onRequestExitFullscreen={text.onRequestExitFullscreen}
                        />
                        ) : (
                          <div className="player-panel__document-status" role="status">
                            Interactive reader assets are still being prepared.
                          </div>
                        )}
                      </div>
                    ) : null}
                  </div>
                  <div className="player-panel__selection-header" data-testid="player-panel-selection">
                    <div className="player-panel__selection-name" title={selection.title}>
                      {selection.label}
                    </div>
                    <dl className="player-panel__selection-meta">
                      <div className="player-panel__selection-meta-item">
                        <dt>Created</dt>
                        <dd>{selection.timestamp ?? '—'}</dd>
                      </div>
                      <div className="player-panel__selection-meta-item">
                        <dt>File size</dt>
                        <dd>{selection.size ?? '—'}</dd>
                      </div>
                      <div className="player-panel__selection-meta-item">
                        <dt>Chunk</dt>
                        <dd>{selection.chunkLabel ?? '—'}</dd>
                      </div>
                      <div className="player-panel__selection-meta-item">
                        <dt>Sentences</dt>
                        <dd>{selection.sentenceRange}</dd>
                      </div>
                    </dl>
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
