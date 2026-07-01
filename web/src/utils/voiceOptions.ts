import type { MacOSVoice, VoiceInventoryResponse } from '../api/dtos';

export type VoiceOption = {
  value: string;
  label: string;
  description?: string;
};

export type VoiceOptionBuildOptions<TOption extends VoiceOption> = {
  voiceInventory: VoiceInventoryResponse | null;
  targetLanguageCode: string;
  baseOptions: TOption[];
  capitalizeMacOSGender?: boolean;
  sortByLabel?: boolean;
  mergeStrategy?: 'first' | 'last';
  describeGTTS?: (entry: VoiceInventoryResponse['gtts'][number]) => string | undefined;
  describeMacOS?: (voice: MacOSVoice) => string | undefined;
  describePiper?: (voice: NonNullable<VoiceInventoryResponse['piper']>[number]) => string | undefined;
};

function capitalize(value: string): string {
  if (!value) {
    return value;
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatGender(value: string | null | undefined, capitalizeGender: boolean): string | undefined {
  if (!value) {
    return undefined;
  }
  return capitalizeGender ? capitalize(value) : value;
}

export function formatMacOSVoiceIdentifier(
  voice: MacOSVoice,
  options: { capitalizeGender?: boolean } = {}
): string {
  const quality = voice.quality ? voice.quality : 'Default';
  const gender = formatGender(voice.gender, options.capitalizeGender ?? false);
  const genderSuffix = gender ? ` - ${gender}` : '';
  return `${voice.name} - ${voice.lang} - (${quality})${genderSuffix}`;
}

export function formatMacOSVoiceLabel(
  voice: MacOSVoice,
  options: { capitalizeGender?: boolean } = {}
): string {
  const descriptors: string[] = [voice.lang];
  const gender = formatGender(voice.gender, options.capitalizeGender ?? false);
  if (gender) {
    descriptors.push(gender);
  }
  if (voice.quality) {
    descriptors.push(voice.quality);
  }
  const meta = descriptors.length > 0 ? ` (${descriptors.join(', ')})` : '';
  return `${voice.name}${meta}`;
}

export function voiceMatchesLanguage(lang: string, targetLanguageCode: string): boolean {
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

function optionWithDescription(value: string, label: string, description?: string): VoiceOption {
  const option: VoiceOption = { value, label };
  if (description) {
    option.description = description;
  }
  return option;
}

export function buildVoiceOptionsFromInventory<TOption extends VoiceOption>({
  voiceInventory,
  targetLanguageCode,
  baseOptions,
  capitalizeMacOSGender = false,
  sortByLabel = false,
  mergeStrategy = 'last',
  describeGTTS,
  describeMacOS,
  describePiper,
}: VoiceOptionBuildOptions<TOption>): VoiceOption[] {
  if (!voiceInventory) {
    return baseOptions;
  }

  const gttsSeen = new Set<string>();
  const gttsVoices: VoiceOption[] = [];
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
    gttsVoices.push(optionWithDescription(
      `gTTS-${shortCode}`,
      `gTTS (${entry.name})`,
      describeGTTS?.(entry)
    ));
  }

  const macVoices = voiceInventory.macos
    .filter((voice) => voiceMatchesLanguage(voice.lang, targetLanguageCode))
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((voice) => optionWithDescription(
      formatMacOSVoiceIdentifier(voice, { capitalizeGender: capitalizeMacOSGender }),
      formatMacOSVoiceLabel(voice, { capitalizeGender: capitalizeMacOSGender }),
      describeMacOS?.(voice)
    ));

  const piperVoices = (voiceInventory.piper ?? [])
    .filter((voice) => voiceMatchesLanguage(voice.lang, targetLanguageCode))
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((voice) => optionWithDescription(
      voice.name,
      `Piper: ${voice.name}`,
      describePiper?.(voice)
    ));

  const merged = new Map<string, VoiceOption>();
  for (const option of [...baseOptions, ...gttsVoices, ...macVoices, ...piperVoices]) {
    if (!option.value) {
      continue;
    }
    if (mergeStrategy === 'first' && merged.has(option.value)) {
      continue;
    }
    merged.set(option.value, option);
  }

  const options = Array.from(merged.values());
  return sortByLabel ? options.sort((a, b) => a.label.localeCompare(b.label)) : options;
}
