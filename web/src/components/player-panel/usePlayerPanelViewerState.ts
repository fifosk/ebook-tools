import { useMemo } from 'react';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import { useWakeLock } from '../../hooks/useWakeLock';
import { fallbackTextFromSentences } from './utils';
import { useInteractiveFullscreenPreference } from './useInteractiveFullscreenPreference';
import { buildPlayerPanelChromeState } from './playerPanelChromeState';
import { buildPlayerPanelDocumentState } from './playerPanelDocumentState';

type TextPreviewState = {
  content: string;
  raw: string;
} | null;

type UsePlayerPanelViewerStateArgs = {
  mediaTextCount: number;
  mediaAudioCount: number;
  mediaVideoCount: number;
  isLoading: boolean;
  hasInlineAudioControls: boolean;
  isInlineAudioPlaying: boolean;
  origin: 'job' | 'library';
  showBackToLibrary: boolean;
  textPreview: TextPreviewState;
  textLoading: boolean;
  textError: string | null;
  resolvedActiveTextChunk: LiveMediaChunk | null | undefined;
  hasInteractiveChunks: boolean;
  hasSelectedItem: boolean;
};

export function usePlayerPanelViewerState({
  mediaTextCount,
  mediaAudioCount,
  mediaVideoCount,
  isLoading,
  hasInlineAudioControls,
  isInlineAudioPlaying,
  origin,
  showBackToLibrary,
  textPreview,
  textLoading,
  textError,
  resolvedActiveTextChunk,
  hasInteractiveChunks,
  hasSelectedItem,
}: UsePlayerPanelViewerStateArgs) {
  const fallbackTextContent = useMemo(
    () => fallbackTextFromSentences(resolvedActiveTextChunk),
    [resolvedActiveTextChunk],
  );
  const baseDocumentState = buildPlayerPanelDocumentState({
    textPreview,
    fallbackTextContent,
    resolvedActiveTextChunk,
    isInteractiveFullscreen: false,
    hasTextItems: mediaTextCount > 0,
    hasSelectedItem,
    textLoading,
    textError,
  });

  const {
    isInteractiveFullscreen,
    handleInteractiveFullscreenToggle,
    handleExitInteractiveFullscreen,
    resetInteractiveFullscreen,
  } = useInteractiveFullscreenPreference({
    canRenderInteractiveViewer: baseDocumentState.canRenderInteractiveViewer,
    hasInteractiveChunks,
  });

  const documentState = buildPlayerPanelDocumentState({
    textPreview,
    fallbackTextContent,
    resolvedActiveTextChunk,
    isInteractiveFullscreen,
    hasTextItems: mediaTextCount > 0,
    hasSelectedItem,
    textLoading,
    textError,
  });

  const chromeState = buildPlayerPanelChromeState({
    mediaTextCount,
    mediaAudioCount,
    mediaVideoCount,
    isLoading,
    hasInlineAudioControls,
    canRenderInteractiveViewer: documentState.canRenderInteractiveViewer,
    isInlineAudioPlaying,
    origin,
    showBackToLibrary,
  });

  useWakeLock(chromeState.shouldHoldWakeLock);

  return {
    ...documentState,
    ...chromeState,
    isInteractiveFullscreen,
    handleInteractiveFullscreenToggle,
    handleExitInteractiveFullscreen,
    resetInteractiveFullscreen,
  };
}
