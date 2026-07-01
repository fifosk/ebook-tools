import { renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { DEFAULT_FORM_STATE } from '../book-narration/bookNarrationFormDefaults';
import { useBookNarrationWorkflowRefs } from '../book-narration/useBookNarrationWorkflowRefs';

describe('useBookNarrationWorkflowRefs', () => {
  it('preserves fields marked as user edited', () => {
    const { result } = renderHook(() => useBookNarrationWorkflowRefs());
    const previous = {
      ...DEFAULT_FORM_STATE,
      input_file: '/books/manual.epub',
      base_output_file: 'manual-output',
      target_languages: ['Dutch'],
    };
    const next = {
      ...previous,
      input_file: '/books/default.epub',
      base_output_file: 'default-output',
      target_languages: ['Italian'],
    };

    result.current.userEditedFieldsRef.current.add('input_file');
    result.current.userEditedFieldsRef.current.add('target_languages');

    expect(result.current.preserveUserEditedFields(previous, next)).toEqual({
      ...next,
      input_file: '/books/manual.epub',
      target_languages: ['Dutch'],
    });
  });

  it('keeps workflow refs and the preserve callback stable across rerenders', () => {
    const { result, rerender } = renderHook(() => useBookNarrationWorkflowRefs());
    const firstRefs = result.current;

    firstRefs.prefillAppliedRef.current = 'prefill-key';
    firstRefs.defaultsAppliedRef.current = true;
    firstRefs.lastAutoEndSentenceRef.current = '42';
    firstRefs.userEditedFieldsRef.current.add('base_output_file');

    rerender();

    expect(result.current.prefillAppliedRef).toBe(firstRefs.prefillAppliedRef);
    expect(result.current.creationTemplateAppliedRef).toBe(firstRefs.creationTemplateAppliedRef);
    expect(result.current.userEditedStartRef).toBe(firstRefs.userEditedStartRef);
    expect(result.current.userEditedInputRef).toBe(firstRefs.userEditedInputRef);
    expect(result.current.userEditedEndRef).toBe(firstRefs.userEditedEndRef);
    expect(result.current.userEditedFieldsRef).toBe(firstRefs.userEditedFieldsRef);
    expect(result.current.defaultsAppliedRef).toBe(firstRefs.defaultsAppliedRef);
    expect(result.current.lastAutoEndSentenceRef).toBe(firstRefs.lastAutoEndSentenceRef);
    expect(result.current.preserveUserEditedFields).toBe(firstRefs.preserveUserEditedFields);
    expect(result.current.prefillAppliedRef.current).toBe('prefill-key');
    expect(result.current.defaultsAppliedRef.current).toBe(true);
    expect(result.current.lastAutoEndSentenceRef.current).toBe('42');
    expect(result.current.userEditedFieldsRef.current.has('base_output_file')).toBe(true);
  });
});
