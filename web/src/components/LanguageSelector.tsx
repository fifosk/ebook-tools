import { ChangeEvent, useId, useMemo } from 'react';
import { TOP_LANGUAGES } from '../constants/menuOptions';
import { formatLanguageWithFlag } from '../utils/languages';

type Props = {
  id?: string;
  value: string[];
  onChange: (next: string[]) => void;
};

export function LanguageSelector({ id, value, onChange }: Props) {
  const autoId = useId();
  const selectId = id ?? `language-selector-${autoId}`;
  const helperId = `${selectId}-helper`;
  const sortedLanguages = useMemo(() => {
    const copy = TOP_LANGUAGES.slice();
    copy.sort((a, b) => a.localeCompare(b));
    return copy;
  }, []);
  const combinedOptions = useMemo(() => {
    const optionSet = new Set(sortedLanguages.map((language) => language.toLowerCase()));
    const extras: string[] = [];
    for (const language of value) {
      const normalized = language.toLowerCase();
      if (!optionSet.has(normalized)) {
        optionSet.add(normalized);
        extras.push(language);
      }
    }
    return [...sortedLanguages, ...extras];
  }, [sortedLanguages, value]);

  const handleChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const next = Array.from(event.target.selectedOptions).map((option) => option.value);
    onChange(next);
  };

  return (
    <div className="language-selector">
      <select
        id={selectId}
        name="target_languages"
        multiple
        size={Math.min(8, Math.max(4, combinedOptions.length))}
        value={value}
        onChange={handleChange}
        aria-describedby={helperId}
      >
        {combinedOptions.map((language) => (
          <option key={language} value={language}>
            {formatLanguageWithFlag(language)}
          </option>
        ))}
      </select>
      <p id={helperId} className="language-helper">
        Select one or more languages. Hold Command (macOS) or Control (Windows) while clicking to
        choose additional languages. You can still enter custom languages below.
      </p>
    </div>
  );
}

export default LanguageSelector;
