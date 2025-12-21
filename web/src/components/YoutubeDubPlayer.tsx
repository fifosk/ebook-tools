import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { LiveMediaItem, LiveMediaState } from '../hooks/useLiveMedia';
import { useMediaMemory } from '../hooks/useMediaMemory';
import VideoPlayer, { type SubtitleTrack } from './VideoPlayer';
import { NavigationControls } from './player-panel/NavigationControls';
import { PlayerPanelShell } from './player-panel/PlayerPanelShell';
import {
  appendAccessToken,
  createExport,
  fetchSubtitleTvMetadata,
  fetchYoutubeVideoMetadata,
  resolveLibraryMediaUrl,
  withBase,
} from '../api/client';
import {
  DEFAULT_TRANSLATION_SPEED,
  TRANSLATION_SPEED_MAX,
  TRANSLATION_SPEED_MIN,
  TRANSLATION_SPEED_STEP,
  normaliseTranslationSpeed,
} from './player-panel/constants';
import { buildMediaFileId, toVideoFiles } from './player-panel/utils';
import type { NavigationIntent } from './player-panel/constants';
import type { LibraryItem, SubtitleTvMetadataResponse, YoutubeVideoMetadataResponse } from '../api/dtos';
import { coerceExportPath } from '../utils/storageResolver';
import { downloadWithSaveAs } from '../utils/downloads';

type PlaybackControls = { pause: () => void; play: () => void; ensureFullscreen?: () => void };

interface YoutubeDubPlayerProps {
  jobId: string;
  media: LiveMediaState;
  mediaComplete: boolean;
  isLoading: boolean;
  error: Error | null;
  playerMode?: 'online' | 'export';
  onFullscreenChange?: (isFullscreen: boolean) => void;
  onPlaybackStateChange?: (isPlaying: boolean) => void;
  onVideoPlaybackStateChange?: (isPlaying: boolean) => void;
  showBackToLibrary?: boolean;
  onBackToLibrary?: () => void;
  libraryItem?: LibraryItem | null;
}

function replaceUrlExtension(value: string, suffix: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const [pathPart, hashPart] = trimmed.split('#', 2);
  const [pathOnly, queryPart] = pathPart.split('?', 2);
  if (!pathOnly || !/\.[^/.]+$/.test(pathOnly)) {
    return null;
  }
  let result = pathOnly.replace(/\.[^/.]+$/, suffix);
  if (queryPart) {
    result += `?${queryPart}`;
  }
  if (hashPart) {
    result += `#${hashPart}`;
  }
  return result;
}

function readNestedValue(source: unknown, path: string[]): unknown {
  let current: unknown = source;
  for (const key of path) {
    if (!current || typeof current !== 'object') {
      return null;
    }
    current = (current as Record<string, unknown>)[key];
  }
  return current;
}

function coerceRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function resolveLibraryAssetUrl(jobId: string, value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (/^[a-z]+:\/\//i.test(trimmed)) {
    return trimmed;
  }
  if (trimmed.startsWith('/api/')) {
    return appendAccessToken(trimmed);
  }
  if (trimmed.startsWith('/')) {
    return trimmed;
  }
  return resolveLibraryMediaUrl(jobId, trimmed);
}

function extractTvMediaMetadataFromLibrary(item: LibraryItem | null | undefined): Record<string, unknown> | null {
  const payload = item?.metadata ?? null;
  if (!payload || typeof payload !== 'object') {
    return null;
  }
  const candidate =
    readNestedValue(payload, ['result', 'youtube_dub', 'media_metadata']) ??
    readNestedValue(payload, ['result', 'subtitle', 'metadata', 'media_metadata']) ??
    readNestedValue(payload, ['request', 'media_metadata']) ??
    readNestedValue(payload, ['media_metadata']) ??
    null;
  return coerceRecord(candidate);
}

function resolveTvImage(
  jobId: string,
  tvMetadata: Record<string, unknown> | null,
  path: 'show' | 'episode',
  resolver: (jobId: string, value: unknown) => string | null,
): string | null {
  const section = coerceRecord(tvMetadata?.[path]);
  if (!section) {
    return null;
  }
  const image = section['image'];
  if (!image) {
    return null;
  }
  if (typeof image === 'string') {
    return resolver(jobId, image);
  }
  const record = coerceRecord(image);
  if (!record) {
    return null;
  }
  return resolver(jobId, record['medium']) ?? resolver(jobId, record['original']);
}

function extractYoutubeVideoMetadataFromTv(tvMetadata: Record<string, unknown> | null): Record<string, unknown> | null {
  return coerceRecord(tvMetadata?.['youtube']);
}

