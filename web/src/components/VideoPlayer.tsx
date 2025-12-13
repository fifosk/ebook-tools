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
}

interface VideoPlayerProps {
  files: VideoFile[];
  activeId: string | null;
  onSelectFile: (fileId: string) => void;
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
        }
      | null
  ) => void;
  subtitlesEnabled?: boolean;
  tracks?: SubtitleTrack[];
  cueVisibility?: {
    original: boolean;
    transliteration: boolean;
    translation: boolean;
  };
  subtitleScale?: number;
  subtitleBackgroundOpacity?: number;
}

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties } from 'react';

const DEFAULT_PLAYBACK_RATE = 1;

function sanitiseRate(value: number | null | undefined): number {
  if (!Number.isFinite(value) || !value) {
    return DEFAULT_PLAYBACK_RATE;
  }
  return Math.max(0.25, Math.min(4, value));
}

function sanitiseOpacity(value: number | null | undefined): number | null {
  if (value === null || value === undefined) {
    return null;
  }
  if (!Number.isFinite(value)) {
    return null;
  }
  return Math.max(0, Math.min(1, value));
}

function sanitiseOpacityPercent(value: number | null | undefined): number | null {
  const opacity = sanitiseOpacity(value);
  if (opacity === null) {
    return null;
  }
  const percent = Math.round(opacity * 100);
  const snapped = Math.round(percent / 10) * 10;
  return Math.max(0, Math.min(100, snapped));
}

function injectVttCueStyle(payload: string, backgroundPercent: number, subtitleScale: number): string {
  const clampedBackground = Math.max(0, Math.min(100, Math.round(backgroundPercent / 10) * 10));
  const alpha = clampedBackground / 100;
  const clampedScale = Math.max(0.25, Math.min(4, subtitleScale));
  const scalePercent = Math.round(clampedScale * 100);
  const cueRules = [
    `::cue { font-size: ${scalePercent}% !important; line-height: 1.2 !important; }`,
    clampedBackground === 0
      ? `::cue { background: none !important; background-color: transparent !important; }`
      : `::cue { background: rgba(0, 0, 0, ${alpha}) !important; background-color: rgba(0, 0, 0, ${alpha}) !important; }`,
  ].join('\n');
  const styleBlock = `STYLE\n${cueRules}\n\n`;
  if (!payload) {
    return `WEBVTT\n\n${styleBlock}`;
  }
  if (/^\ufeff?WEBVTT/i.test(payload)) {
    const headerMatch = payload.match(/^\ufeff?WEBVTT[^\n]*\n(?:\n|\r\n)/i);
    if (headerMatch && headerMatch.index === 0) {
      const headerLength = headerMatch[0].length;
      return `${payload.slice(0, headerLength)}${styleBlock}${payload.slice(headerLength)}`;
    }
  }
  return `WEBVTT\n\n${styleBlock}${payload}`;
}

function filterCueTextByVisibility(
  rawText: string,
  visibility: { original: boolean; transliteration: boolean; translation: boolean }
): string {
  if (!rawText) {
    return rawText;
  }
  const lines = rawText.split(/\r?\n/);
  const filtered: string[] = [];

  for (const line of lines) {
    const classMatch = line.match(/<c\.([^>]+)>/i);
    if (classMatch) {
      const classes = classMatch[1]
        .split(/\s+/)
        .map((value) => value.trim())
        .filter(Boolean);
      if (classes.some((value) => value === 'original') && !visibility.original) {
        continue;
      }
      if (classes.some((value) => value === 'transliteration') && !visibility.transliteration) {
        continue;
      }
      if (classes.some((value) => value === 'translation') && !visibility.translation) {
        continue;
      }
    }
    filtered.push(line);
  }

  if (filtered.length === lines.length) {
    return rawText;
  }
  return filtered.join('\n');
}

