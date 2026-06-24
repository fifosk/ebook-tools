import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { buildPlayerPanelNavigationGroups } from '../player-panel/PlayerPanelNavigationGroups';
import type { NavigationControlsProps } from '../player-panel/NavigationControls';

const navigationControlsMock = vi.hoisted(() => ({
  calls: [] as NavigationControlsProps[],
}));

vi.mock('../player-panel/NavigationControls', () => ({
  NavigationControls: (props: NavigationControlsProps) => {
    navigationControlsMock.calls.push(props);
    const role = props.context === 'panel'
      ? 'panel'
      : props.showPrimaryControls === false
        ? 'fullscreen-advanced'
        : 'fullscreen-main';
    return (
      <div data-testid={`navigation-${role}`}>
        {props.searchPanel}
      </div>
    );
  },
}));

type NavigationBaseProps = Omit<NavigationControlsProps, 'context' | 'sentenceJumpInputId'>;

function baseNavigationProps(overrides: Partial<NavigationBaseProps> = {}): NavigationBaseProps {
  return {
    onNavigate: vi.fn(),
    onToggleFullscreen: vi.fn(),
    onTogglePlayback: vi.fn(),
    disableFirst: false,
    disablePrevious: false,
    disableNext: false,
    disableLast: false,
    disablePlayback: false,
    disableFullscreen: false,
    isFullscreen: false,
    isPlaying: false,
    fullscreenLabel: 'Enter fullscreen',
    showTranslationSpeed: false,
    translationSpeed: 1,
    translationSpeedMin: 0.5,
    translationSpeedMax: 2,
    translationSpeedStep: 0.1,
    onTranslationSpeedChange: vi.fn(),
    ...overrides,
  };
}

describe('buildPlayerPanelNavigationGroups', () => {
  beforeEach(() => {
    navigationControlsMock.calls = [];
  });

  it('routes panel controls through advanced toggle state', () => {
    const onToggleAdvancedControls = vi.fn();
    const { panelNavigation } = buildPlayerPanelNavigationGroups({
      baseProps: baseNavigationProps(),
      panelSentenceJumpInputId: 'panel-jump',
      fullscreenSentenceJumpInputId: 'fullscreen-jump',
      panelSearchPanel: <span>Panel search</span>,
      fullscreenSearchPanel: null,
      hasAdvancedControls: true,
      advancedControlsOpen: false,
      onToggleAdvancedControls,
    });

    render(<>{panelNavigation}</>);

    expect(screen.getByTestId('navigation-panel')).toHaveTextContent('Panel search');
    expect(navigationControlsMock.calls[0]).toMatchObject({
      context: 'panel',
      sentenceJumpInputId: 'panel-jump',
      showAdvancedControls: false,
      showAdvancedToggle: true,
      advancedControlsOpen: false,
      onToggleAdvancedControls,
    });
  });

  it('routes fullscreen controls into primary and advanced groups', () => {
    const {
      fullscreenMainControls,
      fullscreenAdvancedControls,
    } = buildPlayerPanelNavigationGroups({
      baseProps: baseNavigationProps({ isFullscreen: true }),
      panelSentenceJumpInputId: 'panel-jump',
      fullscreenSentenceJumpInputId: 'fullscreen-jump',
      panelSearchPanel: null,
      fullscreenSearchPanel: <span>Fullscreen search</span>,
      hasAdvancedControls: false,
      advancedControlsOpen: false,
      onToggleAdvancedControls: vi.fn(),
    });

    render(
      <>
        {fullscreenMainControls}
        {fullscreenAdvancedControls}
      </>,
    );

    expect(screen.getByTestId('navigation-fullscreen-main')).toHaveTextContent('Fullscreen search');
    expect(screen.getByTestId('navigation-fullscreen-advanced')).toBeInTheDocument();
    expect(navigationControlsMock.calls[0]).toMatchObject({
      context: 'fullscreen',
      sentenceJumpInputId: 'fullscreen-jump',
      showPrimaryControls: true,
      showAdvancedControls: false,
    });
    expect(navigationControlsMock.calls[1]).toMatchObject({
      context: 'fullscreen',
      sentenceJumpInputId: 'fullscreen-jump',
      showPrimaryControls: false,
      showAdvancedControls: true,
    });
  });
});
