import { useEffect, useMemo, useState } from 'react';
import AudioPlayer, { type AudioFile } from './AudioPlayer';
import VideoPlayer, { type VideoFile } from './VideoPlayer';
import TextViewer, { type TextFile } from './TextViewer';
import MediaList from './MediaList';
import type { LiveMediaState } from '../hooks/useLiveMedia';
import { useActiveFile, type ActiveFileState } from './useActiveFile';
import { deriveMediaItemId } from './mediaUtils';
import { useMediaQuery } from '../hooks/useMediaQuery';

type MediaCategory = keyof LiveMediaState;

interface PlayerPanelProps {
  jobId: string;
  media: LiveMediaState;
  isLoading: boolean;
  error: Error | null;
}

interface TabDefinition {
  key: MediaCategory;
  label: string;
  emptyMessage: string;
}

const TAB_DEFINITIONS: TabDefinition[] = [
  { key: 'text', label: 'Text', emptyMessage: 'No text media yet.' },
  { key: 'audio', label: 'Audio', emptyMessage: 'No audio media yet.' },
  { key: 'video', label: 'Video', emptyMessage: 'No video media yet.' },
];

const DESKTOP_MEDIA_QUERY = '(min-width: 48rem)';

function selectInitialTab(media: LiveMediaState): MediaCategory {
  const populated = TAB_DEFINITIONS.find((tab) => media[tab.key].length > 0);
  return populated?.key ?? 'text';
}

function toTextFiles(media: LiveMediaState['text']): TextFile[] {
  return media.map((item, index) => ({
    id: deriveMediaItemId(item, index) ?? `${item.type}:${index}`,
    name: item.name,
    url: item.url ?? undefined,
  }));
}

function toAudioFiles(media: LiveMediaState['audio']): AudioFile[] {
  return media
    .filter((item) => typeof item.url === 'string' && item.url.length > 0)
    .map((item, index) => ({
      id: deriveMediaItemId(item, index) ?? `${item.type}:${index}`,
      url: item.url ?? '',
      name: item.name,
    }));
}

function toVideoFiles(media: LiveMediaState['video']): VideoFile[] {
  return media
    .filter((item) => typeof item.url === 'string' && item.url.length > 0)
    .map((item, index) => ({
      id: deriveMediaItemId(item, index) ?? `${item.type}:${index}`,
      url: item.url ?? '',
      name: item.name,
    }));
}

