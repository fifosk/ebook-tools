import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { buildPlayerPanelSearchSlots, PlayerPanelSearchSlot } from '../player-panel/PlayerPanelSearchSlot';

const mediaSearchPanelMock = vi.hoisted(() => ({
  calls: [] as Array<{ currentJobId: string | null; variant?: string }>,
}));

vi.mock('../MediaSearchPanel', () => ({
  default: (props: { currentJobId: string | null; variant?: string }) => {
    mediaSearchPanelMock.calls.push(props);
    return <div data-testid="media-search-panel">{props.currentJobId}</div>;
  },
}));

const handleResultAction = vi.fn();

describe('PlayerPanelSearchSlot', () => {
  beforeEach(() => {
    mediaSearchPanelMock.calls = [];
  });

  it('renders the compact search panel for the standard player surface', () => {
    render(
      <PlayerPanelSearchSlot
        currentJobId="job-1"
        enabled
        isFullscreen={false}
        target="panel"
        onResultAction={handleResultAction}
      />,
    );

    expect(screen.getByTestId('media-search-panel')).toHaveTextContent('job-1');
    expect(mediaSearchPanelMock.calls[0]).toMatchObject({
      currentJobId: 'job-1',
      variant: 'compact',
    });
  });

  it('renders the compact search panel for the fullscreen surface only while fullscreen', () => {
    const { rerender } = render(
      <PlayerPanelSearchSlot
        currentJobId="job-2"
        enabled
        isFullscreen={false}
        target="fullscreen"
        onResultAction={handleResultAction}
      />,
    );

    expect(screen.queryByTestId('media-search-panel')).not.toBeInTheDocument();

    rerender(
      <PlayerPanelSearchSlot
        currentJobId="job-2"
        enabled
        isFullscreen
        target="fullscreen"
        onResultAction={handleResultAction}
      />,
    );

    expect(screen.getByTestId('media-search-panel')).toHaveTextContent('job-2');
  });

  it('renders nothing when search is disabled', () => {
    render(
      <PlayerPanelSearchSlot
        currentJobId="job-3"
        enabled={false}
        isFullscreen={false}
        target="panel"
        onResultAction={handleResultAction}
      />,
    );

    expect(screen.queryByTestId('media-search-panel')).not.toBeInTheDocument();
  });

  it('builds paired search panels for panel and fullscreen navigation groups', () => {
    const { panelSearchPanel, fullscreenSearchPanel } = buildPlayerPanelSearchSlots({
      currentJobId: 'job-4',
      enabled: true,
      isFullscreen: true,
      onResultAction: handleResultAction,
    });

    render(
      <>
        {panelSearchPanel}
        {fullscreenSearchPanel}
      </>,
    );

    expect(screen.getByTestId('media-search-panel')).toHaveTextContent('job-4');
    expect(mediaSearchPanelMock.calls).toHaveLength(1);
  });
});
