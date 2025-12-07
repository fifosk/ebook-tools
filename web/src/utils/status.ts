export type StatusGlyph = { icon: string; label: string };

function titleCase(value: string): string {
  if (!value) {
    return 'Unknown';
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

const STATUS_GLYPHS: Record<string, StatusGlyph> = {
  completed: { icon: '✅', label: 'Completed' },
  running: { icon: '▶️', label: 'Running' },
  pending: { icon: '⏳', label: 'Pending' },
  pausing: { icon: '⏯️', label: 'Pausing' },
  paused: { icon: '⏸️', label: 'Paused' },
  failed: { icon: '❌', label: 'Failed' },
  cancelled: { icon: '🚫', label: 'Cancelled' }
};

export function getStatusGlyph(status: string | null | undefined): StatusGlyph {
  const normalized = (status ?? '').toLowerCase();
  if (STATUS_GLYPHS[normalized]) {
    return STATUS_GLYPHS[normalized];
  }
  const fallbackLabel = titleCase(normalized || 'Unknown');
  return { icon: '•', label: fallbackLabel };
}
