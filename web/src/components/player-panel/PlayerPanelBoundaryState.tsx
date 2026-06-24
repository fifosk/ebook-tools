import type { ReactNode } from 'react';

type PlayerPanelBoundaryStateProps = {
  sectionLabel: string;
  error: Error | null;
  isInitialLoading: boolean;
  loadingMessage: string;
  hasJobId: boolean;
  noJobPrelude: ReactNode;
};

export function PlayerPanelBoundaryState({
  sectionLabel,
  error,
  isInitialLoading,
  loadingMessage,
  hasJobId,
  noJobPrelude,
}: PlayerPanelBoundaryStateProps) {
  if (error) {
    return (
      <div className="player-panel" role="region" aria-label={sectionLabel}>
        <p role="alert">Unable to load generated media: {error.message}</p>
      </div>
    );
  }

  if (isInitialLoading) {
    return (
      <div className="player-panel" role="region" aria-label={sectionLabel}>
        <p role="status">{loadingMessage}</p>
      </div>
    );
  }

  if (!hasJobId) {
    return (
      <div className="player-panel" role="region" aria-label={sectionLabel}>
        {noJobPrelude}
        <div className="player-panel__empty" role="status">
          <p>No job selected.</p>
        </div>
      </div>
    );
  }

  return null;
}
