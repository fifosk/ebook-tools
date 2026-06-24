import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PlayerPanelBoundaryState } from '../player-panel/PlayerPanelBoundaryState';

function renderBoundary(overrides: Partial<Parameters<typeof PlayerPanelBoundaryState>[0]> = {}) {
  return render(
    <PlayerPanelBoundaryState
      sectionLabel="Interactive reader"
      error={null}
      isInitialLoading={false}
      loadingMessage="Loading generated media..."
      hasJobId
      noJobPrelude={<span>Prelude</span>}
      {...overrides}
    />,
  );
}

describe('PlayerPanelBoundaryState', () => {
  it('renders load errors as alerts', () => {
    renderBoundary({ error: new Error('Network failed') });

    expect(screen.getByRole('region', { name: 'Interactive reader' })).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Unable to load generated media: Network failed');
  });

  it('renders initial loading status before media arrives', () => {
    renderBoundary({ isInitialLoading: true });

    expect(screen.getByRole('status')).toHaveTextContent('Loading generated media...');
  });

  it('renders the no-job state with prelude content', () => {
    renderBoundary({ hasJobId: false });

    expect(screen.getByText('Prelude')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('No job selected.');
  });

  it('renders nothing for the normal player path', () => {
    const { container } = renderBoundary();

    expect(container).toBeEmptyDOMElement();
  });
});
