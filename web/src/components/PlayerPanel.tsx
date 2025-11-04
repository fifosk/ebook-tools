import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { UIEvent } from 'react';
import AudioPlayer from './AudioPlayer';
import VideoPlayer from './VideoPlayer';
import type { LiveMediaChunk, LiveMediaItem, LiveMediaState } from '../hooks/useLiveMedia';
import { useMediaMemory } from '../hooks/useMediaMemory';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/Tabs';
import { extractTextFromHtml, formatFileSize, formatTimestamp } from '../utils/mediaFormatters';
import MediaSearchPanel from './MediaSearchPanel';
import type { ChunkSentenceMetadata, LibraryItem, MediaSearchResult } from '../api/dtos';
import { appendAccessToken, buildStorageUrl, resolveJobCoverUrl, resolveLibraryMediaUrl } from '../api/client';
import InteractiveTextViewer from './InteractiveTextViewer';
import { resolve as resolveStoragePath } from '../utils/storageResolver';

const MEDIA_CATEGORIES = ['text', 'audio', 'video'] as const;
type MediaCategory = (typeof MEDIA_CATEGORIES)[number];
type SearchCategory = MediaCategory | 'library';
type NavigationIntent = 'first' | 'previous' | 'next' | 'last';
type PlaybackControls = {
  pause: () => void;
  play: () => void;
};

interface MediaSelectionRequest {
  baseId: string | null;
  preferredType?: MediaCategory | null;
  offsetRatio?: number | null;
  approximateTime?: number | null;
  token?: number;
}

interface PlayerPanelProps {
  jobId: string;
  media: LiveMediaState;
  chunks: LiveMediaChunk[];
  mediaComplete: boolean;
  isLoading: boolean;
  error: Error | null;
  bookMetadata?: Record<string, unknown> | null;
  onVideoPlaybackStateChange?: (isPlaying: boolean) => void;
  origin?: 'job' | 'library';
  onOpenLibraryItem?: (item: LibraryItem | string) => void;
}

interface TabDefinition {
  key: MediaCategory;
  label: string;
  emptyMessage: string;
}

const TAB_DEFINITIONS: TabDefinition[] = [
  { key: 'text', label: 'Interactive Reader', emptyMessage: 'No interactive reader media yet.' },
  { key: 'audio', label: 'Audio', emptyMessage: 'No audio media yet.' },
  { key: 'video', label: 'Video', emptyMessage: 'No video media yet.' },
];

const DEFAULT_COVER_URL = '/assets/default-cover.png';

interface NavigationControlsProps {
  context: 'panel' | 'fullscreen';
  onNavigate: (intent: NavigationIntent) => void;
  onToggleFullscreen: () => void;
  onPlay: () => void;
  onPause: () => void;
  disableFirst: boolean;
  disablePrevious: boolean;
  disableNext: boolean;
  disableLast: boolean;
  disablePlay: boolean;
  disablePause: boolean;
  disableFullscreen: boolean;
  isFullscreen: boolean;
  fullscreenLabel: string;
  inlineAudioOptions: { url: string; label: string }[];
  inlineAudioSelection: string | null;
  onSelectInlineAudio: (audioUrl: string) => void;
  showInlineAudio: boolean;
}

