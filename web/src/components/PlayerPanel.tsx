import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import type { LiveMediaChunk, LiveMediaItem, LiveMediaState } from '../hooks/useLiveMedia';
import { useMediaMemory } from '../hooks/useMediaMemory';
import { usePlaybackBookmarks } from '../hooks/usePlaybackBookmarks';
import { useWakeLock } from '../hooks/useWakeLock';
import { useMyLinguist } from '../context/MyLinguistProvider';
import {
  DEFAULT_MY_LINGUIST_FONT_SCALE_PERCENT,
  FONT_SCALE_MAX,
  FONT_SCALE_MIN,
  FONT_SCALE_STEP,
  MY_LINGUIST_FONT_SCALE_MAX,
  MY_LINGUIST_FONT_SCALE_MIN,
  MY_LINGUIST_FONT_SCALE_STEP,
  TRANSLATION_SPEED_MAX,
  TRANSLATION_SPEED_MIN,
  TRANSLATION_SPEED_STEP,
} from './player-panel/constants';
import MediaSearchPanel from './MediaSearchPanel';
import type { LibraryItem } from '../api/dtos';
import { PlayerPanelInteractiveDocument } from './player-panel/PlayerPanelInteractiveDocument';
import {
  buildInteractiveAudioCatalog,
  fallbackTextFromSentences,
  isAudioFileType,
} from './player-panel/utils';
import { enableDebugOverlay } from '../player/AudioSyncController';
import type { LibraryOpenInput, MediaSelectionRequest, PlayerFeatureFlags, PlayerMode } from '../types/player';
import { NavigationControls } from './player-panel/NavigationControls';
import { PlayerPanelShell } from './player-panel/PlayerPanelShell';
import {
  deriveBaseIdFromReference,
  findChunkIndexForBaseId,
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
import { usePlayerPanelJobInfo } from './player-panel/usePlayerPanelJobInfo';
import { usePlayerPanelSelectionState } from './player-panel/usePlayerPanelSelectionState';
import { usePlayerPanelPlaybackState } from './player-panel/usePlayerPanelPlaybackState';
import { usePlayerPanelNavigation } from './player-panel/usePlayerPanelNavigation';
import { usePlayerPanelExport } from './player-panel/usePlayerPanelExport';
import { useMediaSessionActions, useMediaSessionMetadata } from './player-panel/useMediaSession';
import { usePlayerPanelActions } from './player-panel/usePlayerPanelActions';
import { buildInteractiveViewerProps, buildNavigationBaseProps } from './player-panel/playerPanelProps';
import { useInteractiveFullscreenPreference } from './player-panel/useInteractiveFullscreenPreference';
import { usePlayerPanelScrollMemory } from './player-panel/usePlayerPanelScrollMemory';

type ReadingBedOverride = {
  id: string;
  label: string;
  url: string;
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
  const hasJobId = Boolean(jobId);
  const normalisedJobId = jobId ?? '';
  const mediaMemory = useMediaMemory({ jobId });
  const { state: memoryState, rememberSelection, rememberPosition, getPosition, findMatchingMediaId, deriveBaseId } =
    mediaMemory;
  const { bookmarks, addBookmark, removeBookmark } = usePlaybackBookmarks({ jobId });
  const {
    selectedItemIds,
    setSelectedItemIds,
    pendingSelection,
    setPendingSelection,
    pendingChunkSelection,
    setPendingChunkSelection,
    pendingTextScrollRatio,
    setPendingTextScrollRatio,
    getMediaItem,
    updateSelection,
  } = usePlayerPanelSelectionState({
    media,
    selectionRequest,
    memoryState,
    rememberSelection,
  });
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
  const [panelAdvancedControlsOpen, setPanelAdvancedControlsOpen] = useState(false);
  const textScrollRef = useRef<HTMLDivElement | null>(null);
  const interactiveTextSettings = useInteractiveTextSettings();
  const {
    interactiveTextVisibility,
    toggleInteractiveTextLayer: handleToggleInteractiveTextLayer,
    translationSpeed,
    adjustTranslationSpeed,
    fontScalePercent,
    adjustFontScale,
    interactiveTextTheme,
    interactiveBackgroundOpacityPercent,
    interactiveSentenceCardOpacityPercent,
    resetInteractiveTextSettings,
  } = interactiveTextSettings;
  const readingBedControls = useReadingBedControls({ bedOverride: readingBedOverride, playerMode });
  const {
    readingBedEnabled,
    toggleReadingBed: handleToggleReadingBed,
    playReadingBed,
    resetReadingBed,
  } = readingBedControls;
  const {
    bookTitle,
    bookAuthor,
    bookYear,
    bookGenre,
    isBookLike,
    channelBug,
    sectionLabel,
    loadingMessage,
    emptyMediaMessage,
    coverAltText,
    bookSentenceCount,
    chapterEntries,
    jobOriginalLanguage,
    jobTranslationLanguage,
    jobScopeStartSentence,
    jobScopeEndSentence,
  } = usePlayerPanelJobInfo({
    jobId,
    jobType,
    itemType,
    origin,
    playerMode,
    bookMetadata,
    chunks,
  });
  const [activeSentenceNumber, setActiveSentenceNumber] = useState<number | null>(null);
  const {
    inlineAudioPlayingRef,
    mediaSessionTimeRef,
    isInlineAudioPlaying,
    hasInlineAudioControls,
    requestAutoPlay,
    handleInlineAudioPlaybackStateChange,
    handleInlineAudioControlsRegistration,
    handleInlineAudioProgress,
    getInlineAudioPosition,
    handlePauseActiveMedia,
    handlePlayActiveMedia,
    handleToggleActiveMedia,
  } = usePlayerPanelPlaybackState({
    inlineAudioSelection,
    getMediaItem,
    deriveBaseId,
    rememberPosition,
    getPosition,
    readingBedEnabled,
    playReadingBed,
  });

  const sentenceNavigation = useSentenceNavigation({
    chunks,
    mediaAudio: media.audio,
    showOriginalAudio,
    showTranslationAudio,
    findMatchingMediaId,
    requestAutoPlay,
    inlineAudioPlayingRef,
    onRequestSelection: setPendingSelection,
  });
  const {
    sentenceLookup,
    jobStartSentence,
    jobEndSentence,
    canJumpToSentence,
    onInteractiveSentenceJump: handleInteractiveSentenceJump,
  } = sentenceNavigation;

  const handleActiveSentenceChange = useCallback((value: number | null) => {
    setActiveSentenceNumber(value);
  }, []);

  const activeChapterId = useMemo(() => {
    if (!activeSentenceNumber || chapterEntries.length === 0) {
      return null;
    }
    const target = chapterEntries.find((chapter) => {
      const end = typeof chapter.endSentence === 'number' ? chapter.endSentence : Number.POSITIVE_INFINITY;
      return activeSentenceNumber >= chapter.startSentence && activeSentenceNumber <= end;
    });
    return target?.id ?? null;
  }, [activeSentenceNumber, chapterEntries]);

  const handleChapterJump = useCallback(
    (chapterId: string) => {
      const target = chapterEntries.find((chapter) => chapter.id === chapterId);
      if (!target) {
        return;
      }
      handleInteractiveSentenceJump(target.startSentence);
    },
    [chapterEntries, handleInteractiveSentenceJump],
  );

  useEffect(() => {
    if (import.meta.env.DEV) {
      return enableDebugOverlay();
    }
    return undefined;
  }, []);

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
  const {
    handleSearchSelection,
    handleAddBookmark,
    handleJumpBookmark,
    handleRemoveBookmark,
  } = usePlayerPanelActions({
    jobId,
    chunks,
    canJumpToSentence,
    onInteractiveSentenceJump: handleInteractiveSentenceJump,
    onOpenLibraryItem,
    setPendingSelection,
    getMediaItem,
    deriveBaseId,
    getPosition,
    inlineAudioSelection,
    activeSentenceNumber,
    addBookmark,
    removeBookmark,
  });

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

  const inlineAudioOptions = useInlineAudioOptions({
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
  } = inlineAudioOptions;

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

  const fallbackTextContent = useMemo(
    () => fallbackTextFromSentences(resolvedActiveTextChunk),
    [resolvedActiveTextChunk],
  );
  const interactiveViewerContent = (textPreview?.content ?? fallbackTextContent) || '';
  const interactiveViewerRaw = textPreview?.raw ?? fallbackTextContent;
  const canRenderInteractiveViewer =
    Boolean(resolvedActiveTextChunk) || interactiveViewerContent.trim().length > 0;
  const {
    isInteractiveFullscreen,
    handleInteractiveFullscreenToggle,
    handleExitInteractiveFullscreen,
    resetInteractiveFullscreen,
  } = useInteractiveFullscreenPreference({
    canRenderInteractiveViewer,
    hasInteractiveChunks,
  });
  const shouldForceInteractiveViewer = isInteractiveFullscreen;
  const hasTextItems = media.text.length > 0;
  const shouldShowInteractiveViewer = canRenderInteractiveViewer || shouldForceInteractiveViewer;
  const shouldShowEmptySelectionPlaceholder =
    hasTextItems && !selectedItem && !shouldForceInteractiveViewer;
  const shouldShowLoadingPlaceholder =
    Boolean(textLoading && selectedItem && !shouldForceInteractiveViewer);
  const shouldShowStandaloneError = Boolean(textError) && !shouldForceInteractiveViewer;
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

  const {
    isFirstDisabled,
    isPreviousDisabled,
    isNextDisabled,
    isLastDisabled,
    handleNavigatePreservingPlayback,
  } = usePlayerPanelNavigation({
    mediaText: media.text,
    selectedTextId: selectedItemIds.text,
    chunks,
    activeTextChunkIndex,
    activateTextItem,
    activateChunk,
    updateSelection,
    inlineAudioPlayingRef,
  });

  const handlePanelAdvancedControlsToggle = useCallback(() => {
    setPanelAdvancedControlsOpen((value) => !value);
  }, []);
  const handleMediaSessionSentenceSkip = useCallback(
    (direction: -1 | 1) => {
      if (!canJumpToSentence) {
        return false;
      }
      const fallback = direction > 0 ? jobStartSentence : null;
      const current = activeSentenceNumber ?? fallback;
      if (!current || !Number.isFinite(current)) {
        return false;
      }
      const target = Math.trunc(current) + direction;
      if (jobStartSentence !== null && target < jobStartSentence) {
        return false;
      }
      if (jobEndSentence !== null && target > jobEndSentence) {
        return false;
      }
      handleInteractiveSentenceJump(target);
      return true;
    },
    [
      activeSentenceNumber,
      canJumpToSentence,
      handleInteractiveSentenceJump,
      jobEndSentence,
      jobStartSentence,
    ],
  );
  const handleMediaSessionTrackSkip = useCallback(
    (direction: -1 | 1) => {
      if (handleMediaSessionSentenceSkip(direction)) {
        return;
      }
      handleNavigatePreservingPlayback(direction > 0 ? 'next' : 'previous');
    },
    [handleMediaSessionSentenceSkip, handleNavigatePreservingPlayback],
  );
  const handleMediaSessionSeekTo = useCallback(
    (details: MediaSessionActionDetails) => {
      const seekTime =
        typeof details.seekTime === 'number' && Number.isFinite(details.seekTime)
          ? details.seekTime
          : null;
      const current = mediaSessionTimeRef.current;
      if (seekTime === null || current === null || !Number.isFinite(current)) {
        return;
      }
      if (Math.abs(seekTime - current) < 0.25) {
        return;
      }
      handleMediaSessionTrackSkip(seekTime > current ? 1 : -1);
    },
    [handleMediaSessionTrackSkip],
  );

  useMediaSessionActions({
    inlineAudioSelection,
    onPlay: handlePlayActiveMedia,
    onPause: handlePauseActiveMedia,
    onTrackSkip: handleMediaSessionTrackSkip,
    onSeekTo: handleMediaSessionSeekTo,
  });

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
  const { handleTextScroll } = usePlayerPanelScrollMemory({
    textScrollRef,
    activeTextId: selectedItemIds.text,
    pendingTextScrollRatio,
    setPendingTextScrollRatio,
    textPlaybackPosition,
    textPreviewUrl: textPreview?.url ?? null,
    getMediaItem,
    deriveBaseId,
    rememberPosition,
  });

  useEffect(() => {
    if (!selectionRequest?.autoPlay) {
      return;
    }
    requestAutoPlay();
  }, [requestAutoPlay, selectionRequest?.autoPlay, selectionRequest?.token]);

  useEffect(() => {
    resetInteractiveFullscreen();
    setPendingSelection(null);
    setPendingChunkSelection(null);
    setPendingTextScrollRatio(null);
  }, [normalisedJobId, resetInteractiveFullscreen]);

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

  const exportState = usePlayerPanelExport({
    jobId,
    origin,
    playerMode,
    isBookLike,
    mediaComplete,
    hasInteractiveChunks,
    hasTextItems,
  });
  const hasAnyMedia = media.text.length + media.audio.length + media.video.length > 0;
  const interactiveFontScale = fontScalePercent / 100;

  useMediaSessionMetadata({
    inlineAudioSelection,
    isActiveMediaPlaying,
    activeSentenceNumber,
    jobEndSentence,
    bookTitle,
    bookAuthor,
    subtitleInfo,
    isSubtitleContext,
    displayCoverUrl,
    shouldShowCoverImage,
  });

  const interactiveFullscreenLabel = isInteractiveFullscreen ? 'Exit fullscreen' : 'Enter fullscreen';
  const sentenceJumpListId = useId();
  const sentenceJumpInputId = useId();
  const sentenceJumpInputFullscreenId = useId();
  const sentenceJumpDatalist =
    sentenceLookup.suggestions.length > 0 ? (
      <datalist id={sentenceJumpListId}>
        {sentenceLookup.suggestions.map((value) => (
          <option key={value} value={value} />
        ))}
      </datalist>
    ) : null;

  const shouldShowBackToLibrary = origin === 'library' && showBackToLibrary;
  const panelSearchPanel =
    searchEnabled && !isInteractiveFullscreen ? (
      <MediaSearchPanel currentJobId={jobId} onResultAction={handleSearchSelection} variant="compact" />
    ) : null;
  const fullscreenSearchPanel =
    searchEnabled && isInteractiveFullscreen ? (
      <MediaSearchPanel currentJobId={jobId} onResultAction={handleSearchSelection} variant="compact" />
    ) : null;
  const chapterScopeStart = jobScopeStartSentence ?? jobStartSentence;
  const chapterScopeEnd = jobScopeEndSentence ?? jobEndSentence;

  const navigationBaseProps = buildNavigationBaseProps({
    navigation: {
      onNavigate: handleNavigatePreservingPlayback,
      onToggleFullscreen: handleInteractiveFullscreenToggle,
      onTogglePlayback: handleToggleActiveMedia,
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
    },
    sentenceNavigation,
    textSettings: interactiveTextSettings,
    myLinguist: {
      enabled: linguistEnabled,
      baseFontScalePercent,
      setBaseFontScalePercent,
    },
    inlineAudioOptions,
    readingBedControls,
    chapters: {
      chapterEntries,
      activeChapterId,
      onChapterJump: handleChapterJump,
    },
    bookmarks: {
      showBookmarks: Boolean(jobId),
      bookmarks,
      onAddBookmark: handleAddBookmark,
      onJumpToBookmark: handleJumpBookmark,
      onRemoveBookmark: handleRemoveBookmark,
    },
    exportState,
    sentenceJumpListId,
    sentenceTotals: {
      activeSentenceNumber,
      chapterScopeStart,
      chapterScopeEnd,
      bookSentenceCount,
    },
    onResetLayout: handleResetInteractiveLayout,
  });
  const hasPanelAdvancedControls = Boolean(
    navigationBaseProps.showTranslationSpeed ||
      navigationBaseProps.showSubtitleScale ||
      navigationBaseProps.showSubtitleBackgroundOpacity ||
      navigationBaseProps.showFontScale ||
      navigationBaseProps.showMyLinguistFontScale ||
      navigationBaseProps.showInteractiveBackgroundOpacity ||
      navigationBaseProps.showInteractiveSentenceCardOpacity ||
      navigationBaseProps.showInteractiveThemeControls ||
      navigationBaseProps.showReadingBedVolume ||
      navigationBaseProps.showReadingBedTrack,
  );

  const navigationGroup = (
    <NavigationControls
      context="panel"
      sentenceJumpInputId={sentenceJumpInputId}
      searchPanel={panelSearchPanel}
      {...navigationBaseProps}
      showAdvancedControls={panelAdvancedControlsOpen && hasPanelAdvancedControls}
      showAdvancedToggle={hasPanelAdvancedControls}
      advancedControlsOpen={panelAdvancedControlsOpen}
      onToggleAdvancedControls={hasPanelAdvancedControls ? handlePanelAdvancedControlsToggle : undefined}
    />
  );

  const fullscreenMainControls = isInteractiveFullscreen ? (
    <NavigationControls
      context="fullscreen"
      sentenceJumpInputId={sentenceJumpInputFullscreenId}
      showPrimaryControls
      showAdvancedControls={false}
      searchPanel={fullscreenSearchPanel}
      {...navigationBaseProps}
    />
  ) : null;

  const fullscreenAdvancedControls = isInteractiveFullscreen ? (
    <NavigationControls
      context="fullscreen"
      sentenceJumpInputId={sentenceJumpInputFullscreenId}
      showPrimaryControls={false}
      showAdvancedControls
      {...navigationBaseProps}
    />
  ) : null;

  const interactiveViewerProps = buildInteractiveViewerProps({
    core: {
      playerMode,
      playerFeatures: {
        linguist: linguistEnabled,
        painter: painterEnabled,
      },
      content: interactiveViewerContent,
      rawContent: interactiveViewerRaw,
      chunk: resolvedActiveTextChunk,
      chunks,
      activeChunkIndex: activeTextChunkIndex,
      bookSentenceCount,
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
    },
    fullscreen: {
      isFullscreen: isInteractiveFullscreen,
      onRequestExitFullscreen: handleExitInteractiveFullscreen,
      fullscreenControls: isInteractiveFullscreen ? fullscreenMainControls : null,
      fullscreenAdvancedControls: isInteractiveFullscreen ? fullscreenAdvancedControls : null,
      shortcutHelpOverlay: isInteractiveFullscreen ? shortcutHelpOverlay : null,
    },
    playback: {
      translationSpeed,
      audioTracks: activeAudioTracks,
      activeTimingTrack,
      originalAudioEnabled: effectiveOriginalAudioEnabled,
      translationAudioEnabled: effectiveTranslationAudioEnabled,
    },
    appearance: {
      fontScale: interactiveFontScale,
      theme: interactiveTextTheme,
      backgroundOpacityPercent: interactiveBackgroundOpacityPercent,
      sentenceCardOpacityPercent: interactiveSentenceCardOpacityPercent,
    },
    info: {
      channelBug,
      isSubtitleContext,
      subtitleInfo,
    },
    book: {
      bookTitle,
      bookAuthor,
      bookYear,
      bookGenre,
      displayCoverUrl,
      coverAltText,
      shouldShowCoverImage,
    },
  });

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
          {isInteractiveFullscreen ? null : shortcutHelpOverlay}
        </>
      }
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
