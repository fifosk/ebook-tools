import type { SubtitleTrack } from './types';

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
