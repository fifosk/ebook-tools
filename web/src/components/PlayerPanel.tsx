import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { UIEvent } from 'react';
import AudioPlayer from './AudioPlayer';
import VideoPlayer from './VideoPlayer';
import type { LiveMediaChunk, LiveMediaItem, LiveMediaState } from '../hooks/useLiveMedia';
import { useMediaMemory } from '../hooks/useMediaMemory';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/Tabs';
import { extractTextFromHtml, formatFileSize, formatTimestamp } from '../utils/mediaFormatters';
import MediaSearchPanel from './MediaSearchPanel';
import type { MediaSearchResult } from '../api/dtos';
import { appendAccessToken, buildStorageUrl, resolveJobCoverUrl, resolveLibraryMediaUrl } from '../api/client';
import InteractiveTextViewer from './InteractiveTextViewer';

type MediaCategory = keyof LiveMediaState;
type NavigationIntent = 'first' | 'previous' | 'next' | 'last';

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

const DEFAULT_COVER_URL = '/assets/default-cover.png';

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
  (['text', 'audio', 'video'] as MediaCategory[]).forEach((category) => {
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
}: PlayerPanelProps) {
  const [selectedMediaType, setSelectedMediaType] = useState<MediaCategory>(() => selectInitialTab(media));
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
  const [pendingSelection, setPendingSelection] = useState<MediaSelectionRequest | null>(null);
  const [pendingTextScrollRatio, setPendingTextScrollRatio] = useState<number | null>(null);
  const [isVideoPlaying, setIsVideoPlaying] = useState(false);
  const [coverSourceIndex, setCoverSourceIndex] = useState(0);
  const [isImmersiveMode, setIsImmersiveMode] = useState(false);
  const hasJobId = Boolean(jobId);
  const normalisedJobId = jobId ?? '';
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
        return buildStorageUrl(stripped);
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
  const coverErrorHandler = shouldHandleCoverError ? handleCoverError : undefined;

  const handleSearchSelection = useCallback(
    (result: MediaSearchResult, category: MediaCategory) => {
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
    [jobId],
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
    if (!pendingSelection) {
      return;
    }

    const { baseId, preferredType, offsetRatio = null, approximateTime = null } = pendingSelection;

    const candidates: MediaCategory[] = [];
    if (preferredType) {
      candidates.push(preferredType);
    }
    (['text', 'audio', 'video'] as MediaCategory[]).forEach((category) => {
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

    setPendingSelection(null);
  }, [
    pendingSelection,
    findMatchingMediaId,
    media,
    getMediaItem,
    deriveBaseId,
    rememberPosition,
  ]);

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
  const chunkAudioItems = useMemo(() => {
    if (!selectedChunk) {
      return [];
    }
    const seen = new Set<string>();
    const items: LiveMediaItem[] = [];
    selectedChunk.files.forEach((file) => {
      if (file.type !== 'audio' || !file.url) {
        return;
      }
      if (seen.has(file.url)) {
        return;
      }
      seen.add(file.url);
      items.push(file);
    });
    return items;
  }, [selectedChunk]);
  const interactiveAudioItems = useMemo(() => {
    const seen = new Set<string>();
    const register = (item: LiveMediaItem | null | undefined) => {
      if (!item || !item.url || seen.has(item.url)) {
        return;
      }
      seen.add(item.url);
      result.push(item);
    };
    const result: LiveMediaItem[] = [];
    chunkAudioItems.forEach(register);
    const baseId = selectedItem ? deriveBaseId(selectedItem) : null;
    if (baseId) {
      media.audio.forEach((item) => {
        if (deriveBaseId(item) === baseId) {
          register(item);
        }
      });
    }
    const selectedAudio = getMediaItem('audio', selectedItemIds.audio);
    register(selectedAudio);
    if (result.length === 0) {
      register(media.audio[0]);
    }
    return result;
  }, [
    chunkAudioItems,
    deriveBaseId,
    getMediaItem,
    media.audio,
    selectedItem,
    selectedItemIds.audio,
  ]);
  const isImmersiveLayout = isVideoTabActive && isImmersiveMode;
  const panelClassName = isImmersiveLayout ? 'player-panel player-panel--immersive' : 'player-panel';
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
  }, [normalisedJobId]);

  const bookTitle = extractMetadataText(bookMetadata, ['book_title', 'title', 'book_name', 'name']);
  const bookAuthor = extractMetadataText(bookMetadata, ['book_author', 'author', 'writer', 'creator']);
  const sectionLabel = bookTitle ? `Player for ${bookTitle}` : 'Player';
  const loadingMessage = bookTitle ? `Loading generated media for ${bookTitle}…` : 'Loading generated media…';
  const emptyMediaMessage = bookTitle ? `No generated media yet for ${bookTitle}.` : 'No generated media yet.';

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
            <div className="player-panel__cover" aria-hidden={false}>
              <img
                src={displayCoverUrl}
                alt={coverAltText}
                data-testid="player-cover-image"
                onError={coverErrorHandler}
              />
            </div>
            <div className="player-panel__heading-text">
              <h2>{headingLabel}</h2>
              <span className="player-panel__job">{jobLabel}</span>
            </div>
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
            <button
              type="button"
              className="player-panel__immersive-toggle"
              onClick={handleImmersiveToggle}
              disabled={!isVideoTabActive || media.video.length === 0}
              aria-pressed={isImmersiveMode}
              aria-label={immersiveToggleLabel}
              data-testid="player-panel-immersive-toggle"
            >
              {immersiveToggleLabel}
            </button>
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
          const tabItems = media[tab.key];
          return (
            <TabsContent key={tab.key} value={tab.key} className="player-panel__panel">
              {!hasAnyMedia && !isLoading ? (
                <p role="status">{emptyMediaMessage}</p>
              ) : tabItems.length === 0 ? (
                <p role="status">{tab.emptyMessage}</p>
              ) : (
                isActive ? (
                  <div className="player-panel__stage">
                    {!mediaComplete ? (
                      <div className="player-panel__notice" role="status">
                        Media generation is still finishing. Newly generated files will appear automatically.
                      </div>
                    ) : null}
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
                        <div className="player-panel__selection-meta-item">
                          <dt>Chunk</dt>
                          <dd>{selectedChunk?.rangeFragment ?? '—'}</dd>
                        </div>
                        <div className="player-panel__selection-meta-item">
                          <dt>Sentences</dt>
                          <dd>{formatSentenceRange(selectedChunk?.startSentence ?? null, selectedChunk?.endSentence ?? null)}</dd>
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
                          isTheaterMode={isImmersiveMode}
                          onExitTheaterMode={handleExitImmersiveMode}
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
                                <InteractiveTextViewer
                                  ref={textScrollRef}
                                  content={textPreview.content}
                                  rawContent={textPreview.raw}
                                  chunk={selectedChunk}
                                  audioItems={interactiveAudioItems}
                                  onScroll={handleTextScroll}
                                  onAudioProgress={handleInlineAudioProgress}
                                  getStoredAudioPosition={getInlineAudioPosition}
                                />
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
