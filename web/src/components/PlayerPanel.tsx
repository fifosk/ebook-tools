import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import type { UIEvent } from 'react';
import type { LiveMediaChunk, LiveMediaItem, LiveMediaState } from '../hooks/useLiveMedia';
import { useMediaMemory } from '../hooks/useMediaMemory';
import { useWakeLock } from '../hooks/useWakeLock';
import { useMyLinguist } from '../context/MyLinguistProvider';
import {
  DEFAULT_MY_LINGUIST_FONT_SCALE_PERCENT,
  FONT_SCALE_MAX,
  FONT_SCALE_MIN,
  FONT_SCALE_STEP,
  MEDIA_CATEGORIES,
  MY_LINGUIST_FONT_SCALE_MAX,
  MY_LINGUIST_FONT_SCALE_MIN,
  MY_LINGUIST_FONT_SCALE_STEP,
  TRANSLATION_SPEED_MAX,
  TRANSLATION_SPEED_MIN,
  TRANSLATION_SPEED_STEP,
  type MediaCategory,
  type NavigationIntent,
} from './player-panel/constants';
import MediaSearchPanel from './MediaSearchPanel';
import type {
  LibraryItem,
  MediaSearchResult,
} from '../api/dtos';
import {
  appendAccessToken,
  createExport,
  fetchPipelineStatus,
  withBase,
} from '../api/client';
import { PlayerPanelInteractiveDocument } from './player-panel/PlayerPanelInteractiveDocument';
import { resolve as resolveStoragePath } from '../utils/storageResolver';
import {
  buildInteractiveAudioCatalog,
  isAudioFileType,
} from './player-panel/utils';
import { enableDebugOverlay } from '../player/AudioSyncController';
import type { LibraryOpenInput, LibraryOpenRequest, MediaSelectionRequest, PlayerFeatureFlags, PlayerMode } from '../types/player';
import { NavigationControls, type NavigationControlsProps } from './player-panel/NavigationControls';
import { PlayerPanelShell } from './player-panel/PlayerPanelShell';
import {
  deriveBaseIdFromReference,
  extractMetadataFirstString,
  extractMetadataText,
  findChunkIndexForBaseId,
  normaliseBookSentenceCount,
  resolveBaseIdFromResult,
} from './player-panel/helpers';
import { useCoverArt } from './player-panel/useCoverArt';
import { useChunkMetadata } from './player-panel/useChunkMetadata';
import { useInlineAudioOptions } from './player-panel/useInlineAudioOptions';
import { useInlineAudioSelection } from './player-panel/useInlineAudioSelection';
import { usePendingSelection } from './player-panel/usePendingSelection';
import { useSentenceNavigation } from './player-panel/useSentenceNavigation';
import { useReadingBedControls } from './player-panel/useReadingBedControls';
import { useInteractiveTextSettings } from './player-panel/useInteractiveTextSettings';
import { useSubtitleInfo } from './player-panel/useSubtitleInfo';
import { useTextPreview } from './player-panel/useTextPreview';
import { ShortcutHelpOverlay } from './player-panel/ShortcutHelpOverlay';
import { usePlayerShortcuts } from './player-panel/usePlayerShortcuts';
type SearchCategory = Exclude<MediaCategory, 'audio'> | 'library';
type PlaybackControls = {
  pause: () => void;
  play: () => void;
};

type ReadingBedOverride = {
  id: string;
  label: string;
  url: string;
};

const deriveSentenceCountFromChunks = (chunks: LiveMediaChunk[]): number | null => {
  let maxSentence = 0;
  let hasValue = false;
  chunks.forEach((chunk) => {
    if (!chunk) {
      return;
    }
    const endSentence =
      typeof chunk.endSentence === 'number' && Number.isFinite(chunk.endSentence)
        ? Math.trunc(chunk.endSentence)
        : null;
    if (endSentence !== null) {
      maxSentence = Math.max(maxSentence, endSentence);
      hasValue = true;
      return;
    }
    const startSentence =
      typeof chunk.startSentence === 'number' && Number.isFinite(chunk.startSentence)
        ? Math.trunc(chunk.startSentence)
        : null;
    const sentenceCount =
      typeof chunk.sentenceCount === 'number' && Number.isFinite(chunk.sentenceCount)
        ? Math.trunc(chunk.sentenceCount)
        : Array.isArray(chunk.sentences) && chunk.sentences.length > 0
          ? chunk.sentences.length
          : null;
    if (startSentence !== null && sentenceCount !== null) {
      maxSentence = Math.max(maxSentence, startSentence + Math.max(sentenceCount - 1, 0));
      hasValue = true;
    }
  });
  return hasValue ? maxSentence : null;
};

interface PlayerPanelProps {
  jobId: string;
  jobType?: string | null;
  itemType?: 'book' | 'video' | 'narrated_subtitle' | null;
  libraryItem?: LibraryItem | null;
  media: LiveMediaState;
  chunks: LiveMediaChunk[];
  mediaComplete: boolean;
  isLoading: boolean;
  error: Error | null;
  bookMetadata?: Record<string, unknown> | null;
  onVideoPlaybackStateChange?: (isPlaying: boolean) => void;
  onPlaybackStateChange?: (isPlaying: boolean) => void;
  onFullscreenChange?: (isFullscreen: boolean) => void;
  origin?: 'job' | 'library';
  onOpenLibraryItem?: (item: LibraryOpenInput) => void;
  selectionRequest?: MediaSelectionRequest | null;
  showBackToLibrary?: boolean;
  onBackToLibrary?: () => void;
  playerMode?: PlayerMode;
  playerFeatures?: PlayerFeatureFlags;
  readingBedOverride?: ReadingBedOverride | null;
}


