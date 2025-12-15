import { useId, useMemo } from 'react';
import { buildLanguageOptions, normalizeLanguageLabel, sortLanguageLabelsByName } from '../utils/languages';
import LanguageSelect from './LanguageSelect';

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
      <LanguageSelect
        id={selectId}
        value={value}
        options={options}
        onChange={onChange}
        disabled={disabled}
        ariaDescribedBy={helperText ? helperId : undefined}
      />
      {helperText ? (
        <small id={helperId} className="form-help-text">
          {helperText}
        </small>
      ) : null}
    </label>
  );
}

export default LanguageDropdown;
