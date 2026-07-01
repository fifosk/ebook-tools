import type { MacOSVoice, VoiceInventoryResponse } from '../../api/dtos';
import { VOICE_OPTIONS } from '../../constants/menuOptions';

export type VideoDubbingVoiceOption = {
  value: string;
  label: string;
};

export function formatMacOSVoiceIdentifier(voice: MacOSVoice): string {
  const quality = voice.quality ? voice.quality : 'Default';
  const genderSuffix = voice.gender ? ` - ${voice.gender}` : '';
  return `${voice.name} - ${voice.lang} - (${quality})${genderSuffix}`;
}

export function formatMacOSVoiceLabel(voice: MacOSVoice): string {
  const descriptors: string[] = [voice.lang];
  if (voice.gender) {
    descriptors.push(voice.gender);
  }
  if (voice.quality) {
    descriptors.push(voice.quality);
  }
  const meta = descriptors.length > 0 ? ` (${descriptors.join(', ')})` : '';
  return `${voice.name}${meta}`;
}

function voiceMatchesLanguage(lang: string, targetLanguageCode: string): boolean {
  const targetCode = (targetLanguageCode || '').toLowerCase();
  if (!targetCode) {
    return true;
  }
  const normalized = (lang || '').toLowerCase();
  if (!normalized) {
    return false;
  }
  if (normalized === targetCode) {
    return true;
  }
  const targetBase = targetCode.split(/[-_]/)[0];
  return normalized.split(/[-_]/)[0] === targetBase;
}

export function buildVoiceOptions(
  voiceInventory: VoiceInventoryResponse | null,
  targetLanguageCode: string
): VideoDubbingVoiceOption[] {
  const base = VOICE_OPTIONS.map((option) => ({
    value: option.value,
    label: option.label
  }));
  if (!voiceInventory) {
    return base;
  }

  const macVoices = voiceInventory.macos
    .filter((voice) => voiceMatchesLanguage(voice.lang, targetLanguageCode))
    .map((voice) => ({
      value: formatMacOSVoiceIdentifier(voice),
      label: formatMacOSVoiceLabel(voice)
    }));

  const piperVoices = (voiceInventory.piper ?? [])
    .filter((voice) => voiceMatchesLanguage(voice.lang, targetLanguageCode))
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((voice) => ({
      value: voice.name,
      label: `Piper: ${voice.name}`
    }));

  const gttsSeen = new Set<string>();
  const gttsVoices: VideoDubbingVoiceOption[] = [];
  for (const entry of voiceInventory.gtts) {
    const entryCode = entry.code.toLowerCase();
    if (!voiceMatchesLanguage(entryCode, targetLanguageCode)) {
      continue;
    }
    const shortCode = entryCode.split(/[-_]/)[0];
    if (!shortCode || gttsSeen.has(shortCode)) {
      continue;
    }
    gttsSeen.add(shortCode);
    gttsVoices.push({ value: `gTTS-${shortCode}`, label: `gTTS (${entry.name})` });
  }

  const merged = new Map<string, VideoDubbingVoiceOption>();
  [...base, ...macVoices, ...piperVoices, ...gttsVoices].forEach((entry) => {
    merged.set(entry.value, entry);
  });
  return Array.from(merged.values()).sort((a, b) => a.label.localeCompare(b.label));
}
