import { useCallback, useEffect, useMemo, useState } from 'react';
import type { LiveMediaItem, LiveMediaState } from '../hooks/useLiveMedia';
import { useMediaMemory } from '../hooks/useMediaMemory';
import { formatBookmarkTime, usePlaybackBookmarks } from '../hooks/usePlaybackBookmarks';
import { useSubtitlePreferences } from '../hooks/useSubtitlePreferences';
import { useYoutubeKeyboardShortcuts } from '../hooks/useYoutubeKeyboardShortcuts';
import VideoPlayer from './VideoPlayer';
import { NavigationControls } from './player-panel/NavigationControls';
import MediaSearchPanel from './MediaSearchPanel';
import { PlayerPanelShell } from './player-panel/PlayerPanelShell';
import {
  appendAccessToken,
  createExport,
  withBase,
} from '../api/client';
import {
  FONT_SCALE_STEP,
  MY_LINGUIST_FONT_SCALE_STEP,
  TRANSLATION_SPEED_MAX,
  TRANSLATION_SPEED_MIN,
  TRANSLATION_SPEED_STEP,
} from './player-panel/constants';
import { buildMediaFileId, resolveBaseIdFromResult, toVideoFiles } from './player-panel/utils';
import type {
  LibraryItem,
  MediaSearchResult,
} from '../api/dtos';
import { coerceExportPath } from '../utils/storageResolver';
import { downloadWithSaveAs } from '../utils/downloads';
import { extractJobType } from '../utils/jobGlyphs';
import type { ExportPlayerManifest } from '../types/exportPlayer';
import { useMyLinguist } from '../context/MyLinguistProvider';
import { useYoutubeMetadata } from './youtube-player/useYoutubeMetadata';
import { useInfoBadge } from './youtube-player/useInfoBadge';
import { useSubtitleTracks } from './youtube-player/useSubtitleTracks';
import { useVideoPlaybackState } from './youtube-player/useVideoPlaybackState';


interface YoutubeDubPlayerProps {
  jobId: string;
  media: LiveMediaState;
  mediaComplete: boolean;
  isLoading: boolean;
  error: Error | null;
  jobType?: string | null;
  playerMode?: 'online' | 'export';
  onFullscreenChange?: (isFullscreen: boolean) => void;
  onPlaybackStateChange?: (isPlaying: boolean) => void;
  onVideoPlaybackStateChange?: (isPlaying: boolean) => void;
  showBackToLibrary?: boolean;
  onBackToLibrary?: () => void;
  libraryItem?: LibraryItem | null;
  mediaMetadata?: Record<string, unknown> | null;
}

const SUBTITLE_SCALE_STEP = FONT_SCALE_STEP / 100;
const FULLSCREEN_LINGUIST_SCALE_MULTIPLIER = 1.25;

