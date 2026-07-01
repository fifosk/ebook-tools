import type { AcquisitionCandidate } from '../../api/dtos';
import {
  formatBytes,
  formatDurationSeconds
} from './videoDubbingUtils';
import { isDownloadStationHandoffCandidate } from './videoDubbingDownloadStationUtils';
import {
  DEFAULT_VIDEO_DISCOVERY_PROVIDER,
  isYoutubeMetadataVideoDiscoveryProvider,
  type VideoDiscoveryProvider
} from './videoDubbingDiscovery';

export function resolveDiscoveryPlaceholder(provider: VideoDiscoveryProvider): string {
  if (provider === DEFAULT_VIDEO_DISCOVERY_PROVIDER) {
    return 'Search default video sources';
  }
  if (provider === 'youtube_url') {
    return 'Paste a YouTube video URL or ID';
  }
  if (provider === 'youtube_search') {
    return 'Search YouTube videos by title or channel';
  }
  if (provider === 'newznab_torznab') {
    return 'Search configured indexers';
  }
  return 'Search title or filename';
}

export function resolveDiscoveryHint(provider: VideoDiscoveryProvider): string {
  if (provider === DEFAULT_VIDEO_DISCOVERY_PROVIDER) {
    return 'Search the backend-owned default video sources in one pass.';
  }
  if (provider === 'youtube_search') {
    return 'Search YouTube metadata, then review the selected URL before downloading subtitles or video.';
  }
  if (provider === 'youtube_url') {
    return 'Paste a YouTube URL or video id, then review metadata before downloading subtitles or video.';
  }
  if (provider === 'manual_downloads') {
    return 'Search configured manual download video inboxes and fill the existing video selection.';
  }
  if (provider === 'newznab_torznab') {
    return 'Search configured indexer metadata, then review and confirm lawful access before any downloader handoff.';
  }
  return 'Search backend-visible NAS videos and fill the existing video selection.';
}

export function filenameFromPath(path: string): string {
  const trimmed = path.trim();
  const normalized = trimmed.replace(/[\\/]+$/, '');
  const parts = normalized.split(/[\\/]/);
  return parts[parts.length - 1] || normalized || trimmed;
}

export function formatDiscoveryCandidateMeta(candidate: AcquisitionCandidate): string {
  const parts: string[] = [];
  if (isYoutubeMetadataVideoDiscoveryProvider(candidate.provider)) {
    parts.push('YouTube metadata');
    const channel = candidate.contributors.find((value) => value.trim());
    if (channel) {
      parts.push(channel);
    }
    const duration = formatDurationSeconds(candidate.duration_seconds);
    if (duration) {
      parts.push(duration);
    }
    const metadataYoutubeUrl = candidate.metadata['youtube_url'];
    const youtubeUrl =
      candidate.source_url?.trim() ||
      (typeof metadataYoutubeUrl === 'string' ? metadataYoutubeUrl.trim() : '');
    if (youtubeUrl) {
      parts.push(youtubeUrl);
    }
  } else if (candidate.provider === 'newznab_torznab') {
    parts.push('Indexer metadata');
    const indexer = candidate.contributors.find((value) => value.trim());
    if (indexer) {
      parts.push(indexer);
    }
    if (candidate.size_bytes) {
      parts.push(formatBytes(candidate.size_bytes));
    }
    const seeders = candidate.metadata['seeders'];
    const peers = candidate.metadata['peers'];
    if (typeof seeders === 'number') {
      parts.push(`${seeders} seeders`);
    }
    if (typeof peers === 'number') {
      parts.push(`${peers} peers`);
    }
    if (isDownloadStationHandoffCandidate(candidate)) {
      parts.push('Download Station handoff');
    }
  } else if (candidate.local_path) {
    parts.push(candidate.local_path);
  }

  if (candidate.subtitles.length > 0) {
    parts.push(`${candidate.subtitles.length} subtitle${candidate.subtitles.length === 1 ? '' : 's'}`);
  }
  if (candidate.requires_confirmation) {
    parts.push('review required');
  }
  return parts.join(' · ') || candidate.provider;
}
