import { renderHook } from '@testing-library/react';
import type { FormEvent } from 'react';
import { describe, expect, it, vi } from 'vitest';
import {
  BOOK_NARRATION_SECTION_META,
  DEFAULT_FORM_STATE,
} from '../book-narration/bookNarrationFormDefaults';
import { useBookNarrationSubmitFlow } from '../book-narration/useBookNarrationSubmitFlow';

function submitEvent(): FormEvent<HTMLFormElement> {
  return {
    preventDefault: vi.fn(),
  } as unknown as FormEvent<HTMLFormElement>;
}

describe('useBookNarrationSubmitFlow', () => {
  it('submits valid narration payloads and refreshes intake after success', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const refreshIntakeStatus = vi.fn().mockResolvedValue(undefined);
    const setError = vi.fn();
    const formState = {
      ...DEFAULT_FORM_STATE,
      input_file: '/books/current.epub',
      base_output_file: 'current-output',
      target_languages: ['Dutch'],
    };

    const { result } = renderHook(() => useBookNarrationSubmitFlow({
      activeSection: 'submit',
      chapterSelection: null,
      chapterSelectionMode: 'range',
      forcedBaseOutputFile: null,
      formState,
      implicitEndOffsetThreshold: null,
      isGeneratedSource: false,
      isIntakeAtCapacity: false,
      isSubmitting: false,
      normalizedTargetLanguages: ['Dutch'],
      onSubmit,
      refreshIntakeStatus,
      sectionMeta: BOOK_NARRATION_SECTION_META,
      setError,
      submitLabel: 'Start narration',
    }));

    await result.current.handleSubmitAndRefreshIntake(submitEvent());

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(refreshIntakeStatus).toHaveBeenCalledTimes(1);
    expect(result.current.submitPresentation.submitText).toBe('Start narration');
    expect(result.current.submitPresentation.isSubmitDisabled).toBe(false);
  });

  it('does not refresh intake when validation prevents submit', async () => {
    const onSubmit = vi.fn();
    const refreshIntakeStatus = vi.fn();
    const setError = vi.fn();

    const { result } = renderHook(() => useBookNarrationSubmitFlow({
      activeSection: 'submit',
      chapterSelection: null,
      chapterSelectionMode: 'range',
      forcedBaseOutputFile: null,
      formState: {
        ...DEFAULT_FORM_STATE,
        input_file: '/books/current.epub',
        base_output_file: 'current-output',
        target_languages: [],
      },
      implicitEndOffsetThreshold: null,
      isGeneratedSource: false,
      isIntakeAtCapacity: false,
      isSubmitting: false,
      normalizedTargetLanguages: [],
      onSubmit,
      refreshIntakeStatus,
      sectionMeta: BOOK_NARRATION_SECTION_META,
      setError,
    }));

    await result.current.handleSubmitAndRefreshIntake(submitEvent());

    expect(onSubmit).not.toHaveBeenCalled();
    expect(refreshIntakeStatus).not.toHaveBeenCalled();
    expect(setError).toHaveBeenCalledWith('Please choose at least one target language.');
    expect(result.current.submitPresentation.isSubmitDisabled).toBe(true);
  });
});
