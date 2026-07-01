import { useCallback, useMemo } from 'react';
import type { Dispatch, MutableRefObject, SetStateAction } from 'react';
import {
  applyBookNarrationFieldChange,
  applyBookNarrationVoiceOverride,
  resolveBookNarrationFieldChangeApplication,
  resolveBookNarrationVoiceOverrideLanguages,
} from './bookNarrationFormUtils';
import type { FormState } from './bookNarrationFormTypes';

type UseBookNarrationFormEditingArgs = {
  formState: FormState;
  forcedBaseOutputFile: string | null;
  lastAutoEndSentenceRef: MutableRefObject<string | null>;
  normalizedTargetLanguages: string[];
  setFormState: Dispatch<SetStateAction<FormState>>;
  setSharedEnableLookupCache: (value: boolean) => void;
  setSharedInputLanguage: (value: string) => void;
  setSharedTargetLanguages: (value: string[]) => void;
  sharedTargetLanguages: string[];
  userEditedEndRef: MutableRefObject<boolean>;
  userEditedFieldsRef: MutableRefObject<Set<keyof FormState>>;
  userEditedImageDefaultsRef: MutableRefObject<Set<keyof FormState>>;
  userEditedInputRef: MutableRefObject<boolean>;
  userEditedStartRef: MutableRefObject<boolean>;
};

export function useBookNarrationFormEditing({
  formState,
  forcedBaseOutputFile,
  lastAutoEndSentenceRef,
  normalizedTargetLanguages,
  setFormState,
  setSharedEnableLookupCache,
  setSharedInputLanguage,
  setSharedTargetLanguages,
  sharedTargetLanguages,
  userEditedEndRef,
  userEditedFieldsRef,
  userEditedImageDefaultsRef,
  userEditedInputRef,
  userEditedStartRef,
}: UseBookNarrationFormEditingArgs) {
  const markUserEditedField = useCallback((key: keyof FormState) => {
    userEditedFieldsRef.current.add(key);
  }, [userEditedFieldsRef]);

  const handleChange = useCallback(<K extends keyof FormState>(key: K, value: FormState[K]) => {
    const application = resolveBookNarrationFieldChangeApplication({
      key,
      value,
      formState,
      forcedBaseOutputFile,
      sharedTargetLanguages,
    });
    if (!application.allowed) {
      return;
    }
    if (application.markStartEdited) userEditedStartRef.current = true;
    if (application.markEndEdited) userEditedEndRef.current = true;
    if (application.resetAutoEndSentence) lastAutoEndSentenceRef.current = null;
    if (application.markInputEdited) userEditedInputRef.current = true;
    application.editedFields.forEach(markUserEditedField);
    application.imageDefaultFields.forEach((field) => userEditedImageDefaultsRef.current.add(field));
    setFormState((previous) => applyBookNarrationFieldChange(previous, key, value));

    const { sharedPreferenceUpdate } = application;
    if (sharedPreferenceUpdate?.inputLanguage !== undefined) {
      setSharedInputLanguage(sharedPreferenceUpdate.inputLanguage);
    }
    if (sharedPreferenceUpdate?.targetLanguages !== undefined) {
      setSharedTargetLanguages(sharedPreferenceUpdate.targetLanguages);
    }
    if (sharedPreferenceUpdate?.enableLookupCache !== undefined) {
      setSharedEnableLookupCache(sharedPreferenceUpdate.enableLookupCache);
    }
  }, [
    forcedBaseOutputFile,
    formState,
    lastAutoEndSentenceRef,
    markUserEditedField,
    setFormState,
    setSharedEnableLookupCache,
    setSharedInputLanguage,
    setSharedTargetLanguages,
    sharedTargetLanguages,
    userEditedEndRef,
    userEditedImageDefaultsRef,
    userEditedInputRef,
    userEditedStartRef,
  ]);

  const updateVoiceOverride = useCallback((languageCode: string, voiceValue: string) => {
    if (!languageCode.trim()) {
      return;
    }
    markUserEditedField('voice_overrides');
    setFormState((previous) => {
      return applyBookNarrationVoiceOverride(previous, languageCode, voiceValue);
    });
  }, [markUserEditedField, setFormState]);

  const languagesForOverride = useMemo(() => {
    return resolveBookNarrationVoiceOverrideLanguages(
      formState.input_language,
      normalizedTargetLanguages,
    );
  }, [formState.input_language, normalizedTargetLanguages]);

  return {
    handleChange,
    languagesForOverride,
    markUserEditedField,
    updateVoiceOverride,
  };
}
