import { useCallback } from 'react';
import type { FormEvent } from 'react';
import type { PipelineRequestPayload } from '../../api/dtos';
import type { BookNarrationFormSection, FormState } from './bookNarrationFormTypes';
import type {
  BookNarrationSectionMeta,
} from './bookNarrationFormUtils';
import { resolveBookNarrationSubmitPresentation } from './bookNarrationFormUtils';
import { useBookNarrationSubmit } from './useBookNarrationSubmit';

type ChapterSelection = {
  startSentence: number;
  endSentence: number;
};

type UseBookNarrationSubmitFlowArgs = {
  activeSection: BookNarrationFormSection;
  chapterSelection: ChapterSelection | null;
  chapterSelectionMode: 'range' | 'chapters';
  forcedBaseOutputFile: string | null;
  formState: FormState;
  implicitEndOffsetThreshold: number | null;
  isGeneratedSource: boolean;
  isIntakeAtCapacity: boolean;
  isSubmitting: boolean;
  normalizedTargetLanguages: string[];
  onSubmit: (payload: PipelineRequestPayload) => Promise<void> | void;
  refreshIntakeStatus: () => Promise<void> | void;
  sectionMeta: BookNarrationSectionMeta;
  setError: (error: string | null) => void;
  submitLabel?: string | null;
};

export function useBookNarrationSubmitFlow({
  activeSection,
  chapterSelection,
  chapterSelectionMode,
  forcedBaseOutputFile,
  formState,
  implicitEndOffsetThreshold,
  isGeneratedSource,
  isIntakeAtCapacity,
  isSubmitting,
  normalizedTargetLanguages,
  onSubmit,
  refreshIntakeStatus,
  sectionMeta,
  setError,
  submitLabel,
}: UseBookNarrationSubmitFlowArgs) {
  const { handleSubmit } = useBookNarrationSubmit({
    formState,
    normalizedTargetLanguages,
    chapterSelectionMode,
    chapterSelection,
    isGeneratedSource,
    forcedBaseOutputFile,
    implicitEndOffsetThreshold,
    onSubmit,
    setError,
  });

  const handleSubmitAndRefreshIntake = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      const didSubmit = await handleSubmit(event);
      if (didSubmit) {
        await refreshIntakeStatus();
      }
    },
    [handleSubmit, refreshIntakeStatus],
  );

  const submitPresentation = resolveBookNarrationSubmitPresentation({
    activeSection,
    sectionMeta,
    formState,
    normalizedTargetLanguages,
    isGeneratedSource,
    chapterSelectionMode,
    hasChapterSelection: Boolean(chapterSelection),
    isSubmitting,
    isIntakeAtCapacity,
    submitLabel,
  });

  return {
    handleSubmitAndRefreshIntake,
    submitPresentation,
  };
}
