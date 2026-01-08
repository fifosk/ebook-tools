import { useEffect } from 'react';
import { fetchPipelineDefaults } from '../../api/client';
import type { PipelineStatusResponse } from '../../api/dtos';
import type { FormState } from './bookNarrationFormTypes';
import {
  applyConfigDefaults,
  areLanguageArraysEqual,
  normalizeSingleTargetLanguages,
} from './bookNarrationFormUtils';

type ResolveLatestJobSelection = () => { input?: string | null; base?: string | null } | null;

type UseBookNarrationDefaultsOptions = {
  formState: FormState;
  isGeneratedSource: boolean;
  forcedBaseOutputFile: string | null;
  recentJobs: PipelineStatusResponse[] | null;
  resolveLatestJobSelection: ResolveLatestJobSelection;
  resolveStartFromHistory: (inputPath: string) => number | null;
  applyImageDefaults: (state: FormState) => FormState;
  preserveUserEditedFields: (previous: FormState, next: FormState) => FormState;
  defaultsAppliedRef: React.MutableRefObject<boolean>;
  userEditedFieldsRef: React.MutableRefObject<Set<keyof FormState>>;
  userEditedImageDefaultsRef: React.MutableRefObject<Set<keyof FormState>>;
  userEditedInputRef: React.MutableRefObject<boolean>;
  userEditedStartRef: React.MutableRefObject<boolean>;
  userEditedEndRef: React.MutableRefObject<boolean>;
  lastAutoEndSentenceRef: React.MutableRefObject<string | null>;
  setFormState: React.Dispatch<React.SetStateAction<FormState>>;
  sharedInputLanguage: string;
  sharedTargetLanguages: string[];
  setSharedInputLanguage: (value: string) => void;
  setSharedTargetLanguages: (value: string[]) => void;
};

