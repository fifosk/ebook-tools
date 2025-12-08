import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { LiveMediaItem, LiveMediaState } from '../hooks/useLiveMedia';
import { useMediaMemory } from '../hooks/useMediaMemory';
import VideoPlayer, { type SubtitleTrack } from './VideoPlayer';
import { NavigationControls } from './PlayerPanel';
import { appendAccessToken } from '../api/client';
import {
  DEFAULT_TRANSLATION_SPEED,
  TRANSLATION_SPEED_MAX,
  TRANSLATION_SPEED_MIN,
  TRANSLATION_SPEED_STEP,
  normaliseTranslationSpeed,
} from './player-panel/constants';
import { buildMediaFileId, toVideoFiles } from './player-panel/utils';
import type { NavigationIntent } from './player-panel/constants';

type PlaybackControls = { pause: () => void; play: () => void; ensureFullscreen?: () => void };

interface YoutubeDubPlayerProps {
  jobId: string;
  media: LiveMediaState;
  mediaComplete: boolean;
  isLoading: boolean;
  error: Error | null;
  onFullscreenChange?: (isFullscreen: boolean) => void;
  onPlaybackStateChange?: (isPlaying: boolean) => void;
  onVideoPlaybackStateChange?: (isPlaying: boolean) => void;
}

export default function YoutubeDubPlayer({
  jobId,
  media,
  mediaComplete,
  isLoading,
  error,
  onFullscreenChange,
  onPlaybackStateChange,
  onVideoPlaybackStateChange,
}: YoutubeDubPlayerProps) {
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
        const urlWithToken = appendAccessToken(file.url);
        return {
          ...file,
          url: urlWithToken,
        };
      }),
    [media.video],
  );
  const { state: memoryState, rememberSelection, rememberPosition, getPosition, deriveBaseId } = useMediaMemory({
    jobId,
  });
  const subtitleMap = useMemo(() => {
    const priorities = ['vtt', 'srt', 'ass', 'text'];
    const resolveSuffix = (value: string | null | undefined) =>
      value?.split('.').pop()?.toLowerCase() ?? '';
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
        url: appendAccessToken(entry.url!),
        label: entry.name ?? entry.url ?? 'Subtitles',
        kind: 'subtitles',
        language: (entry as { language?: string }).language ?? undefined,
      }));
    media.video.forEach((video, index) => {
      if (typeof video.url !== 'string' || video.url.length === 0) {
        return;
      }
      const videoId = buildMediaFileId(video, index);
      const videoUrl = appendAccessToken(video.url);
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
          map.set(videoUrl, fallbackTracks);
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
            url: appendAccessToken(best.url!),
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
              url: appendAccessToken(entry.url!),
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
  }, [deriveBaseId, media.text, media.video]);

  const buildSiblingSubtitleTracks = useCallback((videoUrl: string | null | undefined): SubtitleTrack[] => {
    if (!videoUrl) {
      return [];
    }
    try {
      const url = new URL(videoUrl, window.location.origin);
      const candidates = ['.vtt', '.srt', '.ass'].map((suffix) => {
        const clone = new URL(url.toString());
        const path = clone.pathname.replace(/\.[^/.]+$/, suffix);
        clone.pathname = path;
        return appendAccessToken(clone.toString());
      });
      return candidates.map((candidate, index) => ({
        url: candidate,
        label: index === 0 ? 'Subtitles' : `Subtitles (${index + 1})`,
        kind: 'subtitles',
      }));
    } catch (error) {
      void error;
    }
    return [];
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
  const pendingAutoplayRef = useRef(false);
  const previousFileCountRef = useRef<number>(videoFiles.length);
  const controlsRef = useRef<PlaybackControls | null>(null);
  const lastActivatedVideoRef = useRef<string | null>(null);
  const activeSubtitleTracks = useMemo(() => {
    const base =
      activeVideoId
        ? subtitleMap.get(activeVideoId) ?? subtitleMap.get('__fallback__') ?? []
        : subtitleMap.get('__fallback__') ?? [];
    if (base.length > 0) {
      return base;
    }
    const activeVideo = activeVideoId
      ? videoFiles.find((file) => file.id === activeVideoId) ?? null
      : null;
    const siblingTracks = buildSiblingSubtitleTracks(activeVideo?.url);
    if (siblingTracks.length > 0) {
      return siblingTracks;
    }
    return base;
  }, [activeVideoId, buildSiblingSubtitleTracks, subtitleMap, videoFiles]);

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

  useEffect(() => {
    resetPlaybackPosition(activeVideoId);
  }, [activeVideoId, resetPlaybackPosition]);

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
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleToggleFullscreen]);

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

  const toggleCueVisibility = useCallback((key: 'original' | 'transliteration' | 'translation') => {
    setCueVisibility((current) => ({ ...current, [key]: !current[key] }));
  }, []);

  const handlePlaybackPositionChange = useCallback(
    (position: number) => {
      if (!activeVideoId) {
        return;
      }
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

  const activeVideo = activeVideoId ? videoLookup.get(activeVideoId) ?? null : null;
  const playbackPosition =
    activeVideoId && lastActivatedVideoRef.current === activeVideoId ? getPosition(activeVideoId) : 0;
  const videoCount = videoFiles.length;
  const currentIndex = activeVideoId ? videoFiles.findIndex((file) => file.id === activeVideoId) : -1;
  const disableFirst = videoCount === 0 || currentIndex <= 0;
  const disablePrevious = videoCount === 0 || currentIndex <= 0;
  const disableNext = videoCount === 0 || currentIndex >= videoCount - 1;
  const disableLast = videoCount === 0 || currentIndex >= videoCount - 1;
  const disablePlayback = videoCount === 0 || !controlsRef.current;
  const disableFullscreen = videoCount === 0;
  const selectionLabel = activeVideo?.name ?? activeVideo?.url ?? 'Video';
  const selectionMeta = activeVideo?.updated_at ?? '';

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

  return (
    <section className="player-panel" aria-label={`YouTube dub ${jobId}`}>
      {error ? (
        <p role="alert">Unable to load generated media: {error.message}</p>
      ) : (
        <>
          <div className="player-panel__tabs-container">
            <header className="player-panel__header">
              <div className="player-panel__tabs-row">
                <NavigationControls
                  context="panel"
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
                />
              </div>
            </header>
            <div className="player-panel__panel">
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
                <>
                  <VideoPlayer
                    files={videoFiles}
                    activeId={activeVideoId}
                    onSelectFile={(id) => {
                      resetPlaybackPosition(id);
                      setActiveVideoId(id);
                    }}
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
                />
                <div className="player-panel__selection-header" data-testid="player-panel-selection">
                  <div className="player-panel__selection-name" title={selectionLabel}>
                    {selectionLabel}
                  </div>
                  <dl className="player-panel__selection-meta">
                    <div className="player-panel__selection-meta-item">
                      <dt>Updated</dt>
                      <dd>{selectionMeta || '—'}</dd>
                    </div>
                    <div className="player-panel__selection-meta-item">
                      <dt>Batches</dt>
                      <dd>
                        {videoCount > 0 && currentIndex >= 0 ? `${currentIndex + 1} of ${videoCount}` : '—'}
                      </dd>
                    </div>
                  </dl>
                </div>
              </>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
