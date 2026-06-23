import { useEffect } from 'react';
import { fetchPipelineDefaults } from '../../api/client';
import type { PipelineStatusResponse } from '../../api/dtos';
import type { BookNarrationPipelineDefaults, FormState } from './bookNarrationFormTypes';
import {
  applyConfigDefaults,
  areLanguageArraysEqual,
  normalizeSingleTargetLanguages,
  restoreBookNarrationEditedImageDefaults,
} from './bookNarrationFormUtils';

type ResolveLatestJobSelection = () => { input?: string | null; base?: string | null } | null;

type ResolveLatestJobSettings = () => {
  inputLanguage: string | null;
  targetLanguages: string[] | null;
  enableLookupCache: boolean | null;
} | null;

type UseBookNarrationDefaultsOptions = {
  formState: FormState;
  isGeneratedSource: boolean;
  forcedBaseOutputFile: string | null;
  recentJobs: PipelineStatusResponse[] | null;
  resolveLatestJobSelection: ResolveLatestJobSelection;
  resolveLatestJobSettings: ResolveLatestJobSettings;
  resolveStartFromHistory: (inputPath: string) => number | null;
  applyImageDefaults: (state: FormState) => FormState;
  defaultPipelineSettings: BookNarrationPipelineDefaults | null;
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
  setSharedEnableLookupCache: (value: boolean) => void;
};

function compactPipelineDefaults(
  defaults: BookNarrationPipelineDefaults | null
): Record<string, unknown> | null {
  if (!defaults) {
    return null;
  }
  const config: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(defaults)) {
    if (value !== undefined && value !== null) {
      config[key] = value;
    }
  }
  return Object.keys(config).length > 0 ? config : null;
}

function targetLanguagesFromConfig(config: Record<string, unknown>): string[] {
  const targetLanguages = config['target_languages'];
  if (!Array.isArray(targetLanguages)) {
    return [];
  }
  return Array.from(
    new Set(
      targetLanguages
        .filter((language): language is string => typeof language === 'string')
        .map((language) => language.trim())
        .filter((language) => language.length > 0),
    ),
  );
}

export function useBookNarrationDefaults({
  formState,
  isGeneratedSource,
  forcedBaseOutputFile,
  recentJobs,
  resolveLatestJobSelection,
  resolveLatestJobSettings,
  resolveStartFromHistory,
  applyImageDefaults,
  defaultPipelineSettings,
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
  setSharedEnableLookupCache,
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
          next = restoreBookNarrationEditedImageDefaults(previous, next, userEditedImageDefaultsRef.current);
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
        const enableLookupCache = config['enable_lookup_cache'];
        if (
          typeof enableLookupCache === 'boolean' &&
          !userEditedFieldsRef.current.has('enable_lookup_cache')
        ) {
          setSharedEnableLookupCache(enableLookupCache);
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
    setSharedEnableLookupCache,
    userEditedFieldsRef,
    userEditedImageDefaultsRef,
    userEditedInputRef,
    userEditedStartRef,
    userEditedEndRef,
    lastAutoEndSentenceRef,
  ]);

  useEffect(() => {
    const config = compactPipelineDefaults(defaultPipelineSettings);
    if (!config) {
      return;
    }
    const allowInputDefaults = !userEditedFieldsRef.current.has('input_language');
    const allowTargetDefaults = !userEditedFieldsRef.current.has('target_languages');
    lastAutoEndSentenceRef.current = null;
    setFormState((previous) => {
      let next = applyConfigDefaults(previous, config);
      if (isGeneratedSource || userEditedInputRef.current) {
        next = { ...next, input_file: previous.input_file };
      }
      if (userEditedStartRef.current) {
        next = { ...next, start_sentence: previous.start_sentence };
      }
      if (userEditedEndRef.current) {
        next = { ...next, end_sentence: previous.end_sentence };
      }
      next = preserveUserEditedFields(previous, next);
      return {
        ...next,
        base_output_file: forcedBaseOutputFile ?? next.base_output_file,
      };
    });

    const inputLanguage = typeof config['input_language'] === 'string' ? config['input_language'] : null;
    if (allowInputDefaults && inputLanguage) {
      setSharedInputLanguage(inputLanguage);
    }
    const targetLanguages = targetLanguagesFromConfig(config);
    if (allowTargetDefaults && targetLanguages.length > 0) {
      setSharedTargetLanguages(normalizeSingleTargetLanguages(targetLanguages));
    }
    const enableLookupCache = config['enable_lookup_cache'];
    if (
      typeof enableLookupCache === 'boolean' &&
      !userEditedFieldsRef.current.has('enable_lookup_cache')
    ) {
      setSharedEnableLookupCache(enableLookupCache);
    }
  }, [
    defaultPipelineSettings,
    forcedBaseOutputFile,
    isGeneratedSource,
    lastAutoEndSentenceRef,
    preserveUserEditedFields,
    setFormState,
    setSharedEnableLookupCache,
    setSharedInputLanguage,
    setSharedTargetLanguages,
    userEditedEndRef,
    userEditedFieldsRef,
    userEditedInputRef,
    userEditedStartRef,
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

  // Pick up input language, target language(s) and lookup-cache preference
  // from the most recent book job. Server defaults from fetchPipelineDefaults
  // arrive first, then this effect (running whenever recentJobs changes)
  // overrides them with the last actual job settings — but only for fields
  // the user has not manually edited in the current session.
  useEffect(() => {
    const settings = resolveLatestJobSettings();
    if (!settings) {
      return;
    }
    if (
      settings.inputLanguage &&
      !userEditedFieldsRef.current.has('input_language') &&
      settings.inputLanguage !== sharedInputLanguage
    ) {
      setSharedInputLanguage(settings.inputLanguage);
    }
    if (
      settings.targetLanguages &&
      settings.targetLanguages.length > 0 &&
      !userEditedFieldsRef.current.has('target_languages')
    ) {
      const next = normalizeSingleTargetLanguages(settings.targetLanguages);
      if (!areLanguageArraysEqual(sharedTargetLanguages, next)) {
        setSharedTargetLanguages(next);
      }
    }
    if (
      typeof settings.enableLookupCache === 'boolean' &&
      !userEditedFieldsRef.current.has('enable_lookup_cache')
    ) {
      setSharedEnableLookupCache(settings.enableLookupCache);
      setFormState((previous) => {
        if (previous.enable_lookup_cache === settings.enableLookupCache) {
          return previous;
        }
        return { ...previous, enable_lookup_cache: settings.enableLookupCache as boolean };
      });
    }
  }, [
    recentJobs,
    resolveLatestJobSettings,
    sharedInputLanguage,
    sharedTargetLanguages,
    setSharedEnableLookupCache,
    setSharedInputLanguage,
    setSharedTargetLanguages,
    setFormState,
    userEditedFieldsRef,
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
