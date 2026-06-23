import { useEffect, useState } from 'react';
import { fetchLlmModels } from '../../api/client';

export function useSubtitleModels() {
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [modelsLoading, setModelsLoading] = useState<boolean>(false);
  const [modelsError, setModelsError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setModelsLoading(true);
    setModelsError(null);
    fetchLlmModels()
      .then((models) => {
        if (!cancelled) {
          setAvailableModels(models ?? []);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          console.warn('Unable to load available subtitle models', error);
          const message = error instanceof Error ? error.message : 'Request failed';
          setModelsError(message);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setModelsLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return {
    availableModels,
    modelsLoading,
    modelsError
  };
}
