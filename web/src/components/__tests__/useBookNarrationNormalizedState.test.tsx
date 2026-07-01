import { renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { DEFAULT_FORM_STATE } from '../book-narration/bookNarrationFormDefaults';
import { useBookNarrationNormalizedState } from '../book-narration/useBookNarrationNormalizedState';

describe('useBookNarrationNormalizedState', () => {
  it('normalizes existing EPUB inputs and merged target languages', () => {
    const normalizePath = vi.fn((value: string | null | undefined) =>
      value?.trim().toLowerCase() || null
    );

    const { result } = renderHook(() => useBookNarrationNormalizedState({
      formState: {
        ...DEFAULT_FORM_STATE,
        input_file: ' /Volumes/Books/Current.EPUB ',
        target_languages: ['Dutch', ' Italian '],
        custom_target_languages: 'italian, German',
      },
      isGeneratedSource: false,
      normalizePath,
    }));

    expect(result.current.normalizedInputForBookMetadataCache).toBe('/volumes/books/current.epub');
    expect(result.current.normalizedTargetLanguages).toEqual(['Dutch', 'Italian', 'German']);
    expect(normalizePath).toHaveBeenCalledWith(' /Volumes/Books/Current.EPUB ');
  });

  it('skips metadata-cache input paths for generated sources', () => {
    const normalizePath = vi.fn((value: string | null | undefined) =>
      value?.trim().toLowerCase() || null
    );

    const { result } = renderHook(() => useBookNarrationNormalizedState({
      formState: {
        ...DEFAULT_FORM_STATE,
        input_file: ' /Volumes/Books/Generated.EPUB ',
        target_languages: ['Dutch'],
        custom_target_languages: '',
      },
      isGeneratedSource: true,
      normalizePath,
    }));

    expect(result.current.normalizedInputForBookMetadataCache).toBeNull();
    expect(result.current.normalizedTargetLanguages).toEqual(['Dutch']);
    expect(normalizePath).not.toHaveBeenCalled();
  });

  it('uses the latest form state after rerender', () => {
    const normalizePath = (value: string | null | undefined) =>
      value?.trim().toLowerCase() || null;

    const { result, rerender } = renderHook(
      ({ inputFile, targetLanguages, customTargets }) => useBookNarrationNormalizedState({
        formState: {
          ...DEFAULT_FORM_STATE,
          input_file: inputFile,
          target_languages: targetLanguages,
          custom_target_languages: customTargets,
        },
        isGeneratedSource: false,
        normalizePath,
      }),
      {
        initialProps: {
          inputFile: '/Books/First.epub',
          targetLanguages: ['Dutch'],
          customTargets: '',
        },
      },
    );

    expect(result.current.normalizedInputForBookMetadataCache).toBe('/books/first.epub');
    expect(result.current.normalizedTargetLanguages).toEqual(['Dutch']);

    rerender({
      inputFile: '/Books/Second.epub',
      targetLanguages: ['Italian'],
      customTargets: 'German',
    });

    expect(result.current.normalizedInputForBookMetadataCache).toBe('/books/second.epub');
    expect(result.current.normalizedTargetLanguages).toEqual(['Italian', 'German']);
  });
});
