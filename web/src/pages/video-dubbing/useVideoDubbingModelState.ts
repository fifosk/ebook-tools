import { useCallback, useEffect, useState } from 'react';
import { fetchSubtitleModels } from '../../api/client';
import type { BookCreationOptionsResponse } from '../../api/createBook';
import { DEFAULT_LLM_MODEL } from './videoDubbingConfig';

const DEFAULT_TRANSLATION_PROVIDER = 'llm';
const DEFAULT_TRANSLITERATION_MODE = 'default';

export function useVideoDubbingModelState() {
  const [llmModel, setLlmModel] = useState(DEFAULT_LLM_MODEL);
  const [transliterationModel, setTransliterationModel] = useState('');
  const [translationProvider, setTranslationProvider] = useState(DEFAULT_TRANSLATION_PROVIDER);
  const [transliterationMode, setTransliterationMode] = useState(DEFAULT_TRANSLITERATION_MODE);
  const [llmModels, setLlmModels] = useState<string[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [modelError, setModelError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const loadModels = async () => {
      setIsLoadingModels(true);
      setModelError(null);
      try {
        const models = await fetchSubtitleModels();
        if (cancelled) return;
        setLlmModels(models);
        setLlmModel((current) => {
          if (current || models.length === 0) {
            return current;
          }
          return models.includes(DEFAULT_LLM_MODEL) ? DEFAULT_LLM_MODEL : models[0];
        });
      } catch (error) {
        if (cancelled) return;
        const message =
          error instanceof Error ? error.message || 'Unable to load translation models.' : 'Unable to load translation models.';
        setModelError(message);
      } finally {
        if (!cancelled) {
          setIsLoadingModels(false);
        }
      }
    };
    void loadModels();
    return () => {
      cancelled = true;
    };
  }, []);

  const applyPipelineDefaults = useCallback((defaults: BookCreationOptionsResponse['pipeline_defaults'] | null) => {
    const provider = defaults?.translation_provider.trim();
    if (provider) {
      setTranslationProvider((current) =>
        current === DEFAULT_TRANSLATION_PROVIDER ? provider : current
      );
    }
    const nextTransliterationMode = defaults?.transliteration_mode.trim();
    if (nextTransliterationMode) {
      setTransliterationMode((current) =>
        current === DEFAULT_TRANSLITERATION_MODE ? nextTransliterationMode : current
      );
    }
  }, []);

  return {
    llmModel,
    setLlmModel,
    transliterationModel,
    setTransliterationModel,
    translationProvider,
    setTranslationProvider,
    transliterationMode,
    setTransliterationMode,
    applyPipelineDefaults,
    llmModels,
    isLoadingModels,
    modelError
  };
}
