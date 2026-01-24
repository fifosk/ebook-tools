/**
 * Hook for resolving and mapping subtitle tracks to video files.
 */

import { useCallback, useMemo } from 'react';
import type { LiveMediaItem } from '../../hooks/useLiveMedia';
import type { SubtitleTrack } from '../VideoPlayer';
import { subtitleFormatFromPath } from '../../utils/subtitles';
import { buildMediaFileId } from '../player-panel/utils';
import { replaceUrlExtension } from './utils';
import {
  resolveInlineSubtitlePayload,
  buildSubtitleDataUrl,
  extractFileSuffix,
} from './subtitleHelpers';
import { buildSiblingSubtitleTracks as buildSiblingSubtitleTracksHelper } from './mediaHelpers';

const SUBTITLE_FORMAT_PRIORITIES = ['ass', 'vtt', 'srt', 'text'];

interface TextEntry {
  url?: string | null;
  name?: string | null;
  path?: string | null;
  range_fragment?: string | null;
  chunk_id?: string | null;
  language?: string;
}

export interface UseSubtitleTracksOptions {
  jobId: string;
  isExportMode: boolean;
  inlineSubtitles: Record<string, string> | null;
  videoItems: LiveMediaItem[];
  textItems: TextEntry[];
  resolveMediaUrl: (url: string) => string;
  deriveBaseId: (item: Pick<LiveMediaItem, 'name' | 'url'> | null | undefined) => string | null;
}

export interface SubtitleTracksState {
  /** Map of video ID to subtitle tracks */
  subtitleMap: Map<string, SubtitleTrack[]>;
  /** Build sibling subtitle tracks for a video URL */
  buildSiblingSubtitleTracks: (videoUrl: string | null | undefined) => SubtitleTrack[];
  /** Get active subtitle tracks for a video */
  getActiveSubtitleTracks: (
    activeVideoId: string | null,
    videoFiles: Array<{ id: string; url: string }>,
  ) => SubtitleTrack[];
}

function formatRank(entry: TextEntry): number {
  const suffix =
    extractFileSuffix(entry.url ?? null) ||
    extractFileSuffix(entry.name ?? null) ||
    extractFileSuffix(entry.path ?? null);
  const score = SUBTITLE_FORMAT_PRIORITIES.indexOf(suffix ?? '');
  return score >= 0 ? score : SUBTITLE_FORMAT_PRIORITIES.length;
}

function scoreTrack(
  entry: TextEntry,
  context: { range: string | null; chunk: string | null; base: string | null },
  deriveBaseId: (item: Pick<LiveMediaItem, 'name' | 'url'> | null | undefined) => string | null,
): { entry: TextEntry; score: readonly [number, number, number, number] } {
  const formatScore = formatRank(entry);
  const rangeScore = context.range
    ? entry.range_fragment === context.range
      ? 0
      : 2
    : entry.range_fragment
      ? 1
      : 3;
  // Cast entry to compatible type - safe because deriveBaseId handles nulls gracefully
  const entryForBaseId = entry.name && entry.url ? { name: entry.name, url: entry.url } : null;
  const baseScore = context.base ? (deriveBaseId(entryForBaseId) === context.base ? 0 : 2) : 1;
  const chunkScore = context.chunk
    ? entry.chunk_id === context.chunk
      ? 0
      : 2
    : entry.chunk_id
      ? 1
      : 3;
  return { entry, score: [formatScore, rangeScore, chunkScore, baseScore] as const };
}

