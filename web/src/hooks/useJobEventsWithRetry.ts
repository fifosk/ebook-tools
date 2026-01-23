import { useEffect, useRef, useCallback } from 'react';
import { subscribeToJobEvents } from '../services/api';
import type { ProgressEventPayload } from '../api/dtos';

export interface UseJobEventsOptions {
  jobId: string;
  enabled: boolean;
  onEvent: (event: ProgressEventPayload) => void;
  onError?: (error: Event) => void;
  maxRetries?: number; // Default: 5
  retryDelayMs?: number; // Default: 2000 (exponential backoff base)
}

/**
 * Hook for subscribing to job SSE events with automatic retry logic.
 *
 * Features:
 * - Exponential backoff: 2s, 4s, 8s, 16s, 32s
 * - Configurable retry count and delay
 * - Resets retry count on successful connection
 * - Proper cleanup on unmount
 *
 * @example
 * ```tsx
 * useJobEventsWithRetry({
 *   jobId: 'job-123',
 *   enabled: true,
 *   onEvent: (event) => console.log(event),
 *   onError: (error) => console.error(error),
 *   maxRetries: 5,
 *   retryDelayMs: 2000,
 * });
 * ```
 */
export function useJobEventsWithRetry({
  jobId,
  enabled,
  onEvent,
  onError,
  maxRetries = 5,
  retryDelayMs = 2000,
}: UseJobEventsOptions): void {
  const retryCountRef = useRef(0);
  const retryTimeoutRef = useRef<number | null>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  // Calculate exponential backoff delay: 2s, 4s, 8s, 16s, 32s
  const calculateDelay = useCallback(
    (attempt: number) => {
      return retryDelayMs * Math.pow(2, attempt);
    },
    [retryDelayMs]
  );

  useEffect(() => {
    if (!enabled || !jobId) {
      return;
    }

    const connect = () => {
      const unsubscribe = subscribeToJobEvents(jobId, {
        onEvent: (payload) => {
          // Reset retry count on successful event
          retryCountRef.current = 0;
          onEvent(payload);
        },
        onError: (event) => {
          // Call user error handler
          onError?.(event);

          // Check if we should retry
          if (retryCountRef.current < maxRetries) {
            const delay = calculateDelay(retryCountRef.current);
            retryCountRef.current += 1;

            console.warn(
              `SSE connection error for job ${jobId}. ` +
                `Retry ${retryCountRef.current}/${maxRetries} in ${delay}ms`
            );

            // Schedule reconnection
            retryTimeoutRef.current = window.setTimeout(() => {
              // Clean up current connection
              if (unsubscribeRef.current) {
                unsubscribeRef.current();
              }
              // Reconnect
              const newUnsubscribe = connect();
              unsubscribeRef.current = newUnsubscribe;
            }, delay);
          } else {
            console.error(
              `SSE connection failed after ${maxRetries} retries for job ${jobId}`
            );
          }
        },
      });

      return unsubscribe;
    };

    // Initial connection
    const unsubscribe = connect();
    unsubscribeRef.current = unsubscribe;

    // Cleanup
    return () => {
      if (retryTimeoutRef.current !== null) {
        window.clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = null;
      }
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
      // Reset retry count on unmount
      retryCountRef.current = 0;
    };
  }, [enabled, jobId, onEvent, onError, maxRetries, calculateDelay]);
}
