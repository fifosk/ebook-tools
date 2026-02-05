/**
 * Audio track URL extraction and selection.
 *
 * Centralises the logic for picking the correct audio URL from a chunk's
 * `audioTracks` object.  Handles the many possible key variants
 * (orig/original, trans/translation, orig_trans/combined/mix) and
 * prioritises based on which tracks are enabled.
 */

import type { AudioTrackMetadata } from '../../api/dtos';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import { resolveStorageUrl } from './chunkResolver';

type TrackMap = Record<string, AudioTrackMetadata | null | undefined>;

function pickUrl(tracks: TrackMap, ...keys: string[]): string | null {
  for (const key of keys) {
    const entry = tracks[key];
    const url = entry?.url ?? entry?.path ?? null;
    if (url) return url;
  }
  return null;
}

/** Extract the raw (un-resolved) original track URL. */
export function extractOriginalUrl(audioTracks: TrackMap | null | undefined): string | null {
  if (!audioTracks) return null;
  return pickUrl(audioTracks, 'orig', 'original');
}

/** Extract the raw (un-resolved) translation track URL. */
export function extractTranslationUrl(audioTracks: TrackMap | null | undefined): string | null {
  if (!audioTracks) return null;
  return pickUrl(audioTracks, 'translation', 'trans');
}

/** Extract the raw (un-resolved) combined/mix track URL. */
export function extractCombinedUrl(audioTracks: TrackMap | null | undefined): string | null {
  if (!audioTracks) return null;
  return pickUrl(audioTracks, 'orig_trans', 'combined', 'mix');
}

/**
 * Select the best audio URL based on which tracks are enabled.
 *
 * Returns a resolved (fetch-ready) URL or null.
 */
export function resolveChunkAudioUrl(
  chunk: LiveMediaChunk,
  jobId: string | null,
  originalAudioEnabled: boolean,
  translationAudioEnabled: boolean,
): string | null {
  const tracks = (chunk.audioTracks ?? null) as TrackMap | null;
  const translationUrl = extractTranslationUrl(tracks);
  const originalUrl = extractOriginalUrl(tracks);
  const combinedUrl = extractCombinedUrl(tracks);

  const candidate =
    (translationAudioEnabled ? translationUrl : null) ??
    (originalAudioEnabled ? originalUrl : null) ??
    (translationAudioEnabled ? combinedUrl : null) ??
    (originalAudioEnabled ? combinedUrl : null) ??
    translationUrl ??
    originalUrl ??
    combinedUrl;

  return resolveStorageUrl(candidate, jobId);
}
