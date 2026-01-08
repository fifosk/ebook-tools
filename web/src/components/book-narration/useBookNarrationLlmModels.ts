import { useEffect, useState } from 'react';
import { fetchLlmModels } from '../../api/client';

export function useBookNarrationLlmModels() {
  const [availableLlmModels, setAvailableLlmModels] = useState<string[]>([]);
  const [llmModelError, setLlmModelError] = useState<string | null>(null);
  const [isLoadingLlmModels, setIsLoadingLlmModels] = useState<boolean>(false);

  useEffect(() => {
    let cancelled = false;
    const loadModels = async () => {
      setIsLoadingLlmModels(true);
      try {
        const models = await fetchLlmModels();
        if (cancelled) {
          return;
        }
        setAvailableLlmModels(models ?? []);
        setLlmModelError(null);
      } catch (modelError) {
        if (!cancelled) {
          const message =
            modelError instanceof Error ? modelError.message : 'Unable to load model list.';
          setLlmModelError(message);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingLlmModels(false);
        }
      }
    };
    void loadModels();
    return () => {
      cancelled = true;
    };
  }, []);

  return { availableLlmModels, llmModelError, isLoadingLlmModels };
}
