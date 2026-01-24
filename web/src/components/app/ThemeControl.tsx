import { useCallback, useId, useMemo } from 'react';
import { useTheme } from '../ThemeProvider';
import type { ThemeMode } from '../ThemeProvider';

interface ThemeOption {
  mode: ThemeMode;
  label: string;
  description: string;
}

interface ThemeControlProps {
  variant?: 'sidebar' | 'standalone';
}

const THEME_OPTIONS: ThemeOption[] = [
  {
    mode: 'light',
    label: 'Light',
    description: 'Bright surfaces with dark text for daytime environments.'
  },
  {
    mode: 'dark',
    label: 'Dark',
    description: 'Dim surfaces with light text to reduce glare at night.'
  },
  {
    mode: 'magenta',
    label: 'Magenta',
    description: 'High-contrast magenta palette for vibrant accents.'
  },
  {
    mode: 'system',
    label: 'System',
    description: 'Automatically match your operating system theme.'
  }
];

/**
 * Theme selector control with visual swatches and descriptions.
 */
export function ThemeControl({ variant = 'sidebar' }: ThemeControlProps) {
  const { mode: themeMode, resolvedTheme, setMode: setThemeMode } = useTheme();
  const themeLabelId = useId();
  const themeHintId = useId();

  const handleThemeSelect = useCallback(
    (mode: ThemeMode) => {
      setThemeMode(mode);
    },
    [setThemeMode]
  );

  const classNames = useMemo(() => {
    const base = 'theme-control';
    return variant === 'sidebar' ? `${base} ${base}--sidebar` : base;
  }, [variant]);

  return (
    <div className={classNames}>
      <span className="theme-control__label" id={themeLabelId}>
        Theme
      </span>
      <div className="theme-control__options" role="group" aria-labelledby={themeLabelId}>
        {THEME_OPTIONS.map((option) => {
          const descriptionId = `${themeLabelId}-${option.mode}`;
          const describedBy =
            themeMode === 'system' && option.mode === 'system'
              ? `${descriptionId} ${themeHintId}`
              : descriptionId;
          return (
            <button
              key={option.mode}
              type="button"
              className="theme-control__option"
              data-theme-option={option.mode}
              aria-pressed={themeMode === option.mode}
              aria-describedby={describedBy}
              onClick={() => {
                handleThemeSelect(option.mode);
              }}
            >
              <span
                className={`theme-control__option-swatch theme-control__option-swatch--${option.mode}`}
                aria-hidden="true"
              />
              <span className="theme-control__option-copy">
                <span className="theme-control__option-label">{option.label}</span>
                <span className="theme-control__option-description" id={descriptionId}>
                  {option.description}
                </span>
              </span>
            </button>
          );
        })}
      </div>
      {themeMode === 'system' ? (
        <span className="theme-control__hint" id={themeHintId} aria-live="polite">
          Following {resolvedTheme} mode
        </span>
      ) : null}
    </div>
  );
}

export default ThemeControl;
