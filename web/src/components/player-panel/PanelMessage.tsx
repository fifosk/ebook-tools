import type { ReactNode } from 'react';

type PanelMessageProps = {
  children: ReactNode;
  className?: string;
  role?: 'status' | 'alert';
  as?: 'p' | 'div';
};

export function PanelMessage({
  children,
  className,
  role,
  as: Tag = 'p',
}: PanelMessageProps) {
  return (
    <Tag className={className} role={role}>
      {children}
    </Tag>
  );
}
