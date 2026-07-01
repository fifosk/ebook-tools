import type { NavigationControlsProps } from './navigation';

type NavigationControlsStateArgs = Pick<NavigationControlsProps, 'context'> &
  Partial<
    Pick<
      NavigationControlsProps,
      | 'controlsLayout'
      | 'showPrimaryControls'
      | 'showAdvancedControls'
      | 'searchPanel'
      | 'searchPlacement'
      | 'advancedControlsOpen'
      | 'exportBusy'
      | 'exportLabel'
      | 'exportTitle'
      | 'showTranslationSpeed'
      | 'showSubtitleScale'
      | 'showSubtitleBackgroundOpacity'
      | 'showFontScale'
      | 'showMyLinguistFontScale'
      | 'showInteractiveBackgroundOpacity'
      | 'showInteractiveSentenceCardOpacity'
      | 'showInteractiveThemeControls'
      | 'showReadingBedVolume'
      | 'showReadingBedTrack'
    >
  >;

export function hasCompactNavigationControls({
  controlsLayout,
  showTranslationSpeed,
  showSubtitleScale,
  showSubtitleBackgroundOpacity,
  showFontScale,
  showMyLinguistFontScale,
  showInteractiveBackgroundOpacity,
  showInteractiveSentenceCardOpacity,
  showInteractiveThemeControls,
  showReadingBedVolume,
  showReadingBedTrack,
}: Pick<
  NavigationControlsStateArgs,
  | 'controlsLayout'
  | 'showTranslationSpeed'
  | 'showSubtitleScale'
  | 'showSubtitleBackgroundOpacity'
  | 'showFontScale'
  | 'showMyLinguistFontScale'
  | 'showInteractiveBackgroundOpacity'
  | 'showInteractiveSentenceCardOpacity'
  | 'showInteractiveThemeControls'
  | 'showReadingBedVolume'
  | 'showReadingBedTrack'
>): boolean {
  return Boolean(
    controlsLayout === 'compact' &&
      (showTranslationSpeed ||
        showSubtitleScale ||
        showSubtitleBackgroundOpacity ||
        showFontScale ||
        showMyLinguistFontScale ||
        showInteractiveBackgroundOpacity ||
        showInteractiveSentenceCardOpacity ||
        showInteractiveThemeControls ||
        showReadingBedVolume ||
        showReadingBedTrack),
  );
}

export function buildNavigationControlsState({
  context,
  controlsLayout = 'stacked',
  showPrimaryControls,
  showAdvancedControls,
  searchPanel,
  searchPlacement = 'secondary',
  advancedControlsOpen,
  exportBusy,
  exportLabel,
  exportTitle,
  showTranslationSpeed,
  showSubtitleScale,
  showSubtitleBackgroundOpacity,
  showFontScale,
  showMyLinguistFontScale,
  showInteractiveBackgroundOpacity,
  showInteractiveSentenceCardOpacity,
  showInteractiveThemeControls,
  showReadingBedVolume,
  showReadingBedTrack,
}: NavigationControlsStateArgs) {
  const shouldShowPrimaryControls = showPrimaryControls !== false;
  const shouldShowAdvancedControls = showAdvancedControls !== false;
  const groupClassName = [
    context === 'fullscreen'
      ? 'player-panel__navigation-group player-panel__navigation-group--fullscreen'
      : 'player-panel__navigation-group',
    controlsLayout === 'compact' ? 'player-panel__navigation-group--compact-controls' : null,
  ]
    .filter(Boolean)
    .join(' ');
  const navigationClassName =
    context === 'fullscreen'
      ? 'player-panel__navigation player-panel__navigation--fullscreen'
      : 'player-panel__navigation';
  const searchInPrimary = Boolean(searchPanel) && searchPlacement === 'primary';
  const advancedToggleLabel = advancedControlsOpen ? 'Hide advanced controls' : 'Show advanced controls';
  const resolvedExportLabel = exportLabel ?? (exportBusy ? 'Preparing export' : 'Export offline player');

  return {
    shouldShowPrimaryControls,
    shouldShowAdvancedControls,
    groupClassName,
    navigationClassName,
    fullscreenTestId: context === 'panel' ? 'player-panel-interactive-fullscreen' : undefined,
    searchInPrimary,
    searchInSecondary: Boolean(searchPanel) && !searchInPrimary,
    showPrimaryInfoRow: searchInPrimary,
    advancedToggleClassName: [
      'player-panel__nav-button',
      'player-panel__nav-button--caret',
      advancedControlsOpen ? 'player-panel__nav-button--advanced-active' : null,
    ]
      .filter(Boolean)
      .join(' '),
    advancedToggleLabel,
    resolvedExportLabel,
    resolvedExportTitle: exportTitle ?? resolvedExportLabel,
    shouldShowCompactControls: hasCompactNavigationControls({
      controlsLayout,
      showTranslationSpeed,
      showSubtitleScale,
      showSubtitleBackgroundOpacity,
      showFontScale,
      showMyLinguistFontScale,
      showInteractiveBackgroundOpacity,
      showInteractiveSentenceCardOpacity,
      showInteractiveThemeControls,
      showReadingBedVolume,
      showReadingBedTrack,
    }),
  };
}
