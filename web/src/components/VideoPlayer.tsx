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
  tracks?: SubtitleTrack[];
  cueVisibility?: {
    original: boolean;
    transliteration: boolean;
    translation: boolean;
  };
  subtitleScale?: number;
  myLinguistScale?: number;
  subtitleBackgroundOpacity?: number;
}

import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import { formatMediaDropdownLabel } from '../utils/mediaLabels';
import { formatDurationLabel } from '../utils/timeFormatters';
import { DEFAULT_LANGUAGE_FLAG, resolveLanguageFlag } from '../constants/languageCodes';
import { normalizeLanguageLabel } from '../utils/languages';
import EmojiIcon from './EmojiIcon';
import PlayerChannelBug from './PlayerChannelBug';
import SubtitleTrackOverlay from './video-subtitles/SubtitleTrackOverlay';

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

function selectAssSubtitleTrack(tracks: SubtitleTrack[]): SubtitleTrack | null {
  if (!tracks || tracks.length === 0) {
    return null;
  }
  return (
    tracks.find((track) => {
      const candidate = track.url ?? '';
      const withoutQuery = candidate.split(/[?#]/)[0] ?? '';
      return withoutQuery.toLowerCase().endsWith('.ass');
    }) ?? null
  );
}

function isAssSubtitleTrack(track: SubtitleTrack | null): boolean {
  if (!track?.url) {
    return false;
  }
  const withoutQuery = track.url.split(/[?#]/)[0] ?? '';
  return withoutQuery.toLowerCase().endsWith('.ass');
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
  tracks = [],
  cueVisibility = { original: true, transliteration: true, translation: true },
  subtitleScale = 1,
  myLinguistScale,
  subtitleBackgroundOpacity,
}: VideoPlayerProps) {
  const playlistSelectId = useId();
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
    label: formatMediaDropdownLabel(file.name ?? file.url, `Video ${index + 1}`),
  }));

  const activeFile = activeId ? files.find((file) => file.id === activeId) ?? null : null;

  const getFullscreenTarget = useCallback(() => fullscreenRef.current ?? elementRef.current, []);

  const activeSubtitleTrack = useMemo(() => selectPrimarySubtitleTrack(tracks), [tracks]);
  const overlaySubtitleTrack = useMemo(() => selectAssSubtitleTrack(tracks), [tracks]);
  const resolvedSubtitleBackgroundOpacity = useMemo(
    () => sanitiseOpacity(subtitleBackgroundOpacity),
    [subtitleBackgroundOpacity],
  );
  const resolvedSubtitleBackgroundOpacityPercent = useMemo(
    () => sanitiseOpacityPercent(subtitleBackgroundOpacity),
    [subtitleBackgroundOpacity],
  );
  const isFileProtocol = typeof window !== 'undefined' && window.location.protocol === 'file:';
  const allowCrossOrigin = !isFileProtocol;
  const [processedSubtitleUrl, setProcessedSubtitleUrl] = useState<string>(EMPTY_VTT_DATA_URL);
  const [subtitleOverlayActive, setSubtitleOverlayActive] = useState(false);
  const [coverFailed, setCoverFailed] = useState(false);
  const [secondaryCoverFailed, setSecondaryCoverFailed] = useState(false);
  const [playbackClock, setPlaybackClock] = useState({ current: 0, duration: 0 });
  const playbackClockRef = useRef({ current: 0, duration: 0 });
  useEffect(() => {
    setCoverFailed(false);
  }, [infoBadge?.coverUrl]);
  useEffect(() => {
    setSecondaryCoverFailed(false);
  }, [infoBadge?.coverSecondaryUrl]);
  useEffect(() => {
    playbackClockRef.current = { current: 0, duration: 0 };
    setPlaybackClock({ current: 0, duration: 0 });
  }, [activeFile?.id]);
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
    if (files.length <= 1) {
      return null;
    }
    const index = activeFile ? files.findIndex((file) => file.id === activeFile.id) : -1;
    const resolvedIndex = index >= 0 ? index + 1 : 1;
    return `Video ${resolvedIndex} / ${files.length}`;
  }, [activeFile, files]);
  const timelineLabel = useMemo(() => {
    if (!Number.isFinite(playbackClock.duration) || playbackClock.duration <= 0) {
      return null;
    }
    const played = Math.min(Math.max(playbackClock.current, 0), playbackClock.duration);
    const remaining = Math.max(playbackClock.duration - played, 0);
    return `${formatDurationLabel(played)} / ${formatDurationLabel(remaining)} remaining`;
  }, [playbackClock.current, playbackClock.duration]);
  const showInfoHeader = Boolean(
    infoBadge &&
      (infoBadge.title ||
        infoBadge.meta ||
        infoBadge.coverUrl ||
        infoBadge.glyph ||
        languageFlags.length > 0 ||
        segmentLabel ||
        timelineLabel),
  );
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

    if (isFileProtocol || typeof fetch !== 'function') {
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
  }, [activeSubtitleTrack?.url, isFileProtocol, resolvedSubtitleBackgroundOpacityPercent, subtitleScale, subtitlesEnabled]);

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
      const wantsEnabled = Boolean(
        subtitlesEnabled && track?.url && nextSrc !== EMPTY_VTT_DATA_URL && !subtitleOverlayActive && !isAssSubtitleTrack(track),
      );

      const setTrackSrc = (src: string) => {
        if (trackElement.getAttribute('src') !== src) {
          trackElement.setAttribute('src', src);
        }
        try {
          // Some browsers (notably iOS Safari) behave more consistently when using the property setter.
          trackElement.src = src;
        } catch (error) {
          void error;
        }
      };

      const bumpRevision = () => {
        setSubtitleRevision((value) => value + 1);
      };

      const applyEnabledMode = () => {
        try {
          const textTrack = trackElement.track;
          textTrack.mode = 'hidden';
          const show = () => {
            try {
              textTrack.mode = 'showing';
            } catch (error) {
              void error;
            }
          };
          show();
          if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
            window.requestAnimationFrame(show);
          }
          setTimeout(show, 0);
        } catch (error) {
          // Ignore text track mode failures in unsupported environments.
        }
      };

      const applyDisabledMode = () => {
        try {
          const textTrack = trackElement.track;
          textTrack.mode = 'disabled';
        } catch (error) {
          // Ignore text track mode failures in unsupported environments.
        }
      };

      const previousSrc = trackElement.getAttribute('src') ?? '';
      const needsReload = wantsEnabled && previousSrc === EMPTY_VTT_DATA_URL && nextSrc !== EMPTY_VTT_DATA_URL;

      if (needsReload) {
        // Safari can fail to restore cues after disabling a track unless the source is reloaded asynchronously.
        setTrackSrc(EMPTY_VTT_DATA_URL);
        applyDisabledMode();
        const scheduleApply = () => {
          setTrackSrc(nextSrc);
          applyEnabledMode();
          bumpRevision();
        };
        if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
          window.requestAnimationFrame(scheduleApply);
        } else {
          setTimeout(scheduleApply, 0);
        }
        return;
      }

      setTrackSrc(nextSrc);
      if (!wantsEnabled) {
        applyDisabledMode();
      } else {
        applyEnabledMode();
      }
      bumpRevision();
    },
    [processedSubtitleUrl, subtitlesEnabled, subtitleOverlayActive],
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
      fullscreenActiveFileIdRef.current = activeFile?.id ?? null;
      sourceChangedWhileFullscreenRef.current = false;
      return;
    }
    if (typeof anyTarget.webkitRequestFullscreen === 'function') {
      try {
        anyTarget.webkitRequestFullscreen();
        fullscreenRequestedRef.current = true;
        fullscreenActiveFileIdRef.current = activeFile?.id ?? null;
        sourceChangedWhileFullscreenRef.current = false;
        return;
      } catch (error) {
        // Ignore failures caused by user gesture requirements.
      }
    }
    if (typeof anyTarget.webkitRequestFullScreen === 'function') {
      try {
        anyTarget.webkitRequestFullScreen();
        fullscreenRequestedRef.current = true;
        fullscreenActiveFileIdRef.current = activeFile?.id ?? null;
        sourceChangedWhileFullscreenRef.current = false;
        return;
      } catch (error) {
        // Ignore failures caused by user gesture requirements.
      }
    }

    const presentationVideo = videoElement as unknown as
      | { webkitSetPresentationMode?: (mode: string) => void; webkitPresentationMode?: string }
      | null;
    if (presentationVideo && typeof presentationVideo.webkitSetPresentationMode === 'function') {
      try {
        if (presentationVideo.webkitPresentationMode !== 'fullscreen') {
          presentationVideo.webkitSetPresentationMode('fullscreen');
        }
        fullscreenRequestedRef.current = true;
        fullscreenActiveFileIdRef.current = activeFile?.id ?? null;
        sourceChangedWhileFullscreenRef.current = false;
        return;
      } catch (error) {
        void error;
      }
    }

    const legacyVideo = videoElement as unknown as {
      webkitEnterFullscreen?: () => void;
      webkitEnterFullScreen?: () => void;
    } | null;

    if (!legacyVideo) {
      return;
    }

    try {
      if (typeof legacyVideo.webkitEnterFullscreen === 'function') {
        legacyVideo.webkitEnterFullscreen();
        fullscreenRequestedRef.current = true;
      } else if (typeof legacyVideo.webkitEnterFullScreen === 'function') {
        legacyVideo.webkitEnterFullScreen();
        fullscreenRequestedRef.current = true;
      }
    } catch (error) {
      // Ignore failures caused by gesture requirements or unsupported environments.
    }
  }, [activeFile?.id, getFullscreenTarget, isTheaterMode]);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) {
      return;
    }

    const handleBegin = () => {
      nativeFullscreenRef.current = true;
      nativeFullscreenReentryRef.current = false;
      nativeFullscreenReentryDeadlineRef.current = 0;
      fullscreenActiveFileIdRef.current = activeFile?.id ?? null;
      sourceChangedWhileFullscreenRef.current = false;
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
      const ended = Boolean(element.ended);
      const treatAsLost =
        Boolean(isTheaterMode) && (sourceChangedWhileFullscreenRef.current || nativeFullscreenReentryRef.current || ended);
      sourceChangedWhileFullscreenRef.current = false;
      if (pendingSubtitleTrackRef.current) {
        const pending = pendingSubtitleTrackRef.current;
        pendingSubtitleTrackRef.current = null;
        setTimeout(() => {
          applySubtitleTrack(pending);
        }, 0);
      }
      if (isTheaterMode) {
        onExitTheaterMode?.(treatAsLost ? 'lost' : 'user');
        if (!treatAsLost) {
          nativeFullscreenReentryRef.current = false;
          nativeFullscreenReentryDeadlineRef.current = 0;
        }
      }
    };

    element.addEventListener('webkitbeginfullscreen', handleBegin as EventListener);
    element.addEventListener('webkitendfullscreen', handleEnd as EventListener);

    return () => {
      element.removeEventListener('webkitbeginfullscreen', handleBegin as EventListener);
      element.removeEventListener('webkitendfullscreen', handleEnd as EventListener);
    };
  }, [activeFile?.id, applySubtitleTrack, isTheaterMode, onExitTheaterMode]);

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

  const updatePlaybackClock = useCallback(() => {
    const element = elementRef.current;
    if (!element) {
      return;
    }
    const nextCurrent = Number.isFinite(element.currentTime) ? Math.max(0, Math.floor(element.currentTime)) : 0;
    const nextDuration = Number.isFinite(element.duration) ? Math.max(0, Math.floor(element.duration)) : 0;
    const last = playbackClockRef.current;
    if (last.current === nextCurrent && last.duration === nextDuration) {
      return;
    }
    playbackClockRef.current = { current: nextCurrent, duration: nextDuration };
    setPlaybackClock({ current: nextCurrent, duration: nextDuration });
  }, []);

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
    updatePlaybackClock();
  }, [playbackPosition, activeFile?.id, updatePlaybackClock]);

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
    updatePlaybackClock();
    onPlaybackPositionChange?.(element.currentTime ?? 0);
  }, [onPlaybackPositionChange, updatePlaybackClock]);

  const handleLoadedData = useCallback(() => {
    attemptAutoplay();
    updatePlaybackClock();
  }, [attemptAutoplay, updatePlaybackClock]);

  const handleLoadedMetadata = useCallback(() => {
    updatePlaybackClock();
  }, [updatePlaybackClock]);

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
      const anyVideo = element as unknown as
        | {
            webkitExitFullscreen?: () => void;
            webkitExitFullScreen?: () => void;
            webkitSetPresentationMode?: (mode: string) => void;
          }
        | null;
      if (anyVideo) {
        try {
          if (typeof anyVideo.webkitSetPresentationMode === 'function') {
            anyVideo.webkitSetPresentationMode('inline');
          }
        } catch (error) {
          // Ignore presentation mode failures.
        }
      }

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

      const anyLegacyVideo = element as unknown as { webkitExitFullscreen?: () => void; webkitExitFullScreen?: () => void } | null;
      if (anyLegacyVideo) {
        try {
          if (typeof anyLegacyVideo.webkitExitFullscreen === 'function') {
            anyLegacyVideo.webkitExitFullscreen();
          } else if (typeof anyLegacyVideo.webkitExitFullScreen === 'function') {
            anyLegacyVideo.webkitExitFullScreen();
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
          <div className="video-player__canvas" style={canvasStyle}>
            {infoBadge && showInfoHeader ? (
              <div className="player-panel__player-info-header video-player__info-header" aria-hidden="true">
                <div className="video-player__info-header-left">
                  <PlayerChannelBug
                    glyph={(infoBadge.glyph ?? '').trim() || 'TV'}
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
                        {infoBadge.meta ? (
                          <span className="video-player__info-meta">{infoBadge.meta}</span>
                        ) : null}
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
            ) : null}
            <video
              ref={elementRef}
              className="video-player__element"
              style={videoStyle}
              data-testid="video-player"
              controls
              crossOrigin={allowCrossOrigin ? 'anonymous' : undefined}
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
              cueVisibility={cueVisibility}
              subtitleScale={subtitleScale}
              subtitleBackgroundOpacity={resolvedSubtitleBackgroundOpacity}
              onOverlayActiveChange={setSubtitleOverlayActive}
              jobId={jobId}
              jobOriginalLanguage={jobOriginalLanguage}
              jobTranslationLanguage={jobTranslationLanguage}
            />
          </div>
        </div>
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
