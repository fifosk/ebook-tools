import { useMemo } from 'react';
import type { FormState } from './bookNarrationFormTypes';
import { resolveBookNarrationTargetLanguages } from './bookNarrationFormUtils';

type UseBookNarrationNormalizedStateArgs = {
  formState: Pick<FormState, 'input_file' | 'target_languages' | 'custom_target_languages'>;
  isGeneratedSource: boolean;
  normalizePath: (value: string | null | undefined) => string | null;
};

export function useBookNarrationNormalizedState({
  formState,
  isGeneratedSource,
  normalizePath,
}: UseBookNarrationNormalizedStateArgs) {
  const normalizedInputForBookMetadataCache = useMemo(() => {
    if (isGeneratedSource) {
      return null;
    }
    return normalizePath(formState.input_file);
  }, [formState.input_file, isGeneratedSource, normalizePath]);

  const normalizedTargetLanguages = useMemo(
    () => resolveBookNarrationTargetLanguages({
      target_languages: formState.target_languages,
      custom_target_languages: formState.custom_target_languages,
    }),
    [formState.custom_target_languages, formState.target_languages],
  );

  return {
    normalizedInputForBookMetadataCache,
    normalizedTargetLanguages,
  };
}