export default function PlayerPanel({ jobId, media, isLoading, error }: PlayerPanelProps) {
  const [activeTab, setActiveTab] = useState<MediaCategory>(() => selectInitialTab(media));
  const [isDrawerOpen, setDrawerOpen] = useState(false);
  const isDesktop = useMediaQuery(DESKTOP_MEDIA_QUERY);

  useEffect(() => {
    setActiveTab((current) => {
      if (media[current].length > 0) {
        return current;
      }
      return selectInitialTab(media);
    });
  }, [media]);

  useEffect(() => {
    if (isDesktop) {
      setDrawerOpen(false);
    }
  }, [isDesktop]);

  const textFiles = useMemo(() => toTextFiles(media.text), [media.text]);
  const audioFiles = useMemo(() => toAudioFiles(media.audio), [media.audio]);
  const videoFiles = useMemo(() => toVideoFiles(media.video), [media.video]);

  const textState = useActiveFile(textFiles);
  const audioState = useActiveFile(audioFiles);
  const videoState = useActiveFile(videoFiles);

  const stateByTab: Record<MediaCategory, ActiveFileState<TextFile | AudioFile | VideoFile>> = {
    text: textState,
    audio: audioState,
    video: videoState,
  };

  const activeState = stateByTab[activeTab];
  const activeTabDefinition = TAB_DEFINITIONS.find((tab) => tab.key === activeTab) ?? TAB_DEFINITIONS[0];
  const activeItems = media[activeTab];

  const handleSelectMedia = (itemId: string) => {
    activeState.selectFile(itemId);
    if (!isDesktop) {
      setDrawerOpen(false);
    }
  };

  const toggleDrawer = () => {
    setDrawerOpen((open) => !open);
  };

  if (!jobId) {
    return (
      <section className="player-panel" aria-label="Generated media">
        <p>No job selected.</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="player-panel" aria-label="Generated media">
        <p role="alert">Unable to load generated media: {error.message}</p>
      </section>
    );
  }

  if (isLoading && media.text.length === 0 && media.audio.length === 0 && media.video.length === 0) {
    return (
      <section className="player-panel" aria-label="Generated media">
        <p role="status">Loading generated media…</p>
      </section>
    );
  }

  const hasAnyMedia = media.text.length + media.audio.length + media.video.length > 0;

  const renderActivePanel = () => {
    const isCategoryLoading = isLoading && activeItems.length === 0;

    switch (activeTab) {
      case 'audio':
        return (
          <AudioPlayer
            file={(audioState.activeFile as AudioFile | null) ?? null}
            isLoading={isCategoryLoading}
          />
        );
      case 'video':
        return (
          <VideoPlayer
            file={(videoState.activeFile as VideoFile | null) ?? null}
            isLoading={isCategoryLoading}
          />
        );
      case 'text':
      default:
        return (
          <TextViewer
            file={(textState.activeFile as TextFile | null) ?? null}
            isLoading={isCategoryLoading}
          />
        );
    }
  };

  const panelClassName = ['player-panel'];
  if (isDrawerOpen) {
    panelClassName.push('player-panel--drawer-open');
  }

  return (
    <section className={panelClassName.join(' ')} aria-label="Generated media">
      <header className="player-panel__header">
        <h2>Generated media</h2>
        <span className="player-panel__job">Job {jobId}</span>
      </header>
      <div className="player-panel__tabs" role="tablist" aria-label="Media categories">
        {TAB_DEFINITIONS.map((tab) => {
          const count = media[tab.key].length;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              id={`media-tab-${tab.key}`}
              role="tab"
              type="button"
              className="player-panel__tab"
              aria-selected={isActive}
              aria-controls={`media-panel-${tab.key}`}
              onClick={() => {
                setActiveTab(tab.key);
                if (!isDesktop) {
                  setDrawerOpen(false);
                }
              }}
              data-testid={`media-tab-${tab.key}`}
            >
              {tab.label} ({count})
            </button>
          );
        })}
      </div>
      {!hasAnyMedia && !isLoading ? (
        <div className="player-panel__empty" role="status">
          No generated media yet.
        </div>
      ) : (
        <div className="player-panel__body" role="tabpanel" id={`media-panel-${activeTab}`} aria-labelledby={`media-tab-${activeTab}`}>
          <div className="player-panel__primary">
            <div className="player-panel__panel">{renderActivePanel()}</div>
            <button
              type="button"
              className="player-panel__drawer-toggle"
              onClick={toggleDrawer}
              aria-expanded={isDrawerOpen}
              aria-controls="player-panel-drawer"
            >
              Browse {activeTabDefinition.label} files
            </button>
          </div>
          <aside className="player-panel__secondary" aria-label={`${activeTabDefinition.label} files`}>
            <header className="player-panel__secondary-header">
              <h3>{activeTabDefinition.label} playlist</h3>
              <span>{activeItems.length} items</span>
            </header>
            <div className="player-panel__list">
              <MediaList
                items={activeItems}
                category={activeTab}
                emptyMessage={activeTabDefinition.emptyMessage}
                selectedId={activeState.activeId}
                onSelect={(_, id) => handleSelectMedia(id)}
              />
            </div>
          </aside>
        </div>
      )}
      <button
        type="button"
        className="player-panel__drawer-backdrop"
        hidden={!isDrawerOpen}
        aria-label="Close media drawer"
        onClick={() => setDrawerOpen(false)}
      />
      <aside
        id="player-panel-drawer"
        className="player-panel__drawer"
        role="dialog"
        aria-modal="true"
        aria-label={`${activeTabDefinition.label} files`}
        hidden={!isDrawerOpen}
      >
        <header className="player-panel__drawer-header">
          <h3>{activeTabDefinition.label} files</h3>
          <button type="button" onClick={() => setDrawerOpen(false)} className="player-panel__drawer-close">
            Close
          </button>
        </header>
        <div className="player-panel__drawer-content">
          <header className="player-panel__secondary-header player-panel__secondary-header--drawer">
            <h3>{activeTabDefinition.label} playlist</h3>
            <span>{activeItems.length} items</span>
          </header>
          <MediaList
            items={activeItems}
            category={activeTab}
            emptyMessage={activeTabDefinition.emptyMessage}
            selectedId={activeState.activeId}
            onSelect={(_, id) => handleSelectMedia(id)}
          />
        </div>
      </aside>
    </section>
  );
}
