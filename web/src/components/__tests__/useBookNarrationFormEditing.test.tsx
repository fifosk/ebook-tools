import { act, renderHook } from '@testing-library/react';
import { useRef, useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { DEFAULT_FORM_STATE } from '../book-narration/bookNarrationFormDefaults';
import type { FormState } from '../book-narration/bookNarrationFormTypes';
import { useBookNarrationFormEditing } from '../book-narration/useBookNarrationFormEditing';

function renderEditingHook(initialState: FormState = DEFAULT_FORM_STATE) {
  const setSharedEnableLookupCache = vi.fn();
  const setSharedInputLanguage = vi.fn();
  const setSharedTargetLanguages = vi.fn();

  const rendered = renderHook(() => {
    const [formState, setFormState] = useState<FormState>(initialState);
    const lastAutoEndSentenceRef = useRef<string | null>('24');
    const userEditedEndRef = useRef(false);
    const userEditedFieldsRef = useRef<Set<keyof FormState>>(new Set());
    const userEditedImageDefaultsRef = useRef<Set<keyof FormState>>(new Set());
    const userEditedInputRef = useRef(false);
    const userEditedStartRef = useRef(false);

    const editing = useBookNarrationFormEditing({
      formState,
      forcedBaseOutputFile: null,
      lastAutoEndSentenceRef,
      normalizedTargetLanguages: ['Arabic', 'English', 'German'],
      setFormState,
      setSharedEnableLookupCache,
      setSharedInputLanguage,
      setSharedTargetLanguages,
      sharedTargetLanguages: ['Arabic'],
      userEditedEndRef,
      userEditedFieldsRef,
      userEditedImageDefaultsRef,
      userEditedInputRef,
      userEditedStartRef,
    });

    return {
      ...editing,
      formState,
      lastAutoEndSentence: lastAutoEndSentenceRef.current,
      userEditedEnd: userEditedEndRef.current,
      userEditedFields: Array.from(userEditedFieldsRef.current).sort(),
      userEditedImageDefaults: Array.from(userEditedImageDefaultsRef.current).sort(),
      userEditedInput: userEditedInputRef.current,
      userEditedStart: userEditedStartRef.current,
    };
  });

  return {
    ...rendered,
    setSharedEnableLookupCache,
    setSharedInputLanguage,
    setSharedTargetLanguages,
  };
}

describe('useBookNarrationFormEditing', () => {
  it('applies field edits, marks refs, and syncs shared language preferences', () => {
    const { result, setSharedEnableLookupCache, setSharedInputLanguage, setSharedTargetLanguages } =
      renderEditingHook({
        ...DEFAULT_FORM_STATE,
        target_languages: ['Arabic'],
        custom_target_languages: '',
      });

    act(() => {
      result.current.handleChange('custom_target_languages', 'German, French');
      result.current.handleChange('input_language', 'Spanish');
      result.current.handleChange('enable_lookup_cache', false);
      result.current.handleChange('end_sentence', '42');
      result.current.handleChange('add_images', true);
    });

    expect(result.current.formState).toMatchObject({
      custom_target_languages: 'German, French',
      input_language: 'Spanish',
      enable_lookup_cache: false,
      end_sentence: '42',
      add_images: true,
    });
    expect(result.current.lastAutoEndSentence).toBeNull();
    expect(result.current.userEditedEnd).toBe(true);
    expect(result.current.userEditedFields).toEqual(expect.arrayContaining([
      'add_images',
      'custom_target_languages',
      'enable_lookup_cache',
      'end_sentence',
      'input_language',
      'target_languages',
    ]));
    expect(result.current.userEditedImageDefaults).toContain('add_images');
    expect(setSharedTargetLanguages).toHaveBeenCalledWith(['Arabic', 'German', 'French']);
    expect(setSharedInputLanguage).toHaveBeenCalledWith('Spanish');
    expect(setSharedEnableLookupCache).toHaveBeenCalledWith(false);
  });

  it('applies voice overrides and exposes deduped override languages', () => {
    const { result } = renderEditingHook({
      ...DEFAULT_FORM_STATE,
      input_language: ' English ',
      target_languages: ['Arabic'],
      custom_target_languages: 'German',
      voice_overrides: { ar: 'old-arabic-voice' },
    });

    expect(result.current.languagesForOverride).toEqual([
      { label: 'English', code: 'en' },
      { label: 'Arabic', code: 'ar' },
      { label: 'German', code: 'de' },
    ]);

    act(() => {
      result.current.updateVoiceOverride(' de ', '  Anna  ');
    });

    expect(result.current.formState.voice_overrides).toEqual({
      ar: 'old-arabic-voice',
      de: 'Anna',
    });
    expect(result.current.userEditedFields).toContain('voice_overrides');
  });
});