function extractMediaName(file: VideoFile, fallbackLabel?: string): string {
  const raw = file.name || file.url || fallbackLabel || "";
  if (!raw) {
    return "";
  }
  const withoutQuery = raw.split(/[?#]/)[0];
  const afterSlash = withoutQuery.replace(/\\/g, "/");
  const leaf = afterSlash.substring(afterSlash.lastIndexOf("/") + 1) || afterSlash;
  const trimmedLeaf = leaf.endsWith("/") ? leaf.slice(0, -1) : leaf;
  const dotIndex = trimmedLeaf.lastIndexOf(".");
  if (dotIndex > 0) {
    return trimmedLeaf.slice(0, dotIndex) || trimmedLeaf;
  }
  return trimmedLeaf || raw;
}

const EMPTY_VTT_DATA_URL = 'data:text/vtt;charset=utf-8,WEBVTT%0A%0A';

function selectPrimarySubtitleTrack(tracks: SubtitleTrack[]): SubtitleTrack | null {
  if (!tracks || tracks.length === 0) {
    return null;
  }
  const vtt = tracks.find((track) => {
    const candidate = track.url ?? '';
    const withoutQuery = candidate.split(/[?#]/)[0] ?? '';
    return withoutQuery.toLowerCase().endsWith('.vtt');
  });
  return vtt ?? tracks[0] ?? null;
}

function isNativeWebkitFullscreen(video: HTMLVideoElement | null): boolean {
  if (!video) {
    return false;
  }
  const anyVideo = video as unknown as { webkitDisplayingFullscreen?: boolean; webkitPresentationMode?: string };
  return Boolean(anyVideo.webkitDisplayingFullscreen || anyVideo.webkitPresentationMode === 'fullscreen');
}

export default function VideoPlayer({
  files,
  activeId,
  onSelectFile,
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
  tracks = [],
  cueVisibility = { original: true, transliteration: true, translation: true },
  subtitleScale = 1,
  subtitleBackgroundOpacity,
}: VideoPlayerProps) {
  const elementRef = useRef<HTMLVideoElement | null>(null);
  const fullscreenRef = useRef<HTMLDivElement | null>(null);
  const fullscreenRequestedRef = useRef(false);
  const nativeFullscreenRef = useRef(false);
  const nativeFullscreenReentryRef = useRef(false);
  const nativeFullscreenReentryDeadlineRef = useRef(0);
  const fullscreenActiveFileIdRef = useRef<string | null>(null);
  const sourceChangedWhileFullscreenRef = useRef(false);
  const subtitleTrackElementRef = useRef<HTMLTrackElement | null>(null);
  const pendingSubtitleTrackRef = useRef<SubtitleTrack | null>(null);
  const [subtitleRevision, setSubtitleRevision] = useState(0);
  const cueTextCacheRef = useRef<WeakMap<TextTrackCue, string>>(new WeakMap());
  const labels = files.map((file, index) => ({
    id: file.id,
    label: file.name ?? `Video ${index + 1}`
  }));

  const activeFile = activeId ? files.find((file) => file.id === activeId) ?? null : null;
  const activeIndex = activeFile ? labels.findIndex((file) => file.id === activeFile.id) : -1;
  const fallbackLabel = activeIndex >= 0 ? labels[activeIndex]?.label : undefined;
  const displayName = activeFile ? extractMediaName(activeFile, fallbackLabel) : '';
  const labelText =
    displayName && activeIndex >= 0
      ? `Now playing \u2022 ${displayName} (Video ${activeIndex + 1} of ${labels.length})`
      : displayName
        ? `Now playing \u2022 ${displayName}`
        : activeIndex >= 0
          ? `Now playing \u2022 Video ${activeIndex + 1} of ${labels.length}`
          : 'Now playing';

  const getFullscreenTarget = useCallback(() => fullscreenRef.current ?? elementRef.current, []);

  const activeSubtitleTrack = useMemo(() => selectPrimarySubtitleTrack(tracks), [tracks]);
  const resolvedSubtitleBackgroundOpacity = useMemo(
    () => sanitiseOpacity(subtitleBackgroundOpacity),
    [subtitleBackgroundOpacity],
  );
  const resolvedSubtitleBackgroundOpacityPercent = useMemo(
    () => sanitiseOpacityPercent(subtitleBackgroundOpacity),
    [subtitleBackgroundOpacity],
  );
  const [processedSubtitleUrl, setProcessedSubtitleUrl] = useState<string>(EMPTY_VTT_DATA_URL);
  const videoStyle = useMemo(() => {
    return { '--subtitle-scale': subtitleScale } as CSSProperties;
  }, [subtitleScale]);

  useEffect(() => {
    if (!subtitlesEnabled || !activeSubtitleTrack?.url) {
      setProcessedSubtitleUrl(EMPTY_VTT_DATA_URL);
      return;
    }

    if (resolvedSubtitleBackgroundOpacityPercent === null) {
      setProcessedSubtitleUrl(activeSubtitleTrack.url);
      return;
    }

    const candidate = activeSubtitleTrack.url ?? '';
    const withoutQuery = candidate.split(/[?#]/)[0] ?? '';
    if (!withoutQuery.toLowerCase().endsWith('.vtt')) {
      setProcessedSubtitleUrl(activeSubtitleTrack.url);
      return;
    }

    if (typeof fetch !== 'function') {
      setProcessedSubtitleUrl(activeSubtitleTrack.url);
      return;
    }

    const controller = new AbortController();
    let revokedUrl: string | null = null;

    const run = async () => {
      try {
        const response = await fetch(activeSubtitleTrack.url, { signal: controller.signal });
        if (!response.ok) {
          setProcessedSubtitleUrl(activeSubtitleTrack.url);
          return;
        }
        const raw = await response.text();
        const vtt = injectVttCueStyle(raw, resolvedSubtitleBackgroundOpacityPercent, subtitleScale);
        const blob = new Blob([vtt], { type: 'text/vtt' });
        const objectUrl = URL.createObjectURL(blob);
        revokedUrl = objectUrl;
        setProcessedSubtitleUrl(objectUrl);
      } catch (error) {
        void error;
        setProcessedSubtitleUrl(activeSubtitleTrack.url);
      }
    };

    void run();

    return () => {
      controller.abort();
      if (revokedUrl) {
        URL.revokeObjectURL(revokedUrl);
      }
    };
  }, [activeSubtitleTrack?.url, resolvedSubtitleBackgroundOpacityPercent, subtitleScale, subtitlesEnabled]);

  const applySubtitleTrack = useCallback(
    (track: SubtitleTrack | null) => {
      const trackElement = subtitleTrackElementRef.current;
      if (!trackElement) {
        return;
      }

      const nextLanguage = track?.language || 'und';
      const nextKind = track?.kind || 'subtitles';
      const nextLabel = track?.label || 'Subtitles';

      try {
        trackElement.kind = nextKind;
        trackElement.label = nextLabel;
        trackElement.srclang = nextLanguage;
        trackElement.default = true;
      } catch (error) {
        // Ignore attribute failures in unsupported environments.
      }

      const nextSrc = subtitlesEnabled && track?.url ? processedSubtitleUrl : EMPTY_VTT_DATA_URL;
      if (trackElement.getAttribute('src') !== nextSrc) {
        trackElement.setAttribute('src', nextSrc);
      }

      try {
        const textTrack = trackElement.track;
        if (!subtitlesEnabled || !track?.url || nextSrc === EMPTY_VTT_DATA_URL) {
          textTrack.mode = 'disabled';
        } else {
          textTrack.mode = 'hidden';
          textTrack.mode = 'showing';
        }
      } catch (error) {
        // Ignore text track mode failures in unsupported environments.
      }

      setSubtitleRevision((value) => value + 1);
    },
    [processedSubtitleUrl, subtitlesEnabled],
  );

  const requestFullscreenPlayback = useCallback((force = false) => {
    const target = getFullscreenTarget();
    const videoElement = elementRef.current;
    if (typeof document === 'undefined' || !target || (!force && !isTheaterMode)) {
      return;
    }
    const fullscreenElement =
      document.fullscreenElement ??
      (document as Document & { webkitFullscreenElement?: Element | null }).webkitFullscreenElement ??
      null;
    if (fullscreenElement === target) {
      return;
    }
    const anyTarget = target as unknown as {
      requestFullscreen?: () => Promise<void> | void;
      webkitRequestFullscreen?: () => Promise<void> | void;
      webkitRequestFullScreen?: () => Promise<void> | void;
    };
    if (typeof anyTarget.requestFullscreen === 'function') {
      const result = anyTarget.requestFullscreen();
      if (result && typeof (result as Promise<unknown>).catch === 'function') {
        (result as Promise<unknown>).catch(() => {
          /* Ignore request rejections (e.g. lacking user gesture). */
        });
      }
      fullscreenRequestedRef.current = true;
      return;
    }
    if (typeof anyTarget.webkitRequestFullscreen === 'function') {
      try {
        anyTarget.webkitRequestFullscreen();
        fullscreenRequestedRef.current = true;
        return;
      } catch (error) {
        // Ignore failures caused by user gesture requirements.
      }
    }
    if (typeof anyTarget.webkitRequestFullScreen === 'function') {
      try {
        anyTarget.webkitRequestFullScreen();
        fullscreenRequestedRef.current = true;
        return;
      } catch (error) {
        // Ignore failures caused by user gesture requirements.
      }
    }

    const anyVideo = videoElement as unknown as {
      webkitEnterFullscreen?: () => void;
      webkitEnterFullScreen?: () => void;
    } | null;

    if (!anyVideo) {
      return;
    }

    try {
      if (typeof anyVideo.webkitEnterFullscreen === 'function') {
        anyVideo.webkitEnterFullscreen();
        fullscreenRequestedRef.current = true;
      } else if (typeof anyVideo.webkitEnterFullScreen === 'function') {
        anyVideo.webkitEnterFullScreen();
        fullscreenRequestedRef.current = true;
      }
    } catch (error) {
      // Ignore failures caused by gesture requirements or unsupported environments.
    }
  }, [getFullscreenTarget, isTheaterMode]);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) {
      return;
    }

    const handleBegin = () => {
      nativeFullscreenRef.current = true;
      nativeFullscreenReentryRef.current = false;
      nativeFullscreenReentryDeadlineRef.current = 0;
    };

    const handleEnd = () => {
      nativeFullscreenRef.current = false;
      fullscreenRequestedRef.current = false;
      if (
        nativeFullscreenReentryRef.current &&
        nativeFullscreenReentryDeadlineRef.current > 0 &&
        Date.now() > nativeFullscreenReentryDeadlineRef.current
      ) {
        nativeFullscreenReentryRef.current = false;
        nativeFullscreenReentryDeadlineRef.current = 0;
      }
      if (pendingSubtitleTrackRef.current) {
        const pending = pendingSubtitleTrackRef.current;
        pendingSubtitleTrackRef.current = null;
        setTimeout(() => {
          applySubtitleTrack(pending);
        }, 0);
      }
      if (isTheaterMode) {
        onExitTheaterMode?.('user');
      }
    };

    element.addEventListener('webkitbeginfullscreen', handleBegin as EventListener);
    element.addEventListener('webkitendfullscreen', handleEnd as EventListener);

    return () => {
      element.removeEventListener('webkitbeginfullscreen', handleBegin as EventListener);
      element.removeEventListener('webkitendfullscreen', handleEnd as EventListener);
    };
  }, [applySubtitleTrack, isTheaterMode, onExitTheaterMode]);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) {
      return;
    }

    if (isNativeWebkitFullscreen(element)) {
      pendingSubtitleTrackRef.current = activeSubtitleTrack;
      return;
    }
    pendingSubtitleTrackRef.current = null;
    applySubtitleTrack(activeSubtitleTrack);
  }, [activeFile?.id, activeSubtitleTrack, applySubtitleTrack, processedSubtitleUrl]);

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
    };
    onRegisterControls(controls);
    return () => {
      onRegisterControls(null);
    };
  }, [onRegisterControls, activeFile?.id, requestFullscreenPlayback]);

  const attemptAutoplay = useCallback(() => {
    if (!autoPlay) {
      return;
    }

    const element = elementRef.current;
    if (!element) {
      return;
    }

    try {
      const playResult = element.play();
      if (playResult && typeof playResult.then === 'function') {
        playResult.catch(() => {
          // Ignore autoplay rejections triggered by browser or test environments.
        });
      }
    } catch (error) {
      // Ignore autoplay errors that stem from user gesture requirements.
    }
  }, [autoPlay]);

  useEffect(() => {
    attemptAutoplay();
  }, [attemptAutoplay, activeFile?.id]);

  useEffect(() => {
    const element = elementRef.current;
    if (!element || playbackPosition === null || playbackPosition === undefined) {
      return;
    }

    const clamped = Number.isFinite(playbackPosition) ? Math.max(playbackPosition, 0) : 0;

    if (Math.abs(element.currentTime - clamped) < 0.25) {
      return;
    }

    try {
      element.currentTime = clamped;
    } catch (error) {
      // Ignore assignment failures that can happen in non-media test environments.
    }
  }, [playbackPosition, activeFile?.id]);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) {
      return;
    }
    const safeRate = sanitiseRate(playbackRate);
    if (Math.abs(element.playbackRate - safeRate) < 1e-3) {
      return;
    }
    element.playbackRate = safeRate;
  }, [playbackRate, activeFile?.id]);

  useEffect(() => {
    const element = elementRef.current;
    if (!element || !onPlaybackRateChange) {
      return;
    }
    const handleRateChange = () => {
      onPlaybackRateChange(sanitiseRate(element.playbackRate));
    };
    element.addEventListener('ratechange', handleRateChange);
    return () => {
      element.removeEventListener('ratechange', handleRateChange);
    };
  }, [onPlaybackRateChange, activeFile?.id]);

  const handleTimeUpdate = useCallback(() => {
    const element = elementRef.current;
    if (!element) {
      return;
    }

    onPlaybackPositionChange?.(element.currentTime ?? 0);
  }, [onPlaybackPositionChange]);

  const handlePlay = useCallback(() => {
    onPlaybackStateChange?.('playing');
  }, [onPlaybackStateChange]);

  const handlePause = useCallback(() => {
    onPlaybackStateChange?.('paused');
  }, [onPlaybackStateChange]);

  const handleEnded = useCallback(() => {
    const element = elementRef.current;
    const isNativeFullscreen = Boolean(element && isNativeWebkitFullscreen(element));
    nativeFullscreenReentryRef.current = isNativeFullscreen;
    nativeFullscreenReentryDeadlineRef.current = isNativeFullscreen ? Date.now() + 1500 : 0;
    onPlaybackStateChange?.('paused');
    onPlaybackEnded?.();
  }, [onPlaybackEnded, onPlaybackStateChange]);

  useEffect(() => {
    if (!isTheaterMode) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onExitTheaterMode?.('user');
        fullscreenRequestedRef.current = false;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isTheaterMode, onExitTheaterMode]);

  useEffect(() => {
    const element = elementRef.current;
    const target = getFullscreenTarget();
    if (typeof document === 'undefined' || !target) {
      return;
    }

    const releaseFullscreen = () => {
      const anyDocument = document as Document & {
        exitFullscreen?: () => Promise<void> | void;
        webkitExitFullscreen?: () => Promise<void> | void;
        webkitCancelFullScreen?: () => Promise<void> | void;
      };
      if (typeof anyDocument.exitFullscreen === 'function') {
        const result = anyDocument.exitFullscreen();
        if (result && typeof (result as Promise<unknown>).catch === 'function') {
          (result as Promise<unknown>).catch(() => {
            /* Ignore exit failures in unsupported environments. */
          });
        }
      } else if (typeof anyDocument.webkitExitFullscreen === 'function') {
        try {
          anyDocument.webkitExitFullscreen();
        } catch (error) {
          // Ignore exit failures for unsupported environments.
        }
      } else if (typeof anyDocument.webkitCancelFullScreen === 'function') {
        try {
          anyDocument.webkitCancelFullScreen();
        } catch (error) {
          // Ignore exit failures for unsupported environments.
        }
      }

      const anyVideo = element as unknown as { webkitExitFullscreen?: () => void; webkitExitFullScreen?: () => void } | null;
      if (anyVideo) {
        try {
          if (typeof anyVideo.webkitExitFullscreen === 'function') {
            anyVideo.webkitExitFullscreen();
          } else if (typeof anyVideo.webkitExitFullScreen === 'function') {
            anyVideo.webkitExitFullScreen();
          }
        } catch (error) {
          // Ignore exit failures for unsupported environments.
        }
      }
      fullscreenRequestedRef.current = false;
      fullscreenActiveFileIdRef.current = null;
      sourceChangedWhileFullscreenRef.current = false;
    };

    if (isTheaterMode) {
      requestFullscreenPlayback(false);
    } else {
      const fullscreenElement =
        document.fullscreenElement ??
        (document as Document & { webkitFullscreenElement?: Element | null }).webkitFullscreenElement ??
        null;
      if (fullscreenElement === target || fullscreenRequestedRef.current) {
        releaseFullscreen();
      } else {
        fullscreenRequestedRef.current = false;
      }
    }

    return () => {
      if (!isTheaterMode) {
        return;
      }
      if (
        typeof document !== 'undefined' &&
        (((document.fullscreenElement ??
          (document as Document & { webkitFullscreenElement?: Element | null }).webkitFullscreenElement ??
          null) === target) ||
          fullscreenRequestedRef.current)
      ) {
        releaseFullscreen();
      }
    };
  }, [getFullscreenTarget, isTheaterMode, activeFile?.id, requestFullscreenPlayback]);

  useEffect(() => {
    if (!isTheaterMode) {
      return;
    }
    const activeIdSnapshot = activeFile?.id ?? null;
    if (!fullscreenActiveFileIdRef.current) {
      return;
    }
    if (activeIdSnapshot && fullscreenActiveFileIdRef.current !== activeIdSnapshot) {
      sourceChangedWhileFullscreenRef.current = true;
    }
  }, [activeFile?.id, isTheaterMode]);

  useEffect(() => {
    const target = getFullscreenTarget();
    if (!isTheaterMode || typeof document === 'undefined' || !target) {
      return;
    }

    const handleFullscreenChange = () => {
      const fullscreenElement =
        document.fullscreenElement ??
        (document as Document & { webkitFullscreenElement?: Element | null }).webkitFullscreenElement ??
        null;
      if (fullscreenElement === target) {
        fullscreenRequestedRef.current = true;
        fullscreenActiveFileIdRef.current = activeFile?.id ?? null;
        sourceChangedWhileFullscreenRef.current = false;
        return;
      }
      // If we expected fullscreen but lost it (e.g. source change), try to re-request.
      if (isTheaterMode && sourceChangedWhileFullscreenRef.current) {
        sourceChangedWhileFullscreenRef.current = false;
        requestFullscreenPlayback(false);
        return;
      }
      fullscreenRequestedRef.current = false;
      fullscreenActiveFileIdRef.current = null;
      sourceChangedWhileFullscreenRef.current = false;
      onExitTheaterMode?.('lost');
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange as EventListener);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange as EventListener);
    };
  }, [getFullscreenTarget, isTheaterMode, onExitTheaterMode, requestFullscreenPlayback, activeFile?.id]);

  useEffect(() => {
    const element = elementRef.current;
    if (!element || !isTheaterMode) {
      return;
    }
    const handleLoadedData = () => {
      requestFullscreenPlayback(false);
    };
    element.addEventListener('loadeddata', handleLoadedData);
    return () => {
      element.removeEventListener('loadeddata', handleLoadedData);
    };
  }, [isTheaterMode, activeFile?.id, requestFullscreenPlayback]);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) {
      return;
    }
    if (
      nativeFullscreenReentryRef.current &&
      nativeFullscreenReentryDeadlineRef.current > 0 &&
      Date.now() > nativeFullscreenReentryDeadlineRef.current
    ) {
      nativeFullscreenReentryRef.current = false;
      nativeFullscreenReentryDeadlineRef.current = 0;
      return;
    }
    if (!(nativeFullscreenRef.current || nativeFullscreenReentryRef.current)) {
      return;
    }

    const anyVideo = element as unknown as {
      webkitEnterFullscreen?: () => void;
      webkitEnterFullScreen?: () => void;
      webkitSetPresentationMode?: (mode: string) => void;
      webkitPresentationMode?: string;
    } | null;
    if (!anyVideo) {
      return;
    }

    const forceNativeFullscreenRelayout = () => {
      try {
        element.load();
      } catch (error) {
        // Ignore load failures in unsupported environments.
      }

      try {
        if (typeof anyVideo.webkitSetPresentationMode === 'function') {
          anyVideo.webkitSetPresentationMode('inline');
          requestAnimationFrame(() => {
            try {
              anyVideo.webkitSetPresentationMode?.('fullscreen');
            } catch (error) {
              // Ignore presentation mode failures.
            }
          });
          return;
        }
      } catch (error) {
        // Ignore presentation mode failures.
      }

      try {
        if (typeof anyVideo.webkitEnterFullscreen === 'function') {
          anyVideo.webkitEnterFullscreen();
        } else if (typeof anyVideo.webkitEnterFullScreen === 'function') {
          anyVideo.webkitEnterFullScreen();
        }
      } catch (error) {
        // Ignore fullscreen request failures.
      }
    };

    const nudgeFullscreen = () => {
      try {
        if (typeof anyVideo.webkitSetPresentationMode === 'function') {
          anyVideo.webkitSetPresentationMode('fullscreen');
        } else if (typeof anyVideo.webkitEnterFullscreen === 'function') {
          anyVideo.webkitEnterFullscreen();
        } else if (typeof anyVideo.webkitEnterFullScreen === 'function') {
          anyVideo.webkitEnterFullScreen();
        }
      } catch (error) {
        // Ignore fullscreen request failures.
      }
    };

    const handleLoadedMetadata = () => {
      forceNativeFullscreenRelayout();
    };

    element.addEventListener('loadedmetadata', handleLoadedMetadata, { once: true });
    setTimeout(() => {
      forceNativeFullscreenRelayout();
    }, 50);

    if (nativeFullscreenReentryRef.current && !nativeFullscreenRef.current) {
      setTimeout(() => {
        nativeFullscreenReentryRef.current = false;
        nativeFullscreenReentryDeadlineRef.current = 0;
      }, 250);
    }

    return () => {
      element.removeEventListener('loadedmetadata', handleLoadedMetadata);
    };
  }, [activeFile?.id]);

  useEffect(() => {
    if (!subtitlesEnabled) {
      return;
    }
    const element = elementRef.current;
    if (!element || !element.textTracks) {
      return;
    }
    const track =
      Array.from(element.textTracks).find((item) => item.mode === 'showing' || item.mode === 'hidden') ??
      element.textTracks[0] ??
      null;
    if (!track) {
      return;
    }

    const cache = cueTextCacheRef.current;

    const applyCueVisibility = () => {
      const cues = track.cues;
      if (!cues) {
        return;
      }
      for (let index = 0; index < cues.length; index += 1) {
        const cue = cues[index];
        const cueWithText = cue as VTTCue & { text?: string };
        const baseText = cache.get(cue) ?? cueWithText.text ?? '';
        if (!cache.has(cue)) {
          cache.set(cue, baseText);
        }
        const filteredText = filterCueTextByVisibility(baseText, cueVisibility);
        if (cueWithText.text !== filteredText && typeof cueWithText.text === 'string') {
          cueWithText.text = filteredText;
        }
      }
    };

    applyCueVisibility();
    track.addEventListener('cuechange', applyCueVisibility);
    return () => {
      track.removeEventListener('cuechange', applyCueVisibility);
    };
  }, [cueVisibility, subtitlesEnabled, activeFile?.id, subtitleRevision]);

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
            className="video-player__active-label"
            title={activeFile.name ?? activeFile.url ?? 'Active video'}
            data-testid="video-player-active-label"
          >
            {labelText}
          </div>
          <div className="video-player__canvas">
            <video
              ref={elementRef}
              className="video-player__element"
              style={videoStyle}
              data-testid="video-player"
              controls
              crossOrigin="anonymous"
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
              onLoadedData={attemptAutoplay}
              onTimeUpdate={handleTimeUpdate}
            >
              <track ref={subtitleTrackElementRef} kind="subtitles" label="Subtitles" srcLang="und" default />
              Your browser does not support the video element.
            </video>
          </div>
        </div>
        <div className="video-player__playlist" role="group" aria-label="Video playlist">
          {labels.map((file) => (
            <button
              key={file.id}
              type="button"
              className="video-player__item"
              aria-pressed={file.id === activeId}
              onClick={() => onSelectFile(file.id)}
            >
              {file.label}
            </button>
          ))}
        </div>
      </div>
    </>
  );
}
