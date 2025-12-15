export type JobTypeGlyph = { icon: string; label: string };

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

export function getJobTypeGlyph(jobType: string | null | undefined): JobTypeGlyph {
  const normalized = normalizeJobType(jobType);
  switch (normalized) {
    case 'pipeline':
    case 'book':
      return { icon: '📚', label: 'Book job' };
    case 'subtitle':
      return { icon: '🎞️', label: 'Subtitle job' };
    case 'youtube_dub':
      return { icon: '🎙️', label: 'Dub video job' };
    default:
      return { icon: '📦', label: normalized ? `${normalized} job` : 'Job' };
  }
}
