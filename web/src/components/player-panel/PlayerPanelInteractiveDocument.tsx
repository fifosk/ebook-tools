import type { ComponentPropsWithoutRef, RefObject } from 'react';
import type { LiveMediaItem } from '../../hooks/useLiveMedia';
import InteractiveTextViewer from '../InteractiveTextViewer';

type InteractiveTextViewerProps = ComponentPropsWithoutRef<typeof InteractiveTextViewer>;

interface PlayerPanelInteractiveDocumentProps {
  shouldShowEmptySelectionPlaceholder: boolean;
  shouldShowLoadingPlaceholder: boolean;
  shouldShowStandaloneError: boolean;
  shouldShowInteractiveViewer: boolean;
  canRenderInteractiveViewer: boolean;
  textError: string | null;
  textLoading: boolean;
  selectedItem: LiveMediaItem | null;
  viewerProps: InteractiveTextViewerProps;
  textScrollRef: RefObject<HTMLDivElement | null>;
}

export function PlayerPanelInteractiveDocument({
  shouldShowEmptySelectionPlaceholder,
  shouldShowLoadingPlaceholder,
  shouldShowStandaloneError,
  shouldShowInteractiveViewer,
  canRenderInteractiveViewer,
  textError,
  textLoading,
  selectedItem,
  viewerProps,
  textScrollRef,
}: PlayerPanelInteractiveDocumentProps) {
  if (shouldShowEmptySelectionPlaceholder) {
    return (
      <div className="player-panel__empty-viewer" role="status">
        Select a file to preview.
      </div>
    );
  }

  if (shouldShowLoadingPlaceholder) {
    return (
      <div className="player-panel__document-status" role="status">
        Loading document…
      </div>
    );
  }

  if (shouldShowStandaloneError) {
    return (
      <div className="player-panel__document-error" role="alert">
        {textError}
      </div>
    );
  }

  if (!shouldShowInteractiveViewer) {
    return (
      <div className="player-panel__document-status" role="status">
        Interactive reader assets are still being prepared.
      </div>
    );
  }

  return (
    <>
      <InteractiveTextViewer ref={textScrollRef} {...viewerProps} />
      {textLoading && selectedItem ? (
        <div className="player-panel__document-status" role="status">
          Loading document…
        </div>
      ) : null}
      {textError ? (
        <div className="player-panel__document-error" role="alert">
          {textError}
        </div>
      ) : null}
      {!canRenderInteractiveViewer ? (
        <div className="player-panel__document-status" role="status">
          Interactive reader assets are still being prepared.
        </div>
      ) : null}
    </>
  );
}