export function useBookNarrationDefaults({
  formState,
  isGeneratedSource,
  forcedBaseOutputFile,
  recentJobs,
  resolveLatestJobSelection,
  resolveStartFromHistory,
  applyImageDefaults,
  preserveUserEditedFields,
  defaultsAppliedRef,
  userEditedFieldsRef,
  userEditedImageDefaultsRef,
  userEditedInputRef,
  userEditedStartRef,
  userEditedEndRef,
  lastAutoEndSentenceRef,
  setFormState,
  sharedInputLanguage,
  sharedTargetLanguages,
  setSharedInputLanguage,
  setSharedTargetLanguages,
}: UseBookNarrationDefaultsOptions) {
  useEffect(() => {
    let cancelled = false;
    const loadDefaults = async () => {
      if (defaultsAppliedRef.current) {
        return;
      }
      try {
        const defaults = await fetchPipelineDefaults();
        if (cancelled) {
          return;
        }
        const config = defaults?.config ?? {};
        const allowInputDefaults = !userEditedFieldsRef.current.has('input_language');
        const allowTargetDefaults = !userEditedFieldsRef.current.has('target_languages');
        // Preserve user edits; defaults should not overwrite in-flight changes.
        lastAutoEndSentenceRef.current = null;
        setFormState((previous) => {
          let next = applyImageDefaults(applyConfigDefaults(previous, config));
          if (isGeneratedSource || userEditedInputRef.current) {
            next = { ...next, input_file: previous.input_file };
          }
          if (userEditedStartRef.current) {
            next = { ...next, start_sentence: previous.start_sentence };
          }
          if (userEditedEndRef.current) {
            next = { ...next, end_sentence: previous.end_sentence };
          }
          const editedImageFields = userEditedImageDefaultsRef.current;
          if (editedImageFields.size > 0) {
            const restored: Partial<FormState> = {};
            if (editedImageFields.has('add_images')) {
              restored.add_images = previous.add_images;
            }
            if (editedImageFields.has('image_prompt_pipeline')) {
              restored.image_prompt_pipeline = previous.image_prompt_pipeline;
            }
            if (editedImageFields.has('image_style_template')) {
              restored.image_style_template = previous.image_style_template;
            }
            if (editedImageFields.has('image_prompt_context_sentences')) {
              restored.image_prompt_context_sentences = previous.image_prompt_context_sentences;
            }
            if (editedImageFields.has('image_width')) {
              restored.image_width = previous.image_width;
            }
            if (editedImageFields.has('image_height')) {
              restored.image_height = previous.image_height;
            }
            if (Object.keys(restored).length > 0) {
              next = { ...next, ...restored };
            }
          }
          next = preserveUserEditedFields(previous, next);
          const suggestedStart = resolveStartFromHistory(next.input_file);
          const baseOutput = forcedBaseOutputFile ?? next.base_output_file;
          const shouldApplySuggestedStart =
            suggestedStart !== null &&
            !userEditedStartRef.current &&
            !userEditedFieldsRef.current.has('start_sentence');
          if (shouldApplySuggestedStart) {
            return { ...next, start_sentence: suggestedStart, base_output_file: baseOutput };
          }
          return { ...next, base_output_file: baseOutput };
        });
        const inputLanguage = typeof config['input_language'] === 'string' ? config['input_language'] : null;
        if (allowInputDefaults && inputLanguage) {
          setSharedInputLanguage(inputLanguage);
        }
        const targetLanguages = Array.isArray(config['target_languages'])
          ? Array.from(
              new Set(
                config['target_languages']
                  .filter((language): language is string => typeof language === 'string')
                  .map((language) => language.trim())
                  .filter((language) => language.length > 0),
              ),
            )
          : [];
        if (allowTargetDefaults && targetLanguages.length > 0) {
          setSharedTargetLanguages(normalizeSingleTargetLanguages(targetLanguages));
        }
        defaultsAppliedRef.current = true;
      } catch (defaultsError) {
        console.warn('Unable to load pipeline defaults', defaultsError);
      }
    };
    void loadDefaults();
    return () => {
      cancelled = true;
    };
  }, [
    applyImageDefaults,
    defaultsAppliedRef,
    forcedBaseOutputFile,
    isGeneratedSource,
    preserveUserEditedFields,
    resolveStartFromHistory,
    setFormState,
    setSharedInputLanguage,
    setSharedTargetLanguages,
    userEditedFieldsRef,
    userEditedImageDefaultsRef,
    userEditedInputRef,
    userEditedStartRef,
    userEditedEndRef,
    lastAutoEndSentenceRef,
  ]);

  useEffect(() => {
    setFormState((previous) => {
      if (previous.input_language === sharedInputLanguage) {
        return previous;
      }
      return {
        ...previous,
        input_language: sharedInputLanguage,
      };
    });
  }, [setFormState, sharedInputLanguage]);

  useEffect(() => {
    setFormState((previous) => {
      if (areLanguageArraysEqual(previous.target_languages, sharedTargetLanguages)) {
        return previous;
      }
      return {
        ...previous,
        target_languages: [...sharedTargetLanguages],
      };
    });
  }, [setFormState, sharedTargetLanguages]);

  useEffect(() => {
    if (isGeneratedSource || forcedBaseOutputFile) {
      return;
    }
    if (userEditedInputRef.current) {
      return;
    }
    const latest = resolveLatestJobSelection();
    if (!latest) {
      return;
    }
    const nextInput = latest.input ? latest.input.trim() : '';
    const nextBase = latest.base ? latest.base.trim() : '';
    setFormState((previous) => {
      if (userEditedInputRef.current) {
        return previous;
      }
      const inputChanged = nextInput && previous.input_file !== nextInput;
      const baseChanged = nextBase && previous.base_output_file !== nextBase;
      if (!inputChanged && !baseChanged) {
        return previous;
      }
      const suggestedStart = resolveStartFromHistory(nextInput || previous.input_file);
      return {
        ...previous,
        input_file: inputChanged ? nextInput : previous.input_file,
        base_output_file: baseChanged ? nextBase : previous.base_output_file,
        start_sentence: suggestedStart ?? previous.start_sentence,
      };
    });
  }, [
    forcedBaseOutputFile,
    isGeneratedSource,
    recentJobs,
    resolveLatestJobSelection,
    resolveStartFromHistory,
    setFormState,
    userEditedInputRef,
  ]);

  useEffect(() => {
    if (userEditedStartRef.current) {
      return;
    }
    const suggestedStart = resolveStartFromHistory(formState.input_file);
    if (suggestedStart === null || formState.start_sentence === suggestedStart) {
      return;
    }
    setFormState((previous) => {
      if (previous.input_file !== formState.input_file) {
        return previous;
      }
      if (userEditedStartRef.current || previous.start_sentence === suggestedStart) {
        return previous;
      }
      return { ...previous, start_sentence: suggestedStart };
    });
  }, [formState.input_file, formState.start_sentence, recentJobs, resolveStartFromHistory, setFormState, userEditedStartRef]);

  useEffect(() => {
    if (userEditedEndRef.current) {
      return;
    }

    const start = formState.start_sentence;
    if (!Number.isFinite(start)) {
      return;
    }

    const suggestedEnd = String(Math.max(1, Math.trunc(start)) + 99);
    const currentEnd = formState.end_sentence;
    const lastAuto = lastAutoEndSentenceRef.current;
    const shouldApply = currentEnd === '' || (lastAuto !== null && currentEnd === lastAuto);

    if (!shouldApply) {
      lastAutoEndSentenceRef.current = null;
      return;
    }

    if (currentEnd === suggestedEnd) {
      lastAutoEndSentenceRef.current = suggestedEnd;
      return;
    }

    setFormState((previous) => {
      if (userEditedEndRef.current) {
        return previous;
      }

      const previousStart = previous.start_sentence;
      if (!Number.isFinite(previousStart)) {
        return previous;
      }

      const nextSuggestedEnd = String(Math.max(1, Math.trunc(previousStart)) + 99);
      const previousEnd = previous.end_sentence;
      const previousLastAuto = lastAutoEndSentenceRef.current;
      const previousShouldApply =
        previousEnd === '' || (previousLastAuto !== null && previousEnd === previousLastAuto);

      if (!previousShouldApply && previousEnd !== nextSuggestedEnd) {
        return previous;
      }

      lastAutoEndSentenceRef.current = nextSuggestedEnd;
      return { ...previous, end_sentence: nextSuggestedEnd };
    });
  }, [formState.end_sentence, formState.start_sentence, setFormState, userEditedEndRef, lastAutoEndSentenceRef]);
}