function resolveYoutubeThumbnail(
  jobId: string,
  youtubeMetadata: Record<string, unknown> | null,
  resolver: (jobId: string, value: unknown) => string | null,
): string | null {
  if (!youtubeMetadata) {
    return null;
  }
  return resolver(jobId, youtubeMetadata['thumbnail']);
}

function resolveYoutubeTitle(youtubeMetadata: Record<string, unknown> | null): string | null {
  const title = youtubeMetadata?.['title'];
  return typeof title === 'string' && title.trim() ? title.trim() : null;
}

function resolveYoutubeChannel(youtubeMetadata: Record<string, unknown> | null): string | null {
  const channel = youtubeMetadata?.['channel'];
  if (typeof channel === 'string' && channel.trim()) {
    return channel.trim();
  }
  const uploader = youtubeMetadata?.['uploader'];
  return typeof uploader === 'string' && uploader.trim() ? uploader.trim() : null;
}

function formatTvEpisodeLabel(tvMetadata: Record<string, unknown> | null): string | null {
  const kind = typeof tvMetadata?.['kind'] === 'string' ? (tvMetadata?.['kind'] as string).trim().toLowerCase() : '';
  if (kind !== 'tv_episode') {
    return null;
  }
  const episode = coerceRecord(tvMetadata?.['episode']);
  const season = episode?.['season'];
  const number = episode?.['number'];
  const episodeName = typeof episode?.['name'] === 'string' && episode.name.trim() ? episode.name.trim() : null;
  const code =
    typeof season === 'number' &&
    typeof number === 'number' &&
    Number.isFinite(season) &&
    Number.isFinite(number) &&
    season > 0 &&
    number > 0
      ? `S${Math.trunc(season).toString().padStart(2, '0')}E${Math.trunc(number).toString().padStart(2, '0')}`
      : null;
  if (code && episodeName) {
    return `${code} - ${episodeName}`;
  }
  return episodeName ?? code;
}

