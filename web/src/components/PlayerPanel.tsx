import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { LiveMediaChunk, LiveMediaState } from '../hooks/useLiveMedia';
import { useMediaMemory } from '../hooks/useMediaMemory';
import { usePlaybackBookmarks } from '../hooks/usePlaybackBookmarks';
import { useWakeLock } from '../hooks/useWakeLock';
import { useMyLinguist } from '../context/MyLinguistProvider';
import {
  DEFAULT_MY_LINGUIST_FONT_SCALE_PERCENT,
  MY_LINGUIST_FONT_SCALE_STEP,
} from './player-panel/constants';
import type { LibraryItem } from '../api/dtos';
import { PlayerPanelBoundaryState } from './player-panel/PlayerPanelBoundaryState';
import { PlayerPanelContent } from './player-panel/PlayerPanelContent';
import { PlayerPanelInteractiveDocument } from './player-panel/PlayerPanelInteractiveDocument';
import { buildPlayerPanelSearchSlots } from './player-panel/PlayerPanelSearchSlot';
import { PlayerPanelSentenceJumpDatalist } from './player-panel/PlayerPanelSentenceJumpDatalist';
import {
  fallbackTextFromSentences,
} from './player-panel/utils';
import { enableDebugOverlay } from '../player/AudioSyncController';
import type { LibraryOpenInput, MediaSelectionRequest, PlayerFeatureFlags, PlayerMode } from '../types/player';
import { PlayerPanelShell } from './player-panel/PlayerPanelShell';
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
import { buildInteractiveViewerProps } from './player-panel/playerPanelProps';
import { useInteractiveFullscreenPreference } from './player-panel/useInteractiveFullscreenPreference';
import { usePlayerPanelScrollMemory } from './player-panel/usePlayerPanelScrollMemory';
import { usePlayerPanelMediaNavigation } from './player-panel/usePlayerPanelMediaNavigation';
import { usePlayerPanelChapterNavigation } from './player-panel/usePlayerPanelChapterNavigation';
import { useAudioTrackVisibility } from './player-panel/useAudioTrackVisibility';
import { usePlayerPanelActiveText } from './player-panel/usePlayerPanelActiveText';
import { usePlayerPanelTextActivation } from './player-panel/usePlayerPanelTextActivation';
import { usePendingChunkSelection } from './player-panel/usePendingChunkSelection';
import { SleepTimerControl } from './SleepTimerControl';
import {
  buildPlayerPanelDocumentState,
  resolveInteractiveViewerRenderability,
} from './player-panel/playerPanelDocumentState';
import {
  buildPlayerPanelChromeState,
} from './player-panel/playerPanelChromeState';
import { usePlayerPanelNavigationChrome } from './player-panel/usePlayerPanelNavigationChrome';

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
  mediaMetadata?: Record<string, unknown> | null;
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
  mediaMetadata = null,
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
  const {
    showOriginalAudio,
    setShowOriginalAudio,
    showTranslationAudio,
    setShowTranslationAudio,
  } = useAudioTrackVisibility();
  const [inlineAudioSelection, setInlineAudioSelection] = useState<string | null>(null);
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
    pauseReadingBed,
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
    mediaMetadata,
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

  const handleSleepTimerExpired = useCallback(() => {
    handlePauseActiveMedia();
    pauseReadingBed();
  }, [handlePauseActiveMedia, pauseReadingBed]);

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

  const { activeChapterId, handleChapterJump } = usePlayerPanelChapterNavigation({
    activeSentenceNumber,
    chapterEntries,
    onInteractiveSentenceJump: handleInteractiveSentenceJump,
  });

  useEffect(() => {
    if (import.meta.env.DEV) {
      return enableDebugOverlay();
    }
    return undefined;
  }, []);

  const { coverUrl: displayCoverUrl, shouldShowCoverImage } = useCoverArt({
    jobId,
    origin,
    mediaMetadata,
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
  const allowTextPreview =
    playerMode !== 'export' || (typeof window !== 'undefined' && window.location.protocol !== 'file:');
  const {
    selectedItem,
    selectedChunk,
    interactiveAudioPlaylist,
    interactiveAudioNameMap,
    audioChunkIndexMap,
    activeTextChunk,
    activeTextChunkIndex,
  } = usePlayerPanelActiveText({
    textItems: media.text,
    audioItems: media.audio,
    chunks,
    selectedTextId: selectedItemId,
    selectedAudioId: selectedItemIds.audio,
    inlineAudioSelection,
  });
  const { textPreview, textLoading, textError } = useTextPreview(selectedItem?.url, {
    enabled: allowTextPreview,
  });
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
  const canRenderInteractiveViewer = resolveInteractiveViewerRenderability({
    previewContent: textPreview?.content,
    fallbackTextContent,
    resolvedActiveTextChunk,
  });
  const {
    isInteractiveFullscreen,
    handleInteractiveFullscreenToggle,
    handleExitInteractiveFullscreen,
    resetInteractiveFullscreen,
  } = useInteractiveFullscreenPreference({
    canRenderInteractiveViewer,
    hasInteractiveChunks,
  });
  const {
    hasAnyMedia,
    hasTextItems,
    isInitialLoading,
    playbackControlsAvailable,
    isActiveMediaPlaying,
    shouldHoldWakeLock,
    isPlaybackDisabled,
    isFullscreenDisabled,
    shouldShowBackToLibrary,
  } = buildPlayerPanelChromeState({
    mediaTextCount: media.text.length,
    mediaAudioCount: media.audio.length,
    mediaVideoCount: media.video.length,
    isLoading,
    hasInlineAudioControls,
    canRenderInteractiveViewer,
    isInlineAudioPlaying,
    origin,
    showBackToLibrary,
  });
  const {
    interactiveViewerContent,
    interactiveViewerRaw,
    shouldShowInteractiveViewer,
    shouldShowEmptySelectionPlaceholder,
    shouldShowLoadingPlaceholder,
    shouldShowStandaloneError,
  } = buildPlayerPanelDocumentState({
    textPreview,
    fallbackTextContent,
    resolvedActiveTextChunk,
    isInteractiveFullscreen,
    hasTextItems,
    hasSelectedItem: Boolean(selectedItem),
    textLoading,
    textError,
  });
  useWakeLock(shouldHoldWakeLock);

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

  const activateTextItem = usePlayerPanelTextActivation({
    chunks,
    deriveBaseId,
    activateChunk,
    setSelectedItemIds,
    setPendingTextScrollRatio,
    requestAutoPlay,
  });

  usePendingChunkSelection({
    chunks,
    pendingChunkSelection,
    setPendingChunkSelection,
    activateChunk,
  });

  const {
    isFirstDisabled,
    isPreviousDisabled: isChunkPreviousDisabled,
    isNextDisabled: isChunkNextDisabled,
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

  const {
    hasSentenceNav,
    handleRegisterSequenceSkip,
    handleKeyboardNavigate,
    handleMediaSessionTrackSkip,
    handleMediaSessionSeekTo,
  } = usePlayerPanelMediaNavigation({
    activeSentenceNumber,
    canJumpToSentence,
    jobStartSentence,
    jobEndSentence,
    mediaSessionTimeRef,
    onInteractiveSentenceJump: handleInteractiveSentenceJump,
    onNavigatePreservingPlayback: handleNavigatePreservingPlayback,
  });

  // When sentence-level navigation is possible, next/previous should not be
  // disabled just because we're at a chunk boundary — there may be more
  // sentences to skip to (within the current chunk or across chunks).
  const isPreviousDisabled = hasSentenceNav ? false : isChunkPreviousDisabled;
  const isNextDisabled = hasSentenceNav ? false : isChunkNextDisabled;

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
    onNavigate: handleKeyboardNavigate,
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
  const { panelSearchPanel, fullscreenSearchPanel } = buildPlayerPanelSearchSlots({
    currentJobId: jobId,
    enabled: searchEnabled,
    isFullscreen: isInteractiveFullscreen,
    onResultAction: handleSearchSelection,
  });
  const chapterScopeStart = jobScopeStartSentence ?? jobStartSentence;
  const chapterScopeEnd = jobScopeEndSentence ?? jobEndSentence;

  const {
    panelNavigation,
    fullscreenMainControls,
    fullscreenAdvancedControls,
    sentenceJumpListId,
  } = usePlayerPanelNavigationChrome({
    navigation: {
      onNavigate: handleKeyboardNavigate,
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
    sentenceTotals: {
      activeSentenceNumber,
      chapterScopeStart,
      chapterScopeEnd,
      bookSentenceCount,
    },
    onResetLayout: handleResetInteractiveLayout,
    sleepTimerControl: (
      <SleepTimerControl
        onExpire={handleSleepTimerExpired}
        resetKey={normalisedJobId}
      />
    ),
    panelSearchPanel,
    fullscreenSearchPanel,
  });
  const sentenceJumpDatalist = (
    <PlayerPanelSentenceJumpDatalist id={sentenceJumpListId} suggestions={sentenceLookup.suggestions} />
  );

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
      onToggleCueVisibility: handleToggleInteractiveTextLayer,
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
      onRegisterSequenceSkip: handleRegisterSequenceSkip,
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

  if (error || isInitialLoading || !hasJobId) {
    return (
      <PlayerPanelBoundaryState
        sectionLabel={sectionLabel}
        error={error}
        isInitialLoading={isInitialLoading}
        loadingMessage={loadingMessage}
        hasJobId={hasJobId}
        noJobPrelude={
          <>
            {sentenceJumpDatalist}
            {shortcutHelpOverlay}
          </>
        }
      />
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
      toolbar={panelNavigation}
    >
      <PlayerPanelContent
        hasAnyMedia={hasAnyMedia}
        isLoading={isLoading}
        emptyMediaMessage={emptyMediaMessage}
        hasTextItems={hasTextItems}
        hasInteractiveChunks={hasInteractiveChunks}
        mediaComplete={mediaComplete}
      >
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
      </PlayerPanelContent>
    </PlayerPanelShell>
  );
}
