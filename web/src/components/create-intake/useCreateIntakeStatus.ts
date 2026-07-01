import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchPipelineIntakeStatus } from '../../api/client';
import type { PipelineIntakeStatusResponse } from '../../api/dtos';

export function useCreateIntakeStatus() {
  const [intakeStatus, setIntakeStatus] = useState<PipelineIntakeStatusResponse | null>(null);
  const [isLoadingIntakeStatus, setIsLoadingIntakeStatus] = useState<boolean>(false);
  const isMountedRef = useRef(true);
  const requestSequenceRef = useRef(0);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const refreshIntakeStatus = useCallback(async () => {
    const requestSequence = requestSequenceRef.current + 1;
    requestSequenceRef.current = requestSequence;
    if (isMountedRef.current) {
      setIsLoadingIntakeStatus(true);
    }
    try {
      const status = await fetchPipelineIntakeStatus();
      if (isMountedRef.current && requestSequence === requestSequenceRef.current) {
        setIntakeStatus(status);
      }
    } catch {
      if (isMountedRef.current && requestSequence === requestSequenceRef.current) {
        setIntakeStatus(null);
      }
    } finally {
      if (isMountedRef.current && requestSequence === requestSequenceRef.current) {
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
