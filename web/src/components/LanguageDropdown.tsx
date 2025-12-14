import { useId, useMemo } from 'react';
import { buildLanguageOptions, formatLanguageOptionLabel, normalizeLanguageLabel, sortLanguageLabelsByName } from '../utils/languages';

type Props = {
  id?: string;
  label: string;
  value: string;
  onChange: (next: string) => void;
  fetchedLanguages?: string[];
  preferredLanguages?: Array<string | null | undefined>;
  placeholder?: string;
  helperText?: string | null;
  disabled?: boolean;
};

export function LanguageDropdown({
  id,
  label,
  value,
  onChange,
  fetchedLanguages = [],
  preferredLanguages = [],
  placeholder = 'English',
  helperText = 'Includes flag glyphs when available.',
  disabled = false
}: Props) {
  const autoId = useId();
  const selectId = id ?? `language-dropdown-${autoId}`;
  const helperId = `${selectId}-helper`;

  const options = useMemo(() => {
    const normalizedValue = normalizeLanguageLabel(value);
    const merged = buildLanguageOptions({
      fetchedLanguages,
      preferredLanguages: [normalizedValue, ...preferredLanguages],
      fallback: placeholder
    });
    return sortLanguageLabelsByName(merged);
  }, [fetchedLanguages, placeholder, preferredLanguages, value]);

  return (
    <label htmlFor={selectId}>
      {label}
      <select
        id={selectId}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-describedby={helperText ? helperId : undefined}
        disabled={disabled}
      >
        {options.map((language) => (
          <option key={language} value={language}>
            {formatLanguageOptionLabel(language)}
          </option>
        ))}
      </select>
      {helperText ? (
        <small id={helperId} className="form-help-text">
          {helperText}
        </small>
      ) : null}
    </label>
  );
}

export default LanguageDropdown;
