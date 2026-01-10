import type { JobTypeGlyph } from '../utils/jobGlyphs';

type JobTypeGlyphBadgeProps = {
  glyph: JobTypeGlyph;
  className?: string;
  title?: string;
  ariaLabel?: string;
};

export default function JobTypeGlyphBadge({
  glyph,
  className,
  title,
  ariaLabel,
}: JobTypeGlyphBadgeProps) {
  const label = ariaLabel ?? glyph.label;
  const tooltip = title ?? glyph.label;

  if (glyph.variant === 'youtube') {
    return (
      <span className={className} title={tooltip} aria-label={label}>
        <svg
          className="job-type-glyph__youtube"
          viewBox="0 0 24 24"
          role="img"
          focusable="false"
          aria-hidden="true"
        >
          <rect x="3" y="6.5" width="18" height="11" rx="3.2" fill="#ff0000" />
          <path d="M10 9.5l5 2.5-5 2.5v-5Z" fill="#ffffff" />
        </svg>
      </span>
    );
  }
  if (glyph.variant === 'tv') {
    return (
      <span className={className} title={tooltip} aria-label={label}>
        <svg
          className="job-type-glyph__tv"
          viewBox="0 0 24 24"
          role="img"
          focusable="false"
          aria-hidden="true"
        >
          <rect x="4" y="7.5" width="16" height="9.5" rx="2.6" fill="none" stroke="currentColor" strokeWidth="1.6" />
          <rect x="7" y="9.5" width="10" height="5.3" rx="1.4" fill="none" stroke="currentColor" strokeWidth="1.4" />
          <path d="M12 7.5l-2.3-2.4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
          <path d="M12 7.5l2.3-2.4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
          <path d="M9 18.5h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      </span>
    );
  }

  return (
    <span className={className} title={tooltip} aria-label={label}>
      {glyph.icon}
    </span>
  );
}
