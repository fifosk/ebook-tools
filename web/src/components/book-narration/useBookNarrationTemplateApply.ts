import { useEffect } from 'react';
import type { Dispatch, MutableRefObject, SetStateAction } from 'react';
import type { CreationTemplateEntry } from '../../api/dtos';
import type { BookNarrationSourcePanel } from './BookNarrationSourceSection';
import type { BookNarrationFormSection, FormState } from './bookNarrationFormTypes';
import { resolveBookNarrationTemplateApply } from './bookNarrationTemplates';
import {
  applyBookNarrationTemplateFormState,
  resolveBookNarrationTemplateFormStateApplication,
} from './bookNarrationFormUtils';

type UseBookNarrationTemplateApplyArgs = {
  creationTemplate: CreationTemplateEntry | null;
  creationTemplateAppliedRef: MutableRefObject<string | null>;
  forcedBaseOutputFile: string | null;
  handleSectionChange: (section: BookNarrationFormSection) => void;
  lastAutoEndSentenceRef: MutableRefObject<string | null>;
  setActiveSourcePanel: Dispatch<SetStateAction<BookNarrationSourcePanel>>;
  setFormState: Dispatch<SetStateAction<FormState>>;
  setSelectedDiscoveryTemplateState: Dispatch<SetStateAction<Record<string, unknown> | null>>;
  setSharedEnableLookupCache: (value: boolean) => void;
  setSharedInputLanguage: (value: string) => void;
  setSharedTargetLanguages: (value: string[]) => void;
  setTemplateError: Dispatch<SetStateAction<string | null>>;
  setTemplateStatus: Dispatch<SetStateAction<string | null>>;
  sharedTargetLanguages: string[];
  sourceMode: 'upload' | 'generated';
  userEditedEndRef: MutableRefObject<boolean>;
  userEditedFieldsRef: MutableRefObject<Set<keyof FormState>>;
  userEditedImageDefaultsRef: MutableRefObject<Set<keyof FormState>>;
  userEditedInputRef: MutableRefObject<boolean>;
  userEditedStartRef: MutableRefObject<boolean>;
};

export function useBookNarrationTemplateApply({
  creationTemplate,
  creationTemplateAppliedRef,
  forcedBaseOutputFile,
  handleSectionChange,
  lastAutoEndSentenceRef,
  setActiveSourcePanel,
  setFormState,
  setSelectedDiscoveryTemplateState,
  setSharedEnableLookupCache,
  setSharedInputLanguage,
  setSharedTargetLanguages,
  setTemplateError,
  setTemplateStatus,
  sharedTargetLanguages,
  sourceMode,
  userEditedEndRef,
  userEditedFieldsRef,
  userEditedImageDefaultsRef,
  userEditedInputRef,
  userEditedStartRef,
}: UseBookNarrationTemplateApplyArgs) {
  useEffect(() => {
    const templateResolution = resolveBookNarrationTemplateApply({
      template: creationTemplate,
      sourceMode,
      lastAppliedKey: creationTemplateAppliedRef.current,
    });
    if (templateResolution.action === 'clear') {
      creationTemplateAppliedRef.current = null;
      return;
    }
    if (templateResolution.action === 'skip') {
      return;
    }
    if (templateResolution.action === 'incompatible') {
      setTemplateStatus(null);
      setTemplateError(templateResolution.error);
      creationTemplateAppliedRef.current = templateResolution.applyKey;
      return;
    }

    const { applied } = templateResolution;
    const templateApplication = resolveBookNarrationTemplateFormStateApplication({
      formState: applied.formState,
      sharedTargetLanguages,
    });
    const { appliedFormState, sharedPreferenceUpdate } = templateApplication;
    setSelectedDiscoveryTemplateState(applied.discoveryState);
    setActiveSourcePanel(applied.discoveryState ? 'discovery' : 'source');

    userEditedStartRef.current = templateApplication.markStartEdited;
    userEditedInputRef.current = templateApplication.markInputEdited;
    userEditedEndRef.current = templateApplication.markEndEdited;
    lastAutoEndSentenceRef.current = null;
    templateApplication.editedFields.forEach((key) => userEditedFieldsRef.current.add(key));
    templateApplication.imageDefaultFields.forEach((key) => userEditedImageDefaultsRef.current.add(key));

    if (sharedPreferenceUpdate?.targetLanguages !== undefined) {
      setSharedTargetLanguages(sharedPreferenceUpdate.targetLanguages);
    }
    if (sharedPreferenceUpdate?.inputLanguage !== undefined) {
      setSharedInputLanguage(sharedPreferenceUpdate.inputLanguage);
    }
    if (sharedPreferenceUpdate?.enableLookupCache !== undefined) {
      setSharedEnableLookupCache(sharedPreferenceUpdate.enableLookupCache);
    }
    setFormState((previous) => applyBookNarrationTemplateFormState(
      previous,
      appliedFormState,
      forcedBaseOutputFile,
    ));
    if (applied.activeSection) {
      handleSectionChange(applied.activeSection);
    }
    setTemplateError(templateResolution.error);
    setTemplateStatus(templateResolution.status);
    creationTemplateAppliedRef.current = templateResolution.applyKey;
  }, [
    creationTemplate,
    creationTemplateAppliedRef,
    forcedBaseOutputFile,
    handleSectionChange,
    lastAutoEndSentenceRef,
    setActiveSourcePanel,
    setFormState,
    setSelectedDiscoveryTemplateState,
    setSharedEnableLookupCache,
    setSharedInputLanguage,
    setSharedTargetLanguages,
    setTemplateError,
    setTemplateStatus,
    sharedTargetLanguages,
    sourceMode,
    userEditedEndRef,
    userEditedFieldsRef,
    userEditedImageDefaultsRef,
    userEditedInputRef,
    userEditedStartRef,
  ]);
}
