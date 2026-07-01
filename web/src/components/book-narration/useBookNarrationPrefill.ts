import { useEffect, useRef } from 'react';
import type { Dispatch, MutableRefObject, SetStateAction } from 'react';
import type { JobParameterSnapshot } from '../../api/dtos';
import { loadCachedMediaMetadataJson } from '../../utils/mediaMetadataCache';
import type { FormState } from './bookNarrationFormTypes';
import {
  applyBookNarrationPrefillInputFile,
  applyBookNarrationPrefillParameters,
} from './bookNarrationFormUtils';

type UseBookNarrationPrefillArgs = {
  forcedBaseOutputFile: string | null;
  lastAutoEndSentenceRef: MutableRefObject<string | null>;
  normalizePath: (value: string | null | undefined) => string | null;
  prefillAppliedRef: MutableRefObject<string | null>;
  prefillInputFile: string | null | undefined;
  prefillParameters: JobParameterSnapshot | null | undefined;
  preserveUserEditedFields: (previous: FormState, next: FormState) => FormState;
  resolveStartFromHistory: (inputPath: string) => number | null;
  setFormState: Dispatch<SetStateAction<FormState>>;
  userEditedEndRef: MutableRefObject<boolean>;
  userEditedInputRef: MutableRefObject<boolean>;
  userEditedStartRef: MutableRefObject<boolean>;
};

export function useBookNarrationPrefill({
  forcedBaseOutputFile,
  lastAutoEndSentenceRef,
  normalizePath,
  prefillAppliedRef,
  prefillInputFile,
  prefillParameters,
  preserveUserEditedFields,
  resolveStartFromHistory,
  setFormState,
  userEditedEndRef,
  userEditedInputRef,
  userEditedStartRef,
}: UseBookNarrationPrefillArgs) {
  const prefillParametersRef = useRef<string | null>(null);

  useEffect(() => {
    if (prefillInputFile === undefined) {
      return;
    }
    const normalizedPrefill = prefillInputFile && prefillInputFile.trim();
    if (!normalizedPrefill) {
      prefillAppliedRef.current = null;
      return;
    }
    if (prefillAppliedRef.current === normalizedPrefill) {
      return;
    }
    userEditedStartRef.current = false;
    userEditedInputRef.current = false;
    userEditedEndRef.current = false;
    lastAutoEndSentenceRef.current = null;
    const normalizedInput = normalizePath(normalizedPrefill);
    const cachedBookMetadata = normalizedInput ? loadCachedMediaMetadataJson(normalizedInput) : null;
    const suggestedStart = resolveStartFromHistory(normalizedPrefill);
    setFormState((previous) => {
      return applyBookNarrationPrefillInputFile({
        previous,
        inputFile: normalizedPrefill,
        forcedBaseOutputFile,
        cachedBookMetadata,
        suggestedStartSentence: suggestedStart,
      });
    });
    prefillAppliedRef.current = normalizedPrefill;
  }, [
    forcedBaseOutputFile,
    lastAutoEndSentenceRef,
    normalizePath,
    prefillAppliedRef,
    prefillInputFile,
    resolveStartFromHistory,
    setFormState,
    userEditedEndRef,
    userEditedInputRef,
    userEditedStartRef,
  ]);

  useEffect(() => {
    if (!prefillParameters) {
      prefillParametersRef.current = null;
      return;
    }
    const key = JSON.stringify(prefillParameters);
    if (prefillParametersRef.current === key) {
      return;
    }
    prefillParametersRef.current = key;

    setFormState((previous) => {
      const next = applyBookNarrationPrefillParameters(
        previous,
        prefillParameters,
        forcedBaseOutputFile,
      );
      return preserveUserEditedFields(previous, next);
    });
  }, [forcedBaseOutputFile, prefillParameters, preserveUserEditedFields, setFormState]);
}
