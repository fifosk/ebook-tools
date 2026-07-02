import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it } from 'vitest';
import type { JobParameterSnapshot } from '../../api/dtos';
import { LanguageProvider } from '../../context/LanguageProvider';
import { useBookNarrationBaseState } from '../book-narration/useBookNarrationBaseState';

const STORAGE_KEY = 'ebookTools.bookJobDefaults.v1';

function wrapper({ children }: { children: ReactNode }) {
  return <LanguageProvider>{children}</LanguageProvider>;
}

describe('useBookNarrationBaseState', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('initializes form state from shared language defaults and props', () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        inputLanguage: 'Spanish',
        targetLanguages: ['Dutch', 'Italian', 'Dutch'],
        enableLookupCache: false,
      }),
    );
    const imageSettings = {
      add_images: true,
      image_style_template: 'watercolor',
      image_prompt_context_sentences: 3,
      image_width: '1024',
      image_height: '768',
    };
    const prefillParameters = { add_images: true } as JobParameterSnapshot;

    const { result } = renderHook(
      () => useBookNarrationBaseState({
        defaultImageSettings: imageSettings,
        forcedBaseOutputFile: '/tmp/output/demo',
        prefillParameters,
        sourceMode: 'generated',
      }),
      { wrapper },
    );

    expect(result.current.isGeneratedSource).toBe(true);
    expect(result.current.imageDefaults).toBe(imageSettings);
    expect(result.current.hasPrefillAddImages).toBe(true);
    expect(result.current.formState).toMatchObject({
      base_output_file: '/tmp/output/demo',
      input_language: 'Spanish',
      target_languages: ['Dutch'],
      custom_target_languages: 'Italian',
      enable_lookup_cache: false,
    });
    expect(result.current.sharedInputLanguage).toBe('Spanish');
    expect(result.current.sharedTargetLanguages).toEqual(['Dutch', 'Italian']);
  });

  it('exposes mutable form state while defaulting optional props', () => {
    const { result } = renderHook(
      () => useBookNarrationBaseState({
        defaultImageSettings: null,
        forcedBaseOutputFile: null,
        prefillParameters: null,
        sourceMode: 'upload',
      }),
      { wrapper },
    );

    expect(result.current.isGeneratedSource).toBe(false);
    expect(result.current.imageDefaults).toBeNull();
    expect(result.current.hasPrefillAddImages).toBe(false);
    expect(result.current.formState.base_output_file).toBe('');

    act(() => {
      result.current.setFormState((previous) => ({
        ...previous,
        input_file: 'example.epub',
      }));
    });

    expect(result.current.formState.input_file).toBe('example.epub');
  });
});
