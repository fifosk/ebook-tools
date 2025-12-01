export const LANGUAGE_CODES: Record<string, string> = {
  Afrikaans: 'af',
  Albanian: 'sq',
  Arabic: 'ar',
  Amharic: 'am',
  Armenian: 'hy',
  Basque: 'eu',
  Belarusian: 'be',
  Bengali: 'bn',
  Bulgarian: 'bg',
  Bosnian: 'bs',
  Burmese: 'my',
  Catalan: 'ca',
  Kazakh: 'kk',
  Kyrgyz: 'ky',
  Mongolian: 'mn',
  Tajik: 'tg',
  Turkmen: 'tk',
  Uzbek: 'uz',
  'Chinese (Simplified)': 'zh-CN',
  'Chinese (Traditional)': 'zh-TW',
  Czech: 'cs',
  Croatian: 'hr',
  Danish: 'da',
  Dutch: 'nl',
  English: 'en',
  Esperanto: 'eo',
  Estonian: 'et',
  Faroese: 'fo',
  Filipino: 'tl',
  Finnish: 'fi',
  French: 'fr',
  German: 'de',
  Georgian: 'ka',
  Greek: 'el',
  Gujarati: 'gu',
  Hausa: 'ha',
  Hebrew: 'he',
  Hindi: 'hi',
  Hungarian: 'hu',
  Irish: 'ga',
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
  Lithuanian: 'lt',
  Luxembourgish: 'lb',
  Macedonian: 'mk',
  Malay: 'ms',
  Malayalam: 'ml',
  Maltese: 'mt',
  Marathi: 'mr',
  Nepali: 'ne',
  Norwegian: 'no',
  Pashto: 'ps',
  Polish: 'pl',
  Portuguese: 'pt',
  Punjabi: 'pa',
  Scots: 'sco',
  'Scottish Gaelic': 'gd',
  Galician: 'gl',
  Romani: 'rom',
  Spanish: 'es',
  Romanian: 'ro',
  Russian: 'ru',
  Sinhala: 'si',
  Slovak: 'sk',
  Slovenian: 'sl',
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
