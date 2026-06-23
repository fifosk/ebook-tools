import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLanguagePreferences } from '../../context/LanguageProvider';
import {
  buildLanguageOptions,
  normalizeLanguageLabel,
  sortLanguageLabelsByName
} from '../../utils/languages';
import { normalizeLanguageInput } from './subtitleToolUtils';
import { useSubtitleLanguageDefaults } from './useSubtitleLanguageDefaults';

export function useSubtitleLanguageState() {
  const {
    inputLanguage,
    setInputLanguage,
    primaryTargetLanguage,
    setPrimaryTargetLanguage
  } = useLanguagePreferences();
  const [targetLanguage, setTargetLanguage] = useState<string>(
    normalizeLanguageLabel(primaryTargetLanguage ?? 'French')
  );
  const { fetchedLanguages } = useSubtitleLanguageDefaults({
    inputLanguage,
    setInputLanguage
  });
  const languageOptions = useMemo(
    () =>
      buildLanguageOptions({
        fetchedLanguages,
        preferredLanguages: [inputLanguage, primaryTargetLanguage, targetLanguage]
      }),
    [fetchedLanguages, inputLanguage, primaryTargetLanguage, targetLanguage]
  );
  const sortedLanguageOptions = useMemo(
    () => sortLanguageLabelsByName(languageOptions),
    [languageOptions]
  );

  useEffect(() => {
    setTargetLanguage(primaryTargetLanguage ?? targetLanguage);
  }, [primaryTargetLanguage, targetLanguage]);

  useEffect(() => {
    if (!targetLanguage && languageOptions.length > 0) {
      const preferred = languageOptions[0];
      setTargetLanguage(preferred);
      if (preferred) {
        setPrimaryTargetLanguage(preferred);
      }
    }
  }, [languageOptions, setPrimaryTargetLanguage, targetLanguage]);

  const handleTargetLanguageChange = useCallback((next: string) => {
    const value = normalizeLanguageInput(next);
    setTargetLanguage(value);
    if (value) {
      setPrimaryTargetLanguage(value);
    }
  }, [setPrimaryTargetLanguage]);

  const handleInputLanguageChange = useCallback((next: string) => {
    const value = normalizeLanguageInput(next);
    setInputLanguage(value || 'English');
  }, [setInputLanguage]);

  return {
    inputLanguage,
    setInputLanguage,
    targetLanguage,
    setTargetLanguage,
    setPrimaryTargetLanguage,
    sortedLanguageOptions,
    handleInputLanguageChange,
    handleTargetLanguageChange
  };
}
