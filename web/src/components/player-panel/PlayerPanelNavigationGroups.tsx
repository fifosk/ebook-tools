import type { ReactNode } from 'react';
import { NavigationControls, type NavigationControlsProps } from './NavigationControls';

type NavigationBaseProps = Omit<NavigationControlsProps, 'context' | 'sentenceJumpInputId'>;

type BuildPlayerPanelNavigationGroupsArgs = {
  baseProps: NavigationBaseProps;
  panelSentenceJumpInputId: string;
  fullscreenSentenceJumpInputId: string;
  panelSearchPanel: ReactNode;
  fullscreenSearchPanel: ReactNode;
  hasAdvancedControls: boolean;
  advancedControlsOpen: boolean;
  onToggleAdvancedControls: () => void;
};

export function buildPlayerPanelNavigationGroups({
  baseProps,
  panelSentenceJumpInputId,
  fullscreenSentenceJumpInputId,
  panelSearchPanel,
  fullscreenSearchPanel,
  hasAdvancedControls,
  advancedControlsOpen,
  onToggleAdvancedControls,
}: BuildPlayerPanelNavigationGroupsArgs) {
  const panelNavigation = (
    <NavigationControls
      context="panel"
      sentenceJumpInputId={panelSentenceJumpInputId}
      searchPanel={panelSearchPanel}
      {...baseProps}
      showAdvancedControls={advancedControlsOpen && hasAdvancedControls}
      showAdvancedToggle={hasAdvancedControls}
      advancedControlsOpen={advancedControlsOpen}
      onToggleAdvancedControls={hasAdvancedControls ? onToggleAdvancedControls : undefined}
    />
  );

  const fullscreenMainControls = (
    <NavigationControls
      context="fullscreen"
      sentenceJumpInputId={fullscreenSentenceJumpInputId}
      searchPanel={fullscreenSearchPanel}
      {...baseProps}
      showPrimaryControls
      showAdvancedControls={false}
    />
  );

  const fullscreenAdvancedControls = (
    <NavigationControls
      context="fullscreen"
      sentenceJumpInputId={fullscreenSentenceJumpInputId}
      {...baseProps}
      showPrimaryControls={false}
      showAdvancedControls
    />
  );

  return {
    panelNavigation,
    fullscreenMainControls,
    fullscreenAdvancedControls,
  };
}
