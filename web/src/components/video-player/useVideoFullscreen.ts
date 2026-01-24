/**
 * Hook for managing fullscreen/theater mode in the video player.
 */

import { useCallback, useEffect, useRef } from 'react';
import type { SubtitleTrack } from './utils';
import { isNativeWebkitFullscreen } from './utils';

export interface UseVideoFullscreenOptions {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  fullscreenRef: React.RefObject<HTMLDivElement | null>;
  isTheaterMode: boolean;
  activeFileId: string | null;
  onExitTheaterMode?: (reason?: 'user' | 'lost') => void;
  applySubtitleTrack: (track: SubtitleTrack | null) => void;
  pendingSubtitleTrackRef: React.MutableRefObject<SubtitleTrack | null>;
  activeSubtitleTrack: SubtitleTrack | null;
}

export interface VideoFullscreenState {
  requestFullscreenPlayback: (force?: boolean) => void;
  getFullscreenTarget: () => HTMLElement | null;
  fullscreenRequestedRef: React.MutableRefObject<boolean>;
  nativeFullscreenRef: React.MutableRefObject<boolean>;
  nativeFullscreenReentryRef: React.MutableRefObject<boolean>;
}

export function useVideoFullscreen({
  videoRef,
  fullscreenRef,
  isTheaterMode,
  activeFileId,
  onExitTheaterMode,
  applySubtitleTrack,
  pendingSubtitleTrackRef,
  activeSubtitleTrack,
}: UseVideoFullscreenOptions): VideoFullscreenState {
  const fullscreenRequestedRef = useRef(false);
  const nativeFullscreenRef = useRef(false);
  const nativeFullscreenReentryRef = useRef(false);
  const nativeFullscreenReentryDeadlineRef = useRef(0);
  const fullscreenActiveFileIdRef = useRef<string | null>(null);
  const sourceChangedWhileFullscreenRef = useRef(false);

  const getFullscreenTarget = useCallback(
    () => fullscreenRef.current ?? videoRef.current,
    [fullscreenRef, videoRef]
  );

  const requestFullscreenPlayback = useCallback((force = false) => {
    const target = getFullscreenTarget();
    const videoElement = videoRef.current;
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
      fullscreenActiveFileIdRef.current = activeFileId ?? null;
      sourceChangedWhileFullscreenRef.current = false;
      return;
    }
    if (typeof anyTarget.webkitRequestFullscreen === 'function') {
      try {
        anyTarget.webkitRequestFullscreen();
        fullscreenRequestedRef.current = true;
        fullscreenActiveFileIdRef.current = activeFileId ?? null;
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
        fullscreenActiveFileIdRef.current = activeFileId ?? null;
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
        fullscreenActiveFileIdRef.current = activeFileId ?? null;
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
  }, [activeFileId, getFullscreenTarget, isTheaterMode, videoRef]);

  // Handle native webkit fullscreen events (iOS Safari)
  useEffect(() => {
    const element = videoRef.current;
    if (!element) {
      return;
    }

    const handleBegin = () => {
      nativeFullscreenRef.current = true;
      nativeFullscreenReentryRef.current = false;
      nativeFullscreenReentryDeadlineRef.current = 0;
      fullscreenActiveFileIdRef.current = activeFileId ?? null;
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
  }, [activeFileId, applySubtitleTrack, isTheaterMode, onExitTheaterMode, pendingSubtitleTrackRef, videoRef]);

  // Handle subtitle track application when not in native fullscreen
  useEffect(() => {
    const element = videoRef.current;
    if (!element) {
      return;
    }

    if (isNativeWebkitFullscreen(element)) {
      pendingSubtitleTrackRef.current = activeSubtitleTrack;
      return;
    }
    pendingSubtitleTrackRef.current = null;
    applySubtitleTrack(activeSubtitleTrack);
  }, [activeFileId, activeSubtitleTrack, applySubtitleTrack, pendingSubtitleTrackRef, videoRef]);

  // Handle escape key to exit theater mode
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

  // Request/release fullscreen based on theater mode
  useEffect(() => {
    const element = videoRef.current;
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
  }, [getFullscreenTarget, isTheaterMode, activeFileId, requestFullscreenPlayback, videoRef]);

  // Track source changes while in fullscreen
  useEffect(() => {
    if (!isTheaterMode) {
      return;
    }
    const activeIdSnapshot = activeFileId ?? null;
    if (!fullscreenActiveFileIdRef.current) {
      return;
    }
    if (activeIdSnapshot && fullscreenActiveFileIdRef.current !== activeIdSnapshot) {
      sourceChangedWhileFullscreenRef.current = true;
    }
  }, [activeFileId, isTheaterMode]);

  // Handle fullscreen change events
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
        fullscreenActiveFileIdRef.current = activeFileId ?? null;
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
  }, [getFullscreenTarget, isTheaterMode, onExitTheaterMode, requestFullscreenPlayback, activeFileId]);

  // Re-request fullscreen on loadeddata in theater mode
  useEffect(() => {
    const element = videoRef.current;
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
  }, [isTheaterMode, activeFileId, requestFullscreenPlayback, videoRef]);

  // Handle native fullscreen re-entry for iOS Safari
  useEffect(() => {
    const element = videoRef.current;
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
  }, [activeFileId, videoRef]);

  return {
    requestFullscreenPlayback,
    getFullscreenTarget,
    fullscreenRequestedRef,
    nativeFullscreenRef,
    nativeFullscreenReentryRef,
  };
}
