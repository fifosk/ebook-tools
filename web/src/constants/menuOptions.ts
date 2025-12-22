import assets from '../../../modules/shared/assets_data.json';

export interface MenuOption {
  value: string;
  label: string;
  description: string;
}

const audioModes = assets.audio_modes ?? [];
const writtenModes = assets.written_modes ?? [];
const voiceOptions = assets.voice_options ?? [];

export const AUDIO_MODE_OPTIONS: MenuOption[] = audioModes.map((option) => ({
  value: String(option.value),
  label: option.label,
  description: option.description
}));

export const AUDIO_QUALITY_OPTIONS: MenuOption[] = [
  {
    value: '320',
    label: 'Ultra (320 kbps)',
    description: 'Largest files, maximum MP3 bitrate target.'
  },
  {
    value: '192',
    label: 'High (192 kbps)',
    description: 'Clear speech with smaller files.'
  },
  {
    value: '160',
    label: 'High (160 kbps)',
    description: 'Speech-focused quality with reduced size.'
  },
  {
    value: '128',
    label: 'Standard (128 kbps)',
    description: 'Balanced quality for narration.'
  },
  {
    value: '96',
    label: 'Compact (96 kbps)',
    description: 'Smaller files with acceptable clarity.'
  },
  {
    value: '64',
    label: 'Tiny (64 kbps)',
    description: 'Smallest files, reduced fidelity.'
  }
];

export const WRITTEN_MODE_OPTIONS: MenuOption[] = writtenModes.map((option) => ({
  value: String(option.value),
  label: option.label,
  description: option.description
}));

export const VOICE_OPTIONS: MenuOption[] = voiceOptions.map((option) => ({
  value: String(option.value),
  label: option.label,
  description: option.description
}));

export const TOP_LANGUAGES: string[] = Array.isArray(assets.top_languages)
  ? [...assets.top_languages]
  : [];
