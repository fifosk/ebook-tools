import type { ReactNode } from 'react';

interface InteractiveFullscreenControlsProps {
  isVisible: boolean;
  collapsed: boolean;
  mainControls?: ReactNode;
  children?: ReactNode;
}

export function InteractiveFullscreenControls({
  isVisible,
  collapsed,
  mainControls,
  children,
}: InteractiveFullscreenControlsProps) {
  if (!isVisible) {
    return null;
  }

  return (
    <div
      key="fullscreen-controls"
      className={[
        'player-panel__interactive-fullscreen-controls',
        collapsed ? 'player-panel__interactive-fullscreen-controls--collapsed' : null,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div className="player-panel__interactive-fullscreen-controls-bar">
        {mainControls ? (
          <div className="player-panel__interactive-fullscreen-controls-main">
            {mainControls}
          </div>
        ) : (
          <span className="player-panel__interactive-label">Controls</span>
        )}
      </div>
      {!collapsed && children ? (
        <div className="player-panel__interactive-fullscreen-controls-body">{children}</div>
      ) : null}
    </div>
  );
}
