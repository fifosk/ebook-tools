import type { MacOSVoice, VoiceInventoryResponse } from '../../api/dtos';
import { VOICE_OPTIONS } from '../../constants/menuOptions';

export type VoiceOption = {
  value: string;
  label: string;
  description?: string;
};

export function capitalize(value: string): string {
  if (!value) {
    return value;
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function formatMacOSVoiceIdentifier(voice: MacOSVoice): string {
  const quality = voice.quality ? voice.quality : 'Default';
  const genderSuffix = voice.gender ? ` - ${capitalize(voice.gender)}` : '';
  return `${voice.name} - ${voice.lang} - (${quality})${genderSuffix}`;
}

export function formatMacOSVoiceLabel(voice: MacOSVoice): string {
  const segments: string[] = [voice.lang];
  if (voice.gender) {
    segments.push(capitalize(voice.gender));
  }
  if (voice.quality) {
    segments.push(voice.quality);
  }
  const meta = segments.length > 0 ? ` (${segments.join(', ')})` : '';
  return `${voice.name}${meta}`;
}

export function buildVoiceOptionsForLanguage(
  voiceInventory: VoiceInventoryResponse | null,
  languageCode: string | null,
): VoiceOption[] {
  const baseOptions: VoiceOption[] = VOICE_OPTIONS.map((option) => ({
    value: option.value,
    label: option.label,
    description: option.description,
  }));

  if (!voiceInventory || !languageCode) {
    return baseOptions;
  }

  const extras: VoiceOption[] = [];
  const normalizedCode = languageCode.toLowerCase();

  const gttsMatches = voiceInventory.gtts.filter((entry) => {
    const entryCode = entry.code.toLowerCase();
    if (entryCode === normalizedCode) {
      return true;
    }
    return entryCode.startsWith(`${normalizedCode}-`) || entryCode.startsWith(`${normalizedCode}_`);
  });
  const seenGtts = new Set<string>();
  for (const entry of gttsMatches) {
    const shortCode = entry.code.split(/[-_]/)[0].toLowerCase();
    if (!shortCode || seenGtts.has(shortCode)) {
      continue;
    }
    seenGtts.add(shortCode);
    const identifier = `gTTS-${shortCode}`;
    extras.push({ value: identifier, label: `gTTS (${entry.name})`, description: 'gTTS voice' });
  }

  const macVoices = voiceInventory.macos.filter((voice) => {
    const voiceLang = voice.lang.toLowerCase();
    return (
      voiceLang === normalizedCode ||
      voiceLang.startsWith(`${normalizedCode}-`) ||
      voiceLang.startsWith(`${normalizedCode}_`)
    );
  });
  macVoices
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .forEach((voice) => {
      extras.push({
        value: formatMacOSVoiceIdentifier(voice),
        label: formatMacOSVoiceLabel(voice),
        description: 'macOS system voice',
      });
    });

  const merged = new Map<string, VoiceOption>();
  for (const option of [...baseOptions, ...extras]) {
    if (!option.value) {
      continue;
    }
    if (!merged.has(option.value)) {
      merged.set(option.value, option);
    }
  }
  return Array.from(merged.values());
}
