import { useEffect, useState } from 'react';
import { fetchPipelineDefaults } from '../../api/client';
import { resolveSubtitleLanguageDefaults } from './subtitleLanguageDefaultsUtils';

type UseSubtitleLanguageDefaultsOptions = {
  inputLanguage: string;
  setInputLanguage: (language: string) => void;
};

export function useSubtitleLanguageDefaults({
  inputLanguage,
  setInputLanguage
}: UseSubtitleLanguageDefaultsOptions) {
  const [fetchedLanguages, setFetchedLanguages] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    fetchPipelineDefaults()
      .then((defaults) => {
        if (cancelled) {
          return;
        }
        const config = defaults?.config ?? {};
        const resolved = resolveSubtitleLanguageDefaults(config, inputLanguage);
        if (resolved.fetchedLanguages.length > 0) {
          setFetchedLanguages(resolved.fetchedLanguages);
        }
        if (resolved.inputLanguage) {
          setInputLanguage(resolved.inputLanguage);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          console.warn('Unable to load pipeline defaults for language list', error);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [inputLanguage, setInputLanguage]);

  return { fetchedLanguages };
}
