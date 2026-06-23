import { useEffect, useState } from 'react';
import { SHOW_ORIGINAL_STORAGE_KEY } from './subtitleToolConfig';

function readInitialShowOriginal(): boolean {
  if (typeof window === 'undefined') {
    return true;
  }
  try {
    const persisted = window.localStorage.getItem(SHOW_ORIGINAL_STORAGE_KEY);
    if (persisted === null) {
      return true;
    }
    return persisted === 'true';
  } catch {
    return true;
  }
}

export function useSubtitleShowOriginalPreference() {
  const [showOriginal, setShowOriginal] = useState<boolean>(readInitialShowOriginal);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    try {
      window.localStorage.setItem(SHOW_ORIGINAL_STORAGE_KEY, showOriginal ? 'true' : 'false');
    } catch {
      // Ignore persistence failures; preference resets next session.
    }
  }, [showOriginal]);

  return { showOriginal, setShowOriginal };
}
