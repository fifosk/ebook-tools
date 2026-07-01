import { useEffect } from 'react';
import type { Dispatch, MutableRefObject, SetStateAction } from 'react';
import type { FormState } from './bookNarrationFormTypes';
import {
  applyBookNarrationForcedBaseOutput,
  applyBookNarrationGeneratedSourceDefaults,
} from './bookNarrationFormUtils';

type UseBookNarrationSourceDefaultsArgs = {
  forcedBaseOutputFile: string | null;
  isGeneratedSource: boolean;
  lastAutoEndSentenceRef: MutableRefObject<string | null>;
  setFormState: Dispatch<SetStateAction<FormState>>;
  userEditedEndRef: MutableRefObject<boolean>;
  userEditedStartRef: MutableRefObject<boolean>;
};

export function useBookNarrationSourceDefaults({
  forcedBaseOutputFile,
  isGeneratedSource,
  lastAutoEndSentenceRef,
  setFormState,
  userEditedEndRef,
  userEditedStartRef,
}: UseBookNarrationSourceDefaultsArgs) {
  useEffect(() => {
    if (!isGeneratedSource) {
      return;
    }
    userEditedStartRef.current = false;
    userEditedEndRef.current = false;
    lastAutoEndSentenceRef.current = null;
    setFormState((previous) => applyBookNarrationGeneratedSourceDefaults(previous));
  }, [
    isGeneratedSource,
    lastAutoEndSentenceRef,
    setFormState,
    userEditedEndRef,
    userEditedStartRef,
  ]);

  useEffect(() => {
    setFormState((previous) => applyBookNarrationForcedBaseOutput(previous, forcedBaseOutputFile));
  }, [forcedBaseOutputFile, setFormState]);
}
