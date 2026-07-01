import {
  useCallback,
  useEffect,
  useRef,
} from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { FormState, ImageDefaults } from './bookNarrationFormTypes';
import { applyBookNarrationImageDefaults } from './bookNarrationFormUtils';

type UseBookNarrationImageDefaultsArgs = {
  hasPrefillAddImages: boolean;
  imageDefaults: ImageDefaults | null;
  setFormState: Dispatch<SetStateAction<FormState>>;
};

export function useBookNarrationImageDefaults({
  hasPrefillAddImages,
  imageDefaults,
  setFormState,
}: UseBookNarrationImageDefaultsArgs) {
  const userEditedImageDefaultsRef = useRef<Set<keyof FormState>>(new Set());

  const applyImageDefaults = useCallback((state: FormState): FormState => {
    return applyBookNarrationImageDefaults({
      state,
      imageDefaults,
      editedFields: userEditedImageDefaultsRef.current,
      allowAddImagesDefault: !hasPrefillAddImages,
    });
  }, [hasPrefillAddImages, imageDefaults]);

  useEffect(() => {
    setFormState((previous) => applyImageDefaults(previous));
  }, [applyImageDefaults, setFormState]);

  return {
    applyImageDefaults,
    userEditedImageDefaultsRef,
  };
}
