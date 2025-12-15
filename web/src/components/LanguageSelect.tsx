import { KeyboardEvent, useEffect, useId, useMemo, useRef, useState } from 'react';
import { DEFAULT_LANGUAGE_FLAG, resolveLanguageFlag } from '../constants/languageCodes';
import { formatLanguageOptionLabel, normalizeLanguageLabel, sortLanguageLabelsByName } from '../utils/languages';
import { prefersNativeEmojiFlags } from '../utils/emojiIcons';
import EmojiIcon from './EmojiIcon';

type Props = {
  id?: string;
  value: string;
  options: string[];
  onChange: (next: string) => void;
  disabled?: boolean;
  ariaDescribedBy?: string;
  className?: string;
};

function normalizeOption(value: string): string {
  return value.trim();
}

export function LanguageSelect({
  id,
  value,
  options,
  onChange,
  disabled = false,
  ariaDescribedBy,
  className
}: Props) {
  const autoId = useId();
  const controlId = id ?? `language-select-${autoId}`;
  const listboxId = `${controlId}-listbox`;
  const normalizedValue = normalizeOption(value);
  const shouldUseNative = prefersNativeEmojiFlags();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const activeOptionRef = useRef<HTMLButtonElement | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState<number>(0);

  const resolvedOptions = useMemo(() => {
    const seen = new Set<string>();
    const result: string[] = [];
    const push = (candidate: string) => {
      const normalized = normalizeOption(candidate);
      if (!normalized) {
        return;
      }
      const key = normalized.toLowerCase();
      if (seen.has(key)) {
        return;
      }
      seen.add(key);
      result.push(normalized);
    };
    options.forEach(push);
    push(normalizedValue);
    return sortLanguageLabelsByName(result);
  }, [normalizedValue, options]);

  const selectedIndex = useMemo(() => {
    const selectedKey = normalizedValue.toLowerCase();
    return resolvedOptions.findIndex((option) => option.toLowerCase() === selectedKey);
  }, [normalizedValue, resolvedOptions]);

  const selectedOption = selectedIndex >= 0 ? resolvedOptions[selectedIndex] : normalizedValue || value;
  const selectedLabel = normalizeLanguageLabel(selectedOption) || selectedOption || 'Unknown';
  const flagEmoji = resolveLanguageFlag(selectedOption) ?? DEFAULT_LANGUAGE_FLAG;

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const handlePointerDown = (event: MouseEvent | TouchEvent) => {
      const target = event.target as Node | null;
      if (!target) {
        return;
      }
      const container = containerRef.current;
      if (container && container.contains(target)) {
        return;
      }
      setIsOpen(false);
    };
    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('touchstart', handlePointerDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('touchstart', handlePointerDown);
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || !activeOptionRef.current) {
      return;
    }
    activeOptionRef.current.scrollIntoView({ block: 'nearest' });
  }, [activeIndex, isOpen]);

  const openMenu = () => {
    if (disabled) {
      return;
    }
    setIsOpen(true);
    setActiveIndex(selectedIndex >= 0 ? selectedIndex : 0);
  };

  const closeMenu = () => setIsOpen(false);

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (disabled) {
      return;
    }

    const total = resolvedOptions.length;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      if (!isOpen) {
        openMenu();
        return;
      }
      setActiveIndex((previous) => Math.min(total - 1, previous + 1));
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      if (!isOpen) {
        openMenu();
        return;
      }
      setActiveIndex((previous) => Math.max(0, previous - 1));
      return;
    }
    if (event.key === 'Home') {
      event.preventDefault();
      if (!isOpen) {
        openMenu();
      }
      setActiveIndex(0);
      return;
    }
    if (event.key === 'End') {
      event.preventDefault();
      if (!isOpen) {
        openMenu();
      }
      setActiveIndex(Math.max(0, total - 1));
      return;
    }
    if (event.key === 'Escape') {
      if (!isOpen) {
        return;
      }
      event.preventDefault();
      closeMenu();
      return;
    }
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      if (!isOpen) {
        openMenu();
        return;
      }
      const choice = resolvedOptions[activeIndex];
      if (choice) {
        onChange(choice);
      }
      closeMenu();
    }
  };

  if (shouldUseNative) {
    return (
      <div className="flagged-select">
        <EmojiIcon
          emoji={flagEmoji}
          className="flagged-select__flag"
          ariaLabel={selectedLabel}
        />
        <select
          id={controlId}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          aria-describedby={ariaDescribedBy}
          disabled={disabled}
          className={className}
        >
          {resolvedOptions.map((language) => (
            <option key={language} value={language}>
              {formatLanguageOptionLabel(language)}
            </option>
          ))}
        </select>
      </div>
    );
  }

  return (
    <div className="flagged-select" ref={containerRef}>
      <EmojiIcon
        emoji={flagEmoji}
        className="flagged-select__flag"
        ariaLabel={selectedLabel}
      />
      <div className="language-picker">
        <button
          type="button"
          id={controlId}
          className={['language-picker__button', className].filter(Boolean).join(' ')}
          onClick={() => (isOpen ? closeMenu() : openMenu())}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          aria-haspopup="listbox"
          aria-expanded={isOpen}
          aria-controls={isOpen ? listboxId : undefined}
          aria-describedby={ariaDescribedBy}
        >
          <span className="language-picker__label">{selectedLabel}</span>
          <span className="language-picker__chevron" aria-hidden="true">
            ▾
          </span>
        </button>
        {isOpen ? (
          <div className="language-picker__menu" role="presentation">
            <ul id={listboxId} className="language-picker__list" role="listbox" aria-labelledby={controlId}>
              {resolvedOptions.map((language, index) => {
                const languageLabel = normalizeLanguageLabel(language) || language;
                const emoji = resolveLanguageFlag(language) ?? DEFAULT_LANGUAGE_FLAG;
                const isSelected = index === selectedIndex;
                const isActive = index === activeIndex;
                return (
                  <li key={language} role="option" aria-selected={isSelected}>
                    <button
                      type="button"
                      className={[
                        'language-picker__option',
                        isSelected ? 'language-picker__option--selected' : '',
                        isActive ? 'language-picker__option--active' : ''
                      ]
                        .filter(Boolean)
                        .join(' ')}
                      onMouseEnter={() => setActiveIndex(index)}
                      onClick={() => {
                        onChange(language);
                        closeMenu();
                      }}
                      ref={isActive ? activeOptionRef : undefined}
                    >
                      <EmojiIcon emoji={emoji} className="language-picker__option-flag" />
                      <span className="language-picker__option-label">{languageLabel}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default LanguageSelect;

