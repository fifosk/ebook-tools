import { ReactNode, createContext, useCallback, useContext, useMemo, useState } from 'react';

function sanitizeLanguages(values: string[]): string[] {
  const normalized: string[] = [];
  const seen = new Set<string>();

  for (const entry of values) {
    const trimmed = entry.trim();
    if (!trimmed) {
      continue;
    }
    const key = trimmed.toLowerCase();
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    normalized.push(trimmed);
  }

  return normalized;
}

export interface LanguageContextValue {
  inputLanguage: string;
  setInputLanguage: (language: string) => void;
  targetLanguages: string[];
  setTargetLanguages: (languages: string[]) => void;
  primaryTargetLanguage: string | null;
  setPrimaryTargetLanguage: (language: string) => void;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

const DEFAULT_INPUT_LANGUAGE = 'English';
const DEFAULT_TARGET_LANGUAGES = ['French'];

interface LanguageProviderProps {
  children: ReactNode;
}

export function LanguageProvider({ children }: LanguageProviderProps) {
  const [inputLanguage, setInputLanguageState] = useState<string>(DEFAULT_INPUT_LANGUAGE);
  const [targetLanguages, setTargetLanguagesState] = useState<string[]>(DEFAULT_TARGET_LANGUAGES);

  const setInputLanguage = useCallback((language: string) => {
    const next = language && language.trim() ? language : DEFAULT_INPUT_LANGUAGE;
    setInputLanguageState(next);
  }, []);

  const setTargetLanguages = useCallback((languages: string[]) => {
    const next = sanitizeLanguages(languages);
    if (next.length === 0) {
      setTargetLanguagesState([]);
      return;
    }
    setTargetLanguagesState(next);
  }, []);

  const setPrimaryTargetLanguage = useCallback((language: string) => {
    const trimmed = language.trim();
    if (!trimmed) {
      setTargetLanguagesState((previous) => {
        if (previous.length <= 1) {
          return [];
        }
        return previous.slice(1);
      });
      return;
    }
    setTargetLanguagesState((previous) => {
      const normalizedPrevious = sanitizeLanguages(previous);
      const filtered = normalizedPrevious.filter(
        (entry) => entry.toLowerCase() !== trimmed.toLowerCase()
      );
      return [trimmed, ...filtered];
    });
  }, []);

  const contextValue = useMemo<LanguageContextValue>(() => {
    return {
      inputLanguage,
      setInputLanguage,
      targetLanguages,
      setTargetLanguages,
      primaryTargetLanguage: targetLanguages.length > 0 ? targetLanguages[0] : null,
      setPrimaryTargetLanguage
    };
  }, [inputLanguage, setInputLanguage, targetLanguages, setTargetLanguages, setPrimaryTargetLanguage]);

  return <LanguageContext.Provider value={contextValue}>{children}</LanguageContext.Provider>;
}

export function useLanguagePreferences(): LanguageContextValue {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguagePreferences must be used within a LanguageProvider');
  }
  return context;
}
