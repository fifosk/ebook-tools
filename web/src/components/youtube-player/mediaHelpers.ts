/**
 * Media-related helper functions for YouTube Player
 * Functions for building subtitle tracks, resolving media URLs, and other media operations
 */

import type { SubtitleTrack } from '../VideoPlayer';

/**
 * Build sibling subtitle tracks for a video by trying common subtitle extensions
 * @param videoUrl - The video URL to generate subtitle URLs from
 * @param replaceUrlExtension - Function to replace URL extension
 * @param resolveSubtitleUrl - Function to resolve subtitle URL with auth tokens
 * @param subtitleFormatFromPath - Function to extract subtitle format from path
 * @returns Array of subtitle tracks with .ass, .vtt, and .srt alternatives
 */
export function buildSiblingSubtitleTracks(
  videoUrl: string | null | undefined,
  replaceUrlExtension: (url: string, suffix: string) => string | null,
  resolveSubtitleUrl: (url: string, format?: string | null) => string,
  subtitleFormatFromPath: (path: string) => string | null
): SubtitleTrack[] {
  if (!videoUrl) {
    return [];
  }
  const candidates = ['.ass', '.vtt', '.srt']
    .map((suffix) => replaceUrlExtension(videoUrl, suffix))
    .filter((candidate): candidate is string => Boolean(candidate));
  if (candidates.length === 0) {
    return [];
  }
  return candidates.map((candidate, index) => {
    const format = subtitleFormatFromPath(candidate);
    return {
      url: resolveSubtitleUrl(candidate, format),
      label: index === 0 ? 'Subtitles' : `Subtitles (${index + 1})`,
      kind: 'subtitles',
      language: 'und',
      format: format || undefined,
    };
  });
}

/**
 * Create a resolver function for job-based media URLs (not library)
 * Handles /api/ paths, absolute paths, and URLs with proper token appending
 */
export function createJobMediaResolver(
  appendAccessToken: (url: string) => string
): (jobId: string, value: unknown) => string | null {
  return (jobId: string, value: unknown) => {
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
}
