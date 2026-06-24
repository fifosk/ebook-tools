import type { MediaSearchResult } from '../../api/dtos';
import MediaSearchPanel from '../MediaSearchPanel';

type PlayerPanelSearchSlotProps = {
  currentJobId: string | null;
  enabled: boolean;
  isFullscreen: boolean;
  target: 'panel' | 'fullscreen';
  onResultAction: (result: MediaSearchResult, category: 'text' | 'video' | 'library') => void;
};

type BuildPlayerPanelSearchSlotsOptions = Omit<PlayerPanelSearchSlotProps, 'target'>;

export function PlayerPanelSearchSlot({
  currentJobId,
  enabled,
  isFullscreen,
  target,
  onResultAction,
}: PlayerPanelSearchSlotProps) {
  const shouldRender = enabled && (target === 'fullscreen' ? isFullscreen : !isFullscreen);

  if (!shouldRender) {
    return null;
  }

  return <MediaSearchPanel currentJobId={currentJobId} onResultAction={onResultAction} variant="compact" />;
}

export function buildPlayerPanelSearchSlots(options: BuildPlayerPanelSearchSlotsOptions) {
  return {
    panelSearchPanel: <PlayerPanelSearchSlot {...options} target="panel" />,
    fullscreenSearchPanel: <PlayerPanelSearchSlot {...options} target="fullscreen" />,
  };
}
