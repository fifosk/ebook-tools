import type { VoiceInventoryResponse } from '../../api/dtos';
import { VOICE_OPTIONS } from '../../constants/menuOptions';
import {
  buildVoiceOptionsFromInventory,
  formatMacOSVoiceIdentifier,
  formatMacOSVoiceLabel
} from '../../utils/voiceOptions';

export type VideoDubbingVoiceOption = {
  value: string;
  label: string;
};

export { formatMacOSVoiceIdentifier, formatMacOSVoiceLabel };

export function buildVoiceOptions(
  voiceInventory: VoiceInventoryResponse | null,
  targetLanguageCode: string
): VideoDubbingVoiceOption[] {
  const base = VOICE_OPTIONS.map((option) => ({
    value: option.value,
    label: option.label
  }));
  return buildVoiceOptionsFromInventory({
    voiceInventory,
    targetLanguageCode,
    baseOptions: base,
    sortByLabel: true,
    mergeStrategy: 'last',
  });
}
