import { useState } from 'react';
import type { JobParameterSnapshot } from '../../api/dtos';
import { useLanguagePreferences } from '../../context/LanguageProvider';
import type { BookNarrationFormProps, FormState } from './bookNarrationFormTypes';
import { buildBookNarrationInitialFormState } from './bookNarrationFormUtils';

type UseBookNarrationBaseStateArgs = {
  defaultImageSettings: BookNarrationFormProps['defaultImageSettings'];
  forcedBaseOutputFile: BookNarrationFormProps['forcedBaseOutputFile'];
  prefillParameters: JobParameterSnapshot | null;
  sourceMode: NonNullable<BookNarrationFormProps['sourceMode']>;
};

export function useBookNarrationBaseState({
  defaultImageSettings,
  forcedBaseOutputFile,
  prefillParameters,
  sourceMode,
}: UseBookNarrationBaseStateArgs) {
  const isGeneratedSource = sourceMode === 'generated';
  const imageDefaults = defaultImageSettings ?? null;
  const {
    inputLanguage: sharedInputLanguage,
    setInputLanguage: setSharedInputLanguage,
    targetLanguages: sharedTargetLanguages,
    setTargetLanguages: setSharedTargetLanguages,
    enableLookupCache: sharedEnableLookupCache,
    setEnableLookupCache: setSharedEnableLookupCache,
  } = useLanguagePreferences();
  const hasPrefillAddImages = typeof prefillParameters?.add_images === 'boolean';
  const [formState, setFormState] = useState<FormState>(() => buildBookNarrationInitialFormState({
    forcedBaseOutputFile,
    sharedInputLanguage,
    sharedTargetLanguages,
    sharedEnableLookupCache,
  }));

  return {
    formState,
    hasPrefillAddImages,
    imageDefaults,
    isGeneratedSource,
    setFormState,
    setSharedEnableLookupCache,
    setSharedInputLanguage,
    setSharedTargetLanguages,
    sharedInputLanguage,
    sharedTargetLanguages,
  };
}
