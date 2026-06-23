export function coerceRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

export type SubtitleMetadataDraftUpdater = (draft: Record<string, unknown>) => void;

export function updateSubtitleMediaMetadataDraft(
  current: Record<string, unknown> | null,
  updater: SubtitleMetadataDraftUpdater
): Record<string, unknown> {
  const next: Record<string, unknown> = current ? { ...current } : {};
  updater(next);
  return next;
}

export function updateSubtitleMediaMetadataSection(
  current: Record<string, unknown> | null,
  sectionKey: string,
  updater: SubtitleMetadataDraftUpdater
): Record<string, unknown> {
  return updateSubtitleMediaMetadataDraft(current, (draft) => {
    const currentSection = coerceRecord(draft[sectionKey]);
    const nextSection: Record<string, unknown> = currentSection ? { ...currentSection } : {};
    updater(nextSection);
    draft[sectionKey] = nextSection;
  });
}

export function normalizeTextValue(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const cleaned = value.trim();
  return cleaned.length > 0 ? cleaned : null;
}

export function formatEpisodeCode(season: unknown, episode: unknown): string | null {
  if (typeof season !== 'number' || typeof episode !== 'number') {
    return null;
  }
  if (!Number.isFinite(season) || !Number.isFinite(episode)) {
    return null;
  }
  const seasonInt = Math.trunc(season);
  const episodeInt = Math.trunc(episode);
  if (seasonInt <= 0 || episodeInt <= 0) {
    return null;
  }
  return `S${seasonInt.toString().padStart(2, '0')}E${episodeInt.toString().padStart(2, '0')}`;
}
