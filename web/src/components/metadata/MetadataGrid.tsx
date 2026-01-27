import type { ReactNode } from 'react';

export type MetadataRow = {
  label: string;
  value?: ReactNode;
  href?: string;
};

type MetadataGridProps = {
  rows: MetadataRow[];
  className?: string;
};

/**
 * Displays metadata as a definition list grid.
 * Rows with undefined/null values are automatically hidden.
 */
export function MetadataGrid({ rows, className = 'metadata-grid' }: MetadataGridProps) {
  const visibleRows = rows.filter((row) => row.value != null && row.value !== '');

  if (visibleRows.length === 0) {
    return null;
  }

  return (
    <dl className={className}>
      {visibleRows.map((row) => (
        <div key={row.label} className="metadata-grid__row">
          <dt>{row.label}</dt>
          <dd>
            {row.href ? (
              <a href={row.href} target="_blank" rel="noopener noreferrer">
                {row.value}
              </a>
            ) : (
              row.value
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}
