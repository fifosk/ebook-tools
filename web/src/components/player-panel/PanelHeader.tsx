import type { ReactNode } from 'react';

type PanelHeaderProps = {
  title: ReactNode;
  status?: string | null;
  statusLabel?: string;
  className?: string;
  titleClassName?: string;
  statusClassName?: string;
  statusClassNamePrefix?: string;
};

export function PanelHeader({
  title,
  status = null,
  statusLabel = 'Status',
  className,
  titleClassName,
  statusClassName,
  statusClassNamePrefix,
}: PanelHeaderProps) {
  const trimmedStatus = typeof status === 'string' ? status.trim() : '';
  const statusSlug = trimmedStatus ? trimmedStatus.toLowerCase() : '';
  const variantClassName =
    statusClassNamePrefix && statusSlug ? `${statusClassNamePrefix}${statusSlug}` : null;
  const resolvedStatusClassName = [statusClassName, variantClassName]
    .filter(Boolean)
    .join(' ');

  return (
    <header className={className}>
      <h2 className={titleClassName}>{title}</h2>
      {trimmedStatus ? (
        <span className={resolvedStatusClassName || undefined}>
          {statusLabel}: {trimmedStatus}
        </span>
      ) : null}
    </header>
  );
}
