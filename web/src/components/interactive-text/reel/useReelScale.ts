import { useEffect, useState } from 'react';
import {
  REEL_SCALE_STORAGE_KEY,
  REEL_SCALE_DEFAULT,
  REEL_SCALE_STEP,
  clampReelScale,
} from './constants';

/**
 * Hook to manage reel scale with localStorage persistence and keyboard shortcuts.
 */
export function useReelScale() {
  const [reelScale, setReelScale] = useState<number>(() => {
    if (typeof window === 'undefined') {
      return REEL_SCALE_DEFAULT;
    }
    const stored = window.localStorage.getItem(REEL_SCALE_STORAGE_KEY);
    if (!stored) {
      return REEL_SCALE_DEFAULT;
    }
    const parsed = Number(stored);
    if (!Number.isFinite(parsed)) {
      return REEL_SCALE_DEFAULT;
    }
    return clampReelScale(Math.round(parsed * 100) / 100);
  });

  // Persist to localStorage
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    try {
      window.localStorage.setItem(REEL_SCALE_STORAGE_KEY, String(reelScale));
    } catch {
      // ignore
    }
  }, [reelScale]);

  // Keyboard shortcuts for scaling (Shift + +/-)
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
        isTypingTarget(event.target)
      ) {
        return;
      }
      const key = event.key?.toLowerCase();
      const code = event.code;
      const isPlusKey = key === '+' || key === '=' || code === 'Equal' || code === 'NumpadAdd';
      const isMinusKey = key === '-' || key === '_' || code === 'Minus' || code === 'NumpadSubtract';

      if (event.shiftKey && (isPlusKey || isMinusKey)) {
        event.preventDefault();
        setReelScale((current) => {
          const delta = isPlusKey ? REEL_SCALE_STEP : -REEL_SCALE_STEP;
          return clampReelScale(Math.round((current + delta) * 100) / 100);
        });
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  return { reelScale, setReelScale };
}

export default useReelScale;
