export type JobTypeGlyph = { icon: string; label: string; variant?: 'youtube' | 'tv' };

export function isTvSeriesMetadata(metadata: Record<string, unknown> | null | undefined): boolean {
  if (!metadata || typeof metadata !== 'object') {
    return false;
  }
  const kind = metadata['kind'];
  if (typeof kind === 'string' && kind.trim().toLowerCase() === 'tv_episode') {
    return true;
  }
  const show = metadata['show'];
  if (show && typeof show === 'object' && !Array.isArray(show)) {
    return true;
  }
  const episode = metadata['episode'];
  if (episode && typeof episode === 'object' && !Array.isArray(episode)) {
    return true;
  }
  return false;
}

function normalizeJobType(value: string | null | undefined): string {
  return (value ?? '').trim();
}

export function extractJobType(metadata: Record<string, unknown> | null | undefined): string | null {
  if (!metadata) {
    return null;
  }
  const direct = metadata['job_type'] ?? metadata['jobType'] ?? metadata['type'];
  if (typeof direct === 'string' && direct.trim()) {
    return direct.trim();
  }
  const nestedStatus = metadata['status'];
  if (nestedStatus && typeof nestedStatus === 'object') {
    const statusJobType = (nestedStatus as Record<string, unknown>)['job_type'];
    if (typeof statusJobType === 'string' && statusJobType.trim()) {
      return statusJobType.trim();
    }
  }
  return null;
}

export function getJobTypeGlyph(
  jobType: string | null | undefined,
  options?: { isTvSeries?: boolean },
): JobTypeGlyph {
  const normalized = normalizeJobType(jobType).toLowerCase();
  if (options?.isTvSeries) {
    return { icon: 'TV', label: 'TV series', variant: 'tv' };
  }
  if (normalized.includes('youtube')) {
    const label = normalized.includes('dub') ? 'YouTube dub job' : 'YouTube job';
    return { icon: 'YT', label, variant: 'youtube' };
  }
  switch (normalized) {
    case 'pipeline':
    case 'book':
      return { icon: '📚', label: 'Book job' };
    case 'subtitle':
      return { icon: '🎞️', label: 'Subtitle job' };
    case 'dub':
      return { icon: '🎙️', label: 'Dub video job' };
    default:
      return { icon: '📦', label: normalized ? `${normalized} job` : 'Job' };
  }
}
