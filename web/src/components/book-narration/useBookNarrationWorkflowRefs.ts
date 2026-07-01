import { useCallback, useRef } from 'react';
import type { FormState } from './bookNarrationFormTypes';
import { preserveBookNarrationUserEditedFields } from './bookNarrationFormUtils';

export function useBookNarrationWorkflowRefs() {
  const prefillAppliedRef = useRef<string | null>(null);
  const creationTemplateAppliedRef = useRef<string | null>(null);
  const userEditedStartRef = useRef<boolean>(false);
  const userEditedInputRef = useRef<boolean>(false);
  const userEditedEndRef = useRef<boolean>(false);
  const userEditedFieldsRef = useRef<Set<keyof FormState>>(new Set<keyof FormState>());
  const defaultsAppliedRef = useRef<boolean>(false);
  const lastAutoEndSentenceRef = useRef<string | null>(null);

  const preserveUserEditedFields = useCallback((previous: FormState, next: FormState): FormState => {
    return preserveBookNarrationUserEditedFields(previous, next, userEditedFieldsRef.current);
  }, []);

  return {
    creationTemplateAppliedRef,
    defaultsAppliedRef,
    lastAutoEndSentenceRef,
    prefillAppliedRef,
    preserveUserEditedFields,
    userEditedEndRef,
    userEditedFieldsRef,
    userEditedInputRef,
    userEditedStartRef,
  };
}
