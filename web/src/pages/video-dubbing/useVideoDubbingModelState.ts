import { useEffect, useState } from 'react';
import { fetchSubtitleModels } from '../../api/client';
import { DEFAULT_LLM_MODEL } from './videoDubbingConfig';

export function useVideoDubbingModelState() {
  const [llmModel, setLlmModel] = useState(DEFAULT_LLM_MODEL);
  const [transliterationModel, setTransliterationModel] = useState('');
  const [translationProvider, setTranslationProvider] = useState('llm');
  const [transliterationMode, setTransliterationMode] = useState('default');
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

  return {
    llmModel,
    setLlmModel,
    transliterationModel,
    setTransliterationModel,
    translationProvider,
    setTranslationProvider,
    transliterationMode,
    setTransliterationMode,
    llmModels,
    isLoadingModels,
    modelError
  };
}
