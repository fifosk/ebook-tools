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
