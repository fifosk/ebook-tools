import { useCallback, useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import { appendAccessTokenToStorageUrl, getAuthToken } from '../api/client';
import { formatMediaDropdownLabel } from '../utils/mediaLabels';
import { formatDurationLabel } from '../utils/timeFormatters';
import { DEFAULT_LANGUAGE_FLAG, resolveLanguageFlag } from '../constants/languageCodes';
import { normalizeLanguageLabel } from '../utils/languages';
import { HEADER_COLLAPSE_KEY, loadHeaderCollapsed, storeHeaderCollapsed } from '../utils/playerHeader';
import EmojiIcon from './EmojiIcon';
import PlayerChannelBug from './PlayerChannelBug';
import SubtitleTrackOverlay from './video-subtitles/SubtitleTrackOverlay';
import {
  type CueVisibility,
  DEFAULT_PLAYBACK_RATE,
  SUMMARY_MARQUEE_GAP,
  SUMMARY_MARQUEE_SPEED,
  isSafariBrowser,
} from './video-player/utils';
import { useSubtitleProcessor, useCueVisibilityFilter } from './video-player/useSubtitleProcessor';
import { useVideoFullscreen } from './video-player/useVideoFullscreen';
import { useVideoPlayback } from './video-player/useVideoPlayback';
import { useVideoScrubbing } from './video-player/useVideoScrubbing';

export interface VideoFile {
  id: string;
  url: string;
  name?: string;
  poster?: string;
}

export interface SubtitleTrack {
  url: string;
  label?: string;
  kind?: string;
  language?: string;
  format?: string;
}

interface VideoPlayerProps {
  files: VideoFile[];
  activeId: string | null;
  onSelectFile: (fileId: string) => void;
  jobId?: string | null;
  jobOriginalLanguage?: string | null;
  jobTranslationLanguage?: string | null;
  infoBadge?: {
    title?: string | null;
    meta?: string | null;
    coverUrl?: string | null;
    coverSecondaryUrl?: string | null;
    coverAltText?: string | null;
    glyph?: string | null;
    glyphLabel?: string | null;
    summary?: string | null;
  } | null;
  autoPlay?: boolean;
  onPlaybackEnded?: () => void;
  playbackPosition?: number | null;
  onPlaybackPositionChange?: (position: number) => void;
  onPlaybackStateChange?: (state: 'playing' | 'paused') => void;
  playbackRate?: number | null;
  onPlaybackRateChange?: (rate: number) => void;
  isTheaterMode?: boolean;
  onExitTheaterMode?: (reason?: 'user' | 'lost') => void;
  onRegisterControls?: (
    controls:
      | {
          pause: () => void;
          play: () => void;
          ensureFullscreen?: () => void;
          seek?: (time: number) => void;
        }
      | null
  ) => void;
  subtitlesEnabled?: boolean;
  linguistEnabled?: boolean;
  tracks?: SubtitleTrack[];
  cueVisibility?: CueVisibility;
  subtitleScale?: number;
  myLinguistScale?: number;
  subtitleBackgroundOpacity?: number;
}

type SummaryTickerMetrics = {
  shouldScroll: boolean;
  distance: number;
  duration: number;
};

function SummaryTicker({ text }: { text: string }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const textRef = useRef<HTMLSpanElement | null>(null);
  const [metrics, setMetrics] = useState<SummaryTickerMetrics>({
    shouldScroll: false,
    distance: 0,
    duration: 0,
  });

  const measure = useCallback(() => {
    const container = containerRef.current;
    const textNode = textRef.current;
    if (!container || !textNode) {
      return;
    }
    const containerWidth = container.clientWidth;
    const textWidth = textNode.scrollWidth;
    if (!containerWidth || !textWidth) {
      setMetrics({ shouldScroll: false, distance: 0, duration: 0 });
      return;
    }
    const shouldScroll = textWidth > containerWidth + 8;
    const distance = textWidth + SUMMARY_MARQUEE_GAP;
    const duration = distance > 0 ? distance / SUMMARY_MARQUEE_SPEED : 0;
    setMetrics({ shouldScroll, distance, duration });
  }, []);

  useLayoutEffect(() => {
    measure();
  }, [measure, text]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || typeof ResizeObserver === 'undefined') {
      return;
    }
    const observer = new ResizeObserver(() => {
      measure();
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, [measure]);

  return (
    <div
      className="video-player__info-summary"
      ref={containerRef}
      data-scrolling={metrics.shouldScroll ? 'true' : 'false'}
      aria-label={text}
    >
      <div
        className="video-player__info-summary-track"
        style={
          {
            '--marquee-gap': `${SUMMARY_MARQUEE_GAP}px`,
            '--marquee-distance': `${metrics.distance}px`,
            '--marquee-duration': `${Math.max(metrics.duration, 8)}s`,
          } as CSSProperties
        }
      >
        <span className="video-player__info-summary-text" ref={textRef}>
          {text}
        </span>
        {metrics.shouldScroll ? (
          <span className="video-player__info-summary-text" aria-hidden="true">
            {text}
          </span>
        ) : null}
      </div>
    </div>
  );
}

export default function VideoPlayer({
  files,
  activeId,
  onSelectFile,
  jobId = null,
  jobOriginalLanguage = null,
  jobTranslationLanguage = null,
  infoBadge = null,
  autoPlay = false,
  onPlaybackEnded,
  playbackPosition = null,
  onPlaybackPositionChange,
  onPlaybackStateChange,
  playbackRate = DEFAULT_PLAYBACK_RATE,
  onPlaybackRateChange,
  isTheaterMode = false,
  onExitTheaterMode,
  onRegisterControls,
  subtitlesEnabled = true,
  linguistEnabled = true,
  tracks = [],
  cueVisibility = { original: true, transliteration: true, translation: true },
  subtitleScale = 1,
  myLinguistScale,
  subtitleBackgroundOpacity,
}: VideoPlayerProps) {
  const playlistSelectId = useId();
  const elementRef = useRef<HTMLVideoElement | null>(null);
  const fullscreenRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const [dockedBubbleContainer, setDockedBubbleContainer] = useState<HTMLDivElement | null>(null);
  const [isHeaderCollapsed, setIsHeaderCollapsed] = useState(loadHeaderCollapsed);
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== HEADER_COLLAPSE_KEY) {
        return;
      }
      setIsHeaderCollapsed(loadHeaderCollapsed());
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);
  const toggleHeaderCollapsed = useCallback(() => {
    setIsHeaderCollapsed((previous) => {
      const next = !previous;
      storeHeaderCollapsed(next);
      return next;
    });
  }, []);
  const authToken = getAuthToken();
  const resolvedFiles = useMemo(
    () =>
      files.map((file) => ({
        ...file,
        url: appendAccessTokenToStorageUrl(file.url),
        poster: file.poster ? appendAccessTokenToStorageUrl(file.poster) : file.poster,
      })),
    [files, authToken],
  );
  const resolvedTracks = useMemo(
    () =>
      tracks.map((track) => ({
        ...track,
        url: track.url ? appendAccessTokenToStorageUrl(track.url) : track.url,
      })),
    [tracks, authToken],
  );
  const labels = resolvedFiles.map((file, index) => ({
    id: file.id,
    label: formatMediaDropdownLabel(file.name ?? file.url, `Video ${index + 1}`),
  }));

  const activeFile = activeId ? resolvedFiles.find((file) => file.id === activeId) ?? null : null;

  const isFileProtocol = typeof window !== 'undefined' && window.location.protocol === 'file:';
  const allowCrossOrigin = !isFileProtocol;
  const isSafari = isSafariBrowser();

  // Subtitle processing via hook
  const {
    processedSubtitleUrl,
    activeSubtitleTrack,
    overlaySubtitleTrack,
    subtitleOverlayActive,
    setSubtitleOverlayActive,
    disableNativeTrack,
    resolvedSubtitleBackgroundOpacity,
    resolvedSubtitleBackgroundOpacityPercent,
    subtitleRevision,
    applySubtitleTrack,
    subtitleTrackElementRef,
    pendingSubtitleTrackRef,
    cueTextCacheRef,
  } = useSubtitleProcessor({
    tracks: resolvedTracks,
    subtitlesEnabled,
    subtitleScale,
    subtitleBackgroundOpacity,
    cueVisibility,
    isSafari,
    isFileProtocol,
    activeFileId: activeFile?.id ?? null,
  });

  // Fullscreen management via hook
  const {
    requestFullscreenPlayback,
    getFullscreenTarget,
    fullscreenRequestedRef,
    nativeFullscreenReentryRef,
  } = useVideoFullscreen({
    videoRef: elementRef,
    fullscreenRef,
    isTheaterMode,
    activeFileId: activeFile?.id ?? null,
    onExitTheaterMode,
    applySubtitleTrack,
    pendingSubtitleTrackRef,
    activeSubtitleTrack,
  });

  const crossOriginMode = allowCrossOrigin && !isSafari ? 'use-credentials' : undefined;
  const deferAssLoad = isSafari;
  const [coverFailed, setCoverFailed] = useState(false);
  const [secondaryCoverFailed, setSecondaryCoverFailed] = useState(false);
  useEffect(() => {
    setCoverFailed(false);
  }, [infoBadge?.coverUrl]);
  useEffect(() => {
    setSecondaryCoverFailed(false);
  }, [infoBadge?.coverSecondaryUrl]);

  // Playback state and handlers via hook
  const {
    isPlaying,
    playbackClock,
    handlePlay,
    handlePause,
    handleEnded,
    handleTimeUpdate,
    handleLoadedData,
    handleLoadedMetadata,
    updatePlaybackClock,
  } = useVideoPlayback({
    videoRef: elementRef,
    activeFileId: activeFile?.id ?? null,
    autoPlay,
    playbackPosition,
    playbackRate,
    onPlaybackPositionChange,
    onPlaybackStateChange,
    onPlaybackRateChange,
    onPlaybackEnded,
    nativeFullscreenReentryRef,
  });
  const artVariant = useMemo(() => {
    const glyph = (infoBadge?.glyph ?? '').trim().toLowerCase();
    if (glyph === 'bk' || glyph === 'book') {
      return 'book';
    }
    if (glyph === 'sub' || glyph === 'subtitle' || glyph === 'subtitles' || glyph === 'cc') {
      return 'subtitles';
    }
    if (glyph === 'yt' || glyph === 'youtube') {
      return 'youtube';
    }
    if (glyph === 'nas') {
      return 'nas';
    }
    if (glyph === 'dub') {
      return 'dub';
    }
    return 'video';
  }, [infoBadge?.glyph]);

  const languageFlags = useMemo(() => {
    const hasOriginal = Boolean((jobOriginalLanguage ?? '').trim());
    const hasTranslation = Boolean((jobTranslationLanguage ?? '').trim());
    if (!hasOriginal && !hasTranslation) {
      return [];
    }
    const originalLabel = normalizeLanguageLabel(jobOriginalLanguage) || 'Unknown';
    const translationLabel = normalizeLanguageLabel(jobTranslationLanguage) || 'Unknown';
    return [
      {
        role: 'original',
        label: originalLabel,
        flag: resolveLanguageFlag(jobOriginalLanguage ?? originalLabel) ?? DEFAULT_LANGUAGE_FLAG,
      },
      {
        role: 'translation',
        label: translationLabel,
        flag: resolveLanguageFlag(jobTranslationLanguage ?? translationLabel) ?? DEFAULT_LANGUAGE_FLAG,
      },
    ];
  }, [jobOriginalLanguage, jobTranslationLanguage]);
  const segmentLabel = useMemo(() => {
    if (resolvedFiles.length <= 1) {
      return null;
    }
    const index = activeFile ? resolvedFiles.findIndex((file) => file.id === activeFile.id) : -1;
    const resolvedIndex = index >= 0 ? index + 1 : 1;
    return `Video ${resolvedIndex} / ${resolvedFiles.length}`;
  }, [activeFile, resolvedFiles]);
  const timelineLabel = useMemo(() => {
    if (!Number.isFinite(playbackClock.duration) || playbackClock.duration <= 0) {
      return null;
    }
    const played = Math.min(Math.max(playbackClock.current, 0), playbackClock.duration);
    const remaining = Math.max(playbackClock.duration - played, 0);
    return `${formatDurationLabel(played)} / ${formatDurationLabel(remaining)} remaining`;
  }, [playbackClock.current, playbackClock.duration]);
  const summaryText = useMemo(() => {
    const summary = infoBadge?.summary;
    if (typeof summary !== 'string') {
      return null;
    }
    const trimmed = summary.trim();
    return trimmed ? trimmed : null;
  }, [infoBadge?.summary]);
  const hasInfoHeader = Boolean(
    infoBadge &&
      (infoBadge.title ||
        infoBadge.meta ||
        infoBadge.coverUrl ||
        infoBadge.glyph ||
        summaryText ||
        languageFlags.length > 0 ||
        segmentLabel ||
        timelineLabel),
  );
  const showHeaderContent = hasInfoHeader && !isHeaderCollapsed;
  const videoStyle = useMemo(() => {
    return { '--subtitle-scale': subtitleScale } as CSSProperties;
  }, [subtitleScale]);
  const canvasStyle = useMemo(() => {
    if (!Number.isFinite(myLinguistScale ?? NaN) || !myLinguistScale) {
      return undefined;
    }
    return { '--my-linguist-font-scale': String(myLinguistScale) } as CSSProperties;
  }, [myLinguistScale]);

  useEffect(() => {
    if (!onRegisterControls) {
      return;
    }
    const controls = {
      pause: () => {
        const element = elementRef.current;
        if (!element) {
          return;
        }
        try {
          element.pause();
        } catch (error) {
          // Ignore failures triggered by non-media environments.
        }
      },
      play: () => {
        const element = elementRef.current;
        if (!element) {
          return;
        }
        try {
          const playResult = element.play();
          if (playResult && typeof playResult.catch === 'function') {
            playResult.catch(() => undefined);
          }
        } catch (error) {
          // Swallow play failures caused by autoplay policies.
        }
      },
      ensureFullscreen: () => requestFullscreenPlayback(true),
      seek: (time: number) => {
        const element = elementRef.current;
        if (!element) {
          return;
        }
        const clamped = Number.isFinite(time) ? Math.max(time, 0) : 0;
        try {
          element.currentTime = clamped;
        } catch (error) {
          // Ignore assignment failures that can happen in non-media environments.
        }
      },
    };
    onRegisterControls(controls);
    return () => {
      onRegisterControls(null);
    };
  }, [onRegisterControls, activeFile?.id, requestFullscreenPlayback]);

  // Scrubbing handlers via hook
  const {
    handleScrubPointerDown,
    handleScrubPointerMove,
    handleScrubPointerEnd,
  } = useVideoScrubbing({
    videoRef: elementRef,
    canvasRef,
    activeFileId: activeFile?.id ?? null,
    onPlaybackPositionChange,
    updatePlaybackClock,
  });

  // Apply cue visibility filtering via hook
  useCueVisibilityFilter(
    elementRef,
    cueVisibility,
    subtitlesEnabled,
    activeFile?.id ?? null,
    subtitleRevision,
    cueTextCacheRef,
  );

  if (files.length === 0) {
    return (
      <div className="video-player" role="status">
        Waiting for video files…
      </div>
    );
  }

  if (!activeFile) {
    return (
      <div className="video-player" role="status">
        Preparing the latest video…
      </div>
    );
  }

  return (
    <>
      {isTheaterMode ? (
        <button
          type="button"
          className="video-player__backdrop"
          aria-label="Exit immersive mode"
          onClick={() => onExitTheaterMode?.('user')}
        />
      ) : null}
      <div className={['video-player', isTheaterMode ? 'video-player--enlarged' : null].filter(Boolean).join(' ')}>
        <div className="video-player__stage" ref={fullscreenRef}>
          <div
            className="video-player__canvas"
            ref={canvasRef}
            style={canvasStyle}
            onPointerDown={handleScrubPointerDown}
            onPointerMove={handleScrubPointerMove}
            onPointerUp={handleScrubPointerEnd}
            onPointerCancel={handleScrubPointerEnd}
          >
            {hasInfoHeader && infoBadge ? (
              <div
                className="player-panel__player-info-header video-player__info-header"
                data-collapsed={isHeaderCollapsed ? 'true' : undefined}
              >
                {showHeaderContent ? (
                  <div className="video-player__info-header-body">
                    <div className="player-panel__player-info-header-content" aria-hidden="true">
                      <div className="video-player__info-header-left">
                        <PlayerChannelBug
                          glyph={(infoBadge.glyph ?? '').trim() || 'VID'}
                          label={infoBadge.glyphLabel}
                        />
                        {infoBadge.coverUrl && !coverFailed ? (
                          <div className="player-panel__player-info-art" data-variant={artVariant}>
                            <img
                              className="player-panel__player-info-art-main"
                              src={infoBadge.coverUrl}
                              alt={infoBadge.coverAltText ?? (infoBadge.title ? `Cover for ${infoBadge.title}` : 'Cover')}
                              onError={() => setCoverFailed(true)}
                              loading="lazy"
                            />
                            {infoBadge.coverSecondaryUrl && !secondaryCoverFailed ? (
                              <img
                                className="player-panel__player-info-art-secondary"
                                src={infoBadge.coverSecondaryUrl}
                                alt=""
                                aria-hidden="true"
                                onError={() => setSecondaryCoverFailed(true)}
                                loading="lazy"
                              />
                            ) : null}
                          </div>
                        ) : null}
                        {infoBadge.title || infoBadge.meta || languageFlags.length > 0 ? (
                          <div className="video-player__info-badge">
                            <div className="video-player__info-text">
                              {infoBadge.title ? (
                                <span className="video-player__info-title">{infoBadge.title}</span>
                              ) : null}
                              {infoBadge.meta ? <span className="video-player__info-meta">{infoBadge.meta}</span> : null}
                              {languageFlags.length > 0 ? (
                                <div className="video-player__info-flags">
                                  {languageFlags.map((entry, index) => (
                                    <div className="video-player__info-flag-group" key={`${entry.role}-${entry.label}`}>
                                      <span className="video-player__info-flag">
                                        <EmojiIcon emoji={entry.flag} className="video-player__info-flag-emoji" />
                                        <span className="video-player__info-flag-label">{entry.label}</span>
                                      </span>
                                      {index < languageFlags.length - 1 ? (
                                        <span className="video-player__info-flag-sep">to</span>
                                      ) : null}
                                    </div>
                                  ))}
                                </div>
                              ) : null}
                            </div>
                          </div>
                        ) : null}
                      </div>
                      {segmentLabel || timelineLabel ? (
                        <div className="video-player__info-header-right">
                          {segmentLabel ? <span className="video-player__info-pill">{segmentLabel}</span> : null}
                          {timelineLabel ? <span className="video-player__info-pill">{timelineLabel}</span> : null}
                        </div>
                      ) : null}
                    </div>
                    {!isPlaying && summaryText ? <SummaryTicker text={summaryText} /> : null}
                  </div>
                ) : null}
                <button
                  type="button"
                  className="player-panel__player-info-toggle player-panel__player-info-toggle--video"
                  data-collapsed={isHeaderCollapsed ? 'true' : 'false'}
                  onClick={toggleHeaderCollapsed}
                  onPointerDown={(event) => event.stopPropagation()}
                  aria-label={isHeaderCollapsed ? 'Show info header' : 'Hide info header'}
                >
                  <svg viewBox="0 0 24 24" role="img" focusable="false" aria-hidden="true">
                    <path d="M6 9l6 6 6-6Z" fill="currentColor" />
                  </svg>
                </button>
              </div>
            ) : null}
            <video
              ref={elementRef}
              className="video-player__element"
              style={videoStyle}
              data-testid="video-player"
              controls
              crossOrigin={crossOriginMode}
              src={activeFile.url}
              poster={activeFile.poster}
              autoPlay={autoPlay}
              playsInline
              data-subtitle-bg-opacity={
                resolvedSubtitleBackgroundOpacity !== null ? String(resolvedSubtitleBackgroundOpacityPercent ?? 70) : undefined
              }
              data-cue-original={cueVisibility.original ? 'on' : 'off'}
              data-cue-transliteration={cueVisibility.transliteration ? 'on' : 'off'}
              data-cue-translation={cueVisibility.translation ? 'on' : 'off'}
              onPlay={handlePlay}
              onPause={handlePause}
              onEnded={handleEnded}
              onLoadedData={handleLoadedData}
              onLoadedMetadata={handleLoadedMetadata}
              onDurationChange={handleLoadedMetadata}
              onTimeUpdate={handleTimeUpdate}
            >
              <track ref={subtitleTrackElementRef} kind="subtitles" label="Subtitles" srcLang="und" default />
              Your browser does not support the video element.
            </video>
            <SubtitleTrackOverlay
              videoRef={elementRef}
              track={overlaySubtitleTrack}
              enabled={subtitlesEnabled}
              linguistEnabled={linguistEnabled}
              deferLoadUntilPlay={deferAssLoad}
              cueVisibility={cueVisibility}
              subtitleScale={subtitleScale}
              subtitleBackgroundOpacity={resolvedSubtitleBackgroundOpacity}
              onOverlayActiveChange={setSubtitleOverlayActive}
              jobId={jobId}
              jobOriginalLanguage={jobOriginalLanguage}
              jobTranslationLanguage={jobTranslationLanguage}
              dockedContainer={dockedBubbleContainer}
            />
          </div>
        </div>
        <div
          ref={setDockedBubbleContainer}
          className="player-panel__my-linguist-dock video-player__my-linguist-dock"
          aria-label="MyLinguist lookup dock"
        />
        <div className="video-player__selector">
          <label className="video-player__selector-label" htmlFor={playlistSelectId}>
            Video
          </label>
          <select
            id={playlistSelectId}
            className="video-player__select"
            value={activeFile.id}
            onChange={(event) => {
              const next = event.target.value;
              if (next) {
                onSelectFile(next);
              }
            }}
          >
            {labels.map((file) => (
              <option key={file.id} value={file.id}>
                {file.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </>
  );
}
