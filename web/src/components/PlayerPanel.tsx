import { useEffect, useMemo, useRef, useState } from 'react';
import TextViewer from './TextViewer';
import AudioPlayer from './AudioPlayer';
import VideoPlayer from './VideoPlayer';
import MediaList from './MediaList';

type MediaFilesByType = Record<string, string[]>;

type PlayerPanelProps = {
  mediaFiles: MediaFilesByType;
  isGenerating: boolean;
  isLoading?: boolean;
};

type TabKey = 'text' | 'audio' | 'video';

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: 'text', label: 'Text' },
  { key: 'audio', label: 'Audio' },
  { key: 'video', label: 'Video' }
];

export default function PlayerPanel({ mediaFiles, isGenerating, isLoading = false }: PlayerPanelProps) {
  const [activeTab, setActiveTab] = useState<TabKey>('text');
  const [recentlyUpdated, setRecentlyUpdated] = useState<Record<string, boolean>>({});
  const previousCountsRef = useRef<Record<string, number>>({});

  const filesByTab = useMemo(() => {
    const mapping: Record<TabKey, string[]> = {
      text: mediaFiles.text ?? [],
      audio: mediaFiles.audio ?? [],
      video: mediaFiles.video ?? []
    };
    return mapping;
  }, [mediaFiles]);

  useEffect(() => {
    const updates: Record<string, boolean> = {};
    const previous = previousCountsRef.current;
    for (const tab of TABS) {
      const nextCount = filesByTab[tab.key]?.length ?? 0;
      const prevCount = previous[tab.key] ?? 0;
      if (nextCount > prevCount) {
        updates[tab.key] = true;
      }
      previous[tab.key] = nextCount;
    }
    if (Object.keys(updates).length === 0) {
      return;
    }
    setRecentlyUpdated((current) => ({ ...current, ...updates }));
    const timeout = window.setTimeout(() => {
      setRecentlyUpdated((current) => {
        const next = { ...current };
        for (const key of Object.keys(updates)) {
          next[key] = false;
        }
        return next;
      });
    }, 400);
    return () => {
      window.clearTimeout(timeout);
    };
  }, [filesByTab]);

  useEffect(() => {
    if (filesByTab[activeTab]?.length) {
      return;
    }
    for (const tab of TABS) {
      if (filesByTab[tab.key]?.length) {
        setActiveTab(tab.key);
        return;
      }
    }
  }, [activeTab, filesByTab]);

  const activeFiles = filesByTab[activeTab] ?? [];
  const hasAnyMedia = TABS.some((tab) => filesByTab[tab.key]?.length);
  const showIndicator = recentlyUpdated[activeTab] ?? false;

  return (
    <section className="player-panel">
      <header className="player-panel__header">
        <nav className="player-panel__tabs" aria-label="Media types">
          {TABS.map((tab) => {
            const count = filesByTab[tab.key]?.length ?? 0;
            const label = `${tab.label}${count ? ` (${count})` : ''}`;
            return (
              <button
                key={tab.key}
                type="button"
                className={tab.key === activeTab ? 'active' : undefined}
                onClick={() => setActiveTab(tab.key)}
                disabled={count === 0 && tab.key !== activeTab}
              >
                {label}
              </button>
            );
          })}
        </nav>
        {isGenerating ? (
          <span className="player-panel__status" role="status">
            Generating media…
          </span>
        ) : null}
      </header>
      <div className="player-panel__body">
        {activeTab === 'text' ? (
          <TextViewer files={activeFiles} isLoading={isLoading} isGenerating={isGenerating} />
        ) : null}
        {activeTab === 'audio' ? <AudioPlayer files={activeFiles} showUpdatingIndicator={showIndicator} /> : null}
        {activeTab === 'video' ? <VideoPlayer files={activeFiles} showUpdatingIndicator={showIndicator} /> : null}
      </div>
      <div className="player-panel__list">
        <MediaList mediaType={activeTab} files={activeFiles} />
      </div>
      {!hasAnyMedia && !isLoading ? (
        <p className="player-panel__empty" role="status">
          Media outputs will appear here once they are generated.
        </p>
      ) : null}
    </section>
  );
}
