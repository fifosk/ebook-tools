import { useRef } from 'react';
import type { InteractiveTextTheme } from '../../../types/interactiveTextTheme';
import {
  DEFAULT_INTERACTIVE_TEXT_THEME,
  normalizeHexColor,
} from '../../../types/interactiveTextTheme';

interface ThemeColorPickersProps {
  interactiveTheme: InteractiveTextTheme;
  onInteractiveThemeChange?: (next: InteractiveTextTheme) => void;
  onResetLayout?: () => void;
}

/**
 * Color picker pills for interactive theme customization.
 */
export function ThemeColorPickers({
  interactiveTheme,
  onInteractiveThemeChange,
  onResetLayout,
}: ThemeColorPickersProps) {
  const bgColorInputRef = useRef<HTMLInputElement | null>(null);
  const originalColorInputRef = useRef<HTMLInputElement | null>(null);
  const translationColorInputRef = useRef<HTMLInputElement | null>(null);
  const transliterationColorInputRef = useRef<HTMLInputElement | null>(null);
  const highlightColorInputRef = useRef<HTMLInputElement | null>(null);

  const openColorPicker = (ref: { current: HTMLInputElement | null }) => {
    ref.current?.click();
  };

  return (
    <div className="player-panel__control-theme" role="group" aria-label="Interactive theme colors">
      <button
        type="button"
        className="player-panel__control-color-pill"
        onClick={() => openColorPicker(bgColorInputRef)}
        title="Background color"
        aria-label="Pick background color"
      >
        <span className="player-panel__control-color-pill-label">BG</span>
        <span
          className="player-panel__control-color-pill-swatch"
          style={{ backgroundColor: interactiveTheme.background }}
          aria-hidden="true"
        />
      </button>
      <input
        ref={bgColorInputRef}
        className="player-panel__control-color-input"
        type="color"
        value={interactiveTheme.background}
        onChange={(event) =>
          onInteractiveThemeChange?.({
            ...interactiveTheme,
            background: normalizeHexColor(event.target.value, DEFAULT_INTERACTIVE_TEXT_THEME.background),
          })
        }
        aria-label="Background color"
      />

      <button
        type="button"
        className="player-panel__control-color-pill"
        onClick={() => openColorPicker(originalColorInputRef)}
        title="Original text color"
        aria-label="Pick original text color"
      >
        <span className="player-panel__control-color-pill-label">OR</span>
        <span
          className="player-panel__control-color-pill-swatch"
          style={{ backgroundColor: interactiveTheme.original }}
          aria-hidden="true"
        />
      </button>
      <input
        ref={originalColorInputRef}
        className="player-panel__control-color-input"
        type="color"
        value={interactiveTheme.original}
        onChange={(event) => {
          const next = normalizeHexColor(event.target.value, DEFAULT_INTERACTIVE_TEXT_THEME.original);
          onInteractiveThemeChange?.({
            ...interactiveTheme,
            original: next,
            originalActive: next,
          });
        }}
        aria-label="Original text color"
      />

      <button
        type="button"
        className="player-panel__control-color-pill"
        onClick={() => openColorPicker(translationColorInputRef)}
        title="Translation text color"
        aria-label="Pick translation text color"
      >
        <span className="player-panel__control-color-pill-label">TR</span>
        <span
          className="player-panel__control-color-pill-swatch"
          style={{ backgroundColor: interactiveTheme.translation }}
          aria-hidden="true"
        />
      </button>
      <input
        ref={translationColorInputRef}
        className="player-panel__control-color-input"
        type="color"
        value={interactiveTheme.translation}
        onChange={(event) => {
          const next = normalizeHexColor(event.target.value, DEFAULT_INTERACTIVE_TEXT_THEME.translation);
          onInteractiveThemeChange?.({
            ...interactiveTheme,
            translation: next,
          });
        }}
        aria-label="Translation text color"
      />

      <button
        type="button"
        className="player-panel__control-color-pill"
        onClick={() => openColorPicker(transliterationColorInputRef)}
        title="Transliteration text color"
        aria-label="Pick transliteration text color"
      >
        <span className="player-panel__control-color-pill-label">TL</span>
        <span
          className="player-panel__control-color-pill-swatch"
          style={{ backgroundColor: interactiveTheme.transliteration }}
          aria-hidden="true"
        />
      </button>
      <input
        ref={transliterationColorInputRef}
        className="player-panel__control-color-input"
        type="color"
        value={interactiveTheme.transliteration}
        onChange={(event) => {
          const next = normalizeHexColor(
            event.target.value,
            DEFAULT_INTERACTIVE_TEXT_THEME.transliteration,
          );
          onInteractiveThemeChange?.({
            ...interactiveTheme,
            transliteration: next,
          });
        }}
        aria-label="Transliteration text color"
      />

      <button
        type="button"
        className="player-panel__control-color-pill"
        onClick={() => openColorPicker(highlightColorInputRef)}
        title="Highlight color"
        aria-label="Pick highlight color"
      >
        <span className="player-panel__control-color-pill-label">HL</span>
        <span
          className="player-panel__control-color-pill-swatch"
          style={{ backgroundColor: interactiveTheme.highlight }}
          aria-hidden="true"
        />
      </button>
      <input
        ref={highlightColorInputRef}
        className="player-panel__control-color-input"
        type="color"
        value={interactiveTheme.highlight}
        onChange={(event) => {
          const next = normalizeHexColor(event.target.value, DEFAULT_INTERACTIVE_TEXT_THEME.highlight);
          onInteractiveThemeChange?.({
            ...interactiveTheme,
            highlight: next,
          });
        }}
        aria-label="Highlight color"
      />

      <button
        type="button"
        className="player-panel__control-reset-layout"
        onClick={() => onResetLayout?.()}
        title="Reset layout to defaults"
        aria-label="Reset layout to defaults"
      >
        ↺
      </button>
    </div>
  );
}

export default ThemeColorPickers;
