import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { UIEvent } from 'react';
import AudioPlayer from './AudioPlayer';
import VideoPlayer from './VideoPlayer';
import MediaList from './MediaList';
import type { LiveMediaItem, LiveMediaState } from '../hooks/useLiveMedia';
import { useMediaMemory } from '../hooks/useMediaMemory';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/Tabs';
import { extractTextFromHtml, formatFileSize, formatTimestamp } from '../utils/mediaFormatters';

type MediaCategory = keyof LiveMediaState;
type NavigationIntent = 'first' | 'previous' | 'next' | 'last';

interface PlayerPanelProps {
  jobId: string;
  media: LiveMediaState;
  isLoading: boolean;
  error: Error | null;
  onVideoPlaybackStateChange?: (isPlaying: boolean) => void;
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

export default function PlayerPanel({
  jobId,
  media,
  isLoading,
  error,
  onVideoPlaybackStateChange,
}: PlayerPanelProps) {
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
  const [isVideoPlaying, setIsVideoPlaying] = useState(false);
  const isVideoTabActive = selectedMediaType === 'video';
  const mediaMemory = useMediaMemory({ jobId });
  const { state: memoryState, rememberSelection, rememberPosition, getPosition, findMatchingMediaId, deriveBaseId } = mediaMemory;
  const textScrollRef = useRef<HTMLElement | null>(null);
  const mediaIndex = useMemo(() => {
    const map: Record<MediaCategory, Map<string, LiveMediaItem>> = {
      text: new Map(),
      audio: new Map(),
      video: new Map(),
    };

    (['text', 'audio', 'video'] as MediaCategory[]).forEach((category) => {
      media[category].forEach((item) => {
        if (item.url) {
          map[category].set(item.url, item);
        }
      });
    });

    return map;
  }, [media]);

  const getMediaItem = useCallback(
    (category: MediaCategory, id: string | null | undefined) => {
      if (!id) {
        return null;
      }
      return mediaIndex[category].get(id) ?? null;
    },
    [mediaIndex],
  );

  const activeItemId = selectedItemIds[selectedMediaType];

  useEffect(() => {
    setSelectedMediaType((current) => {
      if (current && media[current].length > 0) {
        return current;
      }
      return selectInitialTab(media);
    });
  }, [media]);

  useEffect(() => {
    const rememberedType = memoryState.currentMediaType;
    const rememberedId = memoryState.currentMediaId;
    if (!rememberedType || !rememberedId) {
      return;
    }

    if (!mediaIndex[rememberedType].has(rememberedId)) {
      return;
    }

    setSelectedItemIds((current) => {
      if (current[rememberedType] === rememberedId) {
        return current;
      }
      return { ...current, [rememberedType]: rememberedId };
    });

    setSelectedMediaType((current) => (current === rememberedType ? current : rememberedType));
  }, [memoryState.currentMediaId, memoryState.currentMediaType, mediaIndex]);

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

  useEffect(() => {
    if (!activeItemId) {
      return;
    }

    const currentItem = getMediaItem(selectedMediaType, activeItemId);
    if (!currentItem) {
      return;
    }

    rememberSelection({ media: currentItem });
  }, [activeItemId, selectedMediaType, getMediaItem, rememberSelection]);

  const handleTabChange = useCallback(
    (nextValue: string) => {
      const nextType = nextValue as MediaCategory;
      setSelectedMediaType(nextType);
      setSelectedItemIds((current) => {
        const baseId = memoryState.baseId;
        if (!baseId) {
          return current;
        }

        const match = findMatchingMediaId(baseId, nextType, media[nextType]);
        if (!match || current[nextType] === match) {
          return current;
        }

        return { ...current, [nextType]: match };
      });
    },
    [findMatchingMediaId, media, memoryState.baseId],
  );

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

  const updateSelection = useCallback(
    (category: MediaCategory, intent: NavigationIntent) => {
      setSelectedItemIds((current) => {
        const navigableItems = media[category].filter(
          (item) => typeof item.url === 'string' && item.url.length > 0,
        );
        if (navigableItems.length === 0) {
          return current;
        }

        const currentId = current[category];
        const currentIndex = currentId
          ? navigableItems.findIndex((item) => item.url === currentId)
          : -1;

        let nextIndex = currentIndex;
        switch (intent) {
          case 'first':
            nextIndex = 0;
            break;
          case 'last':
            nextIndex = navigableItems.length - 1;
            break;
          case 'previous':
            nextIndex = currentIndex <= 0 ? 0 : currentIndex - 1;
            break;
          case 'next':
            nextIndex = currentIndex < 0 ? 0 : Math.min(currentIndex + 1, navigableItems.length - 1);
            break;
          default:
            nextIndex = currentIndex;
        }

        if (nextIndex === currentIndex && currentId !== null) {
          return current;
        }

        const nextItem = navigableItems[nextIndex];
        if (!nextItem?.url) {
          return current;
        }

        if (nextItem.url === currentId) {
          return current;
        }

        return { ...current, [category]: nextItem.url };
      });
    },
    [media],
  );

  const handleSelectFromList = useCallback(
    (category: MediaCategory, item: LiveMediaItem) => {
      if (!item.url) {
        return;
      }

      handleSelectMedia(category, item.url);
      setSelectedMediaType((current) => (current === category ? current : category));
    },
    [handleSelectMedia],
  );

  const audioFiles = useMemo(() => toAudioFiles(media.audio), [media.audio]);
  const videoFiles = useMemo(() => toVideoFiles(media.video), [media.video]);
  useEffect(() => {
    if (videoFiles.length === 0 && isVideoPlaying) {
      setIsVideoPlaying(false);
    }
  }, [videoFiles.length, isVideoPlaying]);
  const textContentCache = useRef(new Map<string, string>());
  const [textPreview, setTextPreview] = useState<{ url: string; content: string } | null>(null);
  const [textLoading, setTextLoading] = useState(false);
  const [textError, setTextError] = useState<string | null>(null);

  useEffect(() => {
    onVideoPlaybackStateChange?.(isVideoPlaying);
  }, [isVideoPlaying, onVideoPlaybackStateChange]);

  useEffect(() => {
    if (!isVideoTabActive && isVideoPlaying) {
      setIsVideoPlaying(false);
    }
  }, [isVideoPlaying, isVideoTabActive]);
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
  const audioPlaybackPosition = getPosition(selectedItemIds.audio);
  const videoPlaybackPosition = getPosition(selectedItemIds.video);
  const textPlaybackPosition = getPosition(selectedItemIds.text);
  const selectedItem = useMemo(() => {
    if (filteredMedia.length === 0) {
      return null;
    }

    if (!selectedItemId) {
      return filteredMedia[0];
    }

    return filteredMedia.find((item) => item.url === selectedItemId) ?? filteredMedia[0];
  }, [filteredMedia, selectedItemId]);
  const isImmersiveMode = isVideoTabActive && isVideoPlaying;
  const panelClassName = isImmersiveMode ? 'player-panel player-panel--immersive' : 'player-panel';
  const selectedTimestamp = selectedItem ? formatTimestamp(selectedItem.updated_at ?? null) : null;
  const selectedSize = selectedItem ? formatFileSize(selectedItem.size ?? null) : null;
  const navigableItems = useMemo(
    () =>
      media[selectedMediaType].filter((item) => typeof item.url === 'string' && item.url.length > 0),
    [media, selectedMediaType],
  );
  const activeNavigableIndex = useMemo(() => {
    const currentId = selectedItemIds[selectedMediaType];
    if (!currentId) {
      return navigableItems.length > 0 ? 0 : -1;
    }

    const matchIndex = navigableItems.findIndex((item) => item.url === currentId);
    if (matchIndex >= 0) {
      return matchIndex;
    }

    return navigableItems.length > 0 ? 0 : -1;
  }, [navigableItems, selectedItemIds, selectedMediaType]);
  const isFirstDisabled =
    navigableItems.length === 0 || (activeNavigableIndex === 0 && navigableItems.length > 0);
  const isPreviousDisabled = navigableItems.length === 0 || activeNavigableIndex <= 0;
  const isNextDisabled =
    navigableItems.length === 0 ||
    (activeNavigableIndex !== -1 && activeNavigableIndex >= navigableItems.length - 1);
  const isLastDisabled =
    navigableItems.length === 0 ||
    (activeNavigableIndex !== -1 && activeNavigableIndex >= navigableItems.length - 1);

  const handleAdvanceMedia = useCallback(
    (category: MediaCategory) => {
      updateSelection(category, 'next');
    },
    [updateSelection],
  );

  const handleNavigate = useCallback(
    (intent: NavigationIntent) => {
      updateSelection(selectedMediaType, intent);
    },
    [selectedMediaType, updateSelection],
  );

  const handleTextScroll = useCallback(
    (event: UIEvent<HTMLElement>) => {
      const mediaId = selectedItemIds.text;
      if (!mediaId) {
        return;
      }

      const current = getMediaItem('text', mediaId);
      const baseId = current ? deriveBaseId(current) : null;
      const target = event.currentTarget as HTMLElement;
      rememberPosition({ mediaId, mediaType: 'text', baseId, position: target.scrollTop ?? 0 });
    },
    [selectedItemIds.text, getMediaItem, deriveBaseId, rememberPosition],
  );

  const handleAudioProgress = useCallback(
    (position: number) => {
      const mediaId = selectedItemIds.audio;
      if (!mediaId) {
        return;
      }

      const current = getMediaItem('audio', mediaId);
      const baseId = current ? deriveBaseId(current) : null;
      rememberPosition({ mediaId, mediaType: 'audio', baseId, position });
    },
    [selectedItemIds.audio, getMediaItem, deriveBaseId, rememberPosition],
  );

  const handleVideoProgress = useCallback(
    (position: number) => {
      const mediaId = selectedItemIds.video;
      if (!mediaId) {
        return;
      }

      const current = getMediaItem('video', mediaId);
      const baseId = current ? deriveBaseId(current) : null;
      rememberPosition({ mediaId, mediaType: 'video', baseId, position });
    },
    [selectedItemIds.video, getMediaItem, deriveBaseId, rememberPosition],
  );

  const handleVideoPlaybackStateChange = useCallback((state: 'playing' | 'paused') => {
    setIsVideoPlaying(state === 'playing');
  }, []);

  useEffect(() => {
    if (selectedMediaType !== 'text') {
      return;
    }

    const mediaId = selectedItemIds.text;
    if (!mediaId) {
      return;
    }

    const element = textScrollRef.current;
    if (!element) {
      return;
    }

    const storedPosition = textPlaybackPosition;
    if (Math.abs(element.scrollTop - storedPosition) < 1) {
      return;
    }

    try {
      element.scrollTop = storedPosition;
      if (typeof element.scrollTo === 'function') {
        element.scrollTo({ top: storedPosition });
      }
    } catch (error) {
      // Swallow assignment errors triggered by unsupported scrolling APIs in tests.
    }
  }, [selectedMediaType, selectedItemIds.text, textPlaybackPosition, textPreview?.url]);

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

    fetch(url, { credentials: 'include' })
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

        const normalised = extractTextFromHtml(raw);
        textContentCache.current.set(url, normalised);
        setTextPreview({ url, content: normalised });
        setTextError(null);
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
    <section className={panelClassName} aria-label="Generated media">
      <Tabs className="player-panel__tabs-container" value={selectedMediaType} onValueChange={handleTabChange}>
        <header className="player-panel__header">
          <div className="player-panel__heading">
            <h2>Generated media</h2>
            <span className="player-panel__job">Job {jobId}</span>
          </div>
          <div className="player-panel__tabs-row">
            <div className="player-panel__navigation" role="group" aria-label="Navigate media items">
              <button
                type="button"
                className="player-panel__nav-button"
                onClick={() => handleNavigate('first')}
                disabled={isFirstDisabled}
                aria-label="Go to first item"
              >
                <span aria-hidden="true">⏮</span>
              </button>
              <button
                type="button"
                className="player-panel__nav-button"
                onClick={() => handleNavigate('previous')}
                disabled={isPreviousDisabled}
                aria-label="Go to previous item"
              >
                <span aria-hidden="true">⏪</span>
              </button>
              <button
                type="button"
                className="player-panel__nav-button"
                onClick={() => handleNavigate('next')}
                disabled={isNextDisabled}
                aria-label="Go to next item"
              >
                <span aria-hidden="true">⏩</span>
              </button>
              <button
                type="button"
                className="player-panel__nav-button"
                onClick={() => handleNavigate('last')}
                disabled={isLastDisabled}
                aria-label="Go to last item"
              >
                <span aria-hidden="true">⏭</span>
              </button>
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
          </div>
        </header>
        {TAB_DEFINITIONS.map((tab) => {
          const isActive = tab.key === selectedMediaType;
          const items = isActive
            ? filteredMedia
            : combinedMedia.filter((item) => item.type === tab.key);
          const shouldHideList = tab.key === 'video' && isImmersiveMode;
          const isExpanded = shouldHideList ? false : expandedLists.has(tab.key);
          const listId = `player-panel-${tab.key}-list`;
          return (
            <TabsContent key={tab.key} value={tab.key} className="player-panel__panel">
              {!hasAnyMedia && !isLoading ? (
                <p role="status">No generated media yet.</p>
              ) : items.length === 0 ? (
                <MediaList
                  id={listId}
                  items={items}
                  category={tab.key}
                  emptyMessage={tab.emptyMessage}
                  selectedKey={selectedItemIds[tab.key] ?? null}
                  onSelectItem={(entry) => handleSelectFromList(tab.key, entry)}
                />
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
                            playbackPosition={audioPlaybackPosition}
                            onPlaybackPositionChange={handleAudioProgress}
                          />
                        ) : null}
                        {tab.key === 'video' ? (
                          <VideoPlayer
                            files={videoFiles}
                            activeId={selectedItemIds.video}
                            onSelectFile={(fileId) => handleSelectMedia('video', fileId)}
                            autoPlay
                            onPlaybackEnded={() => handleAdvanceMedia('video')}
                            playbackPosition={videoPlaybackPosition}
                            onPlaybackPositionChange={handleVideoProgress}
                            onPlaybackStateChange={handleVideoPlaybackStateChange}
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
                                textPreview.content ? (
                                  <article
                                    ref={textScrollRef}
                                    className="player-panel__document-body"
                                    data-testid="player-panel-document"
                                    onScroll={handleTextScroll}
                                  >
                                    <pre className="player-panel__document-text">{textPreview.content}</pre>
                                  </article>
                                ) : (
                                  <div className="player-panel__document-status" role="status">
                                    Document preview is empty.
                                  </div>
                                )
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
                  {shouldHideList ? null : (
                    <>
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
                        <MediaList
                          id={listId}
                          items={items}
                          category={tab.key}
                          emptyMessage={tab.emptyMessage}
                          selectedKey={selectedItemIds[tab.key] ?? null}
                          onSelectItem={(entry) => handleSelectFromList(tab.key, entry)}
                        />
                      </div>
                    </>
                  )}
                </>
              )}
            </TabsContent>
          );
        })}
      </Tabs>
    </section>
  );
}
