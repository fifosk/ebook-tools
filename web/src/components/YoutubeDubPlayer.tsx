import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { LiveMediaItem, LiveMediaState } from '../hooks/useLiveMedia';
import { useMediaMemory } from '../hooks/useMediaMemory';
import { formatBookmarkTime, usePlaybackBookmarks } from '../hooks/usePlaybackBookmarks';
import { useSubtitlePreferences } from '../hooks/useSubtitlePreferences';
import { useYoutubeKeyboardShortcuts } from '../hooks/useYoutubeKeyboardShortcuts';
import VideoPlayer, { type SubtitleTrack } from './VideoPlayer';
import { NavigationControls } from './player-panel/NavigationControls';
import MediaSearchPanel from './MediaSearchPanel';
import { PlayerPanelShell } from './player-panel/PlayerPanelShell';
import {
  appendAccessToken,
  createExport,
  withBase,
} from '../api/client';
import {
  DEFAULT_TRANSLATION_SPEED,
  FONT_SCALE_STEP,
  MY_LINGUIST_FONT_SCALE_STEP,
  TRANSLATION_SPEED_MAX,
  TRANSLATION_SPEED_MIN,
  TRANSLATION_SPEED_STEP,
  normaliseTranslationSpeed,
} from './player-panel/constants';
import { buildMediaFileId, resolveBaseIdFromResult, toVideoFiles } from './player-panel/utils';
import type { NavigationIntent } from './player-panel/constants';
import type {
  LibraryItem,
  MediaSearchResult,
} from '../api/dtos';
import { coerceExportPath } from '../utils/storageResolver';
import { downloadWithSaveAs } from '../utils/downloads';
import { subtitleFormatFromPath } from '../utils/subtitles';
import { extractJobType } from '../utils/jobGlyphs';
import type { ExportPlayerManifest } from '../types/exportPlayer';
import { useMyLinguist } from '../context/MyLinguistProvider';
import { replaceUrlExtension } from './youtube-player/utils';
import {
  resolveInlineSubtitlePayload,
  buildSubtitleDataUrl,
  extractFileSuffix,
} from './youtube-player/subtitleHelpers';
import { buildSiblingSubtitleTracks as buildSiblingSubtitleTracksHelper } from './youtube-player/mediaHelpers';
import { useYoutubeMetadata } from './youtube-player/useYoutubeMetadata';
import { useInfoBadge } from './youtube-player/useInfoBadge';

