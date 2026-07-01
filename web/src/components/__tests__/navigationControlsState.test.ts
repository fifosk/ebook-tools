import { describe, expect, it } from 'vitest';
import {
  buildNavigationControlsState,
  hasCompactNavigationControls,
} from '../player-panel/navigationControlsState';

describe('buildNavigationControlsState', () => {
  it('derives panel defaults and export labels', () => {
    expect(
      buildNavigationControlsState({
        context: 'panel',
        exportBusy: false,
        searchPanel: null,
      }),
    ).toMatchObject({
      shouldShowPrimaryControls: true,
      shouldShowAdvancedControls: true,
      groupClassName: 'player-panel__navigation-group',
      navigationClassName: 'player-panel__navigation',
      fullscreenTestId: 'player-panel-interactive-fullscreen',
      searchInPrimary: false,
      searchInSecondary: false,
      showPrimaryInfoRow: false,
      advancedToggleClassName: 'player-panel__nav-button player-panel__nav-button--caret',
      advancedToggleLabel: 'Show advanced controls',
      resolvedExportLabel: 'Export offline player',
      resolvedExportTitle: 'Export offline player',
      shouldShowCompactControls: false,
    });
  });

  it('derives fullscreen compact state with primary search and advanced toggle', () => {
    expect(
      buildNavigationControlsState({
        context: 'fullscreen',
        controlsLayout: 'compact',
        showPrimaryControls: false,
        showAdvancedControls: true,
        searchPanel: 'search',
        searchPlacement: 'primary',
        advancedControlsOpen: true,
        exportBusy: true,
        showTranslationSpeed: true,
      }),
    ).toMatchObject({
      shouldShowPrimaryControls: false,
      shouldShowAdvancedControls: true,
      groupClassName:
        'player-panel__navigation-group player-panel__navigation-group--fullscreen player-panel__navigation-group--compact-controls',
      navigationClassName: 'player-panel__navigation player-panel__navigation--fullscreen',
      fullscreenTestId: undefined,
      searchInPrimary: true,
      searchInSecondary: false,
      showPrimaryInfoRow: true,
      advancedToggleClassName:
        'player-panel__nav-button player-panel__nav-button--caret player-panel__nav-button--advanced-active',
      advancedToggleLabel: 'Hide advanced controls',
      resolvedExportLabel: 'Preparing export',
      resolvedExportTitle: 'Preparing export',
      shouldShowCompactControls: true,
    });
  });

  it('respects explicit export label and secondary search placement', () => {
    expect(
      buildNavigationControlsState({
        context: 'panel',
        searchPanel: 'search',
        searchPlacement: 'secondary',
        exportBusy: true,
        exportLabel: 'Download bundle',
        exportTitle: 'Download for offline use',
      }),
    ).toMatchObject({
      searchInPrimary: false,
      searchInSecondary: true,
      showPrimaryInfoRow: false,
      resolvedExportLabel: 'Download bundle',
      resolvedExportTitle: 'Download for offline use',
    });
  });
});

describe('hasCompactNavigationControls', () => {
  it('requires compact layout and at least one compact-only control', () => {
    expect(hasCompactNavigationControls({ controlsLayout: 'stacked', showTranslationSpeed: true })).toBe(false);
    expect(hasCompactNavigationControls({ controlsLayout: 'compact' })).toBe(false);
    expect(hasCompactNavigationControls({ controlsLayout: 'compact', showReadingBedTrack: true })).toBe(true);
    expect(hasCompactNavigationControls({ controlsLayout: 'compact', showInteractiveThemeControls: true })).toBe(
      true,
    );
  });
});
