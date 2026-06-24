import { useCallback, useEffect, useMemo, useState } from 'react';
import { fetchPipelineDefaults } from '../../api/client';
import {
  buildLanguageOptions,
  normalizeLanguageLabel,
  preferLanguageLabel,
  resolveLanguageCode,
  sortLanguageLabelsByName
} from '../../utils/languages';

type VideoDubbingLanguageStateOptions = {
  primaryTargetLanguage?: string | null;
  setPrimaryTargetLanguage: (language: string) => void;
  subtitleLanguageCode?: string | null;
  subtitleLanguageLabel?: string | null;
};

export function useVideoDubbingLanguageState({
  primaryTargetLanguage,
  setPrimaryTargetLanguage,
  subtitleLanguageCode,
  subtitleLanguageLabel
}: VideoDubbingLanguageStateOptions) {
  const [targetLanguage, setTargetLanguage] = useState<string>(
    normalizeLanguageLabel(primaryTargetLanguage ?? '')
  );
  const [fetchedLanguages, setFetchedLanguages] = useState<string[]>([]);

  const applyTargetLanguage = useCallback(
    (language: string) => {
      const normalized = normalizeLanguageLabel(language);
      setTargetLanguage(normalized);
      if (normalized) {
        setPrimaryTargetLanguage(normalized);
      }
    },
    [setPrimaryTargetLanguage]
  );

  const ensureTargetLanguage = useCallback(
    (language?: string | null) => {
      if (targetLanguage) {
        return;
      }
      const normalized = normalizeLanguageLabel(language);
      if (normalized) {
        setTargetLanguage(normalized);
        setPrimaryTargetLanguage(normalized);
      }
    },
    [setPrimaryTargetLanguage, targetLanguage]
  );

  useEffect(() => {
    let cancelled = false;
    const loadDefaults = async () => {
      try {
        const defaults = await fetchPipelineDefaults();
        if (cancelled) {
          return;
        }
        const config = defaults?.config ?? {};
        const targetLanguages = Array.isArray(config['target_languages'])
          ? (config['target_languages'] as unknown[])
          : [];
        const normalised = targetLanguages
          .map((language) => (typeof language === 'string' ? normalizeLanguageLabel(language) : ''))
          .filter((language) => language.length > 0);
        if (normalised.length > 0) {
          setFetchedLanguages(normalised);
          if (!primaryTargetLanguage) {
            setPrimaryTargetLanguage(normalised[0]);
          }
        }
      } catch (error) {
        console.warn('Unable to load pipeline defaults for dubbing languages', error);
      }
    };

    void loadDefaults();
    return () => {
      cancelled = true;
    };
  }, [primaryTargetLanguage, setPrimaryTargetLanguage]);

  const languageOptions = useMemo(
    () =>
      buildLanguageOptions({
        fetchedLanguages,
        preferredLanguages: [targetLanguage, subtitleLanguageLabel, primaryTargetLanguage]
      }),
    [fetchedLanguages, primaryTargetLanguage, subtitleLanguageLabel, targetLanguage]
  );

  const sortedLanguageOptions = useMemo(() => sortLanguageLabelsByName(languageOptions), [languageOptions]);

  useEffect(() => {
    if (targetLanguage) {
      return;
    }
    const fallback = preferLanguageLabel([subtitleLanguageLabel, primaryTargetLanguage]);
    if (fallback) {
      applyTargetLanguage(fallback);
    }
  }, [applyTargetLanguage, primaryTargetLanguage, subtitleLanguageLabel, targetLanguage]);

  const targetLanguageCode = useMemo(() => {
    const preferredLabel = preferLanguageLabel([targetLanguage, subtitleLanguageLabel, primaryTargetLanguage]);
    if (preferredLabel) {
      return resolveLanguageCode(preferredLabel);
    }
    return subtitleLanguageCode?.trim().toLowerCase() ?? '';
  }, [primaryTargetLanguage, subtitleLanguageCode, subtitleLanguageLabel, targetLanguage]);

  return {
    targetLanguage,
    setTargetLanguage,
    applyTargetLanguage,
    ensureTargetLanguage,
    sortedLanguageOptions,
    targetLanguageCode
  };
}
