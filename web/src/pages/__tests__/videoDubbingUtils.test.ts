import { describe, expect, it } from 'vitest';
import type { VoiceInventoryResponse, YoutubeInlineSubtitleStream } from '../../api/dtos';
import {
  buildVoiceOptions,
  resolveDefaultStreamLanguages
} from '../video-dubbing/videoDubbingUtils';

function stream(
  language: string | null,
  canExtract = true
): YoutubeInlineSubtitleStream {
  return {
    index: 0,
    position: 0,
    language,
    can_extract: canExtract
  };
}

describe('videoDubbingUtils', () => {
  it('prefers English extractable subtitle streams for inline extraction defaults', () => {
    const defaults = resolveDefaultStreamLanguages([
      stream('de'),
      stream('en-US'),
      stream('en-GB', false)
    ]);

    expect(Array.from(defaults)).toEqual(['en-US']);
  });

  it('selects a single non-English extractable stream when it is the only option', () => {
    const defaults = resolveDefaultStreamLanguages([
      stream('es'),
      stream('en', false)
    ]);

    expect(Array.from(defaults)).toEqual(['es']);
  });

  it('leaves stream selection empty when multiple non-English choices are available', () => {
    const defaults = resolveDefaultStreamLanguages([
      stream('es'),
      stream('fr')
    ]);

    expect(Array.from(defaults)).toEqual([]);
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
});
