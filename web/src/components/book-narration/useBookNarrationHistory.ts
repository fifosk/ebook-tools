import { useCallback, useEffect, useRef } from 'react';
import type { PipelineStatusResponse } from '../../api/dtos';
import {
  normalizeBookNarrationPath,
  resolveLatestBookNarrationJobSelection,
  resolveLatestBookNarrationJobSettings,
  resolveStartFromNarrationHistory,
} from './bookNarrationFormUtils';

type UseBookNarrationHistoryArgs = {
  recentJobs?: PipelineStatusResponse[] | null;
};

export function useBookNarrationHistory({ recentJobs }: UseBookNarrationHistoryArgs) {
  const recentJobsRef = useRef<PipelineStatusResponse[] | null>(recentJobs ?? null);

  useEffect(() => {
    recentJobsRef.current = recentJobs ?? null;
  }, [recentJobs]);

  const normalizePath = useCallback(
    (value: string | null | undefined): string | null => normalizeBookNarrationPath(value),
    [],
  );

  const resolveStartFromHistory = useCallback((inputPath: string): number | null => {
    return resolveStartFromNarrationHistory(inputPath, recentJobsRef.current);
  }, []);

  const resolveLatestJobSelection = useCallback(() => {
    return resolveLatestBookNarrationJobSelection(recentJobsRef.current);
  }, []);

  const resolveLatestJobSettings = useCallback(() => {
    return resolveLatestBookNarrationJobSettings(recentJobsRef.current);
  }, []);

  return {
    normalizePath,
    resolveLatestJobSelection,
    resolveLatestJobSettings,
    resolveStartFromHistory,
  };
}
