import { describe, expect, it } from 'vitest';
import type { VoiceInventoryResponse } from '../../api/dtos';
import {
  buildVoiceOptions,
  formatMacOSVoiceIdentifier,
  formatMacOSVoiceLabel
} from '../video-dubbing/videoDubbingVoiceOptions';

describe('videoDubbingVoiceOptions', () => {
  it('formats macOS voice ids and labels for preview payloads', () => {
    const voice = { name: 'Monica', lang: 'es-MX', quality: 'Enhanced', gender: 'Female' };

    expect(formatMacOSVoiceIdentifier(voice)).toBe('Monica - es-MX - (Enhanced) - Female');
    expect(formatMacOSVoiceLabel(voice)).toBe('Monica (es-MX, Female, Enhanced)');
  });

  it('builds target-matched voice options from backend inventory', () => {
    const inventory: VoiceInventoryResponse = {
      macos: [
        { name: 'Monica', lang: 'es-MX', quality: 'Enhanced', gender: 'Female' },
        { name: 'Daniel', lang: 'en-GB', quality: 'Enhanced', gender: 'Male' }
      ],
      piper: [
        { name: 'en_US-lessac', lang: 'en_US', quality: 'medium' },
        { name: 'es_ES-sharvard', lang: 'es_ES', quality: 'high' }
      ],
      gtts: [
        { code: 'es', name: 'Spanish' },
        { code: 'es-US', name: 'Spanish (US)' },
        { code: 'en', name: 'English' }
      ]
    };

    const options = buildVoiceOptions(inventory, 'es-MX');

    expect(options).toContainEqual({
      value: 'Monica - es-MX - (Enhanced) - Female',
      label: 'Monica (es-MX, Female, Enhanced)'
    });
    expect(options).toContainEqual({ value: 'es_ES-sharvard', label: 'Piper: es_ES-sharvard' });
    expect(options).toContainEqual({ value: 'gTTS-es', label: 'gTTS (Spanish)' });
    expect(options).not.toContainEqual({ value: 'en_US-lessac', label: 'Piper: en_US-lessac' });
    expect(options.some((option) => option.value === 'gTTS-en')).toBe(false);
  });

  it('returns bundled voice options when the backend inventory is unavailable', () => {
    const values = buildVoiceOptions(null, 'nl-NL').map((option) => option.value);

    expect(values).toContain('gTTS');
    expect(values).toContain('piper-auto');
  });
});
