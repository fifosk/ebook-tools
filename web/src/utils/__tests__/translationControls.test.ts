import { describe, expect, it } from 'vitest';
import {
  TRANSLITERATION_MODE_OPTIONS,
  buildLlmModelOptions,
  buildTransliterationModelOptions,
  getTransliterationModeOption,
  normalizeTranslationProvider,
  normalizeTransliterationMode
} from '../translationControls';

describe('translation control helpers', () => {
  it('normalizes translation provider aliases shared by creation surfaces', () => {
    expect(normalizeTranslationProvider('')).toBe('llm');
    expect(normalizeTranslationProvider(' default ')).toBe('llm');
    expect(normalizeTranslationProvider('Ollama')).toBe('llm');
    expect(normalizeTranslationProvider('google-translate')).toBe('googletrans');
    expect(normalizeTranslationProvider('GTRANS')).toBe('googletrans');
    expect(normalizeTranslationProvider('lmstudio_local')).toBe('lmstudio_local');
  });

  it('coerces transliteration modes to supported UI options', () => {
    expect(normalizeTransliterationMode('python')).toBe('python');
    expect(normalizeTransliterationMode('python_module')).toBe('python');
    expect(normalizeTransliterationMode('local-module')).toBe('python');
    expect(normalizeTransliterationMode('ollama')).toBe('default');
    expect(normalizeTransliterationMode('surprise')).toBe('default');
  });

  it('returns the shared transliteration option metadata for normalized values', () => {
    expect(getTransliterationModeOption('python')).toMatchObject({
      value: 'python',
      label: 'Python transliteration module'
    });
    expect(getTransliterationModeOption('unknown')).toBe(TRANSLITERATION_MODE_OPTIONS[0]);
  });

  it('builds deduplicated LLM model options with selected model first', () => {
    expect(buildLlmModelOptions('qwen:latest', ['llama:latest', 'qwen:latest'])).toEqual([
      'qwen:latest',
      'llama:latest'
    ]);
    expect(buildLlmModelOptions('', [], ['default-model'])).toEqual(['default-model']);
    expect(buildLlmModelOptions('  ', [], [])).toEqual([]);
  });

  it('builds transliteration model options without losing a custom selection', () => {
    expect(
      buildTransliterationModelOptions('custom-translit', ['llama:latest', 'custom-translit'])
    ).toEqual(['custom-translit', 'llama:latest']);
    expect(buildTransliterationModelOptions('', ['llama:latest'])).toEqual(['llama:latest']);
  });
});
