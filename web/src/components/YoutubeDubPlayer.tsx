import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { LiveMediaState } from '../hooks/useLiveMedia';
import { useMediaMemory } from '../hooks/useMediaMemory';
import VideoPlayer, { type SubtitleTrack } from './VideoPlayer';
import { NavigationControls } from './PlayerPanel';
import { DEFAULT_TRANSLATION_SPEED } from './player-panel/constants';
import { toVideoFiles } from './player-panel/utils';
import type { NavigationIntent } from './player-panel/constants';

type PlaybackControls = { pause: () => void; play: () => void };

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
  const videoFiles = useMemo(() => toVideoFiles(media.video), [media.video]);
  const { state: memoryState, rememberSelection, rememberPosition, getPosition, deriveBaseId } = useMediaMemory({
    jobId,
  });
  const subtitleMap = useMemo(() => {
    const priorities = ['vtt', 'ass', 'srt', 'text'];
    const scoreTrack = (entry: (typeof media.text)[number], context: { range: string | null; chunk: string | null; base: string | null }) => {
      const suffix = entry.url?.split('.').pop()?.toLowerCase() ?? '';
      const formatScore = priorities.indexOf(suffix);
      const suffixScore = formatScore >= 0 ? formatScore : priorities.length;
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
      return { entry, score: [rangeScore, baseScore, chunkScore, suffixScore] as const };
    };

    const map = new Map<string, SubtitleTrack[]>();
    const fallbackTracks = media.text
      .filter((entry) => typeof entry.url === 'string' && entry.url.length > 0)
      .map((entry) => ({
        url: entry.url!,
        label: entry.name ?? entry.url ?? 'Subtitles',
      }));
    media.video.forEach((video) => {
      const url = typeof video.url === 'string' ? video.url : null;
      if (!url) {
        return;
      }
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
          map.set(url, fallbackTracks);
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
        map.set(url, [
          {
            url: best.url!,
            label: best.name ?? best.url ?? 'Subtitles',
            kind: best.type === 'text' ? 'subtitles' : best.type,
          },
        ]);
        return;
      }
      const filtered = matches.filter((entry) => typeof entry.url === 'string' && entry.url.length > 0);
      if (filtered.length > 0) {
        map.set(
          url,
          filtered.map((entry) => ({
            url: entry.url!,
            label: entry.name ?? entry.url ?? 'Subtitles',
          })),
        );
      }
    });
    return map;
  }, [deriveBaseId, media.text, media.video]);
  const [activeVideoId, setActiveVideoId] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [subtitlesEnabled, setSubtitlesEnabled] = useState(true);
  const pendingAutoplayRef = useRef(false);
  const previousFileCountRef = useRef<number>(videoFiles.length);
  const controlsRef = useRef<PlaybackControls | null>(null);

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
    const match = media.video.find((item) => item.url === activeVideoId);
    if (match) {
      rememberSelection({ media: match });
    }
  }, [activeVideoId, media.video, rememberSelection]);

  useEffect(() => {
    setIsPlaying(false);
  }, [activeVideoId]);

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
      setActiveVideoId(videoFiles[nextIndex].id);
    },
    [activeVideoId, videoFiles],
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
      return next;
    });
  }, [onFullscreenChange]);

  const handleExitFullscreen = useCallback(() => {
    setIsFullscreen(false);
    onFullscreenChange?.(false);
  }, [onFullscreenChange]);

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

  const handleSubtitleToggle = useCallback(() => {
    setSubtitlesEnabled((current) => !current);
  }, []);

  const handlePlaybackPositionChange = useCallback(
    (position: number) => {
      if (!activeVideoId) {
        return;
      }
      const match = media.video.find((item) => item.url === activeVideoId) ?? null;
      const baseId = match ? deriveBaseId(match) : null;
      rememberPosition({
        mediaId: activeVideoId,
        mediaType: 'video',
        baseId,
        position: Math.max(position, 0),
      });
    },
    [activeVideoId, deriveBaseId, media.video, rememberPosition],
  );

  const activeVideo = activeVideoId ? media.video.find((file) => file.url === activeVideoId) ?? null : null;
  const playbackPosition = getPosition(activeVideoId);
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
        setActiveVideoId(nextId);
        // Defer play until the video element mounts with the new source.
        setTimeout(() => {
          controlsRef.current?.play();
        }, 0);
      }
      pendingAutoplayRef.current = false;
    }
  }, [videoFiles]);

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
                  showTranslationSpeed={false}
                  translationSpeed={DEFAULT_TRANSLATION_SPEED}
                  translationSpeedMin={DEFAULT_TRANSLATION_SPEED}
                  translationSpeedMax={DEFAULT_TRANSLATION_SPEED}
                  translationSpeedStep={DEFAULT_TRANSLATION_SPEED}
                  onTranslationSpeedChange={(value) => {
                    // Translation speed is unused for video playback but required by the control API.
                    void value;
                  }}
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
                    onSelectFile={setActiveVideoId}
                    autoPlay
                    onPlaybackEnded={handlePlaybackEnded}
                    playbackPosition={playbackPosition}
                  onPlaybackPositionChange={handlePlaybackPositionChange}
                  onPlaybackStateChange={handlePlaybackStateChange}
                  isTheaterMode={isFullscreen}
                  onExitTheaterMode={handleExitFullscreen}
                  onRegisterControls={handleRegisterControls}
                  subtitlesEnabled={subtitlesEnabled}
                  tracks={activeVideoId ? subtitleMap.get(activeVideoId) ?? [] : []}
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
