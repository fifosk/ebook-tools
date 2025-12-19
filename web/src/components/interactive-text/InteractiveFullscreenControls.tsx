import type { ReactNode } from 'react';

interface InteractiveFullscreenControlsProps {
  isVisible: boolean;
  collapsed: boolean;
  inlineAudioAvailable: boolean;
  onCollapsedChange: (value: boolean) => void;
  children?: ReactNode;
}

export function InteractiveFullscreenControls({
  isVisible,
  collapsed,
  inlineAudioAvailable,
  onCollapsedChange,
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
        <span className="player-panel__interactive-label">{collapsed ? 'Controls hidden' : 'Controls'}</span>
        <div className="player-panel__interactive-fullscreen-controls-actions">
          {inlineAudioAvailable && collapsed ? (
            <button
              type="button"
              className="player-panel__interactive-fullscreen-toggle-btn player-panel__interactive-fullscreen-toggle-btn--audio"
              onClick={() => onCollapsedChange(false)}
            >
              Show audio player
            </button>
          ) : null}
          <button
            type="button"
            className="player-panel__interactive-fullscreen-toggle-btn"
            onClick={() => onCollapsedChange(!collapsed)}
            aria-expanded={!collapsed}
          >
            {collapsed ? 'Show controls' : 'Hide controls'}
          </button>
        </div>
      </div>
      {!collapsed && children ? (
        <div className="player-panel__interactive-fullscreen-controls-body">{children}</div>
      ) : null}
    </div>
  );
}
