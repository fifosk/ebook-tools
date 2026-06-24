import type { ReactNode } from 'react';

type PlayerPanelContentProps = {
  hasAnyMedia: boolean;
  isLoading: boolean;
  emptyMediaMessage: string;
  hasTextItems: boolean;
  hasInteractiveChunks: boolean;
  mediaComplete: boolean;
  children: ReactNode;
};

export function PlayerPanelContent({
  hasAnyMedia,
  isLoading,
  emptyMediaMessage,
  hasTextItems,
  hasInteractiveChunks,
  mediaComplete,
  children,
}: PlayerPanelContentProps) {
  if (!hasAnyMedia && !isLoading) {
    return <p role="status">{emptyMediaMessage}</p>;
  }

  if (!hasTextItems && !hasInteractiveChunks) {
    return <p role="status">No interactive reader media yet.</p>;
  }

  return (
    <div className="player-panel__stage">
      {!mediaComplete ? (
        <div className="player-panel__notice" role="status">
          Media generation is still finishing. Newly generated files will appear automatically.
        </div>
      ) : null}
      <div className="player-panel__viewer">
        <div className="player-panel__document">{children}</div>
      </div>
    </div>
  );
}
