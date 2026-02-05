/**
 * Chunk key and metadata URL resolution.
 *
 * Centralises the logic for deriving a stable cache/identity key from a
 * LiveMediaChunk and resolving its metadata URL.  Previously duplicated
 * across useChunkPrefetch, player-panel/utils, and
 * useInteractiveAudioSequence.
 */

import { appendAccessTokenToStorageUrl, buildStorageUrl } from '../../api/client';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';

/**
 * Derive a stable identity key for a chunk.
 *
 * Tries fields in priority order: chunkId, rangeFragment, metadataPath,
 * metadataUrl, and finally the sentence range.
 */
export function resolveChunkKey(chunk: LiveMediaChunk | null): string | null {
  if (!chunk) {
    return null;
  }
  return (
    chunk.chunkId ??
    chunk.rangeFragment ??
    chunk.metadataPath ??
    chunk.metadataUrl ??
    (chunk.startSentence !== null || chunk.endSentence !== null
      ? `${chunk.startSentence ?? 'na'}-${chunk.endSentence ?? 'na'}`
      : null)
  );
}

/**
 * Resolve a raw value (URL or relative path) into a fetch-ready storage
 * URL with access tokens appended.
 */
export function resolveStorageUrl(value: string | null, jobId: string | null): string | null {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (/^[a-z]+:\/\//i.test(trimmed) || trimmed.startsWith('data:') || trimmed.startsWith('blob:')) {
    return appendAccessTokenToStorageUrl(trimmed);
  }
  return buildStorageUrl(trimmed, jobId ?? null);
}

/**
 * Resolve the metadata fetch URL for a chunk.
 *
 * Prefers `metadataUrl` (absolute) over `metadataPath` (relative).
 */
export function resolveChunkMetadataUrl(chunk: LiveMediaChunk, jobId: string | null): string | null {
  if (chunk.metadataUrl) {
    return resolveStorageUrl(chunk.metadataUrl, jobId);
  }
  if (chunk.metadataPath) {
    return resolveStorageUrl(chunk.metadataPath, jobId);
  }
  return null;
}
