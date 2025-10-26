import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import AudioPlayer from './AudioPlayer';
import VideoPlayer from './VideoPlayer';
import MediaList from './MediaList';
import type { LiveMediaState } from '../hooks/useLiveMedia';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/Tabs';
import { formatFileSize, formatTimestamp } from '../utils/mediaFormatters';

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
  const [expandedLists, setExpandedLists] = useState<Set<MediaCategory>>(() => new Set());
  const [selectedItemIds, setSelectedItemIds] = useState<Record<MediaCategory, string | null>>(() => {
    const initial: Record<MediaCategory, string | null> = {
      text: null,
      audio: null,
      video: null,
    };

    (['text', 'audio', 'video'] as MediaCategory[]).forEach((category) => {
      const firstItem = media[category][0];
      initial[category] = firstItem?.url ?? null;
    });

    return initial;
  });

  useEffect(() => {
    setSelectedMediaType((current) => {
      if (current && media[current].length > 0) {
        return current;
      }
      return selectInitialTab(media);
    });
  }, [media]);

  useEffect(() => {
    setSelectedItemIds((current) => {
      let changed = false;
      const next: Record<MediaCategory, string | null> = { ...current };

      (['text', 'audio', 'video'] as MediaCategory[]).forEach((category) => {
        const items = media[category];
        const currentId = current[category];

        if (items.length === 0) {
          if (currentId !== null) {
            next[category] = null;
            changed = true;
          }
          return;
        }

        const hasCurrent = currentId !== null && items.some((item) => item.url === currentId);

        if (!hasCurrent) {
          next[category] = items[0].url ?? null;
          if (next[category] !== currentId) {
            changed = true;
          }
        }
      });

      return changed ? next : current;
    });
  }, [media]);

  const handleTabChange = useCallback((nextValue: string) => {
    setSelectedMediaType(nextValue as MediaCategory);
  }, []);

  const toggleListVisibility = useCallback((category: MediaCategory) => {
    setExpandedLists((current) => {
      const next = new Set(current);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  }, []);

  const handleSelectMedia = useCallback((category: MediaCategory, fileId: string) => {
    setSelectedItemIds((current) => {
      if (current[category] === fileId) {
        return current;
      }

      return { ...current, [category]: fileId };
    });
  }, []);

  const audioFiles = useMemo(() => toAudioFiles(media.audio), [media.audio]);
  const videoFiles = useMemo(() => toVideoFiles(media.video), [media.video]);
  const textContentCache = useRef(new Map<string, string>());
  const [textPreview, setTextPreview] = useState<{ url: string; content: string } | null>(null);
  const [textLoading, setTextLoading] = useState(false);
  const [textError, setTextError] = useState<string | null>(null);
  const combinedMedia = useMemo(
    () =>
      (['text', 'audio', 'video'] as MediaCategory[]).flatMap((category) =>
        media[category].map((item) => ({ ...item, type: category })),
      ),
    [media],
  );
  const filteredMedia = useMemo(
    () => combinedMedia.filter((item) => item.type === selectedMediaType),
    [combinedMedia, selectedMediaType],
  );
  const selectedItemId = selectedItemIds[selectedMediaType];
  const selectedItem = useMemo(() => {
    if (filteredMedia.length === 0) {
      return null;
    }

    if (!selectedItemId) {
      return filteredMedia[0];
    }

    return filteredMedia.find((item) => item.url === selectedItemId) ?? filteredMedia[0];
  }, [filteredMedia, selectedItemId]);
  const selectedTimestamp = selectedItem ? formatTimestamp(selectedItem.updated_at ?? null) : null;
  const selectedSize = selectedItem ? formatFileSize(selectedItem.size ?? null) : null;

  const handleAdvanceMedia = useCallback(
    (category: MediaCategory) => {
      setSelectedItemIds((current) => {
        const playableItems = media[category].filter(
          (item) => typeof item.url === 'string' && item.url.length > 0,
        );
        if (playableItems.length === 0) {
          return current;
        }

        const currentId = current[category];
        const currentIndex = currentId
          ? playableItems.findIndex((item) => item.url === currentId)
          : -1;
        const nextIndex = currentIndex + 1;
        if (nextIndex >= playableItems.length || nextIndex < 0) {
          return current;
        }

        const nextItem = playableItems[nextIndex];
        if (!nextItem?.url || nextItem.url === currentId) {
          return current;
        }

        return { ...current, [category]: nextItem.url };
      });
    },
    [media],
  );

  useEffect(() => {
    if (selectedMediaType !== 'text') {
      return;
    }

    const url = selectedItem?.url;
    if (!url) {
      setTextPreview(null);
      setTextError(null);
      setTextLoading(false);
      return;
    }

    if (textContentCache.current.has(url)) {
      const cached = textContentCache.current.get(url) ?? '';
      setTextPreview({ url, content: cached });
      setTextError(null);
      setTextLoading(false);
      return;
    }

    let cancelled = false;

    setTextLoading(true);
    setTextError(null);
    setTextPreview(null);

    if (typeof fetch !== 'function') {
      setTextLoading(false);
      setTextPreview(null);
      setTextError('Document preview is unavailable in this environment.');
      return;
    }

    fetch(url)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to load document (status ${response.status})`);
        }
        return response.text();
      })
      .then((raw) => {
        if (cancelled) {
          return;
        }

        let extracted = raw;
        try {
          if (typeof window !== 'undefined' && 'DOMParser' in window) {
            const parser = new DOMParser();
            const doc = parser.parseFromString(raw, 'text/html');
            const text = doc.body?.textContent;
            if (text && text.trim().length > 0) {
              extracted = text;
            }
          }
        } catch (parseError) {
          console.warn('Unable to parse text document', parseError);
        }

        const normalised = extracted
          .replace(/\u00a0/g, ' ')
          .replace(/\r\n/g, '\n')
          .replace(/\n{3,}/g, '\n\n')
          .trim();

        textContentCache.current.set(url, normalised);
        setTextPreview({ url, content: normalised });
      })
      .catch((requestError) => {
        if (cancelled) {
          return;
        }
        const message =
          requestError instanceof Error
            ? requestError.message
            : 'Failed to load document.';
        setTextError(message);
      })
      .finally(() => {
        if (!cancelled) {
          setTextLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedMediaType, selectedItem?.url]);

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
          const isExpanded = expandedLists.has(tab.key);
          const listId = `player-panel-${tab.key}-list`;
          return (
            <TabsContent key={tab.key} value={tab.key} className="player-panel__panel">
              {!hasAnyMedia && !isLoading ? (
                <p role="status">No generated media yet.</p>
              ) : items.length === 0 ? (
                <MediaList id={listId} items={items} category={tab.key} emptyMessage={tab.emptyMessage} />
              ) : (
                <>
                  {isActive ? (
                    <div className="player-panel__stage">
                      <div className="player-panel__selection-header" data-testid="player-panel-selection">
                        <div
                          className="player-panel__selection-name"
                          title={selectedItem?.name ?? 'No media selected'}
                        >
                          {selectedItem ? `Selected media: ${selectedItem.name}` : 'No media selected'}
                        </div>
                        <dl className="player-panel__selection-meta">
                          <div className="player-panel__selection-meta-item">
                            <dt>Created</dt>
                            <dd>{selectedTimestamp ?? '—'}</dd>
                          </div>
                          <div className="player-panel__selection-meta-item">
                            <dt>File size</dt>
                            <dd>{selectedSize ?? '—'}</dd>
                          </div>
                        </dl>
                      </div>
                      <div className="player-panel__viewer">
                        {tab.key === 'audio' ? (
                          <AudioPlayer
                            files={audioFiles}
                            activeId={selectedItemIds.audio}
                            onSelectFile={(fileId) => handleSelectMedia('audio', fileId)}
                            autoPlay
                            onPlaybackEnded={() => handleAdvanceMedia('audio')}
                          />
                        ) : null}
                        {tab.key === 'video' ? (
                          <VideoPlayer
                            files={videoFiles}
                            activeId={selectedItemIds.video}
                            onSelectFile={(fileId) => handleSelectMedia('video', fileId)}
                            autoPlay
                            onPlaybackEnded={() => handleAdvanceMedia('video')}
                          />
                        ) : null}
                        {tab.key === 'text' ? (
                          <div className="player-panel__document">
                            {selectedItem ? (
                              textLoading ? (
                                <div className="player-panel__document-status" role="status">
                                  Loading document…
                                </div>
                              ) : textError ? (
                                <div className="player-panel__document-error" role="alert">
                                  {textError}
                                </div>
                              ) : textPreview ? (
                                <article className="player-panel__document-body" data-testid="player-panel-document">
                                  <pre className="player-panel__document-text">{textPreview.content}</pre>
                                </article>
                              ) : (
                                <div className="player-panel__document-status" role="status">
                                  Preparing document preview…
                                </div>
                              )
                            ) : (
                              <div className="player-panel__empty-viewer" role="status">
                                Select a file to preview.
                              </div>
                            )}
                          </div>
                        ) : null}
                      </div>
                    </div>
                  ) : null}
                  <div className="player-panel__list-toggle">
                    <button
                      type="button"
                      className="player-panel__list-toggle-button"
                      aria-expanded={isExpanded}
                      aria-controls={listId}
                      onClick={() => toggleListVisibility(tab.key)}
                    >
                      {isExpanded ? 'Hide detailed file list' : 'Show detailed file list'}
                    </button>
                  </div>
                  <div
                    className="player-panel__media-list"
                    id={`${listId}-container`}
                    hidden={!isExpanded}
                    aria-hidden={!isExpanded}
                  >
                    <MediaList id={listId} items={items} category={tab.key} emptyMessage={tab.emptyMessage} />
                  </div>
                </>
              )}
            </TabsContent>
          );
        })}
      </Tabs>
    </section>
  );
}
