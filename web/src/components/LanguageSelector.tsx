import { useMemo } from 'react';
import { TOP_LANGUAGES } from '../constants/menuOptions';

type Props = {
  value: string[];
  onChange: (next: string[]) => void;
};

function toggleSelection(selected: string[], language: string): string[] {
  const exists = selected.includes(language);
  if (exists) {
    return selected.filter((item) => item !== language);
  }
  return [...selected, language];
}

export function LanguageSelector({ value, onChange }: Props) {
  const sortedLanguages = useMemo(() => TOP_LANGUAGES.slice(), []);

  return (
    <div className="language-selector">
      <div className="language-grid" role="group" aria-label="Popular target languages">
        {sortedLanguages.map((language) => {
          const id = `language-${language.toLowerCase().replace(/[^a-z0-9]+/gi, '-')}`;
          return (
            <label key={language} className="language-option" htmlFor={id}>
              <input
                id={id}
                type="checkbox"
                name="target_languages"
                value={language}
                checked={value.includes(language)}
                onChange={() => onChange(toggleSelection(value, language))}
              />
              <span>{language}</span>
            </label>
          );
        })}
      </div>
      <p className="language-helper">
        The list mirrors the CLI menu ordering. You can combine these presets with custom languages
        below.
      </p>
    </div>
  );
}

export default LanguageSelector;
