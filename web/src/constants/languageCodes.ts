export const LANGUAGE_CODES: Record<string, string> = {
  Afrikaans: 'af',
  Albanian: 'sq',
  Arabic: 'ar',
  Armenian: 'hy',
  Basque: 'eu',
  Bengali: 'bn',
  Bosnian: 'bs',
  Burmese: 'my',
  Catalan: 'ca',
  'Chinese (Simplified)': 'zh-CN',
  'Chinese (Traditional)': 'zh-TW',
  Czech: 'cs',
  Croatian: 'hr',
  Danish: 'da',
  Dutch: 'nl',
  English: 'en',
  Esperanto: 'eo',
  Estonian: 'et',
  Filipino: 'tl',
  Finnish: 'fi',
  French: 'fr',
  German: 'de',
  Greek: 'el',
  Gujarati: 'gu',
  Hausa: 'ha',
  Hebrew: 'he',
  Hindi: 'hi',
  Hungarian: 'hu',
  Icelandic: 'is',
  Indonesian: 'id',
  Italian: 'it',
  Japanese: 'ja',
  Javanese: 'jw',
  Kannada: 'kn',
  Khmer: 'km',
  Korean: 'ko',
  Latin: 'la',
  Latvian: 'lv',
  Macedonian: 'mk',
  Malay: 'ms',
  Malayalam: 'ml',
  Marathi: 'mr',
  Nepali: 'ne',
  Norwegian: 'no',
  Polish: 'pl',
  Portuguese: 'pt',
  Spanish: 'es',
  Romanian: 'ro',
  Russian: 'ru',
  Sinhala: 'si',
  Slovak: 'sk',
  Serbian: 'sr',
  Sundanese: 'su',
  Swahili: 'sw',
  Swedish: 'sv',
  Tamil: 'ta',
  Telugu: 'te',
  Thai: 'th',
  Turkish: 'tr',
  Ukrainian: 'uk',
  Urdu: 'ur',
  Vietnamese: 'vi',
  Welsh: 'cy',
  Xhosa: 'xh',
  Yoruba: 'yo',
  Zulu: 'zu',
  Persian: 'fa'
};

export function resolveLanguageCode(language: string): string | null {
  const direct = LANGUAGE_CODES[language];
  if (direct) {
    return direct;
  }

  const normalized = language.trim().toLowerCase();
  if (!normalized) {
    return null;
  }

  for (const [name, code] of Object.entries(LANGUAGE_CODES)) {
    if (name.toLowerCase() === normalized) {
      return code;
    }
  }

  if (/^[a-z]{2}(?:[-_][a-z]{2})?$/i.test(language.trim())) {
    return language.trim().toLowerCase();
  }

  return null;
}

export function resolveLanguageName(code: string): string | null {
  const normalized = code.trim().toLowerCase();
  if (!normalized) {
    return null;
  }
  for (const [name, value] of Object.entries(LANGUAGE_CODES)) {
    if (value.toLowerCase() === normalized) {
      return name;
    }
  }
  return null;
}
