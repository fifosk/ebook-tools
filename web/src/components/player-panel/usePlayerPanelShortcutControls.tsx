import { useCallback, useMemo, type ReactNode } from 'react';
import { useMyLinguist } from '../../context/MyLinguistProvider';
import {
  DEFAULT_MY_LINGUIST_FONT_SCALE_PERCENT,
  MY_LINGUIST_FONT_SCALE_STEP,
  type NavigationIntent,
} from './constants';
import { ShortcutHelpOverlay } from './ShortcutHelpOverlay';
import { usePlayerShortcuts } from './usePlayerShortcuts';

type CueLayer = 'original' | 'transliteration' | 'translation';

type UsePlayerPanelShortcutControlsArgs = {
  linguistEnabled: boolean;
  canToggleOriginalAudio: boolean;
  onToggleOriginalAudio: () => void;
  canToggleTranslationAudio: boolean;
  onToggleTranslationAudio: () => void;
  onToggleCueLayer: (layer: CueLayer) => void;
  onToggleReadingBed: () => void;
  onToggleFullscreen: () => void;
  onTogglePlayback: () => void;
  onNavigate: (intent: NavigationIntent) => void;
  adjustTranslationSpeed: (direction: 'faster' | 'slower') => void;
  adjustFontScale: (direction: 'increase' | 'decrease') => void;
};

type UsePlayerPanelShortcutControlsResult = {
  baseFontScalePercent: number;
  setBaseFontScalePercent: (value: number) => void;
  resetMyLinguistFontScale: () => void;
  shortcutHelpOverlay: ReactNode;
};

export function usePlayerPanelShortcutControls({
  linguistEnabled,
  canToggleOriginalAudio,
  onToggleOriginalAudio,
  canToggleTranslationAudio,
  onToggleTranslationAudio,
  onToggleCueLayer,
  onToggleReadingBed,
  onToggleFullscreen,
  onTogglePlayback,
  onNavigate,
  adjustTranslationSpeed,
  adjustFontScale,
}: UsePlayerPanelShortcutControlsArgs): UsePlayerPanelShortcutControlsResult {
  const {
    baseFontScalePercent,
    setBaseFontScalePercent,
    adjustBaseFontScalePercent,
    toggle: toggleMyLinguist,
  } = useMyLinguist();

  const adjustMyLinguistFontScale = useCallback(
    (direction: 'increase' | 'decrease') => {
      const delta = direction === 'increase' ? MY_LINGUIST_FONT_SCALE_STEP : -MY_LINGUIST_FONT_SCALE_STEP;
      adjustBaseFontScalePercent(delta);
    },
    [adjustBaseFontScalePercent],
  );

  const handleToggleMyLinguist = useCallback(() => {
    if (linguistEnabled) {
      toggleMyLinguist();
    }
  }, [linguistEnabled, toggleMyLinguist]);

  const handleAdjustMyLinguistFontScale = useCallback(
    (direction: 'increase' | 'decrease') => {
      if (!linguistEnabled) {
        return;
      }
      adjustMyLinguistFontScale(direction);
    },
    [adjustMyLinguistFontScale, linguistEnabled],
  );

  const resetMyLinguistFontScale = useCallback(() => {
    setBaseFontScalePercent(DEFAULT_MY_LINGUIST_FONT_SCALE_PERCENT);
  }, [setBaseFontScalePercent]);

  const { showShortcutHelp, setShowShortcutHelp } = usePlayerShortcuts({
    canToggleOriginalAudio,
    onToggleOriginalAudio,
    canToggleTranslationAudio,
    onToggleTranslationAudio,
    onToggleCueLayer,
    onToggleMyLinguist: handleToggleMyLinguist,
    enableMyLinguist: linguistEnabled,
    onToggleReadingBed,
    onToggleFullscreen,
    onTogglePlayback,
    onNavigate,
    adjustTranslationSpeed,
    adjustFontScale,
    adjustMyLinguistFontScale: handleAdjustMyLinguistFontScale,
  });

  const shortcutHelpOverlay = useMemo(
    () => (
      <ShortcutHelpOverlay
        isOpen={showShortcutHelp}
        onClose={() => setShowShortcutHelp(false)}
        canToggleOriginalAudio={canToggleOriginalAudio}
        canToggleTranslationAudio={canToggleTranslationAudio}
        showMyLinguist={linguistEnabled}
      />
    ),
    [canToggleOriginalAudio, canToggleTranslationAudio, linguistEnabled, setShowShortcutHelp, showShortcutHelp],
  );

  return {
    baseFontScalePercent,
    setBaseFontScalePercent,
    resetMyLinguistFontScale,
    shortcutHelpOverlay,
  };
}
