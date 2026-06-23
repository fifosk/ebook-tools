import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchPipelineIntakeStatus } from '../../api/client';
import type { PipelineIntakeStatusResponse } from '../../api/dtos';

export function useCreateIntakeStatus() {
  const [intakeStatus, setIntakeStatus] = useState<PipelineIntakeStatusResponse | null>(null);
  const [isLoadingIntakeStatus, setIsLoadingIntakeStatus] = useState<boolean>(false);
  const isMountedRef = useRef(true);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const refreshIntakeStatus = useCallback(async () => {
    if (isMountedRef.current) {
      setIsLoadingIntakeStatus(true);
    }
    try {
      const status = await fetchPipelineIntakeStatus();
      if (isMountedRef.current) {
        setIntakeStatus(status);
      }
    } catch {
      if (isMountedRef.current) {
        setIntakeStatus(null);
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoadingIntakeStatus(false);
      }
    }
  }, []);

  useEffect(() => {
    void refreshIntakeStatus();
  }, [refreshIntakeStatus]);

  return {
    intakeStatus,
    isLoadingIntakeStatus,
    isIntakeAtCapacity: intakeStatus?.acceptingJobs === false,
    refreshIntakeStatus,
  };
}
