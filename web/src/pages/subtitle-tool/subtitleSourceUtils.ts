import type { SubtitleSourceEntry } from '../../api/dtos';
import { subtitleFormatFromPath } from '../../utils/subtitles';
import type { SubtitleSourceMode } from './subtitleToolTypes';

export function basenameFromPath(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return '';
  }
  const normalized = trimmed.replace(/\\/g, '/');
  const parts = normalized.split('/');
  return parts.length ? parts[parts.length - 1] : trimmed;
}

export function resolveSubtitleSourceFormat(entry: SubtitleSourceEntry | null | undefined): string {
  if (!entry) {
    return '';
  }
  return (entry.format || subtitleFormatFromPath(entry.path) || '').toLowerCase();
}

export function isAssSubtitleSelection(
  sourceMode: SubtitleSourceMode,
  selectedSourceEntry: SubtitleSourceEntry | null | undefined
): boolean {
  return sourceMode === 'existing' && resolveSubtitleSourceFormat(selectedSourceEntry) === 'ass';
}

export function resolveSubtitleMetadataSourceName(input: {
  sourceMode: SubtitleSourceMode;
  uploadFileName?: string | null;
  selectedSourceName?: string | null;
  selectedSourcePath: string;
}): string {
  if (input.sourceMode === 'upload') {
    return input.uploadFileName ?? '';
  }
  return input.selectedSourceName ?? (input.selectedSourcePath ? basenameFromPath(input.selectedSourcePath) : '');
}

function parseModifiedTime(value: string | null | undefined): number {
  if (!value) {
    return 0;
  }
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

export function sortSubtitleSourcesForSelection(sources: SubtitleSourceEntry[]): SubtitleSourceEntry[] {
  return [...sources]
    .map((entry, index) => ({ entry, index }))
    .sort((left, right) => {
      const leftWeight = resolveSubtitleSourceFormat(left.entry) === 'ass' ? 1 : 0;
      const rightWeight = resolveSubtitleSourceFormat(right.entry) === 'ass' ? 1 : 0;
      if (leftWeight !== rightWeight) {
        return leftWeight - rightWeight;
      }
      return left.index - right.index;
    })
    .map(({ entry }) => entry);
}

export function pickLatestSubtitleSource(sources: SubtitleSourceEntry[]): string {
  const preferred = sources.filter((item) => resolveSubtitleSourceFormat(item) !== 'ass');
  const pool = preferred.length > 0 ? preferred : sources;
  if (pool.length === 0) {
    return '';
  }
  return pool.reduce<string>((latest, candidate) => {
    if (!latest) {
      return candidate.path;
    }
    const latestEntry = pool.find((item) => item.path === latest) ?? candidate;
    const latestTs = parseModifiedTime(latestEntry.modified_at);
    const candidateTs = parseModifiedTime(candidate.modified_at);
    if (candidateTs > latestTs) {
      return candidate.path;
    }
    if (candidateTs === latestTs && candidate.path.localeCompare(latest) < 0) {
      return candidate.path;
    }
    return latest;
  }, '');
}

export function resolveSubtitleSourceSelectionAfterRefresh({
  sources,
  currentSelection,
  resetSelection,
}: {
  sources: SubtitleSourceEntry[];
  currentSelection: string;
  resetSelection: boolean;
}): string {
  if (!resetSelection && currentSelection && sources.some((entry) => entry.path === currentSelection)) {
    return currentSelection;
  }
  return pickLatestSubtitleSource(sources);
}
