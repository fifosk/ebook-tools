import { useCallback, useEffect, useRef, useState } from 'react';

type UseInteractiveFullscreenPreferenceArgs = {
  canRenderInteractiveViewer: boolean;
  hasInteractiveChunks: boolean;
};

type UseInteractiveFullscreenPreferenceResult = {
  isInteractiveFullscreen: boolean;
  handleInteractiveFullscreenToggle: () => void;
  handleExitInteractiveFullscreen: () => void;
  resetInteractiveFullscreen: () => void;
};

export function useInteractiveFullscreenPreference({
  canRenderInteractiveViewer,
  hasInteractiveChunks,
}: UseInteractiveFullscreenPreferenceArgs): UseInteractiveFullscreenPreferenceResult {
  const resolveStoredInteractiveFullscreenPreference = () => {
    if (typeof window === 'undefined') {
      return false;
    }
    return window.localStorage.getItem('player.textFullscreenPreferred') === 'true';
  };
  const [isInteractiveFullscreen, setIsInteractiveFullscreen] = useState<boolean>(() =>
    resolveStoredInteractiveFullscreenPreference(),
  );
  const interactiveFullscreenPreferenceRef = useRef<boolean>(isInteractiveFullscreen);
  const updateInteractiveFullscreenPreference = useCallback((next: boolean) => {
    interactiveFullscreenPreferenceRef.current = next;
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('player.textFullscreenPreferred', next ? 'true' : 'false');
    }
  }, []);

  const handleInteractiveFullscreenToggle = useCallback(() => {
    setIsInteractiveFullscreen((current) => {
      const next = !current;
      updateInteractiveFullscreenPreference(next);
      return next;
    });
  }, [updateInteractiveFullscreenPreference]);

  const handleExitInteractiveFullscreen = useCallback(() => {
    updateInteractiveFullscreenPreference(false);
    setIsInteractiveFullscreen(false);
  }, [updateInteractiveFullscreenPreference]);

  const resetInteractiveFullscreen = useCallback(() => {
    setIsInteractiveFullscreen(false);
  }, []);

  useEffect(() => {
    if (!canRenderInteractiveViewer) {
      if (!hasInteractiveChunks && isInteractiveFullscreen) {
        updateInteractiveFullscreenPreference(false);
        setIsInteractiveFullscreen(false);
      }
      return;
    }
    if (interactiveFullscreenPreferenceRef.current && !isInteractiveFullscreen) {
      updateInteractiveFullscreenPreference(true);
      setIsInteractiveFullscreen(true);
    }
  }, [
    canRenderInteractiveViewer,
    hasInteractiveChunks,
    isInteractiveFullscreen,
    updateInteractiveFullscreenPreference,
  ]);

  return {
    isInteractiveFullscreen,
    handleInteractiveFullscreenToggle,
    handleExitInteractiveFullscreen,
    resetInteractiveFullscreen,
  };
}
