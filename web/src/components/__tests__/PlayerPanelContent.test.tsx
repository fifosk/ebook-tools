import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PlayerPanelContent } from '../player-panel/PlayerPanelContent';

function renderContent(overrides: Partial<Parameters<typeof PlayerPanelContent>[0]> = {}) {
  return render(
    <PlayerPanelContent
      hasAnyMedia
      isLoading={false}
      emptyMediaMessage="Nothing here yet."
      hasTextItems
      hasInteractiveChunks={false}
      mediaComplete
      {...overrides}
    >
      <div>Interactive document</div>
    </PlayerPanelContent>,
  );
}

describe('PlayerPanelContent', () => {
  it('renders the empty media message when the job has no media', () => {
    renderContent({ hasAnyMedia: false });

    expect(screen.getByRole('status')).toHaveTextContent('Nothing here yet.');
    expect(screen.queryByText('Interactive document')).not.toBeInTheDocument();
  });

  it('renders the interactive media placeholder when text assets are missing', () => {
    renderContent({ hasTextItems: false, hasInteractiveChunks: false });

    expect(screen.getByRole('status')).toHaveTextContent('No interactive reader media yet.');
    expect(screen.queryByText('Interactive document')).not.toBeInTheDocument();
  });

  it('renders the document stage and pending media notice', () => {
    renderContent({ mediaComplete: false });

    expect(screen.getByText('Interactive document')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(
      'Media generation is still finishing. Newly generated files will appear automatically.',
    );
  });
});
