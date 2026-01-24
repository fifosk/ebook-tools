/**
 * Hook for handling keyboard shortcuts in the YouTube dub player.
 *
 * Manages global keyboard event listeners for navigation, playback,
 * subtitle controls, and accessibility features.
 */

import { useEffect, useCallback } from 'react';
import type { NavigationIntent } from '../components/player-panel/constants';
import type { CueVisibility } from './useSubtitlePreferences';

export interface KeyboardShortcutHandlers {
  onNavigate: (intent: NavigationIntent) => void;
  onToggleFullscreen: () => void;
  onTogglePlayback: () => void;
  adjustPlaybackSpeed: (direction: 'faster' | 'slower') => void;
  adjustSubtitleScale: (direction: 'increase' | 'decrease') => void;
  toggleCueVisibility: (key: keyof CueVisibility) => void;
  adjustBaseFontScalePercent: (delta: number) => void;
}

interface UseYoutubeKeyboardShortcutsOptions {
  handlers: KeyboardShortcutHandlers;
  fontScaleStep: number;
  enabled?: boolean;
}

/**
 * Checks if the event target is an editable element (input, textarea, contenteditable).
 */
function isTypingTarget(target: EventTarget | null): boolean {
  if (!target || !(target instanceof HTMLElement)) {
    return false;
  }
  const tag = target.tagName;
  if (!tag) {
    return false;
  }
  return target.isContentEditable || tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
}

export function useYoutubeKeyboardShortcuts({
  handlers,
  fontScaleStep,
  enabled = true,
}: UseYoutubeKeyboardShortcutsOptions): void {
  const {
    onNavigate,
    onToggleFullscreen,
    onTogglePlayback,
    adjustPlaybackSpeed,
    adjustSubtitleScale,
    toggleCueVisibility,
    adjustBaseFontScalePercent,
  } = handlers;

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;
      if (event.defaultPrevented || event.altKey || event.metaKey || isTypingTarget(event.target)) {
        return;
      }

      const key = event.key?.toLowerCase();
      const code = event.code;
      const isPlusKey = key === '+' || key === '=' || code === 'Equal' || code === 'NumpadAdd';
      const isMinusKey = key === '-' || key === '_' || code === 'Minus' || code === 'NumpadSubtract';

      // Ctrl + plus/minus for font scale
      if (event.ctrlKey) {
        if (isPlusKey) {
          adjustBaseFontScalePercent(fontScaleStep);
          event.preventDefault();
        } else if (isMinusKey) {
          adjustBaseFontScalePercent(-fontScaleStep);
          event.preventDefault();
        }
        return;
      }

      // Arrow keys for navigation
      const isArrowRight = code === 'ArrowRight' || key === 'arrowright' || event.key === 'ArrowRight';
      const isArrowLeft = code === 'ArrowLeft' || key === 'arrowleft' || event.key === 'ArrowLeft';
      if (isArrowRight) {
        onNavigate('next');
        event.preventDefault();
        return;
      }
      if (isArrowLeft) {
        onNavigate('previous');
        event.preventDefault();
        return;
      }

      // F for fullscreen
      if (key === 'f') {
        onToggleFullscreen();
        event.preventDefault();
        return;
      }

      // O for original cue visibility
      if (key === 'o') {
        toggleCueVisibility('original');
        event.preventDefault();
        return;
      }

      // I for transliteration cue visibility
      if (key === 'i') {
        toggleCueVisibility('transliteration');
        event.preventDefault();
        return;
      }

      // P for translation (processed) cue visibility
      if (key === 'p') {
        toggleCueVisibility('translation');
        event.preventDefault();
        return;
      }

      // Arrow up/down for playback speed
      const isArrowUp = code === 'ArrowUp' || key === 'arrowup' || event.key === 'ArrowUp';
      if (isArrowUp) {
        adjustPlaybackSpeed('faster');
        event.preventDefault();
        return;
      }
      const isArrowDown = code === 'ArrowDown' || key === 'arrowdown' || event.key === 'ArrowDown';
      if (isArrowDown) {
        adjustPlaybackSpeed('slower');
        event.preventDefault();
        return;
      }

      // Plus/minus for subtitle scale
      if (isPlusKey && !event.shiftKey) {
        adjustSubtitleScale('increase');
        event.preventDefault();
        return;
      }
      if (isMinusKey && !event.shiftKey) {
        adjustSubtitleScale('decrease');
        event.preventDefault();
        return;
      }

      // Space for play/pause
      if (!event.shiftKey && (event.code === 'Space' || key === ' ')) {
        onTogglePlayback();
        event.preventDefault();
      }
    },
    [
      enabled,
      adjustBaseFontScalePercent,
      adjustPlaybackSpeed,
      adjustSubtitleScale,
      fontScaleStep,
      onNavigate,
      onToggleFullscreen,
      onTogglePlayback,
      toggleCueVisibility,
    ]
  );

  useEffect(() => {
    if (typeof window === 'undefined' || !enabled) {
      return undefined;
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [enabled, handleKeyDown]);
}
