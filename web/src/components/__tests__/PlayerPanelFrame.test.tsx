import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PlayerPanelFrame } from '../player-panel/PlayerPanelFrame';

function renderFrame(overrides: Partial<Parameters<typeof PlayerPanelFrame>[0]> = {}) {
  return render(
    <PlayerPanelFrame
      sectionLabel="Interactive reader"
      error={null}
      isInitialLoading={false}
      loadingMessage="Loading generated media..."
      hasJobId
      sentenceJumpListId="sentence-jump-list"
      sentenceSuggestions={[1, 8, 13]}
      shortcutHelpOverlay={<div>Shortcut help</div>}
      isInteractiveFullscreen={false}
      panelNavigation={<button type="button">Play</button>}
      hasAnyMedia
      isLoading={false}
      emptyMediaMessage="Nothing here."
      hasTextItems
      hasInteractiveChunks
      mediaComplete
      {...overrides}
    >
      <div>Interactive document</div>
    </PlayerPanelFrame>,
  );
}

describe('PlayerPanelFrame', () => {
  it('renders boundary states with the player prelude', () => {
    const { container } = renderFrame({ hasJobId: false });

    expect(screen.getByRole('region', { name: 'Interactive reader' })).toBeInTheDocument();
    expect(screen.getByText('Shortcut help')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('No job selected.');
    expect(container.querySelector('#sentence-jump-list')).toBeInTheDocument();
    expect(screen.queryByText('Interactive document')).not.toBeInTheDocument();
  });

  it('renders the shell, toolbar, prelude, and interactive document for normal playback', () => {
    const { container } = renderFrame();

    expect(screen.getByRole('region', { name: 'Interactive reader' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Play' })).toBeInTheDocument();
    expect(screen.getByText('Shortcut help')).toBeInTheDocument();
    expect(screen.getByText('Interactive document')).toBeInTheDocument();
    expect(container.querySelector('#sentence-jump-list')).toBeInTheDocument();
  });

  it('keeps shortcut help out of the panel prelude while fullscreen owns the overlay', () => {
    renderFrame({ isInteractiveFullscreen: true });

    expect(screen.queryByText('Shortcut help')).not.toBeInTheDocument();
    expect(screen.getByText('Interactive document')).toBeInTheDocument();
  });
});
