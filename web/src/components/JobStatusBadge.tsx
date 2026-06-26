import { getStatusGlyph, type StatusGlyph } from '../utils/status';

type JobStatusBadgeProps = {
  status: string | null | undefined;
  glyph?: StatusGlyph | null;
  label?: string | null;
  className?: string;
};

export default function JobStatusBadge({
  status,
  glyph,
  label,
  className
}: JobStatusBadgeProps) {
  const statusValue = status ?? 'pending';
  const resolvedGlyph = glyph ?? getStatusGlyph(statusValue);
  const resolvedLabel = label ?? resolvedGlyph.label;
  const classes = ['job-status', className].filter(Boolean).join(' ');

  return (
    <span
      className={classes}
      data-state={statusValue}
      title={resolvedLabel}
      aria-label={resolvedLabel}
    >
      {resolvedGlyph.icon}
    </span>
  );
}
