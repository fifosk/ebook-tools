const GOOGLE_TRANSLATION_PROVIDER_ALIASES = new Set([
  'google',
  'googletrans',
  'googletranslate',
  'google-translate',
  'gtranslate',
  'gtrans'
]);

export const TRANSLITERATION_MODE_OPTIONS = [
  {
    value: 'default',
    label: 'Use selected LLM model',
    description: 'Transliteration uses the selected LLM model when enabled.'
  },
  {
    value: 'python',
    label: 'Python transliteration module',
    description: 'Transliteration uses local python modules when available.'
  }
] as const;

export type TransliterationModeOption = (typeof TRANSLITERATION_MODE_OPTIONS)[number];
export type NormalizedTransliterationMode = TransliterationModeOption['value'];

export function normalizeTranslationProvider(value: string): string {
  const normalized = value.trim().toLowerCase();
  if (!normalized) {
    return 'llm';
  }
  if (GOOGLE_TRANSLATION_PROVIDER_ALIASES.has(normalized)) {
    return 'googletrans';
  }
  if (normalized === 'llm' || normalized === 'ollama' || normalized === 'default') {
    return 'llm';
  }
  return normalized;
}

export function normalizeTransliterationMode(value: string): NormalizedTransliterationMode {
  const normalized = value.trim().toLowerCase().replace('_', '-');
  if (
    normalized === 'python' ||
    normalized === 'python-module' ||
    normalized === 'module' ||
    normalized === 'local-module'
  ) {
    return 'python';
  }
  return 'default';
}

export function getTransliterationModeOption(value: string): TransliterationModeOption {
  const normalized = normalizeTransliterationMode(value);
  return (
    TRANSLITERATION_MODE_OPTIONS.find((option) => option.value === normalized) ??
    TRANSLITERATION_MODE_OPTIONS[0]
  );
}

export function buildLlmModelOptions(
  selectedModel: string,
  availableModels: string[],
  fallbackModels: string[] = []
): string[] {
  const selected = selectedModel.trim();
  return Array.from(
    new Set([
      ...(selected ? [selected] : []),
      ...(availableModels.length ? availableModels : fallbackModels)
    ])
  );
}

export function buildTransliterationModelOptions(
  transliterationModel: string,
  modelOptions: string[]
): string[] {
  const selected = transliterationModel.trim();
  return Array.from(new Set([...(selected ? [selected] : []), ...modelOptions]));
}