export default function PlayerPanel({
  jobId,
  jobType = null,
  itemType = null,
  libraryItem = null,
  media,
  chunks,
  mediaComplete,
  isLoading,
  error,
  bookMetadata = null,
  onVideoPlaybackStateChange,
  onPlaybackStateChange,
  onFullscreenChange,
  origin = 'job',
  onOpenLibraryItem,
  selectionRequest = null,
  showBackToLibrary = false,
  onBackToLibrary,
  playerMode = 'online',
  playerFeatures,
  readingBedOverride = null,
}: PlayerPanelProps) {
  const features = playerFeatures ?? {};
  const linguistEnabled = features.linguist !== false;
  const painterEnabled = features.painter !== false;
  const searchEnabled = features.search !== false;
  const { baseFontScalePercent, setBaseFontScalePercent, adjustBaseFontScalePercent, toggle: toggleMyLinguist } =
    useMyLinguist();
  const interactiveViewerAvailable = chunks.length > 0;
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
  const [pendingChunkSelection, setPendingChunkSelection] =
    useState<{ index: number; token: number } | null>(null);
  const [pendingTextScrollRatio, setPendingTextScrollRatio] = useState<number | null>(null);
  const [showOriginalAudio, setShowOriginalAudio] = useState<boolean>(() => {
    if (typeof window === 'undefined') {
      return true;
    }
    const stored = window.localStorage.getItem('player.showOriginalAudio');
    if (stored === null) {
      return true;
    }
    return stored === 'true';
  });
  const [showTranslationAudio, setShowTranslationAudio] = useState<boolean>(() => {
    if (typeof window === 'undefined') {
      return true;
    }
    const stored = window.localStorage.getItem('player.showTranslationAudio');
    if (stored === null) {
      return true;
    }
    return stored === 'true';
  });
  const [inlineAudioSelection, setInlineAudioSelection] = useState<string | null>(null);
  const [isInlineAudioPlaying, setIsInlineAudioPlaying] = useState(false);
  const resolveStoredInteractiveFullscreenPreference = () => {
    if (typeof window === 'undefined') {
      return false;
    }
    return window.localStorage.getItem('player.textFullscreenPreferred') === 'true';
  };
  const [isInteractiveFullscreen, setIsInteractiveFullscreen] = useState<boolean>(() =>
    resolveStoredInteractiveFullscreenPreference(),
  );
  const interactiveFullscreenPreferenceRef = useRef<boolean>(isInteractiveFullscreen);
  const updateInteractiveFullscreenPreference = useCallback((next: boolean) => {
    interactiveFullscreenPreferenceRef.current = next;
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('player.textFullscreenPreferred', next ? 'true' : 'false');
    }
  }, []);
  const hasJobId = Boolean(jobId);
  const normalisedJobId = jobId ?? '';
  const mediaMemory = useMediaMemory({ jobId });
  const { state: memoryState, rememberSelection, rememberPosition, getPosition, findMatchingMediaId, deriveBaseId } = mediaMemory;
  const textScrollRef = useRef<HTMLDivElement | null>(null);
  const inlineAudioControlsRef = useRef<PlaybackControls | null>(null);
  const inlineAudioPlayingRef = useRef(false);
  const hasSkippedInitialRememberRef = useRef(false);
  const updateInlineAudioPlaying = useCallback((next: boolean) => {
    inlineAudioPlayingRef.current = next;
    setIsInlineAudioPlaying(next);
  }, []);
  const pendingAutoPlayRef = useRef(false);
  const [autoPlayToken, setAutoPlayToken] = useState(0);
  const requestAutoPlay = useCallback(() => {
    pendingAutoPlayRef.current = true;
    setAutoPlayToken((value) => value + 1);
  }, []);
  const [hasInlineAudioControls, setHasInlineAudioControls] = useState(false);
  const {
    interactiveTextVisibility,
    toggleInteractiveTextLayer: handleToggleInteractiveTextLayer,
    translationSpeed,
    setTranslationSpeed: handleTranslationSpeedChange,
    adjustTranslationSpeed,
    fontScalePercent,
    setFontScalePercent: handleFontScaleChange,
    adjustFontScale,
    interactiveTextTheme,
    setInteractiveTextTheme,
    interactiveBackgroundOpacityPercent,
    setInteractiveBackgroundOpacityPercent,
    interactiveSentenceCardOpacityPercent,
    setInteractiveSentenceCardOpacityPercent,
    resetInteractiveTextSettings,
  } = useInteractiveTextSettings();
  const {
    readingBedEnabled,
    readingBedVolumePercent,
    readingBedTrackSelection,
    readingBedTrackOptions,
    readingBedSupported,
    toggleReadingBed: handleToggleReadingBed,
    onReadingBedVolumeChange: handleReadingBedVolumeChange,
    onReadingBedTrackChange: handleReadingBedTrackChange,
    playReadingBed,
    resetReadingBed,
  } = useReadingBedControls({ bedOverride: readingBedOverride, playerMode });
  const [bookSentenceCount, setBookSentenceCount] = useState<number | null>(null);
  const [activeSentenceNumber, setActiveSentenceNumber] = useState<number | null>(null);
  const [jobOriginalLanguage, setJobOriginalLanguage] = useState<string | null>(null);
  const [jobTranslationLanguage, setJobTranslationLanguage] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  useEffect(() => {
    if (origin !== 'library' && playerMode !== 'export') {
      return;
    }
    const original =
      extractMetadataText(bookMetadata, ['input_language', 'original_language', 'language', 'lang']) ?? null;
    const target =
      extractMetadataFirstString(bookMetadata, ['target_language', 'translation_language', 'target_languages']) ?? null;
    setJobOriginalLanguage(original);
    setJobTranslationLanguage(target);
  }, [bookMetadata, origin, playerMode]);

  useEffect(() => {
    if (!jobId || origin === 'library' || playerMode === 'export') {
      return;
    }
    let cancelled = false;
    void fetchPipelineStatus(jobId)
      .then((status) => {
        if (cancelled) {
          return;
        }
        const parameters = status.parameters;
        const original =
          typeof parameters?.input_language === 'string' && parameters.input_language.trim()
            ? parameters.input_language.trim()
            : null;
        const targetLanguages = Array.isArray(parameters?.target_languages) ? parameters.target_languages : [];
        const firstTarget =
          typeof targetLanguages[0] === 'string' && targetLanguages[0].trim() ? targetLanguages[0].trim() : null;
        setJobOriginalLanguage(original);
        setJobTranslationLanguage(firstTarget);
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        setJobOriginalLanguage(null);
        setJobTranslationLanguage(null);
      });
    return () => {
      cancelled = true;
    };
  }, [jobId, origin, playerMode]);
  useEffect(() => {
    setBookSentenceCount(null);
  }, [jobId]);
  useEffect(() => {
    setIsExporting(false);
    setExportError(null);
  }, [jobId]);

  useEffect(() => {
    let cancelled = false;

    if (!jobId || chunks.length === 0) {
      setBookSentenceCount(null);
      return () => {
        cancelled = true;
      };
    }

    const metadataCount = normaliseBookSentenceCount(bookMetadata);
    if (metadataCount !== null) {
      setBookSentenceCount((current) => (current === metadataCount ? current : metadataCount));
      return () => {
        cancelled = true;
      };
    }

    if (bookSentenceCount !== null) {
      return () => {
        cancelled = true;
      };
    }

    if (playerMode === 'export') {
      const derivedCount = deriveSentenceCountFromChunks(chunks);
      if (derivedCount !== null) {
        setBookSentenceCount((current) => (current === derivedCount ? current : derivedCount));
      }
      return () => {
        cancelled = true;
      };
    }

    const resolveTargetUrl = (): string | null => {
      try {
        return resolveStoragePath(jobId, 'metadata/sentences.json');
      } catch (error) {
        try {
          const encodedJobId = encodeURIComponent(jobId);
          return `/pipelines/jobs/${encodedJobId}/metadata/sentences.json`;
        } catch {
          return null;
        }
      }
    };

    const targetUrl = resolveTargetUrl();
    if (!targetUrl || typeof fetch !== 'function') {
      return () => {
        cancelled = true;
      };
    }

    (async () => {
      try {
        const response = await fetch(targetUrl, { credentials: 'include' });
        if (!response.ok) {
          return;
        }

        let payload: unknown = null;
        if (typeof response.json === 'function') {
          try {
            payload = await response.json();
          } catch {
            payload = null;
          }
        }
        if (payload === null && typeof response.text === 'function') {
          try {
            const raw = await response.text();
            payload = JSON.parse(raw);
          } catch {
            payload = null;
          }
        }

        const count = normaliseBookSentenceCount(payload);
        if (cancelled || count === null) {
          return;
        }
        setBookSentenceCount(count);
      } catch (error) {
        if (import.meta.env.DEV) {
          console.warn('Unable to load book sentence count', targetUrl, error);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [bookMetadata, bookSentenceCount, chunks.length, jobId, playerMode]);

  const {
    sentenceLookup,
    jobStartSentence,
    jobEndSentence,
    canJumpToSentence,
    sentenceJumpPlaceholder,
    sentenceJumpValue,
    sentenceJumpError,
    onSentenceJumpChange: handleSentenceJumpChange,
    onSentenceJumpSubmit: handleSentenceJumpSubmit,
    onInteractiveSentenceJump: handleInteractiveSentenceJump,
  } = useSentenceNavigation({
    chunks,
    mediaAudio: media.audio,
    showOriginalAudio,
    showTranslationAudio,
    findMatchingMediaId,
    requestAutoPlay,
    inlineAudioPlayingRef,
    onRequestSelection: setPendingSelection,
  });

  const handleActiveSentenceChange = useCallback((value: number | null) => {
    setActiveSentenceNumber(value);
  }, []);

  useEffect(() => {
    if (!selectionRequest) {
      return;
    }
    setPendingSelection({
      baseId: selectionRequest.baseId,
      preferredType: selectionRequest.preferredType ?? null,
      offsetRatio: selectionRequest.offsetRatio ?? null,
      approximateTime: selectionRequest.approximateTime ?? null,
      token: selectionRequest.token ?? Date.now(),
    });
  }, [selectionRequest]);

  useEffect(() => {
    if (import.meta.env.DEV) {
      return enableDebugOverlay();
    }
    return undefined;
  }, []);
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

  const { coverUrl: displayCoverUrl, shouldShowCoverImage } = useCoverArt({
    jobId,
    origin,
    bookMetadata,
    mediaComplete,
    playerMode,
  });

  const { isSubtitleContext, subtitleInfo } = useSubtitleInfo({
    jobId,
    jobType,
    itemType,
    origin,
    libraryItem,
    playerMode,
  });

  const handleSearchSelection = useCallback(
    (result: MediaSearchResult, category: SearchCategory) => {
      const preferredCategory: MediaCategory | null = category === 'library' ? 'text' : category;
      const baseId = resolveBaseIdFromResult(result, preferredCategory);
      const offsetRatio = typeof result.offset_ratio === 'number' ? result.offset_ratio : null;
      const approximateTime =
        typeof result.approximate_time_seconds === 'number' ? result.approximate_time_seconds : null;
      const selection: MediaSelectionRequest = {
        baseId,
        preferredType: preferredCategory,
        offsetRatio,
        approximateTime,
        token: Date.now(),
      };

      if (category === 'library') {
        if (!result.job_id) {
          return;
        }
        if (result.job_id === jobId) {
          setPendingSelection(selection);
          return;
        }
        const payload: LibraryOpenRequest = {
          kind: 'library-open',
          jobId: result.job_id,
          selection,
        };
        onOpenLibraryItem?.(payload);
        return;
      }

      if (result.job_id && result.job_id !== jobId) {
        return;
      }

      setPendingSelection(selection);
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

  const activeItemId = selectedItemIds.text;

  const hasResolvedInitialTabRef = useRef(false);

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

    const currentItem = getMediaItem('text', activeItemId);
    if (!currentItem) {
      return;
    }

    rememberSelection({ media: currentItem });
  }, [
    activeItemId,
    getMediaItem,
    rememberSelection,
    memoryState.currentMediaId,
    memoryState.currentMediaType,
  ]);

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

  useEffect(() => {
    onVideoPlaybackStateChange?.(false);
  }, [onVideoPlaybackStateChange]);

  useEffect(() => {
    onPlaybackStateChange?.(isInlineAudioPlaying);
  }, [isInlineAudioPlaying, onPlaybackStateChange]);
  const selectedItemId = selectedItemIds.text;
  const textPlaybackPosition = getPosition(selectedItemIds.text);
  const selectedItem = useMemo(() => {
    if (media.text.length === 0) {
      return null;
    }
    if (!selectedItemId) {
      return media.text[0] ?? null;
    }
    return media.text.find((item) => item.url === selectedItemId) ?? media.text[0] ?? null;
  }, [media.text, selectedItemId]);
  const allowTextPreview =
    playerMode !== 'export' || (typeof window !== 'undefined' && window.location.protocol !== 'file:');
  const { textPreview, textLoading, textError } = useTextPreview(selectedItem?.url, {
    enabled: allowTextPreview,
  });
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
    chunk.files.some((file) => isAudioFileType(file.type) && file.url === audioId),
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
  const { hasInteractiveChunks, resolvedActiveTextChunk } = useChunkMetadata({
    jobId,
    origin,
    playerMode,
    chunks,
    activeTextChunk,
    activeTextChunkIndex,
  });

  const {
    activeAudioTracks,
    visibleInlineAudioOptions,
    inlineAudioUnavailable,
    canToggleOriginalAudio,
    canToggleTranslationAudio,
    effectiveOriginalAudioEnabled,
    effectiveTranslationAudioEnabled,
    handleOriginalAudioToggle,
    handleTranslationAudioToggle,
    activeTimingTrack,
  } = useInlineAudioOptions({
    jobId,
    origin,
    playerMode,
    activeTextChunk,
    resolvedActiveTextChunk,
    activeTextChunkIndex,
    interactiveAudioNameMap,
    interactiveAudioPlaylist,
    inlineAudioSelection,
    showOriginalAudio,
    setShowOriginalAudio,
    showTranslationAudio,
    setShowTranslationAudio,
    setInlineAudioSelection,
  });

  usePendingSelection({
    pendingSelection,
    setPendingSelection,
    chunks,
    media,
    findMatchingMediaId,
    getMediaItem,
    deriveBaseId,
    rememberPosition,
    visibleInlineAudioOptions,
    setSelectedItemIds,
    setPendingChunkSelection,
    setPendingTextScrollRatio,
    setInlineAudioSelection,
  });

  const { activateChunk, handleInlineAudioEnded } = useInlineAudioSelection({
    chunks,
    audioChunkIndexMap,
    activeTextChunkIndex,
    inlineAudioSelection,
    setInlineAudioSelection,
    visibleInlineAudioOptions,
    mediaAudio: media.audio,
    getMediaItem,
    deriveBaseId,
    setSelectedItemIds,
    setPendingTextScrollRatio,
    rememberPosition,
    requestAutoPlay,
    updateSelection,
  });

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
  const shouldForceInteractiveViewer = isInteractiveFullscreen;
  const handleInteractiveFullscreenToggle = useCallback(() => {
    setIsInteractiveFullscreen((current) => {
      const next = !current;
      updateInteractiveFullscreenPreference(next);
      return next;
    });
  }, [updateInteractiveFullscreenPreference]);

  const handleExitInteractiveFullscreen = useCallback(() => {
    updateInteractiveFullscreenPreference(false);
    setIsInteractiveFullscreen(false);
  }, [updateInteractiveFullscreenPreference]);
  useEffect(() => {
    if (!canRenderInteractiveViewer) {
      if (!hasInteractiveChunks && isInteractiveFullscreen) {
        updateInteractiveFullscreenPreference(false);
        setIsInteractiveFullscreen(false);
      }
      return;
    }
    if (interactiveFullscreenPreferenceRef.current && !isInteractiveFullscreen) {
      updateInteractiveFullscreenPreference(true);
      setIsInteractiveFullscreen(true);
    }
  }, [
    canRenderInteractiveViewer,
    hasInteractiveChunks,
    isInteractiveFullscreen,
    updateInteractiveFullscreenPreference,
  ]);
  const hasTextItems = media.text.length > 0;
  const shouldShowInteractiveViewer = canRenderInteractiveViewer || shouldForceInteractiveViewer;
  const shouldShowEmptySelectionPlaceholder =
    hasTextItems && !selectedItem && !shouldForceInteractiveViewer;
  const shouldShowLoadingPlaceholder =
    Boolean(textLoading && selectedItem && !shouldForceInteractiveViewer);
  const shouldShowStandaloneError = Boolean(textError) && !shouldForceInteractiveViewer;
  const navigableItems = useMemo(
    () => media.text.filter((item) => typeof item.url === 'string' && item.url.length > 0),
    [media.text],
  );
  const activeNavigableIndex = useMemo(() => {
    const currentId = selectedItemIds.text;
    if (!currentId) {
      return navigableItems.length > 0 ? 0 : -1;
    }

    const matchIndex = navigableItems.findIndex((item) => item.url === currentId);
    if (matchIndex >= 0) {
      return matchIndex;
    }

    return navigableItems.length > 0 ? 0 : -1;
  }, [navigableItems, selectedItemIds.text]);
  const derivedNavigation = useMemo(() => {
    if (navigableItems.length > 0) {
      return {
        mode: 'media' as const,
        count: navigableItems.length,
        index: Math.max(0, activeNavigableIndex),
      };
    }
    if (chunks.length > 0) {
      const index = activeTextChunkIndex >= 0 ? activeTextChunkIndex : 0;
      return {
        mode: 'chunks' as const,
        count: chunks.length,
        index: Math.max(0, Math.min(index, Math.max(chunks.length - 1, 0))),
      };
    }
    return { mode: 'none' as const, count: 0, index: -1 };
  }, [activeNavigableIndex, activeTextChunkIndex, chunks.length, navigableItems.length]);
  const isFirstDisabled =
    derivedNavigation.count === 0 || derivedNavigation.index <= 0;
  const isPreviousDisabled =
    derivedNavigation.count === 0 || derivedNavigation.index <= 0;
  const isNextDisabled =
    derivedNavigation.count === 0 || derivedNavigation.index >= derivedNavigation.count - 1;
  const isLastDisabled =
    derivedNavigation.count === 0 || derivedNavigation.index >= derivedNavigation.count - 1;
  const playbackControlsAvailable = hasInlineAudioControls;
  const isActiveMediaPlaying = isInlineAudioPlaying;
  const shouldHoldWakeLock = isInlineAudioPlaying;
  useWakeLock(shouldHoldWakeLock);
  const isPlaybackDisabled = !playbackControlsAvailable;
  const isFullscreenDisabled = !canRenderInteractiveViewer;

  const adjustMyLinguistFontScale = useCallback(
    (direction: 'increase' | 'decrease') => {
      const delta = direction === 'increase' ? MY_LINGUIST_FONT_SCALE_STEP : -MY_LINGUIST_FONT_SCALE_STEP;
      adjustBaseFontScalePercent(delta);
    },
    [adjustBaseFontScalePercent],
  );
  const handleToggleMyLinguist = useCallback(() => {
    if (linguistEnabled) {
      toggleMyLinguist();
    }
  }, [linguistEnabled, toggleMyLinguist]);
  const handleAdjustMyLinguistFontScale = useCallback(
    (direction: 'increase' | 'decrease') => {
      if (!linguistEnabled) {
        return;
      }
      adjustMyLinguistFontScale(direction);
    },
    [adjustMyLinguistFontScale, linguistEnabled],
  );

  const activateTextItem = useCallback(
    (item: LiveMediaItem | null | undefined, options?: { scrollRatio?: number; autoPlay?: boolean }) => {
      if (!item?.url) {
        return false;
      }
      const baseId = deriveBaseId(item) ?? deriveBaseIdFromReference(item.url);
      const chunkIndex = baseId ? findChunkIndexForBaseId(baseId, chunks) : -1;
      if (chunkIndex >= 0) {
        return activateChunk(chunks[chunkIndex], options);
      }
      setSelectedItemIds((current) =>
        current.text === item.url ? current : { ...current, text: item.url },
      );
      if (typeof options?.scrollRatio === 'number') {
        setPendingTextScrollRatio(Math.min(Math.max(options.scrollRatio, 0), 1));
      }
      if (options?.autoPlay) {
        requestAutoPlay();
      }
      return false;
    },
    [activateChunk, chunks, deriveBaseId, requestAutoPlay, setPendingTextScrollRatio, setSelectedItemIds],
  );

  useEffect(() => {
    if (!pendingChunkSelection) {
      return;
    }

    const { index } = pendingChunkSelection;
    if (index < 0 || index >= chunks.length) {
      setPendingChunkSelection(null);
      return;
    }

    activateChunk(chunks[index], { scrollRatio: 0 });
    setPendingChunkSelection(null);
  }, [activateChunk, chunks, pendingChunkSelection]);

  const handleInlineAudioPlaybackStateChange = useCallback(
    (state: 'playing' | 'paused') => {
      updateInlineAudioPlaying(state === 'playing');
    },
    [updateInlineAudioPlaying],
  );

  const handleInlineAudioControlsRegistration = useCallback((controls: PlaybackControls | null) => {
    inlineAudioControlsRef.current = controls;
    setHasInlineAudioControls(Boolean(controls));
    if (!controls) {
      updateInlineAudioPlaying(false);
    }
  }, [updateInlineAudioPlaying]);

  const handleNavigate = useCallback(
    (intent: NavigationIntent, options?: { autoPlay?: boolean }) => {
      const autoPlay = options?.autoPlay ?? true;
      if (navigableItems.length > 0) {
        const currentId = selectedItemIds.text;
        const currentIndex = currentId
          ? navigableItems.findIndex((item) => item.url === currentId)
          : -1;
        const lastIndex = navigableItems.length - 1;
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
        const nextItem = navigableItems[nextIndex];
        if (!nextItem) {
          return;
        }
        activateTextItem(nextItem, { autoPlay, scrollRatio: 0 });
        return;
      }

      if (chunks.length > 0) {
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
        activateChunk(targetChunk, { autoPlay, scrollRatio: 0 });
        return;
      }

      updateSelection('text', intent);
    },
    [activateChunk, activateTextItem, activeTextChunkIndex, chunks, navigableItems, selectedItemIds.text, updateSelection],
  );

  const handleNavigatePreservingPlayback = useCallback(
    (intent: NavigationIntent) => {
      handleNavigate(intent, { autoPlay: inlineAudioPlayingRef.current });
    },
    [handleNavigate],
  );

  const handlePauseActiveMedia = useCallback(() => {
    inlineAudioControlsRef.current?.pause();
    updateInlineAudioPlaying(false);
  }, [updateInlineAudioPlaying]);

  const handlePlayActiveMedia = useCallback(() => {
    if (readingBedEnabled) {
      playReadingBed();
    }
    inlineAudioControlsRef.current?.play();
    updateInlineAudioPlaying(true);
  }, [playReadingBed, readingBedEnabled, updateInlineAudioPlaying]);

  const handleToggleActiveMedia = useCallback(() => {
    if (isActiveMediaPlaying) {
      handlePauseActiveMedia();
    } else {
      handlePlayActiveMedia();
    }
  }, [handlePauseActiveMedia, handlePlayActiveMedia, isActiveMediaPlaying]);

  const { showShortcutHelp, setShowShortcutHelp } = usePlayerShortcuts({
    canToggleOriginalAudio,
    onToggleOriginalAudio: handleOriginalAudioToggle,
    canToggleTranslationAudio,
    onToggleTranslationAudio: handleTranslationAudioToggle,
    onToggleCueLayer: handleToggleInteractiveTextLayer,
    onToggleMyLinguist: handleToggleMyLinguist,
    enableMyLinguist: linguistEnabled,
    onToggleReadingBed: handleToggleReadingBed,
    onToggleFullscreen: handleInteractiveFullscreenToggle,
    onTogglePlayback: handleToggleActiveMedia,
    onNavigate: handleNavigatePreservingPlayback,
    adjustTranslationSpeed,
    adjustFontScale,
    adjustMyLinguistFontScale: handleAdjustMyLinguistFontScale,
  });

  const shortcutHelpOverlay = (
    <ShortcutHelpOverlay
      isOpen={showShortcutHelp}
      onClose={() => setShowShortcutHelp(false)}
      canToggleOriginalAudio={canToggleOriginalAudio}
      canToggleTranslationAudio={canToggleTranslationAudio}
      showMyLinguist={linguistEnabled}
    />
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

  useEffect(() => {
    if (!pendingAutoPlayRef.current) {
      return;
    }
    const controls = inlineAudioControlsRef.current;
    if (!controls) {
      return;
    }
    pendingAutoPlayRef.current = false;
    controls.pause();
    controls.play();
  }, [autoPlayToken, hasInlineAudioControls, inlineAudioSelection]);

  useEffect(() => {
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
    selectedItemIds.text,
    textPlaybackPosition,
    textPreview?.url,
    pendingTextScrollRatio,
    getMediaItem,
    deriveBaseId,
    rememberPosition,
  ]);

  useEffect(() => {
    setIsInteractiveFullscreen(false);
    setPendingSelection(null);
    setPendingChunkSelection(null);
    setPendingTextScrollRatio(null);
  }, [normalisedJobId]);

  useEffect(() => {
    onFullscreenChange?.(isInteractiveFullscreen);
  }, [isInteractiveFullscreen, onFullscreenChange]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem('player.showOriginalAudio', showOriginalAudio ? 'true' : 'false');
  }, [showOriginalAudio]);
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem('player.showTranslationAudio', showTranslationAudio ? 'true' : 'false');
  }, [showTranslationAudio]);

  const handleResetInteractiveLayout = useCallback(() => {
    setBaseFontScalePercent(DEFAULT_MY_LINGUIST_FONT_SCALE_PERCENT);
    resetInteractiveTextSettings();
    resetReadingBed();
  }, [resetInteractiveTextSettings, resetReadingBed, setBaseFontScalePercent]);

  const bookTitle = extractMetadataText(bookMetadata, ['book_title', 'title', 'book_name', 'name']);
  const bookAuthor = extractMetadataText(bookMetadata, ['book_author', 'author', 'writer', 'creator']);
  const bookYear = extractMetadataText(bookMetadata, ['book_year', 'year', 'publication_year', 'published_year', 'first_publish_year']);
  const bookGenre = extractMetadataFirstString(bookMetadata, ['genre', 'book_genre', 'series_genre', 'category', 'subjects']);
  const isBookLike =
    itemType === 'book' || (jobType ?? '').trim().toLowerCase().includes('book') || Boolean(bookTitle);
  const canExport = playerMode !== 'export' && isBookLike && mediaComplete && (hasInteractiveChunks || hasTextItems);
  const handleExport = useCallback(() => {
    if (!jobId || isExporting) {
      return;
    }
    setIsExporting(true);
    setExportError(null);
    const payload = {
      source_kind: origin === 'library' ? 'library' : 'job',
      source_id: jobId,
      player_type: 'interactive-text',
    } as const;
    createExport(payload)
      .then((result) => {
        const resolved =
          result.download_url.startsWith('http://') || result.download_url.startsWith('https://')
            ? result.download_url
            : withBase(result.download_url);
        const downloadUrl = appendAccessToken(resolved);
        if (typeof document !== 'undefined') {
          const anchor = document.createElement('a');
          anchor.href = downloadUrl;
          anchor.download = result.filename ?? '';
          anchor.rel = 'noopener';
          document.body.appendChild(anchor);
          anchor.click();
          anchor.remove();
          return;
        }
        if (typeof window !== 'undefined') {
          window.location.assign(downloadUrl);
        }
      })
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : 'Unable to export offline player.';
        setExportError(message);
      })
      .finally(() => {
        setIsExporting(false);
      });
  }, [appendAccessToken, createExport, isExporting, jobId, origin, withBase]);
  const channelBug = useMemo(() => {
    const normalisedJobType = (jobType ?? '').trim().toLowerCase();
    if (itemType === 'book') {
      return { glyph: 'BK', label: 'Book' };
    }
    if (itemType === 'narrated_subtitle') {
      return { glyph: 'SUB', label: 'Subtitles' };
    }
    if (itemType === 'video') {
      return { glyph: 'TV', label: 'Video' };
    }
    if (normalisedJobType.includes('subtitle')) {
      return { glyph: 'SUB', label: 'Subtitles' };
    }
    if (normalisedJobType.includes('book') || Boolean(bookTitle || bookAuthor)) {
      return { glyph: 'BK', label: 'Book' };
    }
    return { glyph: 'JOB', label: 'Job' };
  }, [bookAuthor, bookTitle, itemType, jobType]);
  const sectionLabel = bookTitle ? `Player for ${bookTitle}` : 'Player';
  const loadingMessage = bookTitle ? `Loading generated media for ${bookTitle}…` : 'Loading generated media…';
  const emptyMediaMessage = bookTitle ? `No generated media yet for ${bookTitle}.` : 'No generated media yet.';

  const hasAnyMedia = media.text.length + media.audio.length + media.video.length > 0;
  const headingLabel = bookTitle ?? 'Player';
  const interactiveFontScale = fontScalePercent / 100;
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
  const interactiveFullscreenLabel = isInteractiveFullscreen ? 'Exit fullscreen' : 'Enter fullscreen';
  const sentenceJumpListId = useId();
  const sentenceJumpInputId = useId();
  const sentenceJumpInputFullscreenId = useId();
  const sentenceJumpDisabled = !canJumpToSentence;
  const sentenceJumpDatalist =
    sentenceLookup.suggestions.length > 0 ? (
      <datalist id={sentenceJumpListId}>
        {sentenceLookup.suggestions.map((value) => (
          <option key={value} value={value} />
        ))}
      </datalist>
    ) : null;

  const shouldShowBackToLibrary = origin === 'library' && showBackToLibrary;
  const exportAction = canExport ? (
    <div className="player-panel__export-action">
      <button
        type="button"
        className="player-panel__nav-button player-panel__nav-button--export"
        onClick={handleExport}
        disabled={isExporting}
        aria-label="Export offline player"
        title="Export offline player"
      >
        <span aria-hidden="true" className="player-panel__nav-button-icon">
          📦
        </span>
        <span aria-hidden="true" className="player-panel__nav-button-text">
          {isExporting ? 'Preparing export…' : 'Export offline player'}
        </span>
      </button>
      {exportError ? (
        <span className="player-panel__export-error" role="alert">
          {exportError}
        </span>
      ) : null}
    </div>
  ) : null;

  const navigationBaseProps = {
    onNavigate: handleNavigatePreservingPlayback,
    onToggleFullscreen: handleInteractiveFullscreenToggle,
    onTogglePlayback: handleToggleActiveMedia,
    controlsLayout: 'compact',
    disableFirst: isFirstDisabled,
    disablePrevious: isPreviousDisabled,
    disableNext: isNextDisabled,
    disableLast: isLastDisabled,
    disablePlayback: isPlaybackDisabled,
    disableFullscreen: isFullscreenDisabled,
    isFullscreen: isInteractiveFullscreen,
    isPlaying: isActiveMediaPlaying,
    fullscreenLabel: interactiveFullscreenLabel,
    showBackToLibrary: shouldShowBackToLibrary,
    onBackToLibrary,
    showOriginalAudioToggle: canToggleOriginalAudio,
    onToggleOriginalAudio: handleOriginalAudioToggle,
    originalAudioEnabled: effectiveOriginalAudioEnabled,
    disableOriginalAudioToggle: !canToggleOriginalAudio,
    showTranslationAudioToggle: canToggleTranslationAudio,
    onToggleTranslationAudio: handleTranslationAudioToggle,
    translationAudioEnabled: effectiveTranslationAudioEnabled,
    disableTranslationAudioToggle: !canToggleTranslationAudio,
    showCueLayerToggles: true,
    cueVisibility: interactiveTextVisibility,
    onToggleCueLayer: handleToggleInteractiveTextLayer,
    showTranslationSpeed: true,
    translationSpeed,
    translationSpeedMin: TRANSLATION_SPEED_MIN,
    translationSpeedMax: TRANSLATION_SPEED_MAX,
    translationSpeedStep: TRANSLATION_SPEED_STEP,
    onTranslationSpeedChange: handleTranslationSpeedChange,
    showSentenceJump: canJumpToSentence,
    sentenceJumpValue,
    sentenceJumpMin: sentenceLookup.min,
    sentenceJumpMax: sentenceLookup.max,
    sentenceJumpError,
    sentenceJumpDisabled,
    sentenceJumpListId,
    sentenceJumpPlaceholder,
    onSentenceJumpChange: handleSentenceJumpChange,
    onSentenceJumpSubmit: handleSentenceJumpSubmit,
    showFontScale: true,
    fontScalePercent,
    fontScaleMin: FONT_SCALE_MIN,
    fontScaleMax: FONT_SCALE_MAX,
    fontScaleStep: FONT_SCALE_STEP,
    onFontScaleChange: handleFontScaleChange,
    showMyLinguistFontScale: linguistEnabled,
    myLinguistFontScalePercent: baseFontScalePercent,
    myLinguistFontScaleMin: MY_LINGUIST_FONT_SCALE_MIN,
    myLinguistFontScaleMax: MY_LINGUIST_FONT_SCALE_MAX,
    myLinguistFontScaleStep: MY_LINGUIST_FONT_SCALE_STEP,
    onMyLinguistFontScaleChange: linguistEnabled ? setBaseFontScalePercent : undefined,
    showInteractiveThemeControls: true,
    interactiveTheme: interactiveTextTheme,
    onInteractiveThemeChange: setInteractiveTextTheme,
    showInteractiveBackgroundOpacity: true,
    interactiveBackgroundOpacityPercent: interactiveBackgroundOpacityPercent,
    interactiveBackgroundOpacityMin: 0,
    interactiveBackgroundOpacityMax: 100,
    interactiveBackgroundOpacityStep: 5,
    onInteractiveBackgroundOpacityChange: setInteractiveBackgroundOpacityPercent,
    showInteractiveSentenceCardOpacity: true,
    interactiveSentenceCardOpacityPercent: interactiveSentenceCardOpacityPercent,
    interactiveSentenceCardOpacityMin: 0,
    interactiveSentenceCardOpacityMax: 100,
    interactiveSentenceCardOpacityStep: 5,
    onInteractiveSentenceCardOpacityChange: setInteractiveSentenceCardOpacityPercent,
    onResetLayout: handleResetInteractiveLayout,
    showReadingBedToggle: true,
    readingBedEnabled,
    disableReadingBedToggle: !readingBedSupported,
    onToggleReadingBed: handleToggleReadingBed,
    showReadingBedVolume: true,
    readingBedVolumePercent,
    readingBedVolumeMin: 0,
    readingBedVolumeMax: 100,
    readingBedVolumeStep: 5,
    onReadingBedVolumeChange: handleReadingBedVolumeChange,
    showReadingBedTrack: true,
    readingBedTrack: readingBedTrackSelection ?? '',
    readingBedTrackOptions,
    onReadingBedTrackChange: handleReadingBedTrackChange,
    activeSentenceNumber,
    totalSentencesInBook: jobEndSentence,
    jobStartSentence,
    bookTotalSentences: bookSentenceCount,
  } satisfies Omit<NavigationControlsProps, 'context' | 'sentenceJumpInputId'>;

  const navigationGroup = (
    <>
      <NavigationControls
        context="panel"
        sentenceJumpInputId={sentenceJumpInputId}
        {...navigationBaseProps}
      />
      {exportAction}
    </>
  );

  const fullscreenNavigationGroup = isInteractiveFullscreen ? (
    <NavigationControls
      context="fullscreen"
      sentenceJumpInputId={sentenceJumpInputFullscreenId}
      {...navigationBaseProps}
    />
  ) : null;

  const interactiveViewerProps = {
    playerMode,
    playerFeatures: {
      linguist: linguistEnabled,
      painter: painterEnabled,
    },
    content: interactiveViewerContent,
    rawContent: interactiveViewerRaw,
    chunk: resolvedActiveTextChunk,
    totalSentencesInBook: bookSentenceCount,
    bookTotalSentences: bookSentenceCount,
    jobStartSentence,
    jobEndSentence,
    jobOriginalLanguage,
    jobTranslationLanguage,
    cueVisibility: interactiveTextVisibility,
    activeAudioUrl: inlineAudioSelection,
    noAudioAvailable: inlineAudioUnavailable,
    jobId,
    onActiveSentenceChange: handleActiveSentenceChange,
    onRequestSentenceJump: handleInteractiveSentenceJump,
    onScroll: handleTextScroll,
    onAudioProgress: handleInlineAudioProgress,
    getStoredAudioPosition: getInlineAudioPosition,
    onRegisterInlineAudioControls: handleInlineAudioControlsRegistration,
    onInlineAudioPlaybackStateChange: handleInlineAudioPlaybackStateChange,
    onRequestAdvanceChunk: handleInlineAudioEnded,
    isFullscreen: isInteractiveFullscreen,
    onRequestExitFullscreen: handleExitInteractiveFullscreen,
    fullscreenControls: isInteractiveFullscreen ? fullscreenNavigationGroup : null,
    translationSpeed,
    audioTracks: activeAudioTracks,
    activeTimingTrack,
    originalAudioEnabled: effectiveOriginalAudioEnabled,
    translationAudioEnabled: effectiveTranslationAudioEnabled,
    fontScale: interactiveFontScale,
    theme: interactiveTextTheme,
    backgroundOpacityPercent: interactiveBackgroundOpacityPercent,
    sentenceCardOpacityPercent: interactiveSentenceCardOpacityPercent,
    infoGlyph: channelBug.glyph,
    infoGlyphLabel: channelBug.label,
    infoTitle: isSubtitleContext ? subtitleInfo.title : null,
    infoMeta: isSubtitleContext ? subtitleInfo.meta : null,
    infoCoverUrl: isSubtitleContext ? subtitleInfo.coverUrl : null,
    infoCoverSecondaryUrl: isSubtitleContext ? subtitleInfo.coverSecondaryUrl : null,
    infoCoverAltText: isSubtitleContext ? subtitleInfo.coverAltText : null,
    infoCoverVariant: (isSubtitleContext ? 'subtitles' : null) as 'subtitles' | null,
    bookTitle: bookTitle ?? headingLabel,
    bookAuthor,
    bookYear,
    bookGenre,
    bookCoverUrl: shouldShowCoverImage ? displayCoverUrl : null,
    bookCoverAltText: coverAltText,
  };

  if (error) {
    return (
      <div className="player-panel" role="region" aria-label={sectionLabel}>
        <p role="alert">Unable to load generated media: {error.message}</p>
      </div>
    );
  }

  if (isLoading && media.text.length === 0 && media.audio.length === 0 && media.video.length === 0) {
    return (
      <div className="player-panel" role="region" aria-label={sectionLabel}>
        <p role="status">{loadingMessage}</p>
      </div>
    );
  }

  if (!hasJobId) {
    return (
      <div className="player-panel" role="region" aria-label={sectionLabel}>
        {sentenceJumpDatalist}
        {shortcutHelpOverlay}
        <div className="player-panel__empty" role="status">
          <p>No job selected.</p>
        </div>
      </div>
    );
  }

  return (
    <PlayerPanelShell
      ariaLabel={sectionLabel}
      prelude={
        <>
          {sentenceJumpDatalist}
          {shortcutHelpOverlay}
        </>
      }
      search={searchEnabled ? <MediaSearchPanel currentJobId={jobId} onResultAction={handleSearchSelection} /> : null}
      toolbar={navigationGroup}
    >
      {!hasAnyMedia && !isLoading ? (
        <p role="status">{emptyMediaMessage}</p>
      ) : !hasTextItems && !hasInteractiveChunks ? (
        <p role="status">No interactive reader media yet.</p>
      ) : (
        <div className="player-panel__stage">
          {!mediaComplete ? (
            <div className="player-panel__notice" role="status">
              Media generation is still finishing. Newly generated files will appear automatically.
            </div>
          ) : null}
          <div className="player-panel__viewer">
            <div className="player-panel__document">
              <PlayerPanelInteractiveDocument
                shouldShowEmptySelectionPlaceholder={shouldShowEmptySelectionPlaceholder}
                shouldShowLoadingPlaceholder={shouldShowLoadingPlaceholder}
                shouldShowStandaloneError={shouldShowStandaloneError}
                shouldShowInteractiveViewer={shouldShowInteractiveViewer}
                canRenderInteractiveViewer={canRenderInteractiveViewer}
                textError={textError}
                textLoading={textLoading}
                selectedItem={selectedItem}
                viewerProps={interactiveViewerProps}
                textScrollRef={textScrollRef}
              />
            </div>
          </div>
        </div>
      )}
    </PlayerPanelShell>
  );
}
