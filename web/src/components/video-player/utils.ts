/**
 * Utility functions for the VideoPlayer component.
 */

export const DEFAULT_PLAYBACK_RATE = 1;
export const SUMMARY_MARQUEE_SPEED = 28;
export const SUMMARY_MARQUEE_GAP = 32;
export const EMPTY_VTT_DATA_URL = 'data:text/vtt;charset=utf-8,WEBVTT%0A%0A';

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

export function injectVttCueStyle(payload: string, backgroundPercent: number, subtitleScale: number): string {
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

export function decodeDataUrl(value: string): string | null {
  const match = value.match(/^data:(.*?)(;base64)?,(.*)$/);
  if (!match) {
    return null;
  }
  const isBase64 = Boolean(match[2]);
  const payload = match[3] ?? '';
  try {
    if (isBase64) {
      return atob(payload);
    }
    return decodeURIComponent(payload);
  } catch {
    return null;
  }
}

export interface CueVisibility {
  original: boolean;
  transliteration: boolean;
  translation: boolean;
}

export function filterCueTextByVisibility(rawText: string, visibility: CueVisibility): string {
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

export interface SubtitleTrack {
  url: string;
  label?: string;
  kind?: string;
  language?: string;
  format?: string;
}

export function resolveSubtitleFormat(track: SubtitleTrack | null): string {
  if (!track) {
    return '';
  }
  if (track.format) {
    const cleaned = track.format.split(/[?#]/, 1)[0] ?? track.format;
    return cleaned.toLowerCase();
  }
  const candidate = track.url ?? '';
  if (candidate.startsWith('data:text/vtt')) {
    return 'vtt';
  }
  const withoutQuery = candidate.split(/[?#]/)[0] ?? '';
  const match = withoutQuery.match(/\.([^.\\/]+)$/);
  return match ? match[1].toLowerCase() : '';
}

export function isVttSubtitleTrack(track: SubtitleTrack | null): boolean {
  return resolveSubtitleFormat(track) === 'vtt';
}

export function isAssSubtitleTrack(track: SubtitleTrack | null): boolean {
  return resolveSubtitleFormat(track) === 'ass';
}

export function selectPrimarySubtitleTrack(tracks: SubtitleTrack[]): SubtitleTrack | null {
  if (!tracks || tracks.length === 0) {
    return null;
  }
  const vtt = tracks.find((track) => isVttSubtitleTrack(track));
  return vtt ?? tracks[0] ?? null;
}

export function selectAssSubtitleTrack(tracks: SubtitleTrack[]): SubtitleTrack | null {
  if (!tracks || tracks.length === 0) {
    return null;
  }
  return tracks.find((track) => isAssSubtitleTrack(track)) ?? null;
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