type PlaybackControls = { pause: () => void; play: () => void; ensureFullscreen?: () => void; seek?: (time: number) => void };

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
  bookMetadata?: Record<string, unknown> | null;
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
  bookMetadata = null,
}: YoutubeDubPlayerProps) {
  const isExportMode = playerMode === 'export';
  const { adjustBaseFontScalePercent, baseFontScalePercent } = useMyLinguist();
  const resolvedJobType = useMemo(() => jobType ?? extractJobType(bookMetadata) ?? null, [bookMetadata, jobType]);
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
  const resolveSubtitleUrl = useCallback(
    (url: string, format?: string | null): string => {
      const resolved = resolveMediaUrl(url);
      if (!isExportMode) {
        return resolved;
      }
      const payload = resolveInlineSubtitlePayload(resolved, inlineSubtitles);
      if (!payload) {
        return resolved;
      }
      const inferredFormat = format || subtitleFormatFromPath(resolved);
      return buildSubtitleDataUrl(payload, inferredFormat);
    },
    [inlineSubtitles, isExportMode, resolveMediaUrl],
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
    bookMetadata,
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

  const subtitleMap = useMemo(() => {
    const priorities = ['ass', 'vtt', 'srt', 'text'];
    const formatRank = (entry: (typeof media.text)[number]) => {
      const suffix = extractFileSuffix(entry.url) || extractFileSuffix(entry.name) || extractFileSuffix(entry.path);
      const score = priorities.indexOf(suffix);
      return score >= 0 ? score : priorities.length;
    };
    const scoreTrack = (entry: (typeof media.text)[number], context: { range: string | null; chunk: string | null; base: string | null }) => {
      const formatScore = formatRank(entry);
      const rangeScore = context.range
        ? entry.range_fragment === context.range
          ? 0
          : 2
        : entry.range_fragment
          ? 1
          : 3;
      const baseScore = context.base ? (deriveBaseId(entry) === context.base ? 0 : 2) : 1;
      const chunkScore = context.chunk
        ? entry.chunk_id === context.chunk
          ? 0
          : 2
        : entry.chunk_id
          ? 1
          : 3;
      return { entry, score: [formatScore, rangeScore, chunkScore, baseScore] as const };
    };

    const map = new Map<string, SubtitleTrack[]>();
    const fallbackTracks: SubtitleTrack[] = media.text
      .filter((entry) => typeof entry.url === 'string' && entry.url.length > 0)
      .sort((a, b) => formatRank(a) - formatRank(b))
      .map((entry) => {
        const format = subtitleFormatFromPath(entry.url ?? entry.name ?? entry.path);
        return {
          url: resolveSubtitleUrl(entry.url!, format),
          label: entry.name ?? entry.url ?? 'Subtitles',
          kind: 'subtitles',
          language: (entry as { language?: string }).language ?? undefined,
          format: format || undefined,
        };
      });
    media.video.forEach((video, index) => {
      if (typeof video.url !== 'string' || video.url.length === 0) {
        return;
      }
      const videoId = buildMediaFileId(video, index);
      const baseId = deriveBaseId(video);
      const range = video.range_fragment ?? null;
      const chunkId = video.chunk_id ?? null;
      const matches = media.text.filter((entry) => {
        if (!entry.url) {
          return false;
        }
        if (range && entry.range_fragment && entry.range_fragment === range) {
          return true;
        }
        if (chunkId && entry.chunk_id && entry.chunk_id === chunkId) {
          return true;
        }
        const entryBase = deriveBaseId(entry);
        return !!baseId && entryBase === baseId;
      });
      if (matches.length === 0) {
        if (fallbackTracks.length > 0) {
          map.set(videoId, fallbackTracks);
        }
        return;
      }
      const scored = matches
        .filter((entry) => typeof entry.url === 'string' && entry.url.length > 0)
        .map((entry) => scoreTrack(entry, { range, chunk: chunkId, base: baseId }))
        .sort((a, b) => {
          for (let i = 0; i < Math.max(a.score.length, b.score.length); i += 1) {
            const left = a.score[i] ?? 0;
            const right = b.score[i] ?? 0;
            if (left !== right) {
              return left - right;
            }
          }
          return 0;
        });
      const orderedEntries = scored.map((entry) => entry.entry);
      if (orderedEntries.length > 0) {
        const seen = new Set<string>();
        const unique = orderedEntries.filter((entry) => {
          const url = entry.url ?? '';
          if (!url || seen.has(url)) {
            return false;
          }
          seen.add(url);
          return true;
        });
        if (unique.length > 0) {
          map.set(
            videoId,
            unique.map((entry) => {
              const format = subtitleFormatFromPath(entry.url ?? entry.name ?? entry.path);
              return {
                url: resolveSubtitleUrl(entry.url!, format),
                label: entry.name ?? entry.url ?? 'Subtitles',
                kind: 'subtitles',
                language: (entry as { language?: string }).language ?? undefined,
                format: format || undefined,
              };
            }),
          );
          return;
        }
      }
      const filtered = matches.filter((entry) => typeof entry.url === 'string' && entry.url.length > 0);
      if (filtered.length > 0) {
        const seen = new Set<string>();
        map.set(
          videoId,
          filtered
            .sort((a, b) => formatRank(a) - formatRank(b))
            .filter((entry) => {
              const url = entry.url ?? '';
              if (!url || seen.has(url)) {
                return false;
              }
              seen.add(url);
              return true;
            })
            .map((entry) => {
              const format = subtitleFormatFromPath(entry.url ?? entry.name ?? entry.path);
              return {
                url: resolveSubtitleUrl(entry.url!, format),
                label: entry.name ?? entry.url ?? 'Subtitles',
                kind: 'subtitles',
                language: (entry as { language?: string }).language ?? undefined,
                format: format || undefined,
              };
            }),
        );
      }
    });
    if (fallbackTracks.length > 0) {
      map.set('__fallback__', fallbackTracks);
    }

    return map;
  }, [deriveBaseId, media.text, media.video, resolveMediaUrl, resolveSubtitleUrl]);

  const buildSiblingSubtitleTracks = useCallback(
    (videoUrl: string | null | undefined): SubtitleTrack[] =>
      buildSiblingSubtitleTracksHelper(videoUrl, replaceUrlExtension, resolveSubtitleUrl, subtitleFormatFromPath),
    [resolveSubtitleUrl]
  );
  const [activeVideoId, setActiveVideoId] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(DEFAULT_TRANSLATION_SPEED);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const pendingAutoplayRef = useRef(false);
  const previousFileCountRef = useRef<number>(videoFiles.length);
  const controlsRef = useRef<PlaybackControls | null>(null);
  const lastActivatedVideoRef = useRef<string | null>(null);
  const localPositionRef = useRef<number>(0);
  const pendingBookmarkSeekRef = useRef<{ videoId: string; time: number } | null>(null);

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
  const activeSubtitleTracks = useMemo(() => {
    const direct = activeVideoId ? subtitleMap.get(activeVideoId) ?? [] : [];
    if (direct.length > 0) {
      return direct;
    }
    const activeVideo = activeVideoId
      ? videoFiles.find((file) => file.id === activeVideoId) ?? null
      : null;
    const siblingTracks = buildSiblingSubtitleTracks(activeVideo?.url);
    if (siblingTracks.length > 0) {
      return siblingTracks;
    }
    const fallback = subtitleMap.get('__fallback__') ?? [];
    return fallback;
  }, [activeVideoId, buildSiblingSubtitleTracks, subtitleMap, videoFiles]);

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

  useEffect(() => {
    const availableIds = videoFiles.map((file) => file.id);
    if (availableIds.length === 0) {
      setActiveVideoId(null);
      return;
    }

    const rememberedId = memoryState.currentMediaType === 'video' ? memoryState.currentMediaId : null;
    setActiveVideoId((current) => {
      if (current && availableIds.includes(current)) {
        return current;
      }
      if (rememberedId && availableIds.includes(rememberedId)) {
        return rememberedId;
      }
      return availableIds[0] ?? null;
    });
  }, [videoFiles, memoryState.currentMediaId, memoryState.currentMediaType]);

  useEffect(() => {
    if (!activeVideoId) {
      return;
    }
    const match = videoLookup.get(activeVideoId);
    if (match) {
      rememberSelection({ media: { ...match, url: activeVideoId } });
    }
  }, [activeVideoId, rememberSelection, videoLookup]);

  useEffect(() => {
    setIsPlaying(false);
  }, [activeVideoId]);

  const resetPlaybackPosition = useCallback(
    (videoId: string | null) => {
      if (!videoId) {
        return;
      }
      const match = videoLookup.get(videoId) ?? null;
      const baseId = match ? deriveBaseId(match) : null;
      rememberPosition({
        mediaId: videoId,
        mediaType: 'video',
        baseId,
        position: 0,
      });
      lastActivatedVideoRef.current = videoId;
    },
    [deriveBaseId, rememberPosition, videoLookup],
  );
  const markActivatedVideo = useCallback((videoId: string | null) => {
    if (!videoId) {
      return;
    }
    lastActivatedVideoRef.current = videoId;
  }, []);

  useEffect(() => {
    if (!activeVideoId) {
      localPositionRef.current = 0;
      return;
    }
    localPositionRef.current = getPosition(activeVideoId);
    markActivatedVideo(activeVideoId);
  }, [activeVideoId, getPosition, markActivatedVideo]);

  useEffect(() => {
    onPlaybackStateChange?.(isPlaying);
    onVideoPlaybackStateChange?.(isPlaying);
  }, [isPlaying, onPlaybackStateChange, onVideoPlaybackStateChange]);

  const handleNavigate = useCallback(
    (intent: NavigationIntent) => {
      if (videoFiles.length === 0) {
        return;
      }
      const currentIndex = activeVideoId ? videoFiles.findIndex((file) => file.id === activeVideoId) : -1;
      const lastIndex = videoFiles.length - 1;
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
      if (nextIndex === currentIndex || nextIndex < 0 || nextIndex >= videoFiles.length) {
        return;
      }
      const nextId = videoFiles[nextIndex].id;
      resetPlaybackPosition(nextId);
      setActiveVideoId(nextId);
    },
    [activeVideoId, resetPlaybackPosition, videoFiles],
  );

  const handleTogglePlayback = useCallback(() => {
    if (isPlaying) {
      controlsRef.current?.pause();
    } else {
      controlsRef.current?.play();
    }
  }, [isPlaying]);

  const handlePlaybackStateChange = useCallback(
    (state: 'playing' | 'paused') => {
      setIsPlaying(state === 'playing');
    },
    [],
  );

  const handlePlaybackEnded = useCallback(() => {
    setIsPlaying(false);
    const isLast =
      videoFiles.length > 0 && activeVideoId !== null && videoFiles.findIndex((file) => file.id === activeVideoId) === videoFiles.length - 1;
    pendingAutoplayRef.current = isLast;
    handleNavigate('next');
  }, [activeVideoId, handleNavigate, videoFiles]);

  const handleToggleFullscreen = useCallback(() => {
    setIsFullscreen((current) => {
      const next = !current;
      onFullscreenChange?.(next);
      if (next) {
        controlsRef.current?.ensureFullscreen?.();
      }
      return next;
    });
  }, [onFullscreenChange]);

  const handleExitFullscreen = useCallback(
    (reason?: 'user' | 'lost') => {
      if (reason === 'user') {
        setIsFullscreen(false);
        onFullscreenChange?.(false);
        return;
      }
      // If fullscreen was lost but the toggle is still on, immediately request it again.
      if (isFullscreen) {
        setTimeout(() => {
          controlsRef.current?.ensureFullscreen?.();
        }, 0);
        return;
      }
      onFullscreenChange?.(false);
    },
    [isFullscreen, onFullscreenChange],
  );

  useEffect(() => {
    if (!isFullscreen) {
      return;
    }
    // Reassert fullscreen whenever the active video changes while the toggle is on.
    const timer = window.setTimeout(() => {
      controlsRef.current?.ensureFullscreen?.();
    }, 0);
    return () => {
      window.clearTimeout(timer);
    };
  }, [isFullscreen, activeVideoId]);

  const handleRegisterControls = useCallback(
    (controls: PlaybackControls | null) => {
      controlsRef.current = controls;
      if (!controls) {
        return;
      }
      const pending = pendingBookmarkSeekRef.current;
      if (!pending || pending.videoId !== activeVideoId) {
        return;
      }
      const clamped = Math.max(pending.time, 0);
      localPositionRef.current = clamped;
      const match = videoLookup.get(pending.videoId) ?? null;
      const baseId = match ? deriveBaseId(match) : null;
      rememberPosition({
        mediaId: pending.videoId,
        mediaType: 'video',
        baseId,
        position: clamped,
      });
      controls.seek?.(clamped);
      pendingBookmarkSeekRef.current = null;
    },
    [activeVideoId, deriveBaseId, rememberPosition, videoLookup],
  );

  const handlePlaybackRateChange = useCallback((rate: number) => {
    setPlaybackSpeed(normaliseTranslationSpeed(rate));
  }, []);

  const adjustPlaybackSpeed = useCallback((direction: 'faster' | 'slower') => {
    setPlaybackSpeed((current) => {
      const delta = direction === 'faster' ? TRANSLATION_SPEED_STEP : -TRANSLATION_SPEED_STEP;
      return normaliseTranslationSpeed(current + delta);
    });
  }, []);

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

  const handlePlaybackPositionChange = useCallback(
    (position: number) => {
      if (!activeVideoId) {
        return;
      }
      localPositionRef.current = Math.max(position, 0);
      const match = videoLookup.get(activeVideoId) ?? null;
      const baseId = match ? deriveBaseId(match) : null;
      rememberPosition({
        mediaId: activeVideoId,
        mediaType: 'video',
        baseId,
        position: Math.max(position, 0),
      });
    },
    [activeVideoId, deriveBaseId, rememberPosition, videoLookup],
  );

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

  const applyBookmarkSeek = useCallback(
    (videoId: string, time: number) => {
      const clamped = Math.max(time, 0);
      localPositionRef.current = clamped;
      lastActivatedVideoRef.current = videoId;
      const match = videoLookup.get(videoId) ?? null;
      const baseId = match ? deriveBaseId(match) : null;
      rememberPosition({
        mediaId: videoId,
        mediaType: 'video',
        baseId,
        position: clamped,
      });
      controlsRef.current?.seek?.(clamped);
    },
    [deriveBaseId, rememberPosition, videoLookup],
  );

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

  const playbackPosition =
    activeVideoId && lastActivatedVideoRef.current === activeVideoId ? localPositionRef.current : 0;
  const videoCount = videoFiles.length;
  const currentIndex = activeVideoId ? videoFiles.findIndex((file) => file.id === activeVideoId) : -1;
  const disableFirst = videoCount === 0 || currentIndex <= 0;
  const disablePrevious = videoCount === 0 || currentIndex <= 0;
  const disableNext = videoCount === 0 || currentIndex >= videoCount - 1;
  const disableLast = videoCount === 0 || currentIndex >= videoCount - 1;
  const disablePlayback = videoCount === 0 || !controlsRef.current;
  const disableFullscreen = videoCount === 0;
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

  const handleTranslationSpeedChange = useCallback((value: number) => {
    setPlaybackSpeed(normaliseTranslationSpeed(value));
  }, []);
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

  useEffect(() => {
    return () => {
      onPlaybackStateChange?.(false);
      onVideoPlaybackStateChange?.(false);
    };
  }, [onPlaybackStateChange, onVideoPlaybackStateChange]);

  useEffect(() => {
    const pending = pendingBookmarkSeekRef.current;
    if (!pending || pending.videoId !== activeVideoId) {
      return;
    }
    if (!controlsRef.current?.seek) {
      return;
    }
    applyBookmarkSeek(pending.videoId, pending.time);
    pendingBookmarkSeekRef.current = null;
  }, [activeVideoId, applyBookmarkSeek]);

  useEffect(() => {
    const previousCount = previousFileCountRef.current;
    previousFileCountRef.current = videoFiles.length;

    if (videoFiles.length === 0) {
      pendingAutoplayRef.current = false;
      return;
    }

    const appended = videoFiles.length > previousCount;
    const shouldResume = pendingAutoplayRef.current && appended;
    if (shouldResume) {
      const nextId = videoFiles[videoFiles.length - 1]?.id;
      if (nextId) {
        resetPlaybackPosition(nextId);
        setActiveVideoId(nextId);
        // Defer play until the video element mounts with the new source.
        setTimeout(() => {
          if (isFullscreen) {
            controlsRef.current?.ensureFullscreen?.();
          }
          controlsRef.current?.play();
        }, 0);
      }
      pendingAutoplayRef.current = false;
    }
  }, [isFullscreen, resetPlaybackPosition, videoFiles]);

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
