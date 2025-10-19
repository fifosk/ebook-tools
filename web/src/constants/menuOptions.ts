export interface MenuOption {
  value: string;
  label: string;
  description: string;
}

export const AUDIO_MODE_OPTIONS: MenuOption[] = [
  {
    value: '1',
    label: 'Audio mode 1',
    description: 'Only the translated sentence is narrated.'
  },
  {
    value: '2',
    label: 'Audio mode 2',
    description: 'Narrate the sentence number followed by the translated sentence.'
  },
  {
    value: '3',
    label: 'Audio mode 3',
    description: 'Full original format including numbering, original sentence, and translation.'
  },
  {
    value: '4',
    label: 'Audio mode 4',
    description: 'Original sentence followed by the translated sentence.'
  }
];

export const WRITTEN_MODE_OPTIONS: MenuOption[] = [
  {
    value: '1',
    label: 'Written mode 1',
    description: 'Only the fluent translation is written to the output.'
  },
  {
    value: '2',
    label: 'Written mode 2',
    description: 'Sentence numbering followed by the fluent translation.'
  },
  {
    value: '3',
    label: 'Written mode 3',
    description: 'Full original format including numbering, source, and translation.'
  },
  {
    value: '4',
    label: 'Written mode 4',
    description: 'Original sentence alongside the fluent translation.'
  }
];

export const VOICE_OPTIONS: MenuOption[] = [
  {
    value: 'gTTS',
    label: 'Google Text-to-Speech (gTTS)',
    description: 'Cross-platform default voice provider used by the CLI.'
  },
  {
    value: 'macOS-auto',
    label: 'Auto-select macOS voice',
    description: 'Let macOS decide which system voice to use based on target language.'
  },
  {
    value: 'macOS-auto-female',
    label: 'macOS female voice',
    description: 'Automatically select a female-presenting macOS system voice.'
  },
  {
    value: 'macOS-auto-male',
    label: 'macOS male voice',
    description: 'Automatically select a male-presenting macOS system voice.'
  }
];

export const TOP_LANGUAGES: string[] = [
  'Afrikaans',
  'Albanian',
  'Arabic',
  'Armenian',
  'Basque',
  'Bengali',
  'Bosnian',
  'Burmese',
  'Catalan',
  'Chinese (Simplified)',
  'Chinese (Traditional)',
  'Czech',
  'Croatian',
  'Danish',
  'Dutch',
  'English',
  'Esperanto',
  'Estonian',
  'Filipino',
  'Finnish',
  'French',
  'German',
  'Greek',
  'Gujarati',
  'Hausa',
  'Hebrew',
  'Hindi',
  'Hungarian',
  'Icelandic',
  'Indonesian',
  'Italian',
  'Japanese',
  'Javanese',
  'Kannada',
  'Khmer',
  'Korean',
  'Latin',
  'Latvian',
  'Macedonian',
  'Malay',
  'Malayalam',
  'Marathi',
  'Nepali',
  'Norwegian',
  'Polish',
  'Portuguese',
  'Romanian',
  'Russian',
  'Sinhala',
  'Slovak',
  'Serbian',
  'Sundanese',
  'Swahili',
  'Swedish',
  'Tamil',
  'Telugu',
  'Thai',
  'Turkish',
  'Ukrainian',
  'Urdu',
  'Vietnamese',
  'Welsh',
  'Xhosa',
  'Yoruba',
  'Zulu',
  'Persian'
];
