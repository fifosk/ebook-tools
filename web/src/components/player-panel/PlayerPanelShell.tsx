import type { ReactNode } from 'react';

interface PlayerPanelShellProps {
  ariaLabel: string;
  className?: string;
  prelude?: ReactNode;
  search?: ReactNode;
  toolbar?: ReactNode;
  children: ReactNode;
}

export function PlayerPanelShell({
  ariaLabel,
  className,
  prelude,
  search,
  toolbar,
  children,
}: PlayerPanelShellProps) {
  const rootClassName = ['player-panel', className].filter(Boolean).join(' ');

  return (
    <div className={rootClassName} role="region" aria-label={ariaLabel}>
      {prelude}
      {search ? <div className="player-panel__search">{search}</div> : null}
      <div className="player-panel__tabs-container">
        {toolbar ? (
          <header className="player-panel__header">
            <div className="player-panel__tabs-row">{toolbar}</div>
          </header>
        ) : null}
        <div className="player-panel__panel">{children}</div>
      </div>
    </div>
  );
}
