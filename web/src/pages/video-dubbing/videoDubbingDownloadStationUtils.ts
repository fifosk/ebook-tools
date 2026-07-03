import type {
  AcquisitionCandidate,
  AcquisitionJobStatusResponse,
  YoutubeNasVideo
} from '../../api/dtos';
import {
  basenameFromPath,
  normalizeTextValue
} from './videoDubbingUtils';

function isTruthyMetadataFlag(value: unknown): boolean {
  if (value === true) {
    return true;
  }
  return typeof value === 'string' && value.trim().toLowerCase() === 'true';
}

export function isDownloadStationHandoffCandidate(
  candidate: Pick<AcquisitionCandidate, 'provider' | 'metadata'>
): boolean {
  if (candidate.provider !== 'newznab_torznab') {
    return false;
  }
  const metadata = candidate.metadata ?? {};
  return normalizeTextValue(metadata['handoff_provider'])?.toLowerCase() === 'download_station'
    || isTruthyMetadataFlag(metadata['has_download_url']);
}

function stringArrayFromMetadataValue(value: unknown): string[] {
  const uniqueSafeHints = (values: Array<string | null>): string[] => {
    const seen = new Set<string>();
    const results: string[] = [];
    for (const value of values) {
      const safeValue = safeCompletedFileHint(value);
      if (safeValue && !seen.has(safeValue)) {
        seen.add(safeValue);
        results.push(safeValue);
      }
    }
    return results;
  };
  if (Array.isArray(value)) {
    return uniqueSafeHints(value.map((entry) => normalizeTextValue(entry)));
  }
  const single = normalizeTextValue(value);
  return uniqueSafeHints([single]);
}

function safeCompletedFileHint(value: string | null): string | null {
  if (!value) {
    return null;
  }
  const lower = value.toLowerCase();
  if (
    lower.startsWith('magnet:') ||
    lower.startsWith('file:') ||
    lower.includes('://')
  ) {
    return null;
  }
  const pathParts = value.split(/[\\/]+/);
  if (pathParts.some((part) => part === '..')) {
    return null;
  }
  return value;
}

export function resolveDownloadStationCompletedFiles(
  job: Pick<AcquisitionJobStatusResponse, 'completed_files' | 'metadata'> | null | undefined
): string[] {
  if (!job) {
    return [];
  }
  const topLevel = stringArrayFromMetadataValue(job.completed_files);
  if (topLevel.length > 0) {
    return topLevel;
  }
  const metadata = job.metadata ?? {};
  for (const key of ['completed_files', 'completed_paths', 'files']) {
    const values = stringArrayFromMetadataValue(metadata[key]);
    if (values.length > 0) {
      return values;
    }
  }
  return stringArrayFromMetadataValue(metadata['completed_file'] ?? metadata['completed_path'] ?? metadata['local_path']);
}

function fileNameKeys(value: string | null | undefined): string[] {
  const normalized = normalizeTextValue(value);
  if (!normalized) {
    return [];
  }
  const basename = basenameFromPath(normalized).toLowerCase();
  if (!basename) {
    return [];
  }
  const keys = [basename];
  const extensionIndex = basename.lastIndexOf('.');
  if (extensionIndex > 0) {
    keys.push(basename.slice(0, extensionIndex));
  }
  return keys;
}

export function findDownloadStationCompletedVideo(
  videos: YoutubeNasVideo[],
  completedFiles: string[]
): YoutubeNasVideo | null {
  if (videos.length === 0 || completedFiles.length === 0) {
    return null;
  }
  const completedKeys = new Set(completedFiles.flatMap(fileNameKeys));
  if (completedKeys.size === 0) {
    return null;
  }
  return videos.find((video) => {
    const candidateKeys = [
      ...fileNameKeys(video.path),
      ...fileNameKeys(video.filename),
      ...fileNameKeys(video.folder),
    ];
    return candidateKeys.some((key) => completedKeys.has(key));
  }) ?? null;
}
