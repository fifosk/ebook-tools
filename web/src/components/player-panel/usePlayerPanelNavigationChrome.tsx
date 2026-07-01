import { type ReactNode, useCallback, useId, useState } from 'react';
import {
  buildNavigationBaseProps,
  type BuildNavigationBasePropsArgs,
} from './playerPanelProps';
import { buildPlayerPanelNavigationGroups } from './PlayerPanelNavigationGroups';
import { hasPlayerPanelAdvancedControls } from './playerPanelChromeState';

type UsePlayerPanelNavigationChromeArgs =
  Omit<BuildNavigationBasePropsArgs, 'sentenceJumpListId'> & {
    panelSearchPanel: ReactNode | null;
    fullscreenSearchPanel: ReactNode | null;
  };

export function usePlayerPanelNavigationChrome({
  panelSearchPanel,
  fullscreenSearchPanel,
  ...basePropsArgs
}: UsePlayerPanelNavigationChromeArgs) {
  const [panelAdvancedControlsOpen, setPanelAdvancedControlsOpen] = useState(false);
  const sentenceJumpListId = useId();
  const panelSentenceJumpInputId = useId();
  const fullscreenSentenceJumpInputId = useId();

  const handlePanelAdvancedControlsToggle = useCallback(() => {
    setPanelAdvancedControlsOpen((value) => !value);
  }, []);

  const navigationBaseProps = buildNavigationBaseProps({
    ...basePropsArgs,
    sentenceJumpListId,
  });
  const hasPanelAdvancedControls = hasPlayerPanelAdvancedControls(navigationBaseProps);
  const navigationGroups = buildPlayerPanelNavigationGroups({
    baseProps: navigationBaseProps,
    panelSentenceJumpInputId,
    fullscreenSentenceJumpInputId,
    panelSearchPanel,
    fullscreenSearchPanel,
    hasAdvancedControls: hasPanelAdvancedControls,
    advancedControlsOpen: panelAdvancedControlsOpen,
    onToggleAdvancedControls: handlePanelAdvancedControlsToggle,
  });

  return {
    ...navigationGroups,
    sentenceJumpListId,
  };
}
