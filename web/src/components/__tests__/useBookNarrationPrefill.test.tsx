import { renderHook, waitFor } from '@testing-library/react';
import { useRef, useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { JobParameterSnapshot } from '../../api/dtos';
import { loadCachedMediaMetadataJson } from '../../utils/mediaMetadataCache';
import { DEFAULT_FORM_STATE } from '../book-narration/bookNarrationFormDefaults';
import type { FormState } from '../book-narration/bookNarrationFormTypes';
import { preserveBookNarrationUserEditedFields } from '../book-narration/bookNarrationFormUtils';
import { useBookNarrationPrefill } from '../book-narration/useBookNarrationPrefill';

vi.mock('../../utils/mediaMetadataCache', () => ({
  loadCachedMediaMetadataJson: vi.fn(),
}));

const mockLoadCachedMediaMetadataJson = vi.mocked(loadCachedMediaMetadataJson);

type RenderPrefillOptions = {
  editedFields?: (keyof FormState)[];
  forcedBaseOutputFile?: string | null;
  initialState?: FormState;
  prefillInputFile?: string | null;
  prefillParameters?: JobParameterSnapshot | null;
};

function renderPrefillHook({
  editedFields = [],
  forcedBaseOutputFile = null,
  initialState = DEFAULT_FORM_STATE,
  prefillInputFile,
  prefillParameters = null,
}: RenderPrefillOptions = {}) {
  const resolveStartFromHistory = vi.fn((inputPath: string) =>
    inputPath.includes('Current Book') ? 42 : null,
  );

  const rendered = renderHook(({ nextPrefillInputFile, nextPrefillParameters }) => {
    const [formState, setFormState] = useState<FormState>(initialState);
    const lastAutoEndSentenceRef = useRef<string | null>('999');
    const prefillAppliedRef = useRef<string | null>(null);
    const userEditedEndRef = useRef(true);
    const userEditedFieldsRef = useRef<Set<keyof FormState>>(new Set(editedFields));
    const userEditedInputRef = useRef(true);
    const userEditedStartRef = useRef(true);

    useBookNarrationPrefill({
      forcedBaseOutputFile,
      lastAutoEndSentenceRef,
      normalizePath: (value) => value?.trim().toLowerCase() ?? null,
      prefillAppliedRef,
      prefillInputFile: nextPrefillInputFile,
      prefillParameters: nextPrefillParameters,
      preserveUserEditedFields: (previous, next) =>
        preserveBookNarrationUserEditedFields(previous, next, userEditedFieldsRef.current),
      resolveStartFromHistory,
      setFormState,
      userEditedEndRef,
      userEditedInputRef,
      userEditedStartRef,
    });

    return {
      formState,
      lastAutoEndSentence: lastAutoEndSentenceRef.current,
      prefillApplied: prefillAppliedRef.current,
      userEditedEnd: userEditedEndRef.current,
      userEditedInput: userEditedInputRef.current,
      userEditedStart: userEditedStartRef.current,
    };
  }, {
    initialProps: {
      nextPrefillInputFile: prefillInputFile,
      nextPrefillParameters: prefillParameters,
    },
  });

  return {
    ...rendered,
    resolveStartFromHistory,
  };
}

describe('useBookNarrationPrefill', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('applies input-file prefill with cached metadata and history start', async () => {
    mockLoadCachedMediaMetadataJson.mockReturnValue('{"title":"Cached Current"}');
    const { result, rerender, resolveStartFromHistory } = renderPrefillHook({
      prefillInputFile: ' /NAS/books/Current Book.epub ',
    });

    await waitFor(() => {
      expect(result.current.formState.input_file).toBe('/NAS/books/Current Book.epub');
    });

    expect(result.current.formState).toMatchObject({
      base_output_file: 'current-book',
      book_metadata: '{"title":"Cached Current"}',
      start_sentence: 42,
    });
    expect(result.current.lastAutoEndSentence).toBeNull();
    expect(result.current.prefillApplied).toBe('/NAS/books/Current Book.epub');
    expect(result.current.userEditedEnd).toBe(false);
    expect(result.current.userEditedInput).toBe(false);
    expect(result.current.userEditedStart).toBe(false);
    expect(mockLoadCachedMediaMetadataJson).toHaveBeenCalledWith('/nas/books/current book.epub');
    expect(resolveStartFromHistory).toHaveBeenCalledWith('/NAS/books/Current Book.epub');

    rerender({
      nextPrefillInputFile: ' /NAS/books/Current Book.epub ',
      nextPrefillParameters: null,
    });

    expect(mockLoadCachedMediaMetadataJson).toHaveBeenCalledTimes(1);
  });

  it('applies parameter prefill while preserving user-edited fields', async () => {
    const { result } = renderPrefillHook({
      editedFields: ['input_language'],
      initialState: {
        ...DEFAULT_FORM_STATE,
        input_language: 'English',
        target_languages: ['Spanish'],
      },
      prefillParameters: {
        input_language: 'Turkish',
        target_languages: ['Dutch', 'Italian'],
        start_sentence: 18,
        end_sentence: 24,
        base_output_file: 'prefilled-output',
      },
    });

    await waitFor(() => {
      expect(result.current.formState.base_output_file).toBe('prefilled-output');
    });

    expect(result.current.formState).toMatchObject({
      input_language: 'English',
      target_languages: ['Dutch'],
      custom_target_languages: 'Italian',
      start_sentence: 18,
      end_sentence: '24',
    });
  });
});
