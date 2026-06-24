import type { LiveMediaChunk } from '../../hooks/useLiveMedia';

type TextPreviewState = {
  content: string;
  raw: string;
} | null;

type BuildPlayerPanelDocumentStateArgs = {
  textPreview: TextPreviewState;
  fallbackTextContent: string;
  resolvedActiveTextChunk: LiveMediaChunk | null | undefined;
  isInteractiveFullscreen: boolean;
  hasTextItems: boolean;
  hasSelectedItem: boolean;
  textLoading: boolean;
  textError: string | null;
};

type ResolveInteractiveViewerRenderabilityArgs = {
  previewContent?: string | null;
  fallbackTextContent: string;
  resolvedActiveTextChunk: LiveMediaChunk | null | undefined;
};

export function resolveInteractiveViewerRenderability({
  previewContent,
  fallbackTextContent,
  resolvedActiveTextChunk,
}: ResolveInteractiveViewerRenderabilityArgs): boolean {
  return (
    Boolean(resolvedActiveTextChunk) ||
    fallbackTextContent.trim().length > 0 ||
    Boolean(previewContent?.trim())
  );
}

export function buildPlayerPanelDocumentState({
  textPreview,
  fallbackTextContent,
  resolvedActiveTextChunk,
  isInteractiveFullscreen,
  hasTextItems,
  hasSelectedItem,
  textLoading,
  textError,
}: BuildPlayerPanelDocumentStateArgs) {
  const interactiveViewerContent = (textPreview?.content ?? fallbackTextContent) || '';
  const interactiveViewerRaw = textPreview?.raw ?? fallbackTextContent;
  const canRenderInteractiveViewer = resolveInteractiveViewerRenderability({
    previewContent: textPreview?.content,
    fallbackTextContent,
    resolvedActiveTextChunk,
  });
  const shouldForceInteractiveViewer = isInteractiveFullscreen;

  return {
    interactiveViewerContent,
    interactiveViewerRaw,
    canRenderInteractiveViewer,
    shouldShowInteractiveViewer: canRenderInteractiveViewer || shouldForceInteractiveViewer,
    shouldShowEmptySelectionPlaceholder:
      hasTextItems && !hasSelectedItem && !shouldForceInteractiveViewer,
    shouldShowLoadingPlaceholder:
      Boolean(textLoading && hasSelectedItem && !shouldForceInteractiveViewer),
    shouldShowStandaloneError: Boolean(textError) && !shouldForceInteractiveViewer,
  };
}
