import { useEffect, useState } from 'react';

const VISIBILITY_STORAGE_KEY = 'player.sentenceImageReelVisible';

/**
 * Hook to manage reel visibility with localStorage persistence and keyboard shortcut (R).
 */
export function useReelVisibility() {
  const [isVisible, setVisible] = useState<boolean>(() => {
    if (typeof window === 'undefined') {
      return true;
    }
    const stored = window.localStorage.getItem(VISIBILITY_STORAGE_KEY);
    if (stored === null) {
      return true;
    }
    return stored === 'true';
  });

  // Persist to localStorage
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    try {
      window.localStorage.setItem(VISIBILITY_STORAGE_KEY, isVisible ? 'true' : 'false');
    } catch {
      // ignore
    }
  }, [isVisible]);

  // Keyboard shortcut (R) to toggle visibility
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const isTypingTarget = (target: EventTarget | null): target is HTMLElement => {
      if (!target || !(target instanceof HTMLElement)) {
        return false;
      }
      if (target.isContentEditable) {
        return true;
      }
      const tag = target.tagName;
      return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (
        event.defaultPrevented ||
        event.altKey ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        isTypingTarget(event.target)
      ) {
        return;
      }
      if (event.key?.toLowerCase() === 'r') {
        event.preventDefault();
        setVisible((value) => !value);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  return { isVisible, setVisible };
}

export default useReelVisibility;