export default function YoutubeDubPlayer({
  jobId,
  media,
  mediaComplete,
  isLoading,
  error,
  jobType = null,
  playerMode = 'online',
  onFullscreenChange,
  onPlaybackStateChange,
  onVideoPlaybackStateChange,
  showBackToLibrary = false,
  onBackToLibrary,
  libraryItem = null,
  mediaMetadata = null,
}: YoutubeDubPlayerProps) {
  const isExportMode = playerMode === 'export';
  const { adjustBaseFontScalePercent, baseFontScalePercent } = useMyLinguist();
  const resolvedJobType = useMemo(() => jobType ?? extractJobType(mediaMetadata) ?? null, [mediaMetadata, jobType]);
  const inlineSubtitles = useMemo(() => {
    if (!isExportMode || typeof window === 'undefined') {
      return null;
    }
    const candidate = (window as Window & { __EXPORT_DATA__?: unknown }).__EXPORT_DATA__;
    if (!candidate || typeof candidate !== 'object') {
      return null;
    }
    const manifest = candidate as ExportPlayerManifest;
    if (!manifest.inline_subtitles || typeof manifest.inline_subtitles !== 'object') {
      return null;
    }
    return manifest.inline_subtitles as Record<string, string>;
  }, [isExportMode]);
  const resolveMediaUrl = useCallback(
    (url: string) => {
      if (isExportMode) {
        return coerceExportPath(url, jobId) ?? url;
      }
      return appendAccessToken(url);
    },
    [appendAccessToken, isExportMode, jobId],
  );
  // Metadata fetching and resolution via hook
  const {
    jobTvMetadata,
    jobYoutubeMetadata,
    exportTvMetadata,
    exportYoutubeMetadata,
    jobOriginalLanguage,
    jobTranslationLanguage,
  } = useYoutubeMetadata({
    jobId,
    libraryItem,
    mediaMetadata,
    isExportMode,
  });

  const videoLookup = useMemo(() => {
    const map = new Map<string, LiveMediaItem>();
    media.video.forEach((item, index) => {
      if (typeof item.url !== 'string' || item.url.length === 0) {
        return;
      }
      const id = buildMediaFileId(item, index);
      map.set(id, item);
    });
    return map;
  }, [media.video]);
  const videoFiles = useMemo(
    () =>
      toVideoFiles(media.video).map((file) => {
        const urlWithToken = resolveMediaUrl(file.url);
        return {
          ...file,
          url: urlWithToken,
        };
      }),
    [media.video, resolveMediaUrl],
  );
  const { state: memoryState, rememberSelection, rememberPosition, getPosition, deriveBaseId } = useMediaMemory({
    jobId,
  });
  const { bookmarks, addBookmark, removeBookmark } = usePlaybackBookmarks({ jobId });

  // Subtitle track resolution via hook
  const { getActiveSubtitleTracks } = useSubtitleTracks({
    jobId,
    isExportMode,
    inlineSubtitles,
    videoItems: media.video,
    textItems: media.text,
    resolveMediaUrl,
    deriveBaseId,
  });

  // Video playback state via hook
  const {
    activeVideoId,
    setActiveVideoId,
    isPlaying,
    isFullscreen,
    playbackSpeed,
    controlsRef,
    playbackPosition,
    localPositionRef,
    pendingBookmarkSeekRef,
    navigationState,
    handleNavigate,
    handleTogglePlayback,
    handlePlaybackStateChange,
    handlePlaybackEnded,
    handleToggleFullscreen,
    handleExitFullscreen,
    handleRegisterControls,
    handlePlaybackRateChange,
    adjustPlaybackSpeed,
    handlePlaybackPositionChange,
    resetPlaybackPosition,
    applyBookmarkSeek,
  } = useVideoPlaybackState({
    videoFiles,
    videoLookup,
    memoryState,
    rememberSelection,
    rememberPosition,
    getPosition,
    deriveBaseId,
    onFullscreenChange,
    onPlaybackStateChange,
    onVideoPlaybackStateChange,
  });

  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  // Subtitle preferences (consolidated hook with localStorage persistence)
  const {
    subtitlesEnabled,
    setSubtitlesEnabled,
    toggleSubtitles: handleSubtitleToggle,
    cueVisibility,
    toggleCueVisibility,
    subtitleScale,
    fullscreenSubtitleScale,
    setSubtitleScale,
    setFullscreenSubtitleScale,
    adjustSubtitleScale: adjustSubtitleScaleRaw,
    subtitleBackgroundOpacityPercent,
    setSubtitleBackgroundOpacityPercent,
    getActiveScale,
    getActiveScaleMin,
    getActiveScaleMax,
    constants: subtitleConstants,
  } = useSubtitlePreferences({ jobId });

  // Get active subtitle tracks using the hook
  const activeSubtitleTracks = useMemo(
    () => getActiveSubtitleTracks(activeVideoId, videoFiles),
    [activeVideoId, getActiveSubtitleTracks, videoFiles],
  );

  // Info badge (title, cover, metadata) via hook
  const infoBadge = useInfoBadge({
    jobId,
    activeVideoId,
    videoFiles,
    libraryItem,
    resolvedJobType,
    jobTvMetadata,
    jobYoutubeMetadata,
    exportTvMetadata,
    exportYoutubeMetadata,
  });

  useEffect(() => {
    if (activeSubtitleTracks.length > 0 || media.text.length > 0) {
      // Helpful runtime visibility into subtitle selection/resolution.
      console.debug('Subtitle tracks attached', {
        activeVideoId,
        trackCount: activeSubtitleTracks.length,
        sample: activeSubtitleTracks[0],
        textEntries: media.text.length,
      });
    }
  }, [activeSubtitleTracks, activeVideoId, media.text.length]);

  // Wrapper for adjustSubtitleScale that passes isFullscreen
  const adjustSubtitleScale = useCallback(
    (direction: 'increase' | 'decrease') => {
      adjustSubtitleScaleRaw(direction, isFullscreen, SUBTITLE_SCALE_STEP);
    },
    [adjustSubtitleScaleRaw, isFullscreen]
  );

  // Keyboard shortcuts (navigation, playback, subtitle controls)
  useYoutubeKeyboardShortcuts({
    handlers: {
      onNavigate: handleNavigate,
      onToggleFullscreen: handleToggleFullscreen,
      onTogglePlayback: handleTogglePlayback,
      adjustPlaybackSpeed,
      adjustSubtitleScale,
      toggleCueVisibility,
      adjustBaseFontScalePercent,
    },
    fontScaleStep: MY_LINGUIST_FONT_SCALE_STEP,
  });

  const handleAddBookmark = useCallback(() => {
    if (!jobId || !activeVideoId) {
      return;
    }
    const activeIndex = videoFiles.findIndex((file) => file.id === activeVideoId);
    const activeLabel = videoFiles[activeIndex]?.name ?? (activeIndex >= 0 ? `Segment ${activeIndex + 1}` : null);
    const fallbackPosition = getPosition(activeVideoId);
    const position = Number.isFinite(localPositionRef.current) ? localPositionRef.current : fallbackPosition;
    const labelParts: string[] = [];
    if (videoFiles.length > 1 && activeLabel) {
      labelParts.push(activeLabel);
    }
    if (Number.isFinite(position)) {
      labelParts.push(formatBookmarkTime(position));
    }
    const label = labelParts.length > 0 ? labelParts.join(' · ') : 'Bookmark';
    const match = videoLookup.get(activeVideoId) ?? null;
    const baseId = match ? deriveBaseId(match) : null;
    addBookmark({
      kind: 'time',
      label,
      position,
      mediaType: 'video',
      mediaId: activeVideoId,
      baseId,
    });
  }, [activeVideoId, addBookmark, deriveBaseId, getPosition, jobId, videoFiles, videoLookup]);

  const resolveSearchVideoId = useCallback(
    (result: MediaSearchResult): string | null => {
      const candidates = Array.isArray(result.media?.video) ? result.media.video : [];
      for (let index = 0; index < candidates.length; index += 1) {
        const entry = candidates[index];
        if (!entry) {
          continue;
        }
        const candidateId = buildMediaFileId({ ...entry, type: 'video' }, index);
        if (videoLookup.has(candidateId)) {
          return candidateId;
        }
      }
      const baseId = resolveBaseIdFromResult(result, 'video');
      if (!baseId) {
        return null;
      }
      for (const [candidateId, item] of videoLookup) {
        const itemBaseId = deriveBaseId(item);
        if (itemBaseId && itemBaseId === baseId) {
          return candidateId;
        }
      }
      return null;
    },
    [deriveBaseId, videoLookup],
  );

  const handleSearchSelection = useCallback(
    (result: MediaSearchResult) => {
      if (!jobId || result.job_id !== jobId) {
        return;
      }
      const timeValue = result.approximate_time_seconds;
      if (typeof timeValue !== 'number' || !Number.isFinite(timeValue)) {
        return;
      }
      const clamped = Math.max(timeValue, 0);
      const resolvedId = resolveSearchVideoId(result) ?? activeVideoId ?? videoFiles[0]?.id ?? null;
      if (!resolvedId) {
        return;
      }
      if (resolvedId === activeVideoId) {
        applyBookmarkSeek(resolvedId, clamped);
        return;
      }
      pendingBookmarkSeekRef.current = { videoId: resolvedId, time: clamped };
      setActiveVideoId(resolvedId);
    },
    [activeVideoId, applyBookmarkSeek, jobId, resolveSearchVideoId, videoFiles],
  );

  const handleSearchResultAction = useCallback(
    (result: MediaSearchResult, category: 'text' | 'video' | 'library') => {
      if (category === 'library') {
        return;
      }
      handleSearchSelection(result);
    },
    [handleSearchSelection],
  );

  const handleJumpBookmark = useCallback(
    (bookmark: { mediaId?: string | null; position?: number | null }) => {
      const targetVideoId = bookmark.mediaId ?? activeVideoId;
      if (!targetVideoId) {
        return;
      }
      const targetTime =
        typeof bookmark.position === 'number' && Number.isFinite(bookmark.position) ? bookmark.position : 0;
      if (targetVideoId === activeVideoId) {
        applyBookmarkSeek(targetVideoId, targetTime);
        return;
      }
      pendingBookmarkSeekRef.current = { videoId: targetVideoId, time: targetTime };
      setActiveVideoId(targetVideoId);
    },
    [activeVideoId, applyBookmarkSeek],
  );

  const handleRemoveBookmark = useCallback(
    (bookmark: { id: string }) => {
      removeBookmark(bookmark.id);
    },
    [removeBookmark],
  );

  const {
    disableFirst,
    disablePrevious,
    disableNext,
    disableLast,
    disablePlayback,
    disableFullscreen,
    currentIndex,
    videoCount,
  } = navigationState;
  const canExport = !isExportMode && mediaComplete && videoCount > 0;
  const searchEnabled = !isExportMode;
  const exportSourceKind = libraryItem ? 'library' : 'job';
  const activeSubtitleScale = getActiveScale(isFullscreen);
  const activeSubtitleScaleMin = getActiveScaleMin(isFullscreen);
  const activeSubtitleScaleMax = getActiveScaleMax(isFullscreen);
  const resolvedLinguistScale = useMemo(() => {
    const base = baseFontScalePercent / 100;
    const multiplier = isFullscreen ? FULLSCREEN_LINGUIST_SCALE_MULTIPLIER : 1;
    return Math.round(base * multiplier * 1000) / 1000;
  }, [baseFontScalePercent, isFullscreen]);

  const handleExport = useCallback(async () => {
    if (!jobId || isExporting || !canExport) {
      return;
    }
    setIsExporting(true);
    setExportError(null);
    const payload = {
      source_kind: exportSourceKind,
      source_id: jobId,
      player_type: 'interactive-text',
    } as const;
    try {
      const result = await createExport(payload);
      const resolved =
        result.download_url.startsWith('http://') || result.download_url.startsWith('https://')
          ? result.download_url
          : withBase(result.download_url);
      const downloadUrl = appendAccessToken(resolved);
      await downloadWithSaveAs(downloadUrl, result.filename ?? null);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Unable to export offline player.';
      setExportError(message);
    } finally {
      setIsExporting(false);
    }
  }, [appendAccessToken, canExport, createExport, downloadWithSaveAs, exportSourceKind, isExporting, jobId, withBase]);

  const handleTranslationSpeedChange = useCallback(
    (value: number) => {
      handlePlaybackRateChange(value);
    },
    [handlePlaybackRateChange],
  );
  const handleSubtitleScaleChange = useCallback(
    (value: number) => {
      if (!Number.isFinite(value)) {
        return;
      }
      const min = getActiveScaleMin(isFullscreen);
      const max = getActiveScaleMax(isFullscreen);
      const clamped = Math.min(Math.max(value, min), max);
      if (isFullscreen) {
        setFullscreenSubtitleScale(clamped);
      } else {
        setSubtitleScale(clamped);
      }
    },
    [getActiveScaleMax, getActiveScaleMin, isFullscreen, setFullscreenSubtitleScale, setSubtitleScale],
  );
  const handleSubtitleBackgroundOpacityChange = useCallback((value: number) => {
    if (!Number.isFinite(value)) {
      return;
    }
    const clamped = Math.min(Math.max(value, 0), 100);
    const snapped = Math.round(clamped / 10) * 10;
    setSubtitleBackgroundOpacityPercent(snapped);
  }, [setSubtitleBackgroundOpacityPercent]);

  const searchPanel = searchEnabled ? (
    <MediaSearchPanel currentJobId={jobId} onResultAction={handleSearchResultAction} variant="compact" />
  ) : null;

  if (error) {
    return (
      <div className="player-panel" role="region" aria-label={`YouTube dub ${jobId}`}>
        <p role="alert">Unable to load generated media: {error.message}</p>
      </div>
    );
  }

  return (
    <PlayerPanelShell
      ariaLabel={`YouTube dub ${jobId}`}
      toolbar={
        <NavigationControls
          context="panel"
          controlsLayout="compact"
          onNavigate={handleNavigate}
          onToggleFullscreen={handleToggleFullscreen}
          onTogglePlayback={handleTogglePlayback}
          disableFirst={disableFirst}
          disablePrevious={disablePrevious}
          disableNext={disableNext}
          disableLast={disableLast}
          disablePlayback={disablePlayback}
          disableFullscreen={disableFullscreen}
          isFullscreen={isFullscreen}
          isPlaying={isPlaying}
          fullscreenLabel={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          nowPlayingText={
            videoCount > 0 && currentIndex >= 0 ? `Video ${currentIndex + 1} of ${videoCount}` : null
          }
          showSubtitleToggle
          onToggleSubtitles={handleSubtitleToggle}
          subtitlesEnabled={subtitlesEnabled}
          disableSubtitleToggle={videoCount === 0}
          showCueLayerToggles
          cueVisibility={cueVisibility}
          onToggleCueLayer={toggleCueVisibility}
          disableCueLayerToggles={videoCount === 0 || !subtitlesEnabled}
          showTranslationSpeed
          translationSpeed={playbackSpeed}
          translationSpeedMin={TRANSLATION_SPEED_MIN}
          translationSpeedMax={TRANSLATION_SPEED_MAX}
          translationSpeedStep={TRANSLATION_SPEED_STEP}
          onTranslationSpeedChange={handleTranslationSpeedChange}
          showSubtitleScale
          subtitleScale={activeSubtitleScale}
          subtitleScaleMin={activeSubtitleScaleMin}
          subtitleScaleMax={activeSubtitleScaleMax}
          subtitleScaleStep={SUBTITLE_SCALE_STEP}
          onSubtitleScaleChange={handleSubtitleScaleChange}
          showSubtitleBackgroundOpacity
          subtitleBackgroundOpacityPercent={subtitleBackgroundOpacityPercent}
          subtitleBackgroundOpacityMin={0}
          subtitleBackgroundOpacityMax={100}
          subtitleBackgroundOpacityStep={10}
          onSubtitleBackgroundOpacityChange={handleSubtitleBackgroundOpacityChange}
          showBackToLibrary={showBackToLibrary}
          onBackToLibrary={onBackToLibrary}
          showBookmarks={Boolean(jobId)}
          bookmarks={bookmarks}
          onAddBookmark={activeVideoId ? handleAddBookmark : undefined}
          onJumpToBookmark={handleJumpBookmark}
          onRemoveBookmark={handleRemoveBookmark}
          showExport={canExport}
          onExport={handleExport}
          exportDisabled={isExporting}
          exportBusy={isExporting}
          exportLabel={isExporting ? 'Preparing export' : 'Export offline player'}
          exportTitle={isExporting ? 'Preparing export...' : 'Export offline player'}
          exportError={exportError}
          searchPanel={searchPanel}
          searchPlacement="primary"
        />
      }
    >
      {!mediaComplete ? (
        <div className="player-panel__notice" role="status">
          Video batches are still rendering. Completed segments will appear as soon as they finish.
        </div>
      ) : null}
      {isLoading && videoCount === 0 ? (
        <p role="status">Loading generated video…</p>
      ) : videoCount === 0 ? (
        <p role="status">Awaiting generated video batches for this job.</p>
      ) : (
        <VideoPlayer
          files={videoFiles}
          activeId={activeVideoId}
          onSelectFile={(id) => {
            resetPlaybackPosition(id);
            setActiveVideoId(id);
          }}
          jobId={jobId}
          jobOriginalLanguage={jobOriginalLanguage}
          jobTranslationLanguage={jobTranslationLanguage}
          infoBadge={infoBadge}
          autoPlay
          onPlaybackEnded={handlePlaybackEnded}
          playbackPosition={playbackPosition}
          onPlaybackPositionChange={handlePlaybackPositionChange}
          onPlaybackStateChange={handlePlaybackStateChange}
          playbackRate={playbackSpeed}
          onPlaybackRateChange={handlePlaybackRateChange}
          isTheaterMode={isFullscreen}
          onExitTheaterMode={handleExitFullscreen}
          onRegisterControls={handleRegisterControls}
          subtitlesEnabled={subtitlesEnabled}
          linguistEnabled={!isExportMode}
          tracks={activeSubtitleTracks}
          cueVisibility={cueVisibility}
          subtitleScale={activeSubtitleScale}
          myLinguistScale={resolvedLinguistScale}
          subtitleBackgroundOpacity={subtitleBackgroundOpacityPercent / 100}
        />
      )}
    </PlayerPanelShell>
  );
}
