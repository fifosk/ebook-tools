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

const LANGUAGE_CODE_ALIASES: Record<string, string> = {
  amh: 'am',
  ara: 'ar',
  ben: 'bn',
  bos: 'bs',
  bul: 'bg',
  ces: 'cs',
  chi: 'zh-CN',
  chs: 'zh-CN',
  cht: 'zh-TW',
  cmn: 'zh-CN',
  cze: 'cs',
  dan: 'da',
  deu: 'de',
  dut: 'nl',
  ell: 'el',
  eng: 'en',
  est: 'et',
  fas: 'fa',
  fin: 'fi',
  fre: 'fr',
  fra: 'fr',
  ger: 'de',
  gre: 'el',
  heb: 'he',
  hin: 'hi',
  hrv: 'hr',
  hun: 'hu',
  ind: 'id',
  ita: 'it',
  jpn: 'ja',
  kor: 'ko',
  lav: 'lv',
  lit: 'lt',
  may: 'ms',
  msa: 'ms',
  nor: 'no',
  pes: 'fa',
  per: 'fa',
  pol: 'pl',
  por: 'pt',
  'por-br': 'pt-br',
  ptbr: 'pt-br',
  pus: 'ps',
  ron: 'ro',
  rum: 'ro',
  rus: 'ru',
  slo: 'sk',
  slk: 'sk',
  slv: 'sl',
  spa: 'es',
  srp: 'sr',
  swe: 'sv',
  tam: 'ta',
  tel: 'te',
  tha: 'th',
  tur: 'tr',
  ukr: 'uk',
  vie: 'vi',
  zho: 'zh-CN'
};

export function resolveLanguageCode(language: string): string | null {
  const direct = LANGUAGE_CODES[language];
  if (direct) {
    return direct;
  }

  const normalized = language.trim().toLowerCase();
  const canonical = normalized.replace(/_/g, '-');
  if (!normalized) {
    return null;
  }

  if (LANGUAGE_CODE_ALIASES[canonical]) {
    return LANGUAGE_CODE_ALIASES[canonical];
  }

  for (const [name, code] of Object.entries(LANGUAGE_CODES)) {
    if (name.toLowerCase() === normalized) {
      return code;
    }
  }

  if (LANGUAGE_CODE_ALIASES[canonical]) {
    return LANGUAGE_CODE_ALIASES[canonical];
  }

  if (/^[a-z]{2,3}(?:[-_][a-z]{2,3})?$/i.test(normalized)) {
    return canonical;
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

export const LANGUAGE_FLAG_MAP: Record<string, string> = {
  af: '🇿🇦',
  am: '🇪🇹',
  ar: '🇸🇦',
  be: '🇧🇾',
  bg: '🇧🇬',
  bn: '🇧🇩',
  bs: '🇧🇦',
  ca: '🇪🇸',
  cs: '🇨🇿',
  cy: '🇬🇧',
  da: '🇩🇰',
  de: '🇩🇪',
  el: '🇬🇷',
  en: '🇺🇸',
  'en-gb': '🇬🇧',
  'en-us': '🇺🇸',
  es: '🇪🇸',
  et: '🇪🇪',
  eu: '🇪🇸',
  fa: '🇮🇷',
  fi: '🇫🇮',
  fil: '🇵🇭',
  fo: '🇫🇴',
  fr: '🇫🇷',
  ga: '🇮🇪',
  gd: '🇬🇧',
  gl: '🇪🇸',
  gu: '🇮🇳',
  ha: '🇳🇬',
  he: '🇮🇱',
  hi: '🇮🇳',
  hr: '🇭🇷',
  hu: '🇭🇺',
  hy: '🇦🇲',
  id: '🇮🇩',
  is: '🇮🇸',
  it: '🇮🇹',
  ja: '🇯🇵',
  jw: '🇮🇩',
  ka: '🇬🇪',
  kk: '🇰🇿',
  km: '🇰🇭',
  kn: '🇮🇳',
  ko: '🇰🇷',
  ky: '🇰🇬',
  la: '🇻🇦',
  lb: '🇱🇺',
  lt: '🇱🇹',
  lv: '🇱🇻',
  mk: '🇲🇰',
  ml: '🇮🇳',
  mn: '🇲🇳',
  mr: '🇮🇳',
  ms: '🇲🇾',
  mt: '🇲🇹',
  my: '🇲🇲',
  ne: '🇳🇵',
  nl: '🇳🇱',
  no: '🇳🇴',
  pa: '🇮🇳',
  pl: '🇵🇱',
  ps: '🇦🇫',
  pt: '🇵🇹',
  'pt-br': '🇧🇷',
  ro: '🇷🇴',
  ru: '🇷🇺',
  sco: '🇬🇧',
  si: '🇱🇰',
  sk: '🇸🇰',
  sl: '🇸🇮',
  sq: '🇦🇱',
  sr: '🇷🇸',
  su: '🇮🇩',
  sv: '🇸🇪',
  sw: '🇰🇪',
  ta: '🇮🇳',
  te: '🇮🇳',
  tg: '🇹🇯',
  th: '🇹🇭',
  tl: '🇵🇭',
  tr: '🇹🇷',
  uk: '🇺🇦',
  ur: '🇵🇰',
  uz: '🇺🇿',
  vi: '🇻🇳',
  xh: '🇿🇦',
  yo: '🇳🇬',
  zh: '🇨🇳',
  'zh-cn': '🇨🇳',
  'zh-tw': '🇹🇼',
  zu: '🇿🇦'
};

export const DEFAULT_LANGUAGE_FLAG = '🌐';

function normalizeLanguageFlagKey(value: string): string | null {
  const normalized = value.trim().toLowerCase().replace(/_/g, '-');
  return normalized || null;
}

export function resolveLanguageFlag(language: string): string | null {
  const code = resolveLanguageCode(language) ?? language;
  if (!code) {
    return null;
  }
  const normalized = normalizeLanguageFlagKey(code);
  if (!normalized) {
    return null;
  }
  if (LANGUAGE_FLAG_MAP[normalized]) {
    return LANGUAGE_FLAG_MAP[normalized];
  }
  const base = normalized.split('-')[0];
  if (base && LANGUAGE_FLAG_MAP[base]) {
    return LANGUAGE_FLAG_MAP[base];
  }
  return null;
}
