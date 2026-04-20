import { ReactNode, createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

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
  enableLookupCache: boolean;
  setEnableLookupCache: (enabled: boolean) => void;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

const DEFAULT_INPUT_LANGUAGE = 'English';
const DEFAULT_TARGET_LANGUAGES = ['Arabic'];
const DEFAULT_ENABLE_LOOKUP_CACHE = true;

const STORAGE_KEY = 'ebookTools.bookJobDefaults.v1';

type PersistedJobDefaults = {
  inputLanguage?: string;
  targetLanguages?: string[];
  enableLookupCache?: boolean;
};

function readPersisted(): PersistedJobDefaults {
  if (typeof window === 'undefined') {
    return {};
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === 'object') {
      return parsed as PersistedJobDefaults;
    }
  } catch {
    // Ignore corrupted entries; fall back to defaults.
  }
  return {};
}

function writePersisted(value: PersistedJobDefaults): void {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch {
    // localStorage may be disabled (private browsing); ignore.
  }
}

interface LanguageProviderProps {
  children: ReactNode;
}

export function LanguageProvider({ children }: LanguageProviderProps) {
  const [inputLanguage, setInputLanguageState] = useState<string>(() => {
    const stored = readPersisted().inputLanguage;
    if (stored && typeof stored === 'string' && stored.trim()) {
      return stored;
    }
    return DEFAULT_INPUT_LANGUAGE;
  });
  const [targetLanguages, setTargetLanguagesState] = useState<string[]>(() => {
    const stored = readPersisted().targetLanguages;
    if (Array.isArray(stored)) {
      const sanitized = sanitizeLanguages(stored);
      if (sanitized.length > 0) {
        return sanitized;
      }
    }
    return [...DEFAULT_TARGET_LANGUAGES];
  });
  const [enableLookupCache, setEnableLookupCacheState] = useState<boolean>(() => {
    const stored = readPersisted().enableLookupCache;
    return typeof stored === 'boolean' ? stored : DEFAULT_ENABLE_LOOKUP_CACHE;
  });

  // Mirror state → localStorage so returning users see their last choices.
  useEffect(() => {
    writePersisted({ inputLanguage, targetLanguages, enableLookupCache });
  }, [inputLanguage, targetLanguages, enableLookupCache]);

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

  const setEnableLookupCache = useCallback((enabled: boolean) => {
    setEnableLookupCacheState(Boolean(enabled));
  }, []);

  const contextValue = useMemo<LanguageContextValue>(() => {
    return {
      inputLanguage,
      setInputLanguage,
      targetLanguages,
      setTargetLanguages,
      primaryTargetLanguage: targetLanguages.length > 0 ? targetLanguages[0] : null,
      setPrimaryTargetLanguage,
      enableLookupCache,
      setEnableLookupCache
    };
  }, [
    inputLanguage,
    setInputLanguage,
    targetLanguages,
    setTargetLanguages,
    setPrimaryTargetLanguage,
    enableLookupCache,
    setEnableLookupCache
  ]);

  return <LanguageContext.Provider value={contextValue}>{children}</LanguageContext.Provider>;
}

export function useLanguagePreferences(): LanguageContextValue {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguagePreferences must be used within a LanguageProvider');
  }
  return context;
}
