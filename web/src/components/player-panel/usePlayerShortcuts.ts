import { useEffect, useState } from 'react';
import type { NavigationIntent } from './constants';

type CueLayer = 'original' | 'transliteration' | 'translation';

type UsePlayerShortcutsArgs = {
  canToggleOriginalAudio: boolean;
  onToggleOriginalAudio: () => void;
  canToggleTranslationAudio: boolean;
  onToggleTranslationAudio: () => void;
  onToggleCueLayer: (layer: CueLayer) => void;
  onToggleMyLinguist: () => void;
  enableMyLinguist?: boolean;
  onToggleReadingBed: () => void;
  onToggleFullscreen: () => void;
  onTogglePlayback: () => void;
  onNavigate: (intent: NavigationIntent) => void;
  adjustTranslationSpeed: (direction: 'faster' | 'slower') => void;
  adjustFontScale: (direction: 'increase' | 'decrease') => void;
  adjustMyLinguistFontScale: (direction: 'increase' | 'decrease') => void;
};

type UsePlayerShortcutsResult = {
  showShortcutHelp: boolean;
  setShowShortcutHelp: React.Dispatch<React.SetStateAction<boolean>>;
};

export function usePlayerShortcuts({
  canToggleOriginalAudio,
  onToggleOriginalAudio,
  canToggleTranslationAudio,
  onToggleTranslationAudio,
  onToggleCueLayer,
  onToggleMyLinguist,
  enableMyLinguist = true,
  onToggleReadingBed,
  onToggleFullscreen,
  onTogglePlayback,
  onNavigate,
  adjustTranslationSpeed,
  adjustFontScale,
  adjustMyLinguistFontScale,
}: UsePlayerShortcutsArgs): UsePlayerShortcutsResult {
  const [showShortcutHelp, setShowShortcutHelp] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined;
    }
    const isTypingTarget = (target: EventTarget | null): boolean => {
      if (!target || !(target instanceof HTMLElement)) {
        return false;
      }
      const tag = target.tagName;
      if (!tag) {
        return false;
      }
      const editable =
        target.isContentEditable ||
        tag === 'INPUT' ||
        tag === 'TEXTAREA' ||
        tag === 'SELECT';
      return editable;
    };
    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.defaultPrevented || event.altKey || event.metaKey || isTypingTarget(event.target)) {
        return;
      }
      const key = event.key?.toLowerCase();
      const code = event.code;
      const isPlusKey =
        key === '+' || key === '=' || code === 'Equal' || code === 'NumpadAdd';
      const isMinusKey =
        key === '-' || key === '_' || code === 'Minus' || code === 'NumpadSubtract';

      if (event.ctrlKey) {
        if (enableMyLinguist && isPlusKey) {
          adjustMyLinguistFontScale('increase');
          event.preventDefault();
          return;
        }
        if (enableMyLinguist && isMinusKey) {
          adjustMyLinguistFontScale('decrease');
          event.preventDefault();
          return;
        }
        return;
      }
      const isArrowRight =
        code === 'ArrowRight' || key === 'arrowright' || event.key === 'ArrowRight';
      const isArrowLeft =
        code === 'ArrowLeft' || key === 'arrowleft' || event.key === 'ArrowLeft';
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
      if (key === 'h' && !event.shiftKey) {
        setShowShortcutHelp((value) => !value);
        event.preventDefault();
        return;
      }
      if (key === 'l' && !event.shiftKey && enableMyLinguist) {
        onToggleMyLinguist();
        event.preventDefault();
        return;
      }
      if (key === 'm' && !event.shiftKey) {
        onToggleReadingBed();
        event.preventDefault();
        return;
      }
      if (key === 'f') {
        onToggleFullscreen();
        event.preventDefault();
        return;
      }
      if (key === 'o') {
        if (event.shiftKey && canToggleOriginalAudio) {
          onToggleOriginalAudio();
        } else {
          onToggleCueLayer('original');
        }
        event.preventDefault();
        return;
      }
      if (key === 'i') {
        onToggleCueLayer('transliteration');
        event.preventDefault();
        return;
      }
      if (key === 'p') {
        if (event.shiftKey && canToggleTranslationAudio) {
          onToggleTranslationAudio();
        } else {
          onToggleCueLayer('translation');
        }
        event.preventDefault();
        return;
      }
      const isArrowUp =
        code === 'ArrowUp' || key === 'arrowup' || event.key === 'ArrowUp';
      if (isArrowUp) {
        adjustTranslationSpeed('faster');
        event.preventDefault();
        return;
      }
      const isArrowDown =
        code === 'ArrowDown' || key === 'arrowdown' || event.key === 'ArrowDown';
      if (isArrowDown) {
        adjustTranslationSpeed('slower');
        event.preventDefault();
        return;
      }
      if (isPlusKey && !event.shiftKey) {
        adjustFontScale('increase');
        event.preventDefault();
        return;
      }
      if (isMinusKey && !event.shiftKey) {
        adjustFontScale('decrease');
        event.preventDefault();
        return;
      }
      if (!event.shiftKey && (event.code === 'Space' || key === ' ')) {
        onTogglePlayback();
        event.preventDefault();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [
    adjustFontScale,
    adjustMyLinguistFontScale,
    adjustTranslationSpeed,
    canToggleOriginalAudio,
    canToggleTranslationAudio,
    enableMyLinguist,
    onNavigate,
    onToggleCueLayer,
    onToggleFullscreen,
    onToggleMyLinguist,
    onToggleOriginalAudio,
    onToggleTranslationAudio,
    onTogglePlayback,
    onToggleReadingBed,
  ]);

  return { showShortcutHelp, setShowShortcutHelp };
}
