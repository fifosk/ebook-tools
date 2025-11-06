import { useCallback, useEffect, useRef, useState } from 'react';
import type { Hit, TimingPayload } from '../types/timing';
import { timingStore } from '../stores/timingStore';

interface HighlightState {
  current: Hit | null;
  payload?: TimingPayload;
}

export interface UseWordHighlightingResult {
  current: Hit | null;
  isSeeking: boolean;
  setSeeking: (value: boolean) => void;
  setFence: (segId: string, tokIndex: number) => void;
}

const INVALID_INDEX = -1;

export function useWordHighlighting(): UseWordHighlightingResult {
  const [state, setState] = useState<HighlightState>({
    current: null,
    payload: timingStore.get().payload,
  });
  const [isSeeking, setIsSeeking] = useState(false);

  const fencesRef = useRef<Map<string, number>>(new Map());
  const seekingRef = useRef(false);
  const payloadRef = useRef<TimingPayload | undefined>(timingStore.get().payload);
  const lastSegIdRef = useRef<string | null>(null);

  useEffect(() => {
    const unsubscribe = timingStore.subscribe((nextState) => {
      const { payload, last } = nextState;

      if (payloadRef.current !== payload) {
        payloadRef.current = payload;
        fencesRef.current.clear();
        lastSegIdRef.current = null;
      }

      if (!payload || !payload.segments.length || !last || last.segIndex < 0) {
        setState((prev) => {
          if (prev.current === null && prev.payload === payload) {
            return prev;
          }
          return { current: null, payload };
        });
        return;
      }

      const segment = payload.segments[last.segIndex];
      if (!segment) {
        setState((prev) => {
          if (prev.current === null && prev.payload === payload) {
            return prev;
          }
          return { current: null, payload };
        });
        return;
      }

      const segId = segment.id;
      const fences = fencesRef.current;

      let tokIndex = last.tokIndex;
      if (!Number.isFinite(tokIndex) || tokIndex < 0) {
        tokIndex = 0;
      } else {
        tokIndex = Math.floor(tokIndex);
      }

      const fence = fences.get(segId);
      if (seekingRef.current) {
        fences.set(segId, tokIndex);
        seekingRef.current = false;
        setIsSeeking(false);
      } else if (fence !== undefined && fence > tokIndex) {
        tokIndex = fence;
      } else if (tokIndex > (fence ?? INVALID_INDEX)) {
        fences.set(segId, tokIndex);
      }

      lastSegIdRef.current = segId;

      const nextHit: Hit = { segIndex: last.segIndex, tokIndex };
      setState((prev) => {
        const sameHit =
          prev.current &&
          prev.current.segIndex === nextHit.segIndex &&
          prev.current.tokIndex === nextHit.tokIndex &&
          prev.payload === payload;
        if (sameHit) {
          return prev;
        }
        return {
          current: nextHit,
          payload,
        };
      });
    });
    return () => {
      unsubscribe();
    };
  }, []);

  const setSeeking = useCallback((value: boolean) => {
    seekingRef.current = value;
    setIsSeeking(value);
    if (value) {
      fencesRef.current.clear();
    }
  }, []);

  const setFence = useCallback((segId: string, tokIndex: number) => {
    if (!segId) {
      return;
    }
    const normalized = Number.isFinite(tokIndex) ? Math.max(0, Math.floor(tokIndex)) : 0;
    const fences = fencesRef.current;
    const prev = fences.get(segId) ?? INVALID_INDEX;
    if (normalized <= prev) {
      return;
    }
    fences.set(segId, normalized);
    setState((currentState) => {
      if (
        currentState.current &&
        payloadRef.current?.segments[currentState.current.segIndex]?.id === segId &&
        normalized > currentState.current.tokIndex
      ) {
        return {
          current: {
            segIndex: currentState.current.segIndex,
            tokIndex: normalized,
          },
          payload: currentState.payload,
        };
      }
      return currentState;
    });
  }, []);

  return {
    current: state.current,
    isSeeking,
    setSeeking,
    setFence,
  };
}