export function useSubtitleTracks({
  jobId,
  isExportMode,
  inlineSubtitles,
  videoItems,
  textItems,
  resolveMediaUrl,
  deriveBaseId,
}: UseSubtitleTracksOptions): SubtitleTracksState {
  const resolveSubtitleUrl = useCallback(
    (url: string, format?: string | null): string => {
      const resolved = resolveMediaUrl(url);
      if (!isExportMode) {
        return resolved;
      }
      const payload = resolveInlineSubtitlePayload(resolved, inlineSubtitles);
      if (!payload) {
        return resolved;
      }
      const inferredFormat = format || subtitleFormatFromPath(resolved);
      return buildSubtitleDataUrl(payload, inferredFormat);
    },
    [inlineSubtitles, isExportMode, resolveMediaUrl],
  );

  const subtitleMap = useMemo(() => {
    const map = new Map<string, SubtitleTrack[]>();

    // Build fallback tracks from all text entries
    const fallbackTracks: SubtitleTrack[] = textItems
      .filter((entry) => typeof entry.url === 'string' && entry.url.length > 0)
      .sort((a, b) => formatRank(a) - formatRank(b))
      .map((entry) => {
        const format = subtitleFormatFromPath(entry.url ?? entry.name ?? entry.path);
        return {
          url: resolveSubtitleUrl(entry.url!, format),
          label: entry.name ?? entry.url ?? 'Subtitles',
          kind: 'subtitles',
          language: entry.language ?? undefined,
          format: format || undefined,
        };
      });

    // Map subtitle tracks to each video
    videoItems.forEach((video, index) => {
      if (typeof video.url !== 'string' || video.url.length === 0) {
        return;
      }
      const videoId = buildMediaFileId(video, index);
      const baseId = deriveBaseId(video);
      const range = video.range_fragment ?? null;
      const chunkId = video.chunk_id ?? null;

      // Find matching text entries
      const matches = textItems.filter((entry) => {
        if (!entry.url) {
          return false;
        }
        if (range && entry.range_fragment && entry.range_fragment === range) {
          return true;
        }
        if (chunkId && entry.chunk_id && entry.chunk_id === chunkId) {
          return true;
        }
        const entryForBaseId = entry.name && entry.url ? { name: entry.name, url: entry.url } : null;
        const entryBase = deriveBaseId(entryForBaseId);
        return !!baseId && entryBase === baseId;
      });

      if (matches.length === 0) {
        if (fallbackTracks.length > 0) {
          map.set(videoId, fallbackTracks);
        }
        return;
      }

      // Score and sort matches
      const scored = matches
        .filter((entry) => typeof entry.url === 'string' && entry.url.length > 0)
        .map((entry) =>
          scoreTrack(entry, { range, chunk: chunkId, base: baseId }, deriveBaseId),
        )
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

      const orderedEntries = scored.map((entry) => entry.entry);
      if (orderedEntries.length > 0) {
        const seen = new Set<string>();
        const unique = orderedEntries.filter((entry) => {
          const url = entry.url ?? '';
          if (!url || seen.has(url)) {
            return false;
          }
          seen.add(url);
          return true;
        });
        if (unique.length > 0) {
          map.set(
            videoId,
            unique.map((entry) => {
              const format = subtitleFormatFromPath(entry.url ?? entry.name ?? entry.path);
              return {
                url: resolveSubtitleUrl(entry.url!, format),
                label: entry.name ?? entry.url ?? 'Subtitles',
                kind: 'subtitles',
                language: entry.language ?? undefined,
                format: format || undefined,
              };
            }),
          );
          return;
        }
      }

      // Fallback to filtered matches
      const filtered = matches.filter((entry) => typeof entry.url === 'string' && entry.url.length > 0);
      if (filtered.length > 0) {
        const seen = new Set<string>();
        map.set(
          videoId,
          filtered
            .sort((a, b) => formatRank(a) - formatRank(b))
            .filter((entry) => {
              const url = entry.url ?? '';
              if (!url || seen.has(url)) {
                return false;
              }
              seen.add(url);
              return true;
            })
            .map((entry) => {
              const format = subtitleFormatFromPath(entry.url ?? entry.name ?? entry.path);
              return {
                url: resolveSubtitleUrl(entry.url!, format),
                label: entry.name ?? entry.url ?? 'Subtitles',
                kind: 'subtitles',
                language: entry.language ?? undefined,
                format: format || undefined,
              };
            }),
        );
      }
    });

    if (fallbackTracks.length > 0) {
      map.set('__fallback__', fallbackTracks);
    }

    return map;
  }, [deriveBaseId, textItems, videoItems, resolveSubtitleUrl]);

  const buildSiblingSubtitleTracks = useCallback(
    (videoUrl: string | null | undefined): SubtitleTrack[] =>
      buildSiblingSubtitleTracksHelper(videoUrl, replaceUrlExtension, resolveSubtitleUrl, subtitleFormatFromPath),
    [resolveSubtitleUrl],
  );

  const getActiveSubtitleTracks = useCallback(
    (activeVideoId: string | null, videoFiles: Array<{ id: string; url: string }>): SubtitleTrack[] => {
      const direct = activeVideoId ? subtitleMap.get(activeVideoId) ?? [] : [];
      if (direct.length > 0) {
        return direct;
      }
      const activeVideo = activeVideoId ? videoFiles.find((file) => file.id === activeVideoId) ?? null : null;
      const siblingTracks = buildSiblingSubtitleTracks(activeVideo?.url);
      if (siblingTracks.length > 0) {
        return siblingTracks;
      }
      return subtitleMap.get('__fallback__') ?? [];
    },
    [buildSiblingSubtitleTracks, subtitleMap],
  );

  return {
    subtitleMap,
    buildSiblingSubtitleTracks,
    getActiveSubtitleTracks,
  };
}
