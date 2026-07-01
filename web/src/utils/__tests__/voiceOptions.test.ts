import { describe, expect, it } from 'vitest';
import type { VoiceInventoryResponse } from '../../api/dtos';
import {
  buildVoiceOptionsFromInventory,
  formatMacOSVoiceIdentifier,
  formatMacOSVoiceLabel,
  voiceMatchesLanguage
} from '../voiceOptions';

const inventory: VoiceInventoryResponse = {
  macos: [
    { name: 'Monica', lang: 'es-MX', quality: 'Enhanced', gender: 'female' },
    { name: 'Daniel', lang: 'en-GB', quality: 'Enhanced', gender: 'male' }
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

describe('voiceOptions', () => {
  it('matches exact and base language codes across dash and underscore locales', () => {
    expect(voiceMatchesLanguage('es_ES', 'es-MX')).toBe(true);
    expect(voiceMatchesLanguage('es-MX', 'es-MX')).toBe(true);
    expect(voiceMatchesLanguage('en_US', 'es-MX')).toBe(false);
  });

  it('formats macOS voices with optional gender capitalization', () => {
    const voice = inventory.macos[0];

    expect(formatMacOSVoiceIdentifier(voice)).toBe('Monica - es-MX - (Enhanced) - female');
    expect(formatMacOSVoiceLabel(voice)).toBe('Monica (es-MX, female, Enhanced)');
    expect(formatMacOSVoiceIdentifier(voice, { capitalizeGender: true })).toBe(
      'Monica - es-MX - (Enhanced) - Female'
    );
    expect(formatMacOSVoiceLabel(voice, { capitalizeGender: true })).toBe(
      'Monica (es-MX, Female, Enhanced)'
    );
  });

  it('builds compact sorted voice options for video dubbing', () => {
    const options = buildVoiceOptionsFromInventory({
      voiceInventory: inventory,
      targetLanguageCode: 'es-MX',
      baseOptions: [{ value: 'gTTS', label: 'gTTS' }],
      sortByLabel: true
    });

    expect(options).toContainEqual({ value: 'gTTS-es', label: 'gTTS (Spanish)' });
    expect(options).toContainEqual({
      value: 'Monica - es-MX - (Enhanced) - female',
      label: 'Monica (es-MX, female, Enhanced)'
    });
    expect(options).toContainEqual({ value: 'es_ES-sharvard', label: 'Piper: es_ES-sharvard' });
    expect(options.some((option) => option.value === 'gTTS-en')).toBe(false);
  });

  it('builds described first-merge options for narrate ebook', () => {
    const options = buildVoiceOptionsFromInventory({
      voiceInventory: inventory,
      targetLanguageCode: 'es',
      baseOptions: [{ value: 'gTTS', label: 'gTTS', description: 'Default gTTS' }],
      capitalizeMacOSGender: true,
      mergeStrategy: 'first',
      describeGTTS: () => 'gTTS voice',
      describeMacOS: () => 'macOS system voice',
      describePiper: (voice) => `Piper TTS (${voice.quality})`
    });

    expect(options).toContainEqual({ value: 'gTTS', label: 'gTTS', description: 'Default gTTS' });
    expect(options).toContainEqual({ value: 'gTTS-es', label: 'gTTS (Spanish)', description: 'gTTS voice' });
    expect(options).toContainEqual({
      value: 'Monica - es-MX - (Enhanced) - Female',
      label: 'Monica (es-MX, Female, Enhanced)',
      description: 'macOS system voice'
    });
    expect(options).toContainEqual({
      value: 'es_ES-sharvard',
      label: 'Piper: es_ES-sharvard',
      description: 'Piper TTS (high)'
    });
  });
});
