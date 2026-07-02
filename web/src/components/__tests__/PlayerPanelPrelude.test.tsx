import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PlayerPanelPrelude } from '../player-panel/PlayerPanelPrelude';

describe('PlayerPanelPrelude', () => {
  it('renders shared sentence jump suggestions and shortcut help chrome', () => {
    const { container } = render(
      <PlayerPanelPrelude
        sentenceJumpListId="sentence-jump-list"
        sentenceSuggestions={[2, 4, 8]}
        shortcutHelpOverlay={<div>Shortcut help</div>}
        showShortcutHelp
      />,
    );

    const datalist = container.querySelector('datalist');
    const options = Array.from(container.querySelectorAll('option'));

    expect(datalist).toHaveAttribute('id', 'sentence-jump-list');
    expect(options.map((option) => option.getAttribute('value'))).toEqual(['2', '4', '8']);
    expect(screen.getByText('Shortcut help')).toBeInTheDocument();
  });

  it('keeps the sentence jump datalist while hiding shortcut help', () => {
    const { container } = render(
      <PlayerPanelPrelude
        sentenceJumpListId="sentence-jump-list"
        sentenceSuggestions={[12]}
        shortcutHelpOverlay={<div>Shortcut help</div>}
        showShortcutHelp={false}
      />,
    );

    expect(container.querySelector('datalist')).toHaveAttribute('id', 'sentence-jump-list');
    expect(screen.queryByText('Shortcut help')).not.toBeInTheDocument();
  });

  it('renders only shortcut help when there are no sentence suggestions', () => {
    const { container } = render(
      <PlayerPanelPrelude
        sentenceJumpListId="sentence-jump-list"
        sentenceSuggestions={[]}
        shortcutHelpOverlay={<div>Shortcut help</div>}
        showShortcutHelp
      />,
    );

    expect(container.querySelector('datalist')).not.toBeInTheDocument();
    expect(screen.getByText('Shortcut help')).toBeInTheDocument();
  });
});
