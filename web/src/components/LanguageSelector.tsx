import { ChangeEvent, KeyboardEvent, useId, useMemo, useRef } from 'react';
import { TOP_LANGUAGES } from '../constants/menuOptions';
import { DEFAULT_LANGUAGE_FLAG, resolveLanguageFlag } from '../constants/languageCodes';
import { formatLanguageOptionLabel, normalizeLanguageLabel, sortLanguageLabelsByName } from '../utils/languages';
import { prefersNativeEmojiFlags } from '../utils/emojiIcons';
import EmojiIcon from './EmojiIcon';

type Props = {
  id?: string;
  value: string[];
  onChange: (next: string[]) => void;
};

export function LanguageSelector({ id, value, onChange }: Props) {
  const autoId = useId();
  const selectId = id ?? `language-selector-${autoId}`;
  const helperId = `${selectId}-helper`;
  const shouldUseNative = prefersNativeEmojiFlags();
  const optionInputRefs = useRef<Map<string, HTMLInputElement>>(new Map());
  const typeaheadRef = useRef<{ query: string; lastTime: number }>({ query: '', lastTime: 0 });
  const sortedLanguages = useMemo(() => {
    return sortLanguageLabelsByName(TOP_LANGUAGES);
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
    return sortLanguageLabelsByName([...sortedLanguages, ...extras]);
  }, [sortedLanguages, value]);

  const handleChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const next = Array.from(event.target.selectedOptions).map((option) => option.value);
    onChange(next);
  };

  const selectedKeys = useMemo(() => {
    return new Set(value.map((language) => language.toLowerCase()));
  }, [value]);

  const toggleLanguage = (language: string) => {
    const key = language.toLowerCase();
    const nextKeys = new Set(selectedKeys);
    if (nextKeys.has(key)) {
      nextKeys.delete(key);
    } else {
      nextKeys.add(key);
    }
    const next = combinedOptions.filter((option) => nextKeys.has(option.toLowerCase()));
    onChange(next);
  };

  const handleTypeahead = (event: KeyboardEvent<HTMLDivElement>) => {
    if (shouldUseNative) {
      return;
    }
    if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) {
      return;
    }
    const key = event.key;
    if (key.length !== 1 || !/^[a-z0-9]$/i.test(key)) {
      return;
    }
    event.preventDefault();
    const now = Date.now();
    const previous = typeaheadRef.current;
    const withinWindow = now - previous.lastTime < 700;
    const nextChar = key.toLowerCase();
    let query = withinWindow ? previous.query : '';
    query = `${query}${nextChar}`.slice(0, 32);
    typeaheadRef.current = { query, lastTime: now };

    const normalizedQuery = query.toLowerCase();
    const match = combinedOptions.find((language) => {
      const label = (normalizeLanguageLabel(language) || language).toLowerCase();
      return label.startsWith(normalizedQuery);
    });
    if (!match) {
      return;
    }
    const input = optionInputRefs.current.get(match.toLowerCase());
    if (input) {
      input.focus();
      try {
        input.closest('label')?.scrollIntoView({ block: 'nearest' });
      } catch {
        // ignore
      }
    }
  };

  return (
    <div className="language-selector">
      {value.length > 0 ? (
        <div className="language-selector__flags" aria-hidden="true">
          {value.slice(0, 8).map((language) => {
            const flagEmoji = resolveLanguageFlag(language) ?? DEFAULT_LANGUAGE_FLAG;
            return <EmojiIcon key={language} emoji={flagEmoji} className="language-selector__flag" />;
          })}
          {value.length > 8 ? (
            <span className="language-selector__more">+{value.length - 8}</span>
          ) : null}
        </div>
      ) : null}
      {shouldUseNative ? (
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
              {formatLanguageOptionLabel(language)}
            </option>
          ))}
        </select>
      ) : (
        <>
          <select
            id={selectId}
            name="target_languages"
            multiple
            value={value}
            onChange={handleChange}
            aria-hidden="true"
            tabIndex={-1}
            style={{ display: 'none' }}
          >
            {combinedOptions.map((language) => (
              <option key={language} value={language}>
                {formatLanguageOptionLabel(language)}
              </option>
            ))}
          </select>
          <div
            className="language-selector__options"
            aria-describedby={helperId}
            onKeyDown={handleTypeahead}
          >
            {combinedOptions.map((language) => {
              const label = normalizeLanguageLabel(language) || language;
              const key = language.toLowerCase();
              const isSelected = selectedKeys.has(key);
              const flagEmoji = resolveLanguageFlag(language) ?? DEFAULT_LANGUAGE_FLAG;
              return (
                <label
                  key={language}
                  className={[
                    'language-selector__option',
                    isSelected ? 'language-selector__option--selected' : ''
                  ]
                    .filter(Boolean)
                    .join(' ')}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleLanguage(language)}
                    className="language-selector__option-checkbox"
                    ref={(node) => {
                      if (!node) {
                        optionInputRefs.current.delete(key);
                        return;
                      }
                      optionInputRefs.current.set(key, node);
                    }}
                  />
                  <EmojiIcon emoji={flagEmoji} className="language-selector__option-flag" />
                  <span className="language-selector__option-label">{label}</span>
                </label>
              );
            })}
          </div>
        </>
      )}
      <p id={helperId} className="language-helper">
        {shouldUseNative
          ? 'Select one or more languages. Hold Command (macOS) or Control (Windows) while clicking to choose additional languages.'
          : 'Select one or more languages by toggling the checkboxes.'}
      </p>
    </div>
  );
}

export default LanguageSelector;
