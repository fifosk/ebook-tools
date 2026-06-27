import type { ReactNode } from 'react';

export type MetadataRow = {
  id?: string;
  label: string;
  value?: ReactNode;
  href?: string;
};

type MetadataGridProps = {
  rows: MetadataRow[];
  id?: string;
  className?: string;
  rowClassName?: string | ((row: MetadataRow) => string | undefined);
  ariaLabel?: string;
  dataState?: string;
};

/**
 * Displays metadata as a definition list grid.
 * Rows with undefined/null values are automatically hidden.
 */
export function MetadataGrid({
  rows,
  id,
  className = 'metadata-grid',
  rowClassName = 'metadata-grid__row',
  ariaLabel,
  dataState,
}: MetadataGridProps) {
  const visibleRows = rows.filter((row) => row.value != null && row.value !== '');

  if (visibleRows.length === 0) {
    return null;
  }

  return (
    <dl id={id} className={className} aria-label={ariaLabel} data-state={dataState}>
      {visibleRows.map((row) => {
        const resolvedRowClassName =
          typeof rowClassName === 'function' ? rowClassName(row) : rowClassName;

        return (
          <div key={row.id ?? row.label} className={resolvedRowClassName}>
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
        );
      })}
    </dl>
  );
}
