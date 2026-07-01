import { useCallback, useMemo, useState } from 'react';
import { saveCreationTemplate } from '../../api/client';
import type { CreationTemplateEntry, CreationTemplatePayload } from '../../api/dtos';
import type { BookNarrationFormSection, FormState } from './bookNarrationFormTypes';
import {
  saveBookNarrationTemplate,
  type SaveBookNarrationTemplateResult,
} from './bookNarrationTemplates';

type SaveTemplateClient = (payload: CreationTemplatePayload) => Promise<CreationTemplateEntry>;

type UseBookNarrationTemplateSaveArgs = {
  activeSection: BookNarrationFormSection;
  creationTemplateError?: string | null;
  formState: FormState;
  isLoadingCreationTemplate?: boolean;
  normalizedTargetLanguages: string[];
  payloadExtras?: Record<string, unknown> | null;
  saveTemplate?: SaveTemplateClient;
  sourceMode: 'upload' | 'generated';
};

export function useBookNarrationTemplateSave({
  activeSection,
  creationTemplateError = null,
  formState,
  isLoadingCreationTemplate = false,
  normalizedTargetLanguages,
  payloadExtras = null,
  saveTemplate = saveCreationTemplate,
  sourceMode,
}: UseBookNarrationTemplateSaveArgs) {
  const [templateStatus, setTemplateStatus] = useState<string | null>(null);
  const [templateError, setTemplateError] = useState<string | null>(null);
  const [isSavingTemplate, setIsSavingTemplate] = useState(false);

  const handleSaveTemplate = useCallback(async (): Promise<SaveBookNarrationTemplateResult> => {
    setTemplateStatus(null);
    setTemplateError(null);
    setIsSavingTemplate(true);
    try {
      const result = await saveBookNarrationTemplate({
        formState,
        normalizedTargetLanguages,
        sourceMode,
        activeSection,
        payloadExtras,
        saveTemplate,
      });
      setTemplateStatus(result.status);
      setTemplateError(result.error);
      return result;
    } finally {
      setIsSavingTemplate(false);
    }
  }, [
    activeSection,
    formState,
    normalizedTargetLanguages,
    payloadExtras,
    saveTemplate,
    sourceMode,
  ]);

  return useMemo(
    () => ({
      effectiveTemplateError: creationTemplateError ?? templateError,
      effectiveTemplateStatus: isLoadingCreationTemplate ? 'Loading saved template...' : templateStatus,
      handleSaveTemplate,
      isSavingTemplate,
      setTemplateError,
      setTemplateStatus,
      templateError,
      templateStatus,
    }),
    [
      creationTemplateError,
      handleSaveTemplate,
      isLoadingCreationTemplate,
      isSavingTemplate,
      templateError,
      templateStatus,
    ],
  );
}