function NavigationControls({
  context,
  onNavigate,
  onToggleFullscreen,
  onPlay,
  onPause,
  disableFirst,
  disablePrevious,
  disableNext,
  disableLast,
  disablePlay,
  disablePause,
  disableFullscreen,
  isFullscreen,
  fullscreenLabel,
  inlineAudioOptions,
  inlineAudioSelection,
  onSelectInlineAudio,
  showInlineAudio,
}: NavigationControlsProps) {
  const inlineAudioId =
    context === 'fullscreen' ? 'player-panel-inline-audio-fullscreen' : 'player-panel-inline-audio';
  const groupClassName =
    context === 'fullscreen'
      ? 'player-panel__navigation-group player-panel__navigation-group--fullscreen'
      : 'player-panel__navigation-group';
  const navigationClassName =
    context === 'fullscreen'
      ? 'player-panel__navigation player-panel__navigation--fullscreen'
      : 'player-panel__navigation';
  const inlineAudioClassName =
    context === 'fullscreen'
      ? 'player-panel__inline-audio player-panel__inline-audio--fullscreen'
      : 'player-panel__inline-audio';
  const fullscreenTestId = context === 'panel' ? 'player-panel-interactive-fullscreen' : undefined;

  return (
    <div className={groupClassName}>
      <div className={navigationClassName} role="group" aria-label="Navigate media items">
        <button
          type="button"
          className="player-panel__nav-button"
          onClick={() => onNavigate('first')}
          disabled={disableFirst}
          aria-label="Go to first item"
        >
          <span aria-hidden="true">⏮</span>
        </button>
        <button
          type="button"
          className="player-panel__nav-button"
          onClick={() => onNavigate('previous')}
          disabled={disablePrevious}
          aria-label="Go to previous item"
        >
          <span aria-hidden="true">⏪</span>
        </button>
        <button
          type="button"
          className="player-panel__nav-button"
          onClick={onPlay}
          disabled={disablePlay}
          aria-label="Play playback"
        >
          <span aria-hidden="true">▶</span>
        </button>
        <button
          type="button"
          className="player-panel__nav-button"
          onClick={onPause}
          disabled={disablePause}
          aria-label="Pause playback"
        >
          <span aria-hidden="true">⏸</span>
        </button>
        <button
          type="button"
          className="player-panel__nav-button"
          onClick={() => onNavigate('next')}
          disabled={disableNext}
          aria-label="Go to next item"
        >
          <span aria-hidden="true">⏩</span>
        </button>
        <button
          type="button"
          className="player-panel__nav-button"
          onClick={() => onNavigate('last')}
          disabled={disableLast}
          aria-label="Go to last item"
        >
          <span aria-hidden="true">⏭</span>
        </button>
        <button
          type="button"
          className="player-panel__nav-button"
          onClick={onToggleFullscreen}
          disabled={disableFullscreen}
          aria-pressed={isFullscreen}
          aria-label={fullscreenLabel}
          data-testid={fullscreenTestId}
        >
          <span aria-hidden="true">⛶</span>
        </button>
      </div>
      {showInlineAudio && inlineAudioOptions.length > 0 ? (
        <div className={inlineAudioClassName} role="group" aria-label="Synchronized audio">
          <label className="player-panel__inline-audio-label" htmlFor={inlineAudioId}>
            Synchronized audio
          </label>
          <select
            id={inlineAudioId}
            value={inlineAudioSelection ?? inlineAudioOptions[0]?.url ?? ''}
            onChange={(event) => onSelectInlineAudio(event.target.value)}
            disabled={inlineAudioOptions.length === 1}
          >
            {inlineAudioOptions.map((option) => (
              <option key={`${context}-${option.url}`} value={option.url}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      ) : null}
    </div>
  );
}

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

function deriveBaseIdFromReference(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const normalised = value.replace(/^[\\/]+/, '').split(/[\\/]/).pop();
  if (!normalised) {
    return null;
  }
  const withoutQuery = normalised.replace(/[?#].*$/, '');
  const dotIndex = withoutQuery.lastIndexOf('.');
  const base = dotIndex > 0 ? withoutQuery.slice(0, dotIndex) : withoutQuery;
  const trimmed = base.trim();
  return trimmed ? trimmed.toLowerCase() : null;
}

function resolveBaseIdFromResult(result: MediaSearchResult, preferred: MediaCategory | null): string | null {
  if (result.base_id) {
    return result.base_id;
  }

  const categories: MediaCategory[] = [];
  if (preferred) {
    categories.push(preferred);
  }
  MEDIA_CATEGORIES.forEach((category) => {
    if (!categories.includes(category)) {
      categories.push(category);
    }
  });

  for (const category of categories) {
    const entries = result.media?.[category];
    if (!entries || entries.length === 0) {
      continue;
    }
    const primary = entries[0];
    const baseId =
      deriveBaseIdFromReference(primary.relative_path ?? null) ??
      deriveBaseIdFromReference(primary.name ?? null) ??
      deriveBaseIdFromReference(primary.url ?? null) ??
      deriveBaseIdFromReference(primary.path ?? null);
    if (baseId) {
      return baseId;
    }
  }

  return null;
}

function normaliseMetadataText(value: unknown): string | null {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }

  if (typeof value === 'number' && Number.isFinite(value)) {
    return value.toString();
  }

  return null;
}

function extractMetadataText(
  metadata: Record<string, unknown> | null | undefined,
  keys: string[],
): string | null {
  if (!metadata) {
    return null;
  }

  for (const key of keys) {
    const raw = metadata[key];
    const normalised = normaliseMetadataText(raw);
    if (normalised) {
      return normalised;
    }
  }

  return null;
}

function formatSentenceRange(start: number | null | undefined, end: number | null | undefined): string {
  if (typeof start === 'number' && typeof end === 'number') {
    return start === end ? `${start}` : `${start}–${end}`;
  }
  if (typeof start === 'number') {
    return `${start}`;
  }
  if (typeof end === 'number') {
    return `${end}`;
  }
  return '—';
}

function formatChunkLabel(chunk: LiveMediaChunk, index: number): string {
  const rangeFragment = typeof chunk.rangeFragment === 'string' ? chunk.rangeFragment.trim() : '';
  if (rangeFragment) {
    return rangeFragment;
  }
  const chunkId = typeof chunk.chunkId === 'string' ? chunk.chunkId.trim() : '';
  if (chunkId) {
    return chunkId;
  }
  const sentenceRange = formatSentenceRange(chunk.startSentence ?? null, chunk.endSentence ?? null);
  if (sentenceRange && sentenceRange !== '—') {
    return `Chunk ${index + 1} · ${sentenceRange}`;
  }
  return `Chunk ${index + 1}`;
}

function buildInteractiveAudioCatalog(
  chunks: LiveMediaChunk[],
  audioMedia: LiveMediaItem[],
): {
  playlist: LiveMediaItem[];
  nameMap: Map<string, string>;
  chunkIndexMap: Map<string, number>;
} {
  const playlist: LiveMediaItem[] = [];
  const nameMap = new Map<string, string>();
  const chunkIndexMap = new Map<string, number>();
  const seen = new Set<string>();

  const register = (
    item: LiveMediaItem | null | undefined,
    chunkIndex: number | null,
    fallbackLabel?: string,
  ) => {
    if (!item || !item.url) {
      return;
    }
    const url = item.url;
    if (seen.has(url)) {
      return;
    }
    seen.add(url);
    const trimmedName = typeof item.name === 'string' ? item.name.trim() : '';
    const trimmedFallback = typeof fallbackLabel === 'string' ? fallbackLabel.trim() : '';
    const label = trimmedName || trimmedFallback || `Audio ${playlist.length + 1}`;
    const enriched = trimmedName ? item : { ...item, name: label };
    playlist.push(enriched);
    nameMap.set(url, label);
    if (typeof chunkIndex === 'number' && chunkIndex >= 0) {
      chunkIndexMap.set(url, chunkIndex);
    }
  };

  chunks.forEach((chunk, index) => {
    const chunkLabel = formatChunkLabel(chunk, index);
    chunk.files.forEach((file) => {
      if (file.type !== 'audio') {
        return;
      }
      register(file, index, chunkLabel);
    });
  });

  audioMedia.forEach((item) => {
    if (!item.url) {
      return;
    }
    const existingIndex = chunkIndexMap.get(item.url);
    register(item, typeof existingIndex === 'number' ? existingIndex : null, item.name);
  });

  return { playlist, nameMap, chunkIndexMap };
}

function chunkCacheKey(chunk: LiveMediaChunk): string | null {
  if (chunk.chunkId) {
    return `id:${chunk.chunkId}`;
  }
  if (chunk.rangeFragment) {
    return `range:${chunk.rangeFragment}`;
  }
  if (chunk.metadataPath) {
    return `path:${chunk.metadataPath}`;
  }
  if (chunk.metadataUrl) {
    return `url:${chunk.metadataUrl}`;
  }
  const audioUrl = chunk.files.find((file) => file.type === 'audio' && file.url)?.url;
  if (audioUrl) {
    return `audio:${audioUrl}`;
  }
  return null;
}

const CHUNK_METADATA_PREFETCH_RADIUS = 2;

async function requestChunkMetadata(
  jobId: string,
  chunk: LiveMediaChunk,
): Promise<ChunkSentenceMetadata[] | null> {
  let targetUrl: string | null = chunk.metadataUrl ?? null;

  if (!targetUrl) {
    const metadataPath = chunk.metadataPath ?? null;
    if (metadataPath) {
      try {
        targetUrl = resolveStoragePath(jobId, metadataPath);
      } catch (error) {
        if (jobId) {
          const encodedJobId = encodeURIComponent(jobId);
          const sanitizedPath = metadataPath.replace(/^\/+/, '');
          targetUrl = `/pipelines/jobs/${encodedJobId}/${encodeURI(sanitizedPath)}`;
        } else {
          console.warn('Unable to resolve chunk metadata path', metadataPath, error);
        }
      }
    }
  }

  if (!targetUrl) {
    return null;
  }

  try {
    const response = await fetch(targetUrl, { credentials: 'include' });
    if (!response.ok) {
      throw new Error(`Chunk metadata request failed with status ${response.status}`);
    }
    const payload = await response.json();
    const sentences = payload?.sentences;
    if (Array.isArray(sentences)) {
      return sentences as ChunkSentenceMetadata[];
    }
    return [];
  } catch (error) {
    console.warn('Unable to load chunk metadata', targetUrl, error);
    return null;
  }
}

export default function PlayerPanel({
  jobId,
  media,
  chunks,
  mediaComplete,
  isLoading,
  error,
  bookMetadata = null,
  onVideoPlaybackStateChange,
  origin = 'job',
  onOpenLibraryItem,
}: PlayerPanelProps) {
  const interactiveViewerAvailable = chunks.length > 0;
  const [selectedMediaType, setSelectedMediaType] = useState<MediaCategory>(() =>
    interactiveViewerAvailable ? 'text' : selectInitialTab(media),
  );
  const [selectedItemIds, setSelectedItemIds] = useState<Record<MediaCategory, string | null>>(() => {
    const initial: Record<MediaCategory, string | null> = {
      text: null,
      audio: null,
      video: null,
    };

    MEDIA_CATEGORIES.forEach((category) => {
      const firstItem = media[category][0];
      initial[category] = firstItem?.url ?? null;
    });

    return initial;
  });
  const [pendingSelection, setPendingSelection] = useState<MediaSelectionRequest | null>(null);
  const [pendingTextScrollRatio, setPendingTextScrollRatio] = useState<number | null>(null);
  const [inlineAudioSelection, setInlineAudioSelection] = useState<string | null>(null);
  const [chunkMetadataStore, setChunkMetadataStore] = useState<Record<string, ChunkSentenceMetadata[]>>({});
  const chunkMetadataStoreRef = useRef(chunkMetadataStore);
  const chunkMetadataLoadingRef = useRef<Set<string>>(new Set());
  const [isVideoPlaying, setIsVideoPlaying] = useState(false);
  const [coverSourceIndex, setCoverSourceIndex] = useState(0);
  const [isImmersiveMode, setIsImmersiveMode] = useState(false);
  const [isInteractiveFullscreen, setIsInteractiveFullscreen] = useState(false);
  const hasJobId = Boolean(jobId);
  const normalisedJobId = jobId ?? '';
  const isVideoTabActive = selectedMediaType === 'video';
  const isTextTabActive = selectedMediaType === 'text';
  const visibleTabs = useMemo(() => {
    return TAB_DEFINITIONS.filter((tab) => tab.key !== 'video' || media.video.length > 0);
  }, [media.video.length]);
  const defaultTab = useMemo(() => selectInitialTab(media), [media]);
  const mediaMemory = useMediaMemory({ jobId });
  const { state: memoryState, rememberSelection, rememberPosition, getPosition, findMatchingMediaId, deriveBaseId } = mediaMemory;
  const textScrollRef = useRef<HTMLDivElement | null>(null);
  const audioControlsRef = useRef<PlaybackControls | null>(null);
  const videoControlsRef = useRef<PlaybackControls | null>(null);
  const inlineAudioControlsRef = useRef<PlaybackControls | null>(null);
  const hasSkippedInitialRememberRef = useRef(false);
  const inlineAudioBaseRef = useRef<string | null>(null);
  const [hasAudioControls, setHasAudioControls] = useState(false);
  const [hasVideoControls, setHasVideoControls] = useState(false);
  const [hasInlineAudioControls, setHasInlineAudioControls] = useState(false);

  useEffect(() => {
    chunkMetadataStoreRef.current = chunkMetadataStore;
  }, [chunkMetadataStore]);
  const mediaIndex = useMemo(() => {
    const map: Record<MediaCategory, Map<string, LiveMediaItem>> = {
      text: new Map(),
      audio: new Map(),
      video: new Map(),
    };

    MEDIA_CATEGORIES.forEach((category) => {
      media[category].forEach((item) => {
        if (item.url) {
          map[category].set(item.url, item);
        }
      });
    });

    return map;
  }, [media]);

  const jobCoverAsset = useMemo(() => {
    const value = bookMetadata?.['job_cover_asset'];
    if (typeof value !== 'string') {
      return null;
    }
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }, [bookMetadata]);

  const legacyCoverFile = useMemo(() => {
    const value = bookMetadata?.['book_cover_file'];
    if (typeof value !== 'string') {
      return null;
    }
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }, [bookMetadata]);

  const apiCoverUrl = useMemo(() => {
    if (!hasJobId || origin === 'library') {
      return null;
    }
    return resolveJobCoverUrl(normalisedJobId);
  }, [hasJobId, normalisedJobId, origin]);

  const coverCandidates = useMemo(() => {
    const candidates: string[] = [];
    const unique = new Set<string>();

    const convertCandidate = (value: string | null | undefined): string | null => {
      if (typeof value !== 'string') {
        return null;
      }
      const trimmed = value.trim();
      if (!trimmed) {
        return null;
      }

      if (origin === 'library' && trimmed.includes('/pipelines/')) {
        return null;
      }

      if (/^https?:\/\//i.test(trimmed)) {
        if (origin === 'library' && trimmed.includes('/pipelines/')) {
          return null;
        }
        return appendAccessToken(trimmed);
      }

      if (/^\/?assets\//i.test(trimmed)) {
        return trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
      }

       if (origin === 'library' && trimmed.startsWith('/') && !trimmed.startsWith('/api/library/')) {
         return null;
       }

      if (origin === 'library') {
        if (trimmed.includes('/pipelines/')) {
          return null;
        }
        if (trimmed.startsWith('/api/library/')) {
          return appendAccessToken(trimmed);
        }
        if (trimmed.startsWith('/')) {
          return null;
        }
        const resolved = resolveLibraryMediaUrl(normalisedJobId, trimmed);
        return resolved ? appendAccessToken(resolved) : null;
      }

      if (trimmed.startsWith('/api/library/')) {
        return appendAccessToken(trimmed);
      }
      if (trimmed.startsWith('/pipelines/')) {
        return appendAccessToken(trimmed);
      }

      const stripped = trimmed.replace(/^\/+/, '');
      if (!stripped) {
        return null;
      }
      try {
        return buildStorageUrl(stripped, normalisedJobId);
      } catch (error) {
        console.warn('Unable to build storage URL for cover image', error);
        return `/${stripped}`;
      }
    };

    const push = (candidate: string | null | undefined) => {
      const resolved = convertCandidate(candidate);
      if (!resolved || unique.has(resolved)) {
        return;
      }
      unique.add(resolved);
      candidates.push(resolved);
    };

    if (apiCoverUrl) {
      push(apiCoverUrl);
    }

    const metadataCoverUrl = (() => {
      const value = bookMetadata?.['job_cover_asset_url'];
      return typeof value === 'string' ? value : null;
    })();

    if (metadataCoverUrl && !(origin === 'library' && /\/pipelines\//.test(metadataCoverUrl))) {
      push(metadataCoverUrl);
    }

    push(jobCoverAsset);
    if (legacyCoverFile && legacyCoverFile !== jobCoverAsset) {
      push(legacyCoverFile);
    }

    push(DEFAULT_COVER_URL);

    return candidates;
  }, [apiCoverUrl, bookMetadata, jobCoverAsset, legacyCoverFile, normalisedJobId, origin]);

  useEffect(() => {
    if (coverSourceIndex !== 0) {
      setCoverSourceIndex(0);
    }
  }, [coverCandidates, coverSourceIndex]);

  const displayCoverUrl = coverCandidates[coverSourceIndex] ?? DEFAULT_COVER_URL;
  const handleCoverError = useCallback(() => {
    setCoverSourceIndex((currentIndex) => {
      const nextIndex = currentIndex + 1;
      if (nextIndex >= coverCandidates.length) {
        return currentIndex;
      }
      return nextIndex;
    });
  }, [coverCandidates]);
  const shouldHandleCoverError = coverSourceIndex < coverCandidates.length - 1;
  const shouldShowCoverImage = origin === 'library' || mediaComplete;
  const coverErrorHandler = shouldShowCoverImage && shouldHandleCoverError ? handleCoverError : undefined;

  const handleSearchSelection = useCallback(
    (result: MediaSearchResult, category: SearchCategory) => {
      if (category === 'library') {
        if (result.job_id) {
          onOpenLibraryItem?.(result.job_id);
        }
        return;
      }

      if (result.job_id && result.job_id !== jobId) {
        return;
      }

      const baseId = resolveBaseIdFromResult(result, category);
      const offsetRatio = typeof result.offset_ratio === 'number' ? result.offset_ratio : null;
      const approximateTime = typeof result.approximate_time_seconds === 'number' ? result.approximate_time_seconds : null;
      setPendingSelection({
        baseId,
        preferredType: category,
        offsetRatio,
        approximateTime,
        token: Date.now(),
      });

    },
    [jobId, onOpenLibraryItem],
  );

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

  const hasResolvedInitialTabRef = useRef(false);

  useEffect(() => {
    setSelectedMediaType((current) => {
      const currentHasContent = current ? media[current].length > 0 : false;

      if (!hasResolvedInitialTabRef.current) {
        hasResolvedInitialTabRef.current = true;
        if (interactiveViewerAvailable) {
          return 'text';
        }
        if (current && currentHasContent) {
          return current;
        }
        return selectInitialTab(media);
      }

      if (current && currentHasContent) {
        return current;
      }
      if (interactiveViewerAvailable) {
        return 'text';
      }
      return selectInitialTab(media);
    });
  }, [interactiveViewerAvailable, media]);

  useEffect(() => {
    if (media.video.length > 0 || selectedMediaType !== 'video') {
      return;
    }
    setSelectedMediaType(defaultTab);
  }, [defaultTab, media.video.length, selectedMediaType]);

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

      MEDIA_CATEGORIES.forEach((category) => {
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

    if (
      !hasSkippedInitialRememberRef.current &&
      memoryState.currentMediaType &&
      memoryState.currentMediaId
    ) {
      hasSkippedInitialRememberRef.current = true;
      return;
    }

    const currentItem = getMediaItem(selectedMediaType, activeItemId);
    if (!currentItem) {
      return;
    }

    rememberSelection({ media: currentItem });
  }, [
    activeItemId,
    selectedMediaType,
    getMediaItem,
    rememberSelection,
    memoryState.currentMediaId,
    memoryState.currentMediaType,
  ]);

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

  const audioFiles = useMemo(() => toAudioFiles(media.audio), [media.audio]);
  const videoFiles = useMemo(() => toVideoFiles(media.video), [media.video]);
  useEffect(() => {
    if (videoFiles.length === 0 && isVideoPlaying) {
      setIsVideoPlaying(false);
    }
  }, [videoFiles.length, isVideoPlaying]);
  const textContentCache = useRef(new Map<string, { raw: string; plain: string }>());
  const [textPreview, setTextPreview] = useState<{ url: string; content: string; raw: string } | null>(null);
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
      MEDIA_CATEGORIES.flatMap((category) =>
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
  const hasInteractiveChunks = useMemo(() => {
    return chunks.some((chunk) => {
      if (Array.isArray(chunk.sentences) && chunk.sentences.length > 0) {
        return true;
      }
      if (typeof chunk.sentenceCount === 'number' && chunk.sentenceCount > 0) {
        return true;
      }
      const cacheKey = chunkCacheKey(chunk);
      if (!cacheKey) {
        return false;
      }
      const cached = chunkMetadataStore[cacheKey];
      return cached !== undefined;
    });
  }, [chunks, chunkMetadataStore]);
  const selectedChunk = useMemo(() => {
    if (!selectedItem) {
      return null;
    }
    return (
      chunks.find((chunk) => {
        if (selectedItem.chunk_id && chunk.chunkId) {
          return chunk.chunkId === selectedItem.chunk_id;
        }
        if (selectedItem.range_fragment && chunk.rangeFragment) {
          return chunk.rangeFragment === selectedItem.range_fragment;
        }
        if (selectedItem.url) {
          return chunk.files.some((file) => file.url === selectedItem.url);
        }
        return false;
      }) ?? null
    );
  }, [chunks, selectedItem]);
  const {
    playlist: interactiveAudioPlaylist,
    nameMap: interactiveAudioNameMap,
    chunkIndexMap: audioChunkIndexMap,
  } = useMemo(() => buildInteractiveAudioCatalog(chunks, media.audio), [chunks, media.audio]);
  const activeTextChunk = useMemo(() => {
    if (selectedChunk) {
      return selectedChunk;
    }
    if (!chunks.length) {
      return null;
    }
    if (inlineAudioSelection) {
      const mappedIndex = audioChunkIndexMap.get(inlineAudioSelection);
      if (typeof mappedIndex === 'number' && mappedIndex >= 0 && mappedIndex < chunks.length) {
        return chunks[mappedIndex];
      }
    }
    const audioId = selectedItemIds.audio;
    if (audioId) {
      const mappedIndex = audioChunkIndexMap.get(audioId);
      if (typeof mappedIndex === 'number' && mappedIndex >= 0 && mappedIndex < chunks.length) {
        return chunks[mappedIndex];
      }
      const matchedByAudio = chunks.find((chunk) =>
        chunk.files.some((file) => file.type === 'audio' && file.url === audioId),
      );
      if (matchedByAudio) {
        return matchedByAudio;
      }
    }
    const firstWithSentences = chunks.find(
      (chunk) => Array.isArray(chunk.sentences) && chunk.sentences.length > 0,
    );
    return firstWithSentences ?? chunks[0];
  }, [audioChunkIndexMap, chunks, inlineAudioSelection, selectedChunk, selectedItemIds.audio]);
  const activeTextChunkIndex = useMemo(
    () => (activeTextChunk ? chunks.findIndex((chunk) => chunk === activeTextChunk) : -1),
    [activeTextChunk, chunks],
  );

  const queueChunkMetadataFetch = useCallback(
    (chunk: LiveMediaChunk | null | undefined) => {
      if (!jobId || !chunk) {
        return;
      }
      if (Array.isArray(chunk.sentences) && chunk.sentences.length > 0) {
        return;
      }
      const cacheKey = chunkCacheKey(chunk);
      if (!cacheKey) {
        return;
      }
      if (chunkMetadataStoreRef.current[cacheKey] !== undefined) {
        return;
      }
      if (chunkMetadataLoadingRef.current.has(cacheKey)) {
        return;
      }
      chunkMetadataLoadingRef.current.add(cacheKey);
      requestChunkMetadata(jobId, chunk)
        .then((sentences) => {
          if (sentences !== null) {
            setChunkMetadataStore((current) => {
              if (current[cacheKey] !== undefined) {
                return current;
              }
              return { ...current, [cacheKey]: sentences };
            });
          }
        })
        .catch((error) => {
          console.warn('Unable to load interactive chunk metadata', error);
        })
        .finally(() => {
          chunkMetadataLoadingRef.current.delete(cacheKey);
        });
    },
    [jobId],
  );

  useEffect(() => {
    if (!jobId) {
      return;
    }
    const targets = new Set<LiveMediaChunk>();

    if (activeTextChunk) {
      targets.add(activeTextChunk);
    }

    if (activeTextChunkIndex >= 0) {
      for (let offset = -CHUNK_METADATA_PREFETCH_RADIUS; offset <= CHUNK_METADATA_PREFETCH_RADIUS; offset += 1) {
        const neighbourIndex = activeTextChunkIndex + offset;
        if (neighbourIndex < 0 || neighbourIndex >= chunks.length) {
          continue;
        }
        const neighbour = chunks[neighbourIndex];
        if (neighbour) {
          targets.add(neighbour);
        }
      }
    }

    targets.forEach((chunk) => {
      queueChunkMetadataFetch(chunk);
    });
  }, [jobId, chunks, activeTextChunk, activeTextChunkIndex, queueChunkMetadataFetch]);

  const resolvedActiveTextChunk = useMemo(() => {
    if (!activeTextChunk) {
      return null;
    }
    if (Array.isArray(activeTextChunk.sentences) && activeTextChunk.sentences.length > 0) {
      return activeTextChunk;
    }
    const cacheKey = chunkCacheKey(activeTextChunk);
    if (!cacheKey) {
      return activeTextChunk;
    }
    const cached = chunkMetadataStore[cacheKey];
    if (cached !== undefined) {
      return {
        ...activeTextChunk,
        sentences: cached,
        sentenceCount: cached.length,
      };
    }
    return activeTextChunk;
  }, [activeTextChunk, chunkMetadataStore]);
  const inlineAudioOptions = useMemo(() => {
    const seen = new Set<string>();
    const options: { url: string; label: string }[] = [];
    const register = (url: string | null | undefined, label: string | null | undefined) => {
      if (!url || seen.has(url)) {
        return;
      }
      const trimmedLabel = typeof label === 'string' ? label.trim() : '';
      options.push({
        url,
        label: trimmedLabel || `Audio ${options.length + 1}`,
      });
      seen.add(url);
    };
    const chunkForOptions = resolvedActiveTextChunk ?? activeTextChunk;
    if (chunkForOptions && activeTextChunkIndex >= 0) {
      chunkForOptions.files.forEach((file) => {
        if (file.type !== 'audio' || !file.url) {
          return;
        }
        const label =
          interactiveAudioNameMap.get(file.url) ??
          (typeof file.name === 'string' ? file.name.trim() : '') ??
          formatChunkLabel(chunkForOptions, activeTextChunkIndex);
        register(file.url, label);
      });
    }
    interactiveAudioPlaylist.forEach((item, index) => {
      register(item.url, item.name ?? `Audio ${index + 1}`);
    });
    return options;
  }, [activeTextChunk, activeTextChunkIndex, interactiveAudioNameMap, interactiveAudioPlaylist, resolvedActiveTextChunk]);

  const inlineAudioUnavailable = inlineAudioOptions.length === 0;
  useEffect(() => {
    if (!pendingSelection) {
      return;
    }

    const { baseId, preferredType, offsetRatio = null, approximateTime = null } = pendingSelection;

    const candidates: MediaCategory[] = [];
    if (preferredType) {
      candidates.push(preferredType);
    }
    MEDIA_CATEGORIES.forEach((category) => {
      if (!candidates.includes(category)) {
        candidates.push(category);
      }
    });

    const matchByCategory: Record<MediaCategory, string | null> = {
      text: baseId ? findMatchingMediaId(baseId, 'text', media.text) : null,
      audio: baseId ? findMatchingMediaId(baseId, 'audio', media.audio) : null,
      video: baseId ? findMatchingMediaId(baseId, 'video', media.video) : null,
    };

    let appliedCategory: MediaCategory | null = null;

    for (const category of candidates) {
      const matchId = matchByCategory[category] ?? null;
      if (!matchId) {
        continue;
      }

      setSelectedItemIds((current) => {
        if (current[category] === matchId) {
          return current;
        }
        return { ...current, [category]: matchId };
      });
      setSelectedMediaType((current) => (current === category ? current : category));
      appliedCategory = category;
      break;
    }

    if (!appliedCategory && preferredType) {
      const category = preferredType;
      setSelectedMediaType((current) => (current === category ? current : category));
      setSelectedItemIds((current) => {
        const hasCurrent = current[category] !== null;
        if (hasCurrent) {
          return current;
        }
        const firstItem = media[category].find((item) => item.url);
        if (!firstItem?.url) {
          return current;
        }
        return { ...current, [category]: firstItem.url };
      });
      appliedCategory = media[category].length > 0 ? category : null;
    }

    if (matchByCategory.audio && approximateTime != null && Number.isFinite(approximateTime)) {
      const audioItem = getMediaItem('audio', matchByCategory.audio);
      const audioBaseId = audioItem ? deriveBaseId(audioItem) : null;
      rememberPosition({
        mediaId: matchByCategory.audio,
        mediaType: 'audio',
        baseId: audioBaseId,
        position: Math.max(approximateTime, 0),
      });
    }

    if (matchByCategory.video && approximateTime != null && Number.isFinite(approximateTime)) {
      const videoItem = getMediaItem('video', matchByCategory.video);
      const videoBaseId = videoItem ? deriveBaseId(videoItem) : null;
      rememberPosition({
        mediaId: matchByCategory.video,
        mediaType: 'video',
        baseId: videoBaseId,
        position: Math.max(approximateTime, 0),
      });
    }

    if (matchByCategory.text && offsetRatio != null && Number.isFinite(offsetRatio)) {
      setPendingTextScrollRatio(Math.max(Math.min(offsetRatio, 1), 0));
    } else {
      setPendingTextScrollRatio(null);
    }

    if (matchByCategory.audio && inlineAudioOptions.some((option) => option.url === matchByCategory.audio)) {
      setInlineAudioSelection((current) => (current === matchByCategory.audio ? current : matchByCategory.audio));
    }

    setPendingSelection(null);
  }, [
    pendingSelection,
    findMatchingMediaId,
    media,
    getMediaItem,
    deriveBaseId,
    rememberPosition,
    inlineAudioOptions,
  ]);
  const fallbackTextContent = useMemo(() => {
    if (!resolvedActiveTextChunk || !Array.isArray(resolvedActiveTextChunk.sentences)) {
      return '';
    }
    const blocks = resolvedActiveTextChunk.sentences
      .map((sentence) => {
        if (!sentence) {
          return '';
        }
        const lines: string[] = [];
        if (sentence.original?.text) {
          lines.push(sentence.original.text);
        }
        if (sentence.translation?.text) {
          lines.push(sentence.translation.text);
        }
        if (sentence.transliteration?.text) {
          lines.push(sentence.transliteration.text);
        }
        return lines.filter(Boolean).join('\n');
      })
      .filter((block) => block.trim().length > 0);
    return blocks.join('\n\n');
  }, [resolvedActiveTextChunk]);
  const interactiveViewerContent = (textPreview?.content ?? fallbackTextContent) || '';
  const interactiveViewerRaw = textPreview?.raw ?? fallbackTextContent;
  const canRenderInteractiveViewer =
    Boolean(resolvedActiveTextChunk) || interactiveViewerContent.trim().length > 0;
  const handleInteractiveFullscreenToggle = useCallback(() => {
    if (!isTextTabActive || !canRenderInteractiveViewer) {
      setIsInteractiveFullscreen(false);
      return;
    }
    setIsInteractiveFullscreen((current) => !current);
  }, [canRenderInteractiveViewer, isTextTabActive]);

  const handleExitInteractiveFullscreen = useCallback(() => {
    setIsInteractiveFullscreen(false);
  }, []);
  const isImmersiveLayout = isVideoTabActive && isImmersiveMode;
  const panelClassName = isImmersiveLayout ? 'player-panel player-panel--immersive' : 'player-panel';
  useEffect(() => {
    if (!isTextTabActive) {
      setIsInteractiveFullscreen(false);
    }
  }, [isTextTabActive]);

  useEffect(() => {
    if (!canRenderInteractiveViewer) {
      setIsInteractiveFullscreen(false);
    }
  }, [canRenderInteractiveViewer]);
  const selectedTimestamp = selectedItem ? formatTimestamp(selectedItem.updated_at ?? null) : null;
  const selectedSize = selectedItem ? formatFileSize(selectedItem.size ?? null) : null;
  const activeChunkLabel = useMemo(() => {
    if (!resolvedActiveTextChunk) {
      return null;
    }
    if (inlineAudioSelection) {
      const mappedName = interactiveAudioNameMap.get(inlineAudioSelection);
      if (mappedName) {
        return mappedName;
      }
    }
    if (activeTextChunkIndex >= 0) {
      const chunkAudioLabel = resolvedActiveTextChunk.files
        .filter((file) => file.type === 'audio' && file.url)
        .map((file) => {
          const byMap = interactiveAudioNameMap.get(file.url ?? '');
          if (byMap) {
            return byMap;
          }
          return typeof file.name === 'string' ? file.name.trim() : '';
        })
        .find((value) => value && value.length > 0);
      if (chunkAudioLabel) {
        return chunkAudioLabel;
      }
      return formatChunkLabel(resolvedActiveTextChunk, activeTextChunkIndex);
    }
    return resolvedActiveTextChunk.rangeFragment ?? null;
  }, [activeTextChunkIndex, inlineAudioSelection, interactiveAudioNameMap, resolvedActiveTextChunk]);
  const activeChunkRange = resolvedActiveTextChunk
    ? formatSentenceRange(
        resolvedActiveTextChunk.startSentence ?? null,
        resolvedActiveTextChunk.endSentence ?? null,
      )
    : null;
  const selectionTitle =
    selectedItem?.name ??
    activeChunkLabel ??
    (resolvedActiveTextChunk ? 'Interactive chunk' : 'No media selected');
  const selectionLabel = selectedItem
    ? `Selected media: ${selectedItem.name}`
    : resolvedActiveTextChunk
    ? `Interactive chunk: ${activeChunkLabel ?? 'Chunk'}`
    : 'No media selected';
  const hasTextItems = media.text.length > 0;
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
  const derivedNavigation = useMemo(() => {
    if (navigableItems.length > 0) {
      return {
        mode: 'media' as const,
        count: navigableItems.length,
        index: Math.max(0, activeNavigableIndex),
      };
    }
    if (selectedMediaType === 'text' && chunks.length > 0) {
      const index = activeTextChunkIndex >= 0 ? activeTextChunkIndex : 0;
      return {
        mode: 'chunks' as const,
        count: chunks.length,
        index: Math.max(0, Math.min(index, Math.max(chunks.length - 1, 0))),
      };
    }
    return { mode: 'none' as const, count: 0, index: -1 };
  }, [activeNavigableIndex, activeTextChunkIndex, chunks.length, navigableItems.length, selectedMediaType]);
  const isFirstDisabled =
    derivedNavigation.count === 0 || derivedNavigation.index <= 0;
  const isPreviousDisabled =
    derivedNavigation.count === 0 || derivedNavigation.index <= 0;
  const isNextDisabled =
    derivedNavigation.count === 0 || derivedNavigation.index >= derivedNavigation.count - 1;
  const isLastDisabled =
    derivedNavigation.count === 0 || derivedNavigation.index >= derivedNavigation.count - 1;
  const playbackControlsAvailable =
    selectedMediaType === 'audio'
      ? hasAudioControls
      : selectedMediaType === 'video'
      ? hasVideoControls
      : selectedMediaType === 'text'
      ? hasInlineAudioControls
      : false;
  const isPauseDisabled = !playbackControlsAvailable;
  const isPlayDisabled = !playbackControlsAvailable;
  const isFullscreenDisabled = !isTextTabActive || !canRenderInteractiveViewer;

  const handleAdvanceMedia = useCallback(
    (category: MediaCategory) => {
      updateSelection(category, 'next');
    },
    [updateSelection],
  );

  const handleAudioControlsRegistration = useCallback((controls: PlaybackControls | null) => {
    audioControlsRef.current = controls;
    setHasAudioControls(Boolean(controls));
  }, []);

  const handleVideoControlsRegistration = useCallback((controls: PlaybackControls | null) => {
    videoControlsRef.current = controls;
    setHasVideoControls(Boolean(controls));
  }, []);

  const syncInteractiveSelection = useCallback(
    (audioUrl: string | null) => {
      if (!audioUrl) {
        return;
      }
      setSelectedItemIds((current) =>
        current.audio === audioUrl ? current : { ...current, audio: audioUrl },
      );
      const chunkIndex = audioChunkIndexMap.get(audioUrl);
      if (typeof chunkIndex === 'number' && chunkIndex >= 0 && chunkIndex < chunks.length) {
        const targetChunk = chunks[chunkIndex];
        const nextTextFile = targetChunk.files.find((file) => file.type === 'text' && file.url);
        if (nextTextFile?.url) {
          setSelectedItemIds((current) =>
            current.text === nextTextFile.url ? current : { ...current, text: nextTextFile.url },
          );
        }
      }
    },
    [
      audioChunkIndexMap,
      chunks,
      setSelectedItemIds,
    ],
  );

  const handleInlineAudioSelect = useCallback(
    (audioUrl: string) => {
      if (!audioUrl) {
        return;
      }
      setInlineAudioSelection((current) => (current === audioUrl ? current : audioUrl));
      syncInteractiveSelection(audioUrl);
    },
    [syncInteractiveSelection],
  );

  const handleInlineAudioControlsRegistration = useCallback((controls: PlaybackControls | null) => {
    inlineAudioControlsRef.current = controls;
    setHasInlineAudioControls(Boolean(controls));
  }, []);

  const handleNavigate = useCallback(
    (intent: NavigationIntent) => {
      const textItems = selectedMediaType === 'text' ? navigableItems : [];
      if (
        selectedMediaType === 'text' &&
        textItems.length === 0 &&
        chunks.length > 0
      ) {
        const currentIndex = activeTextChunkIndex >= 0 ? activeTextChunkIndex : 0;
        const lastIndex = chunks.length - 1;
        let nextIndex = currentIndex;
        switch (intent) {
          case 'first':
            nextIndex = 0;
            break;
          case 'last':
            nextIndex = lastIndex;
            break;
          case 'previous':
            nextIndex = currentIndex <= 0 ? 0 : currentIndex - 1;
            break;
          case 'next':
            nextIndex = currentIndex < 0 ? 0 : Math.min(currentIndex + 1, lastIndex);
            break;
          default:
            nextIndex = currentIndex;
        }

        if (nextIndex === currentIndex) {
          return;
        }

        const targetChunk = chunks[nextIndex];
        if (!targetChunk) {
          return;
        }
        const nextAudio = targetChunk.files.find((file) => file.type === 'audio' && file.url);
        if (nextAudio?.url) {
          setInlineAudioSelection((current) => (current === nextAudio.url ? current : nextAudio.url));
          syncInteractiveSelection(nextAudio.url);
        } else {
          const nextText = targetChunk.files.find((file) => file.type === 'text' && file.url);
          if (nextText?.url) {
            setSelectedItemIds((current) =>
              current.text === nextText.url ? current : { ...current, text: nextText.url },
            );
          }
        }
        setPendingTextScrollRatio(0);
        return;
      }

      updateSelection(selectedMediaType, intent);
    },
    [
      activeTextChunkIndex,
      chunks,
      navigableItems,
      selectedMediaType,
      setInlineAudioSelection,
      setPendingTextScrollRatio,
      setSelectedItemIds,
      syncInteractiveSelection,
      updateSelection,
    ],
  );

  const handlePauseActiveMedia = useCallback(() => {
    if (selectedMediaType === 'audio') {
      audioControlsRef.current?.pause();
    } else if (selectedMediaType === 'video') {
      videoControlsRef.current?.pause();
    } else if (selectedMediaType === 'text') {
      inlineAudioControlsRef.current?.pause();
    }
  }, [selectedMediaType]);

  const handlePlayActiveMedia = useCallback(() => {
    if (selectedMediaType === 'audio') {
      audioControlsRef.current?.play();
    } else if (selectedMediaType === 'video') {
      videoControlsRef.current?.play();
    } else if (selectedMediaType === 'text') {
      inlineAudioControlsRef.current?.play();
    }
  }, [selectedMediaType]);

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

  const handleInlineAudioProgress = useCallback(
    (audioUrl: string, position: number) => {
      if (!audioUrl) {
        return;
      }
      const current = getMediaItem('audio', audioUrl);
      const baseId = current ? deriveBaseId(current) : null;
      rememberPosition({ mediaId: audioUrl, mediaType: 'audio', baseId, position });
    },
    [deriveBaseId, getMediaItem, rememberPosition],
  );

  const getInlineAudioPosition = useCallback(
    (audioUrl: string) => getPosition(audioUrl),
    [getPosition],
  );

  const advanceInteractiveChunk = useCallback(() => {
    if (chunks.length === 0) {
      return false;
    }
    let currentIndex = activeTextChunkIndex;
    if (currentIndex < 0 && inlineAudioSelection) {
      const mappedIndex = audioChunkIndexMap.get(inlineAudioSelection);
      if (typeof mappedIndex === 'number' && mappedIndex >= 0) {
        currentIndex = mappedIndex;
      }
    }
    const nextIndex = currentIndex >= 0 ? currentIndex + 1 : 0;
    if (nextIndex >= chunks.length) {
      return false;
    }
    const nextChunk = chunks[nextIndex];
    const nextAudio = nextChunk.files.find((file) => file.type === 'audio' && file.url);
    if (nextAudio?.url) {
      setInlineAudioSelection(nextAudio.url);
      syncInteractiveSelection(nextAudio.url);
    } else {
      const nextText = nextChunk.files.find((file) => file.type === 'text' && file.url);
      if (nextText?.url) {
        setSelectedItemIds((current) =>
          current.text === nextText.url ? current : { ...current, text: nextText.url },
        );
      }
    }
    setPendingTextScrollRatio(0);
    return true;
  }, [
    activeTextChunkIndex,
    audioChunkIndexMap,
    chunks,
    inlineAudioSelection,
    setPendingTextScrollRatio,
    setSelectedItemIds,
    syncInteractiveSelection,
  ]);

  const handleInlineAudioEnded = useCallback(() => {
    const advanced = advanceInteractiveChunk();
    if (!advanced) {
      updateSelection('text', 'next');
    }
  }, [advanceInteractiveChunk, updateSelection]);

  useEffect(() => {
    if (inlineAudioOptions.length === 0) {
      if (inlineAudioSelection) {
        const currentAudio = getMediaItem('audio', inlineAudioSelection);
        if (!currentAudio) {
          setInlineAudioSelection(null);
        }
      }
      return;
    }

    if (inlineAudioSelection) {
      const hasExactMatch = inlineAudioOptions.some((option) => option.url === inlineAudioSelection);
      if (hasExactMatch) {
        return;
      }

      const currentAudio = getMediaItem('audio', inlineAudioSelection);
      const currentBaseId =
        currentAudio ? deriveBaseId(currentAudio) : inlineAudioBaseRef.current ?? deriveBaseIdFromReference(inlineAudioSelection);

      if (currentBaseId) {
        const remapped = inlineAudioOptions.find((option) => {
          const optionAudio = getMediaItem('audio', option.url);
          if (optionAudio) {
            return deriveBaseId(optionAudio) === currentBaseId;
          }
          return deriveBaseIdFromReference(option.url) === currentBaseId;
        });

        if (remapped?.url) {
          setInlineAudioSelection((current) => (current === remapped.url ? current : remapped.url));
          if (remapped.url !== inlineAudioSelection) {
            syncInteractiveSelection(remapped.url);
          }
          return;
        }
      }
    }

    const desiredBaseId = inlineAudioBaseRef.current;
    if (!inlineAudioSelection) {
      const fallbackUrl = inlineAudioOptions[0]?.url ?? null;
      if (fallbackUrl) {
        setInlineAudioSelection(fallbackUrl);
        syncInteractiveSelection(fallbackUrl);
      }
      return;
    }

    if (!desiredBaseId) {
      return;
    }

    const preferredOption = inlineAudioOptions.find((option) => {
      const optionAudio = getMediaItem('audio', option.url);
      if (optionAudio) {
        return deriveBaseId(optionAudio) === desiredBaseId;
      }
      return deriveBaseIdFromReference(option.url) === desiredBaseId;
    });

    if (!preferredOption?.url || preferredOption.url === inlineAudioSelection) {
      return;
    }

    setInlineAudioSelection(preferredOption.url);
    syncInteractiveSelection(preferredOption.url);
  }, [
    deriveBaseId,
    getMediaItem,
    inlineAudioOptions,
    inlineAudioSelection,
    syncInteractiveSelection,
  ]);

  useEffect(() => {
    if (!inlineAudioSelection) {
      inlineAudioBaseRef.current = null;
      return;
    }
    const currentAudio = getMediaItem('audio', inlineAudioSelection);
    const baseId = currentAudio ? deriveBaseId(currentAudio) : deriveBaseIdFromReference(inlineAudioSelection);
    inlineAudioBaseRef.current = baseId;
  }, [deriveBaseId, getMediaItem, inlineAudioSelection]);

  useEffect(() => {
    if (!inlineAudioSelection) {
      return;
    }
    const currentAudio = getMediaItem('audio', inlineAudioSelection);
    if (currentAudio) {
      return;
    }
    const baseId = inlineAudioBaseRef.current ?? deriveBaseIdFromReference(inlineAudioSelection);
    if (!baseId) {
      return;
    }

    const replacement = media.audio.find((item) => {
      if (!item.url) {
        return false;
      }
      const optionAudio = getMediaItem('audio', item.url);
      if (optionAudio) {
        return deriveBaseId(optionAudio) === baseId;
      }
      return deriveBaseIdFromReference(item.url) === baseId;
    });

    if (replacement?.url) {
      setInlineAudioSelection(replacement.url);
      syncInteractiveSelection(replacement.url);
    }
  }, [
    deriveBaseId,
    deriveBaseIdFromReference,
    getMediaItem,
    inlineAudioSelection,
    media.audio,
    syncInteractiveSelection,
  ]);

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

    if (pendingTextScrollRatio !== null) {
      const maxScroll = Math.max(element.scrollHeight - element.clientHeight, 0);
      const target = Math.min(Math.max(pendingTextScrollRatio, 0), 1) * maxScroll;
      try {
        element.scrollTop = target;
        if (typeof element.scrollTo === 'function') {
          element.scrollTo({ top: target });
        }
      } catch (error) {
        // Ignore scroll assignment failures in non-browser environments.
      }

      const current = getMediaItem('text', mediaId);
      const baseId = current ? deriveBaseId(current) : null;
      rememberPosition({ mediaId, mediaType: 'text', baseId, position: target });
      setPendingTextScrollRatio(null);
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
  }, [
    selectedMediaType,
    selectedItemIds.text,
    textPlaybackPosition,
    textPreview?.url,
    pendingTextScrollRatio,
    getMediaItem,
    deriveBaseId,
    rememberPosition,
  ]);

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

    const cached = textContentCache.current.get(url);
    if (cached) {
      setTextPreview({ url, content: cached.plain, raw: cached.raw });
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
        textContentCache.current.set(url, { raw, plain: normalised });
        setTextPreview({ url, content: normalised, raw });
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

  const handleImmersiveToggle = useCallback(() => {
    if (!isVideoTabActive || media.video.length === 0) {
      return;
    }
    setIsImmersiveMode((current) => !current);
  }, [isVideoTabActive, media.video.length]);

  const handleExitImmersiveMode = useCallback(() => {
    setIsImmersiveMode(false);
  }, []);

  useEffect(() => {
    if (!isVideoTabActive) {
      setIsImmersiveMode(false);
    }
  }, [isVideoTabActive]);

  useEffect(() => {
    setIsImmersiveMode(false);
    setIsInteractiveFullscreen(false);
  }, [normalisedJobId]);

  const bookTitle = extractMetadataText(bookMetadata, ['book_title', 'title', 'book_name', 'name']);
  const bookAuthor = extractMetadataText(bookMetadata, ['book_author', 'author', 'writer', 'creator']);
  const sectionLabel = bookTitle ? `Player for ${bookTitle}` : 'Player';
  const loadingMessage = bookTitle ? `Loading generated media for ${bookTitle}…` : 'Loading generated media…';
  const emptyMediaMessage = bookTitle ? `No generated media yet for ${bookTitle}.` : 'No generated media yet.';

  const hasAnyMedia = media.text.length + media.audio.length + media.video.length > 0;
  const headingLabel = bookTitle ?? 'Player';
  const jobLabelParts: string[] = [];
  if (bookAuthor) {
    jobLabelParts.push(`By ${bookAuthor}`);
  }
  if (hasJobId) {
    jobLabelParts.push(`Job ${jobId}`);
  }
  const jobLabel = jobLabelParts.join(' • ');
  const coverAltText =
    bookTitle && bookAuthor
      ? `Cover of ${bookTitle} by ${bookAuthor}`
      : bookTitle
      ? `Cover of ${bookTitle}`
      : bookAuthor
      ? `Book cover for ${bookAuthor}`
      : 'Book cover preview';
  const immersiveToggleLabel = isImmersiveMode ? 'Exit immersive mode' : 'Enter immersive mode';
  const interactiveFullscreenLabel = isInteractiveFullscreen ? 'Exit fullscreen' : 'Enter fullscreen';

  const navigationGroup = (
    <NavigationControls
      context="panel"
      onNavigate={handleNavigate}
      onToggleFullscreen={handleInteractiveFullscreenToggle}
      onPlay={handlePlayActiveMedia}
      onPause={handlePauseActiveMedia}
      disableFirst={isFirstDisabled}
      disablePrevious={isPreviousDisabled}
      disableNext={isNextDisabled}
      disableLast={isLastDisabled}
      disablePlay={isPlayDisabled}
      disablePause={isPauseDisabled}
      disableFullscreen={isFullscreenDisabled}
      isFullscreen={isInteractiveFullscreen}
      fullscreenLabel={interactiveFullscreenLabel}
      inlineAudioOptions={inlineAudioOptions}
      inlineAudioSelection={inlineAudioSelection}
      onSelectInlineAudio={handleInlineAudioSelect}
      showInlineAudio={selectedMediaType === 'text'}
    />
  );
  const fullscreenNavigationGroup = isInteractiveFullscreen ? (
    <NavigationControls
      context="fullscreen"
      onNavigate={handleNavigate}
      onToggleFullscreen={handleInteractiveFullscreenToggle}
      onPlay={handlePlayActiveMedia}
      onPause={handlePauseActiveMedia}
      disableFirst={isFirstDisabled}
      disablePrevious={isPreviousDisabled}
      disableNext={isNextDisabled}
      disableLast={isLastDisabled}
      disablePlay={isPlayDisabled}
      disablePause={isPauseDisabled}
      disableFullscreen={isFullscreenDisabled}
      isFullscreen={isInteractiveFullscreen}
      fullscreenLabel={interactiveFullscreenLabel}
      inlineAudioOptions={inlineAudioOptions}
      inlineAudioSelection={inlineAudioSelection}
      onSelectInlineAudio={handleInlineAudioSelect}
      showInlineAudio={selectedMediaType === 'text'}
    />
  ) : null;

  const fullscreenHeader = isInteractiveFullscreen ? (
    <div className="player-panel__fullscreen-header">
      {shouldShowCoverImage ? (
        <div className="player-panel__fullscreen-cover" aria-hidden={false}>
          <img
            src={displayCoverUrl}
            alt={coverAltText}
            data-testid="player-panel-fullscreen-cover"
            onError={coverErrorHandler}
          />
        </div>
      ) : null}
      <div className="player-panel__fullscreen-meta">
        <h3>{headingLabel}</h3>
        {jobLabel ? <span className="player-panel__fullscreen-job">{jobLabel}</span> : null}
      </div>
    </div>
  ) : null;

  if (error) {
    return (
      <section className="player-panel" aria-label={sectionLabel}>
        <p role="alert">Unable to load generated media: {error.message}</p>
      </section>
    );
  }

  if (isLoading && media.text.length === 0 && media.audio.length === 0 && media.video.length === 0) {
    return (
      <section className="player-panel" aria-label={sectionLabel}>
        <p role="status">{loadingMessage}</p>
      </section>
    );
  }

  return (
    <section className={panelClassName} aria-label={sectionLabel}>
      {!hasJobId ? (
        <div className="player-panel__empty" role="status">
          <p>No job selected.</p>
        </div>
      ) : (
        <>
          <div className="player-panel__search">
            <MediaSearchPanel currentJobId={jobId} onResultAction={handleSearchSelection} />
          </div>
          <Tabs className="player-panel__tabs-container" value={selectedMediaType} onValueChange={handleTabChange}>
            <header className="player-panel__header">
              <div className="player-panel__heading">
                {shouldShowCoverImage ? (
                  <div className="player-panel__cover" aria-hidden={false}>
                    <img
                      src={displayCoverUrl}
                      alt={coverAltText}
                      data-testid="player-cover-image"
                      onError={coverErrorHandler}
                    />
                  </div>
                ) : null}
                <div className="player-panel__heading-text">
                  <h2>{headingLabel}</h2>
                  <span className="player-panel__job">{jobLabel}</span>
                </div>
              </div>
          <div className="player-panel__tabs-row">
            {navigationGroup}
            {media.video.length > 0 ? (
              <button
                type="button"
                className="player-panel__immersive-toggle"
                onClick={handleImmersiveToggle}
                disabled={!isVideoTabActive}
                aria-pressed={isImmersiveMode}
                aria-label={immersiveToggleLabel}
                data-testid="player-panel-immersive-toggle"
              >
                {immersiveToggleLabel}
              </button>
            ) : null}
            <TabsList className="player-panel__tabs" aria-label="Media categories">
              {visibleTabs.map((tab) => {
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
                        files={audioFiles}
                        activeId={selectedItemIds.audio}
                        onSelectFile={(fileId) => handleSelectMedia('audio', fileId)}
                        autoPlay
                        onPlaybackEnded={() => handleAdvanceMedia('audio')}
                        playbackPosition={audioPlaybackPosition}
                        onPlaybackPositionChange={handleAudioProgress}
                        onRegisterControls={handleAudioControlsRegistration}
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
                        isTheaterMode={isImmersiveMode}
                        onExitTheaterMode={handleExitImmersiveMode}
                        onRegisterControls={handleVideoControlsRegistration}
                      />
                      ) : null}
                      {tab.key === 'text' ? (
                        <div className="player-panel__document">
                          {hasTextItems && !selectedItem ? (
                            <div className="player-panel__empty-viewer" role="status">
                              Select a file to preview.
                            </div>
                          ) : textLoading && selectedItem ? (
                            <div className="player-panel__document-status" role="status">
                              Loading document…
                            </div>
                          ) : textError ? (
                            <div className="player-panel__document-error" role="alert">
                              {textError}
                            </div>
                          ) : canRenderInteractiveViewer ? (
                          <InteractiveTextViewer
                            ref={textScrollRef}
                            content={interactiveViewerContent}
                            rawContent={interactiveViewerRaw}
                            chunk={resolvedActiveTextChunk}
                            activeAudioUrl={inlineAudioSelection}
                            noAudioAvailable={inlineAudioUnavailable}
                            onScroll={handleTextScroll}
                            onAudioProgress={handleInlineAudioProgress}
                            getStoredAudioPosition={getInlineAudioPosition}
                          onRegisterInlineAudioControls={handleInlineAudioControlsRegistration}
                          onRequestAdvanceChunk={handleInlineAudioEnded}
                          isFullscreen={isInteractiveFullscreen}
                          onRequestExitFullscreen={handleExitInteractiveFullscreen}
                            fullscreenControls={
                              isInteractiveFullscreen ? (
                                <>
                                  {fullscreenHeader}
                                  {fullscreenNavigationGroup}
                                </>
                              ) : null
                            }
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
                      <div
                        className="player-panel__selection-name"
                        title={selectionTitle}
                      >
                        {selectionLabel}
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
                        <div className="player-panel__selection-meta-item">
                          <dt>Sentences</dt>
                          <dd>{formatSentenceRange(resolvedActiveTextChunk?.startSentence ?? null, resolvedActiveTextChunk?.endSentence ?? null)}</dd>
                        </div>
                      </dl>
                    </div>
                  </div>
                ) : null
              )}
            </TabsContent>
          );
        })}
        </Tabs>
        </>
      )}
    </section>
  );
}
