import { renderHook, waitFor } from '@testing-library/react';
import { useRef, useState } from 'react';
import { describe, expect, it } from 'vitest';
import { DEFAULT_FORM_STATE } from '../book-narration/bookNarrationFormDefaults';
import type { FormState } from '../book-narration/bookNarrationFormTypes';
import { useBookNarrationSourceDefaults } from '../book-narration/useBookNarrationSourceDefaults';

type RenderSourceDefaultsOptions = {
  forcedBaseOutputFile?: string | null;
  initialState?: FormState;
  isGeneratedSource?: boolean;
};

function renderSourceDefaultsHook({
  forcedBaseOutputFile = null,
  initialState = DEFAULT_FORM_STATE,
  isGeneratedSource = false,
}: RenderSourceDefaultsOptions = {}) {
  return renderHook(({ nextForcedBaseOutputFile, nextIsGeneratedSource }) => {
    const [formState, setFormState] = useState<FormState>(initialState);
    const lastAutoEndSentenceRef = useRef<string | null>('48');
    const userEditedEndRef = useRef(true);
    const userEditedStartRef = useRef(true);

    useBookNarrationSourceDefaults({
      forcedBaseOutputFile: nextForcedBaseOutputFile,
      isGeneratedSource: nextIsGeneratedSource,
      lastAutoEndSentenceRef,
      setFormState,
      userEditedEndRef,
      userEditedStartRef,
    });

    return {
      formState,
      lastAutoEndSentence: lastAutoEndSentenceRef.current,
      userEditedEnd: userEditedEndRef.current,
      userEditedStart: userEditedStartRef.current,
    };
  }, {
    initialProps: {
      nextForcedBaseOutputFile: forcedBaseOutputFile,
      nextIsGeneratedSource: isGeneratedSource,
    },
  });
}

describe('useBookNarrationSourceDefaults', () => {
  it('resets generated-source sentence bounds and edit refs', async () => {
    const { result } = renderSourceDefaultsHook({
      isGeneratedSource: true,
      initialState: {
        ...DEFAULT_FORM_STATE,
        start_sentence: 120,
        end_sentence: '240',
      },
    });

    await waitFor(() => {
      expect(result.current.formState.start_sentence).toBe(1);
    });

    expect(result.current.formState.end_sentence).toBe('');
    expect(result.current.lastAutoEndSentence).toBeNull();
    expect(result.current.userEditedEnd).toBe(false);
    expect(result.current.userEditedStart).toBe(false);
  });

  it('keeps forced output name current across prop changes', async () => {
    const { result, rerender } = renderSourceDefaultsHook({
      forcedBaseOutputFile: 'first-output',
      initialState: {
        ...DEFAULT_FORM_STATE,
        base_output_file: 'draft-output',
      },
    });

    await waitFor(() => {
      expect(result.current.formState.base_output_file).toBe('first-output');
    });

    rerender({
      nextForcedBaseOutputFile: 'second-output',
      nextIsGeneratedSource: false,
    });

    await waitFor(() => {
      expect(result.current.formState.base_output_file).toBe('second-output');
    });
    expect(result.current.formState.start_sentence).toBe(DEFAULT_FORM_STATE.start_sentence);
    expect(result.current.formState.end_sentence).toBe(DEFAULT_FORM_STATE.end_sentence);
  });
});
