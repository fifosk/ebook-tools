import { useEffect, useState } from 'react';
import { getLocalStorageItem, setLocalStorageItem } from '../../utils/browserStorage';

export const ORIGINAL_AUDIO_VISIBILITY_KEY = 'player.showOriginalAudio';
export const TRANSLATION_AUDIO_VISIBILITY_KEY = 'player.showTranslationAudio';

function readStoredVisibility(key: string): boolean {
  const stored = getLocalStorageItem(key);
  if (stored === null) {
    return true;
  }
  return stored === 'true';
}

function persistVisibility(key: string, value: boolean) {
  setLocalStorageItem(key, value ? 'true' : 'false');
}

export function useAudioTrackVisibility() {
  const [showOriginalAudio, setShowOriginalAudio] = useState<boolean>(() =>
    readStoredVisibility(ORIGINAL_AUDIO_VISIBILITY_KEY),
  );
  const [showTranslationAudio, setShowTranslationAudio] = useState<boolean>(() =>
    readStoredVisibility(TRANSLATION_AUDIO_VISIBILITY_KEY),
  );

  useEffect(() => {
    persistVisibility(ORIGINAL_AUDIO_VISIBILITY_KEY, showOriginalAudio);
  }, [showOriginalAudio]);

  useEffect(() => {
    persistVisibility(TRANSLATION_AUDIO_VISIBILITY_KEY, showTranslationAudio);
  }, [showTranslationAudio]);

  return {
    showOriginalAudio,
    setShowOriginalAudio,
    showTranslationAudio,
    setShowTranslationAudio,
  };
}
