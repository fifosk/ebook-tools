import { useCallback, useEffect, useMemo, useState } from 'react';
import AudioPlayer from './AudioPlayer';
import VideoPlayer from './VideoPlayer';
import MediaList from './MediaList';
import type { LiveMediaState } from '../hooks/useLiveMedia';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/Tabs';

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
  const [selectedMediaType, setSelectedMediaType] = useState<MediaCategory>(() => selectInitialTab(media));

  useEffect(() => {
    setSelectedMediaType((current) => {
      if (current && media[current].length > 0) {
        return current;
      }
      return selectInitialTab(media);
    });
  }, [media]);

  const handleTabChange = useCallback((nextValue: string) => {
    setSelectedMediaType(nextValue as MediaCategory);
  }, []);

  const audioFiles = useMemo(() => toAudioFiles(media.audio), [media.audio]);
  const videoFiles = useMemo(() => toVideoFiles(media.video), [media.video]);
  const combinedMedia = useMemo(
    () =>
      (['text', 'audio', 'video'] as MediaCategory[]).flatMap((category) =>
        media[category].map((item) => ({ ...item, type: category })),
      ),
    [media],
  );
  const filteredAudioFiles = useMemo(
    () => (selectedMediaType === 'audio' ? audioFiles : []),
    [audioFiles, selectedMediaType],
  );
  const filteredVideoFiles = useMemo(
    () => (selectedMediaType === 'video' ? videoFiles : []),
    [selectedMediaType, videoFiles],
  );
  const filteredMedia = useMemo(
    () => combinedMedia.filter((item) => item.type === selectedMediaType),
    [combinedMedia, selectedMediaType],
  );

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
      <Tabs className="player-panel__tabs-container" value={selectedMediaType} onValueChange={handleTabChange}>
        <header className="player-panel__header">
          <div className="player-panel__heading">
            <h2>Generated media</h2>
            <span className="player-panel__job">Job {jobId}</span>
          </div>
          <TabsList className="player-panel__tabs" aria-label="Media categories">
            {TAB_DEFINITIONS.map((tab) => {
              const count = media[tab.key].length;
              return (
                <TabsTrigger
                  key={tab.key}
                  className="player-panel__tab"
                  value={tab.key}
                  data-testid={`media-tab-${tab.key}`}
                >
                  {tab.label} ({count})
                </TabsTrigger>
              );
            })}
          </TabsList>
        </header>
        {TAB_DEFINITIONS.map((tab) => {
          const isActive = tab.key === selectedMediaType;
          const items = isActive
            ? filteredMedia
            : combinedMedia.filter((item) => item.type === tab.key);
          return (
            <TabsContent key={tab.key} value={tab.key} className="player-panel__panel">
              {!hasAnyMedia && !isLoading ? (
                <p role="status">No generated media yet.</p>
              ) : items.length === 0 ? (
                <MediaList items={items} category={tab.key} emptyMessage={tab.emptyMessage} />
              ) : (
                <>
                  {tab.key === 'audio' ? <AudioPlayer files={filteredAudioFiles} /> : null}
                  {tab.key === 'video' ? <VideoPlayer files={filteredVideoFiles} /> : null}
                  <MediaList items={items} category={tab.key} emptyMessage={tab.emptyMessage} />
                </>
              )}
            </TabsContent>
          );
        })}
      </Tabs>
    </section>
  );
}