export default function YoutubeDubPlayer({
  jobId,
  media,
  mediaComplete,
  isLoading,
  error,
  playerMode = 'online',
  onFullscreenChange,
  onPlaybackStateChange,
  onVideoPlaybackStateChange,
  showBackToLibrary = false,
  onBackToLibrary,
  libraryItem = null,
}: YoutubeDubPlayerProps) {
  const isExportMode = playerMode === 'export';
  const resolveMediaUrl = useCallback(
    (url: string) => {
      if (isExportMode) {
        return coerceExportPath(url, jobId) ?? url;
      }
      return appendAccessToken(url);
    },
    [appendAccessToken, isExportMode, jobId],
  );
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
  const [jobTvMetadata, setJobTvMetadata] = useState<Record<string, unknown> | null>(null);
  const [jobYoutubeMetadata, setJobYoutubeMetadata] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    if (libraryItem || isExportMode) {
      setJobTvMetadata(null);
      setJobYoutubeMetadata(null);
      return;
    }
    let cancelled = false;
    void fetchSubtitleTvMetadata(jobId)
      .then((payload: SubtitleTvMetadataResponse) => {
        if (cancelled) {
          return;
        }
        setJobTvMetadata(payload.media_metadata ? { ...payload.media_metadata } : null);
      })
      .catch(() => {
        if (!cancelled) {
          setJobTvMetadata(null);
        }
      });
    void fetchYoutubeVideoMetadata(jobId)
      .then((payload: YoutubeVideoMetadataResponse) => {
        if (cancelled) {
          return;
        }
        setJobYoutubeMetadata(payload.youtube_metadata ? { ...payload.youtube_metadata } : null);
      })
      .catch(() => {
        if (!cancelled) {
          setJobYoutubeMetadata(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [isExportMode, jobId, libraryItem]);
  const subtitleMap = useMemo(() => {
    const priorities = ['vtt', 'srt', 'ass', 'text'];
    const resolveSuffix = (value: string | null | undefined) => {
      if (!value) {
        return '';
      }
      const cleaned = value.split(/[?#]/)[0] ?? '';
      const leaf = cleaned.split('/').pop() ?? cleaned;
      const parts = leaf.split('.');
      if (parts.length <= 1) {
        return '';
      }
      return parts.pop()?.toLowerCase() ?? '';
    };
    const formatRank = (entry: (typeof media.text)[number]) => {
      const suffix = resolveSuffix(entry.url) || resolveSuffix(entry.name) || resolveSuffix(entry.path);
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
      .map((entry) => ({
        url: resolveMediaUrl(entry.url!),
        label: entry.name ?? entry.url ?? 'Subtitles',
        kind: 'subtitles',
        language: (entry as { language?: string }).language ?? undefined,
      }));
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
      const best = scored[0]?.entry;
      if (best) {
        map.set(videoId, [
          {
            url: resolveMediaUrl(best.url!),
            label: best.name ?? best.url ?? 'Subtitles',
            kind: 'subtitles',
            language: (best as { language?: string }).language ?? undefined,
          },
        ]);
        return;
      }
      const filtered = matches.filter((entry) => typeof entry.url === 'string' && entry.url.length > 0);
      if (filtered.length > 0) {
        map.set(
          videoId,
          filtered
            .sort((a, b) => formatRank(a) - formatRank(b))
            .map((entry) => ({
              url: resolveMediaUrl(entry.url!),
              label: entry.name ?? entry.url ?? 'Subtitles',
              kind: 'subtitles',
              language: (entry as { language?: string }).language ?? undefined,
            })),
        );
      }
    });
    if (fallbackTracks.length > 0) {
      map.set('__fallback__', fallbackTracks);
    }

    return map;
  }, [deriveBaseId, media.text, media.video, resolveMediaUrl]);

  const buildSiblingSubtitleTracks = useCallback((videoUrl: string | null | undefined): SubtitleTrack[] => {
    if (!videoUrl) {
      return [];
    }
    const candidates = ['.vtt', '.srt', '.ass']
      .map((suffix) => replaceUrlExtension(videoUrl, suffix))
      .filter((candidate): candidate is string => Boolean(candidate));
    if (candidates.length === 0) {
      return [];
    }
    return candidates.map((candidate, index) => ({
      url: candidate,
      label: index === 0 ? 'Subtitles' : `Subtitles (${index + 1})`,
      kind: 'subtitles',
      language: 'und',
    }));
  }, []);
  const [activeVideoId, setActiveVideoId] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [subtitlesEnabled, setSubtitlesEnabled] = useState(true);
  const [cueVisibility, setCueVisibility] = useState({
    original: true,
    transliteration: true,
    translation: true,
  });
  const [playbackSpeed, setPlaybackSpeed] = useState(DEFAULT_TRANSLATION_SPEED);
  const [subtitleScale, setSubtitleScale] = useState(1);
  const [subtitleBackgroundOpacityPercent, setSubtitleBackgroundOpacityPercent] = useState(70);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const pendingAutoplayRef = useRef(false);
  const previousFileCountRef = useRef<number>(videoFiles.length);
  const controlsRef = useRef<PlaybackControls | null>(null);
  const lastActivatedVideoRef = useRef<string | null>(null);
  const localPositionRef = useRef<number>(0);
  const toggleCueVisibility = useCallback((key: 'original' | 'transliteration' | 'translation') => {
    setCueVisibility((current) => ({ ...current, [key]: !current[key] }));
  }, []);
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

  const infoBadge = useMemo(() => {
    const isLibrary = Boolean(libraryItem);
    const resolver = isLibrary ? resolveLibraryAssetUrl : (jobIdValue: string, value: unknown) => {
      if (typeof value !== 'string') {
        return null;
      }
      const trimmed = value.trim();
      if (!trimmed) {
        return null;
      }
      if (trimmed.startsWith('/api/')) {
        return appendAccessToken(trimmed);
      }
      if (trimmed.startsWith('/')) {
        return appendAccessToken(trimmed);
      }
      if (/^[a-z]+:\/\//i.test(trimmed)) {
        return trimmed;
      }
      return trimmed;
    };

    const tvMetadata = isLibrary ? extractTvMediaMetadataFromLibrary(libraryItem) : jobTvMetadata;
    const kind = typeof tvMetadata?.['kind'] === 'string' ? (tvMetadata.kind as string).trim().toLowerCase() : '';
    const youtubeFromTv = extractYoutubeVideoMetadataFromTv(tvMetadata);
    const youtubeMetadata = isLibrary ? youtubeFromTv : jobYoutubeMetadata ?? youtubeFromTv;

    const episodeCoverUrl = resolveTvImage(jobId, tvMetadata, 'episode', resolver);
    const showCoverUrl = resolveTvImage(jobId, tvMetadata, 'show', resolver);
    const youtubeThumbnailUrl = resolveYoutubeThumbnail(jobId, youtubeMetadata, resolver);

    const coverFromLibrary =
      isLibrary && libraryItem?.coverPath ? resolver(jobId, libraryItem.coverPath) : null;
    const coverUrl =
      coverFromLibrary ??
      episodeCoverUrl ??
      showCoverUrl ??
      youtubeThumbnailUrl ??
      null;
    const coverSecondaryUrl =
      kind === 'tv_episode' && showCoverUrl && coverUrl && coverUrl !== showCoverUrl ? showCoverUrl : null;

    const titleFromLibrary =
      typeof libraryItem?.bookTitle === 'string' && libraryItem.bookTitle.trim() ? libraryItem.bookTitle.trim() : null;
    const title =
      titleFromLibrary ??
      resolveYoutubeTitle(youtubeMetadata) ??
      formatTvEpisodeLabel(tvMetadata) ??
      (() => {
        const active = activeVideoId ? videoFiles.find((file) => file.id === activeVideoId) ?? null : null;
        const fallback = active ?? videoFiles[0] ?? null;
        return fallback?.name ?? null;
      })() ??
      null;

    const glyph = !isLibrary
      ? 'DUB'
      : kind === 'tv_episode'
        ? 'TV'
        : youtubeMetadata
          ? 'YT'
          : 'NAS';
    const glyphLabel = !isLibrary
      ? 'Dubbed video'
      : kind === 'tv_episode'
        ? 'TV episode'
        : youtubeMetadata
          ? 'YouTube video'
          : 'NAS video';

    const metaParts: string[] = [];
    const authorFromLibrary =
      typeof libraryItem?.author === 'string' && libraryItem.author.trim() ? libraryItem.author.trim() : null;
    const genreFromLibrary =
      typeof libraryItem?.genre === 'string' && libraryItem.genre.trim() ? libraryItem.genre.trim() : null;
    if (authorFromLibrary) {
      metaParts.push(authorFromLibrary);
    } else {
      const channel = resolveYoutubeChannel(youtubeMetadata);
      if (channel) {
        metaParts.push(channel);
      } else {
        const show = coerceRecord(tvMetadata?.['show']);
        const showName = typeof show?.['name'] === 'string' && show.name.trim() ? show.name.trim() : null;
        if (showName) {
          metaParts.push(showName);
        }
      }
    }
    if (genreFromLibrary) {
      metaParts.push(genreFromLibrary);
    } else {
      if (kind === 'tv_episode') {
        metaParts.push('TV');
      } else if (youtubeMetadata) {
        metaParts.push('YouTube');
      }
    }
    const meta = metaParts.filter(Boolean).join(' · ') || null;

    return {
      title,
      meta,
      coverUrl,
      coverAltText: title ? `Cover for ${title}` : 'Cover',
      coverSecondaryUrl,
      glyph,
      glyphLabel,
    };
  }, [activeVideoId, jobId, jobTvMetadata, jobYoutubeMetadata, libraryItem, videoFiles]);

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

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined;
    }
    const isTypingTarget = (target: EventTarget | null): boolean => {
      if (!target || !(target instanceof HTMLElement)) {
        return false;
      }
      const tag = target.tagName;
      if (!tag) {
        return false;
      }
      return target.isContentEditable || tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.altKey || event.metaKey || event.ctrlKey || isTypingTarget(event.target)) {
        return;
      }
      const key = event.key?.toLowerCase();
      if (key === 'f') {
        handleToggleFullscreen();
        event.preventDefault();
        return;
      }
      if (key === 'o') {
        toggleCueVisibility('original');
        event.preventDefault();
        return;
      }
      if (key === 'i') {
        toggleCueVisibility('transliteration');
        event.preventDefault();
        return;
      }
      if (key === 'p') {
        toggleCueVisibility('translation');
        event.preventDefault();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleToggleFullscreen, toggleCueVisibility]);

  const handleRegisterControls = useCallback((controls: PlaybackControls | null) => {
    controlsRef.current = controls;
  }, []);

  const handlePlaybackRateChange = useCallback((rate: number) => {
    setPlaybackSpeed(normaliseTranslationSpeed(rate));
  }, []);

  const handleSubtitleToggle = useCallback(() => {
    setSubtitlesEnabled((current) => !current);
  }, []);

  const cuePreferenceKey = useMemo(() => `youtube-dub-cue-preference-${jobId}`, [jobId]);
  const subtitleScaleKey = useMemo(() => `youtube-dub-subtitle-scale-${jobId}`, [jobId]);
  const subtitleBackgroundOpacityKey = useMemo(() => `youtube-dub-subtitle-bg-opacity-${jobId}`, [jobId]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    try {
      const stored = window.localStorage.getItem(cuePreferenceKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed && typeof parsed === 'object') {
          setCueVisibility((current) => ({
            original: typeof parsed.original === 'boolean' ? parsed.original : current.original,
            transliteration:
              typeof parsed.transliteration === 'boolean' ? parsed.transliteration : current.transliteration,
            translation: typeof parsed.translation === 'boolean' ? parsed.translation : current.translation,
          }));
        }
      }
    } catch (error) {
      void error;
    }
  }, [cuePreferenceKey]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    setSubtitleScale(1);
  }, [subtitleScaleKey]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    setSubtitleBackgroundOpacityPercent(70);
  }, [subtitleBackgroundOpacityKey]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    try {
      const stored = window.localStorage.getItem(subtitleScaleKey);
      if (!stored) {
        return;
      }
      const parsed = Number(stored);
      if (!Number.isFinite(parsed)) {
        return;
      }
      setSubtitleScale((current) => {
        const next = Math.min(Math.max(parsed, 0.5), 2);
        return Math.abs(next - current) < 1e-3 ? current : next;
      });
    } catch (error) {
      void error;
    }
  }, [subtitleScaleKey]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    try {
      const stored = window.localStorage.getItem(subtitleBackgroundOpacityKey);
      if (!stored) {
        return;
      }
      const parsed = Number(stored);
      if (!Number.isFinite(parsed)) {
        return;
      }
      setSubtitleBackgroundOpacityPercent((current) => {
        const clamped = Math.min(Math.max(parsed, 0), 100);
        const next = Math.round(clamped / 10) * 10;
        return next === current ? current : next;
      });
    } catch (error) {
      void error;
    }
  }, [subtitleBackgroundOpacityKey]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    try {
      window.localStorage.setItem(cuePreferenceKey, JSON.stringify(cueVisibility));
    } catch (error) {
      void error;
    }
  }, [cuePreferenceKey, cueVisibility]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    try {
      window.localStorage.setItem(subtitleScaleKey, subtitleScale.toString());
    } catch (error) {
      void error;
    }
  }, [subtitleScale, subtitleScaleKey]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    try {
      window.localStorage.setItem(subtitleBackgroundOpacityKey, subtitleBackgroundOpacityPercent.toString());
    } catch (error) {
      void error;
    }
  }, [subtitleBackgroundOpacityKey, subtitleBackgroundOpacityPercent]);

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
  const exportSourceKind = libraryItem ? 'library' : 'job';

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
  const handleSubtitleScaleChange = useCallback((value: number) => {
    if (!Number.isFinite(value)) {
      return;
    }
    const clamped = Math.min(Math.max(value, 0.5), 2);
    setSubtitleScale(clamped);
  }, []);
  const handleSubtitleBackgroundOpacityChange = useCallback((value: number) => {
    if (!Number.isFinite(value)) {
      return;
    }
    const clamped = Math.min(Math.max(value, 0), 100);
    const snapped = Math.round(clamped / 10) * 10;
    setSubtitleBackgroundOpacityPercent(snapped);
  }, []);

  useEffect(() => {
    return () => {
      onPlaybackStateChange?.(false);
      onVideoPlaybackStateChange?.(false);
    };
  }, [onPlaybackStateChange, onVideoPlaybackStateChange]);

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
          subtitleScale={subtitleScale}
          subtitleScaleMin={0.5}
          subtitleScaleMax={2}
          subtitleScaleStep={0.25}
          onSubtitleScaleChange={handleSubtitleScaleChange}
          showSubtitleBackgroundOpacity
          subtitleBackgroundOpacityPercent={subtitleBackgroundOpacityPercent}
          subtitleBackgroundOpacityMin={0}
          subtitleBackgroundOpacityMax={100}
          subtitleBackgroundOpacityStep={10}
          onSubtitleBackgroundOpacityChange={handleSubtitleBackgroundOpacityChange}
          showBackToLibrary={showBackToLibrary}
          onBackToLibrary={onBackToLibrary}
          showExport={canExport}
          onExport={handleExport}
          exportDisabled={isExporting}
          exportBusy={isExporting}
          exportLabel={isExporting ? 'Preparing export' : 'Export offline player'}
          exportTitle={isExporting ? 'Preparing export...' : 'Export offline player'}
          exportError={exportError}
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
          tracks={activeSubtitleTracks}
          cueVisibility={cueVisibility}
          subtitleScale={subtitleScale}
          subtitleBackgroundOpacity={subtitleBackgroundOpacityPercent / 100}
        />
      )}
    </PlayerPanelShell>
  );
}
