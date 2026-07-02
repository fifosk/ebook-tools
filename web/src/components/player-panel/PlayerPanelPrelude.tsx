import type { ReactNode } from 'react';
import { PlayerPanelSentenceJumpDatalist } from './PlayerPanelSentenceJumpDatalist';

type PlayerPanelPreludeProps = {
  sentenceJumpListId: string;
  sentenceSuggestions: number[];
  shortcutHelpOverlay: ReactNode;
  showShortcutHelp: boolean;
};

export function PlayerPanelPrelude({
  sentenceJumpListId,
  sentenceSuggestions,
  shortcutHelpOverlay,
  showShortcutHelp,
}: PlayerPanelPreludeProps) {
  return (
    <>
      <PlayerPanelSentenceJumpDatalist id={sentenceJumpListId} suggestions={sentenceSuggestions} />
      {showShortcutHelp ? shortcutHelpOverlay : null}
    </>
  );
}
