import { normalizeLanguageLabel } from '../../utils/languages';

export type SubtitleLanguageDefaults = {
  fetchedLanguages: string[];
  inputLanguage: string | null;
};

export function resolveSubtitleLanguageDefaults(
  config: Record<string, unknown> | null | undefined,
  currentInputLanguage: string
): SubtitleLanguageDefaults {
  const targetLanguages = Array.isArray(config?.['target_languages'])
    ? (config['target_languages'] as unknown[])
    : [];
  const fetchedLanguages = targetLanguages
    .map((language) => (typeof language === 'string' ? normalizeLanguageLabel(language) : ''))
    .filter((language) => language.length > 0);
  const defaultInput = normalizeLanguageLabel(
    typeof config?.['input_language'] === 'string' ? config['input_language'] : ''
  );
  return {
    fetchedLanguages,
    inputLanguage: defaultInput && !currentInputLanguage ? defaultInput : null
  };
}
