/**
 * Utility functions for the VideoPlayer component.
 */

// Re-export shared subtitle utilities from lib/subtitles for backward compat
export type { SubtitleTrack, CueVisibility } from '../../lib/subtitles';
export {
  EMPTY_VTT_DATA_URL,
  decodeDataUrl,
  injectVttCueStyle,
  filterCueTextByVisibility,
  resolveSubtitleFormat,
  isVttSubtitleTrack,
  isAssSubtitleTrack,
  selectPrimarySubtitleTrack,
  selectAssSubtitleTrack,
} from '../../lib/subtitles';

export const DEFAULT_PLAYBACK_RATE = 1;
export const SUMMARY_MARQUEE_SPEED = 28;
export const SUMMARY_MARQUEE_GAP = 32;

export function sanitiseRate(value: number | null | undefined): number {
  if (!Number.isFinite(value) || !value) {
    return DEFAULT_PLAYBACK_RATE;
  }
  return Math.max(0.25, Math.min(4, value));
}

export function sanitiseOpacity(value: number | null | undefined): number | null {
  if (value === null || value === undefined) {
    return null;
  }
  if (!Number.isFinite(value)) {
    return null;
  }
  return Math.max(0, Math.min(1, value));
}

export function sanitiseOpacityPercent(value: number | null | undefined): number | null {
  const opacity = sanitiseOpacity(value);
  if (opacity === null) {
    return null;
  }
  const percent = Math.round(opacity * 100);
  const snapped = Math.round(percent / 10) * 10;
  return Math.max(0, Math.min(100, snapped));
}

export function isSafariBrowser(): boolean {
  if (typeof navigator === 'undefined') {
    return false;
  }
  const ua = navigator.userAgent;
  return /safari/i.test(ua) && !/(chrome|chromium|crios|fxios|edg)/i.test(ua);
}

export function isNativeWebkitFullscreen(video: HTMLVideoElement | null): boolean {
  if (!video) {
    return false;
  }
  const anyVideo = video as unknown as { webkitDisplayingFullscreen?: boolean; webkitPresentationMode?: string };
  return Boolean(anyVideo.webkitDisplayingFullscreen || anyVideo.webkitPresentationMode === 'fullscreen');
}
