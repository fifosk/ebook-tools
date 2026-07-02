import type { ReactNode } from 'react';
import { PlayerPanelBoundaryState } from './PlayerPanelBoundaryState';
import { PlayerPanelContent } from './PlayerPanelContent';
import { PlayerPanelPrelude } from './PlayerPanelPrelude';
import { PlayerPanelShell } from './PlayerPanelShell';

type PlayerPanelFrameProps = {
  sectionLabel: string;
  error: Error | null;
  isInitialLoading: boolean;
  loadingMessage: string;
  hasJobId: boolean;
  sentenceJumpListId: string;
  sentenceSuggestions: number[];
  shortcutHelpOverlay: ReactNode;
  isInteractiveFullscreen: boolean;
  panelNavigation: ReactNode;
  hasAnyMedia: boolean;
  isLoading: boolean;
  emptyMediaMessage: string;
  hasTextItems: boolean;
  hasInteractiveChunks: boolean;
  mediaComplete: boolean;
  children: ReactNode;
};

export function PlayerPanelFrame({
  sectionLabel,
  error,
  isInitialLoading,
  loadingMessage,
  hasJobId,
  sentenceJumpListId,
  sentenceSuggestions,
  shortcutHelpOverlay,
  isInteractiveFullscreen,
  panelNavigation,
  hasAnyMedia,
  isLoading,
  emptyMediaMessage,
  hasTextItems,
  hasInteractiveChunks,
  mediaComplete,
  children,
}: PlayerPanelFrameProps) {
  if (error || isInitialLoading || !hasJobId) {
    return (
      <PlayerPanelBoundaryState
        sectionLabel={sectionLabel}
        error={error}
        isInitialLoading={isInitialLoading}
        loadingMessage={loadingMessage}
        hasJobId={hasJobId}
        noJobPrelude={
          <PlayerPanelPrelude
            sentenceJumpListId={sentenceJumpListId}
            sentenceSuggestions={sentenceSuggestions}
            shortcutHelpOverlay={shortcutHelpOverlay}
            showShortcutHelp
          />
        }
      />
    );
  }

  return (
    <PlayerPanelShell
      ariaLabel={sectionLabel}
      prelude={
        <PlayerPanelPrelude
          sentenceJumpListId={sentenceJumpListId}
          sentenceSuggestions={sentenceSuggestions}
          shortcutHelpOverlay={shortcutHelpOverlay}
          showShortcutHelp={!isInteractiveFullscreen}
        />
      }
      toolbar={panelNavigation}
    >
      <PlayerPanelContent
        hasAnyMedia={hasAnyMedia}
        isLoading={isLoading}
        emptyMediaMessage={emptyMediaMessage}
        hasTextItems={hasTextItems}
        hasInteractiveChunks={hasInteractiveChunks}
        mediaComplete={mediaComplete}
      >
        {children}
      </PlayerPanelContent>
    </PlayerPanelShell>
  );
}
