import { useEffect, useMemo, useState } from 'react';
import AudioPlayer from './AudioPlayer';
import VideoPlayer from './VideoPlayer';
import MediaList from './MediaList';
import type { LiveMediaState } from '../hooks/useLiveMedia';

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

function selectInitialTab(media: LiveMediaState): MediaCategory {
  const populated = TAB_DEFINITIONS.find((tab) => media[tab.key].length > 0);
  return populated?.key ?? 'text';
}

function toAudioFiles(media: LiveMediaState['audio']) {
  return media
    .filter((item) => typeof item.url === 'string' && item.url.length > 0)
    .map((item, index) => ({
      id: item.url ?? `${item.type}-${index}`,
      url: item.url ?? '',
      name: item.name,
    }));
}

function toVideoFiles(media: LiveMediaState['video']) {
  return media
    .filter((item) => typeof item.url === 'string' && item.url.length > 0)
    .map((item, index) => ({
      id: item.url ?? `${item.type}-${index}`,
      url: item.url ?? '',
      name: item.name,
    }));
}

export default function PlayerPanel({ jobId, media, isLoading, error }: PlayerPanelProps) {
  const [activeTab, setActiveTab] = useState<MediaCategory>(() => selectInitialTab(media));

  useEffect(() => {
    setActiveTab((current) => {
      if (media[current].length > 0) {
        return current;
      }
      return selectInitialTab(media);
    });
  }, [media]);

  const audioFiles = useMemo(() => toAudioFiles(media.audio), [media.audio]);
  const videoFiles = useMemo(() => toVideoFiles(media.video), [media.video]);

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

  return (
    <section className="player-panel" aria-label="Generated media">
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
              onClick={() => setActiveTab(tab.key)}
              data-testid={`media-tab-${tab.key}`}
            >
              {tab.label} ({count})
            </button>
          );
        })}
      </div>
      {TAB_DEFINITIONS.map((tab) => {
        const isActive = activeTab === tab.key;
        const items = media[tab.key];
        return (
          <div
            key={tab.key}
            role="tabpanel"
            id={`media-panel-${tab.key}`}
            aria-labelledby={`media-tab-${tab.key}`}
            hidden={!isActive}
            className="player-panel__panel"
          >
            {!hasAnyMedia && !isLoading ? (
              <p role="status">No generated media yet.</p>
            ) : items.length === 0 ? (
              <MediaList items={items} category={tab.key} emptyMessage={tab.emptyMessage} />
            ) : (
              <>
                {tab.key === 'audio' ? <AudioPlayer files={audioFiles} /> : null}
                {tab.key === 'video' ? <VideoPlayer files={videoFiles} /> : null}
                <MediaList items={items} category={tab.key} emptyMessage={tab.emptyMessage} />
              </>
            )}
          </div>
        );
      })}
    </section>
  );
}
