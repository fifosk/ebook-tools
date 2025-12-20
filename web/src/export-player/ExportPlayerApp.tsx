import { useEffect, useMemo } from 'react';
import PlayerPanel from '../components/PlayerPanel';
import YoutubeDubPlayer from '../components/YoutubeDubPlayer';
import type { PipelineMediaResponse } from '../api/dtos';
import { normaliseFetchedMedia } from '../hooks/useLiveMedia';
import type { ExportPlayerManifest, ExportReadingBed } from '../types/exportPlayer';

function getExportManifest(): ExportPlayerManifest | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const candidate = (window as Window & { __EXPORT_DATA__?: unknown }).__EXPORT_DATA__;
  if (!candidate || typeof candidate !== 'object') {
    return null;
  }
  return candidate as ExportPlayerManifest;
}

function resolveReadingBed(manifest: ExportPlayerManifest | null): ExportReadingBed | null {
  if (!manifest?.reading_bed) {
    return null;
  }
  const { id, label, url } = manifest.reading_bed;
  if (!id || !label || !url) {
    return null;
  }
  return { id, label, url };
}

export default function ExportPlayerApp() {
  const manifest = getExportManifest();
  if (!manifest) {
    return (
      <div className="player-panel" role="alert">
        Missing export payload. Ensure `player-data.js` is present next to `index.html`.
      </div>
    );
  }

  const jobId = manifest.source?.id ?? 'export';
  const exportLabel = useMemo(() => {
    if (typeof manifest.export_label === 'string' && manifest.export_label.trim()) {
      return manifest.export_label.trim();
    }
    if (typeof manifest.source?.label === 'string' && manifest.source.label.trim()) {
      return manifest.source.label.trim();
    }
    return null;
  }, [manifest]);
  const payload: PipelineMediaResponse = {
    media: manifest.media ?? {},
    chunks: manifest.chunks ?? [],
    complete: Boolean(manifest.complete),
  };

  const snapshot = useMemo(() => normaliseFetchedMedia(payload, jobId), [jobId, payload]);
  const readingBed = resolveReadingBed(manifest);
  const hasInteractiveChunks = useMemo(
    () =>
      snapshot.chunks.some(
        (chunk) =>
          (Array.isArray(chunk.sentences) && chunk.sentences.length > 0) ||
          (typeof chunk.sentenceCount === 'number' && chunk.sentenceCount > 0),
      ),
    [snapshot.chunks],
  );
  const isVideoExport = useMemo(() => {
    const rawPlayerType = manifest.player?.type;
    const playerType = typeof rawPlayerType === 'string' ? rawPlayerType.toLowerCase() : '';
    if (playerType === 'video') {
      return true;
    }
    if (manifest.source?.item_type === 'video') {
      return true;
    }
    return snapshot.media.video.length > 0 && !hasInteractiveChunks;
  }, [hasInteractiveChunks, manifest.player?.type, manifest.source?.item_type, snapshot.media.video.length]);

  useEffect(() => {
    if (!exportLabel || typeof document === 'undefined') {
      return;
    }
    document.title = exportLabel;
  }, [exportLabel]);

  if (isVideoExport) {
    return (
      <YoutubeDubPlayer
        jobId={jobId}
        media={snapshot.media}
        mediaComplete={snapshot.complete}
        isLoading={false}
        error={null}
        playerMode="export"
      />
    );
  }

  return (
    <PlayerPanel
      jobId={jobId}
      jobType={manifest.source?.job_type ?? 'book'}
      itemType={manifest.source?.item_type ?? 'book'}
      origin={manifest.source?.kind === 'library' ? 'library' : 'job'}
      media={snapshot.media}
      chunks={snapshot.chunks}
      mediaComplete={snapshot.complete}
      isLoading={false}
      error={null}
      bookMetadata={(manifest.book_metadata as Record<string, unknown> | null) ?? null}
      playerMode="export"
      playerFeatures={manifest.player?.features ?? undefined}
      readingBedOverride={readingBed}
    />
  );
}
