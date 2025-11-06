import { useCallback, useRef, useState } from 'react';
import type { MutableRefObject } from 'react';
import type { PlayerCoreHandle } from '../player/PlayerCore';

export interface UsePlayerCoreResult {
  ref: (instance: PlayerCoreHandle | null) => void;
  core: PlayerCoreHandle | null;
  ready: boolean;
  handleRef: MutableRefObject<PlayerCoreHandle | null>;
  elementRef: MutableRefObject<HTMLAudioElement | null>;
  mediaRef: (element: HTMLAudioElement | null) => void;
}

export function usePlayerCore(): UsePlayerCoreResult {
  const handleRef = useRef<PlayerCoreHandle | null>(null);
  const elementRef = useRef<HTMLAudioElement | null>(null);
  const [core, setCore] = useState<PlayerCoreHandle | null>(null);

  const attachHandle = useCallback((instance: PlayerCoreHandle | null) => {
    handleRef.current = instance;
    setCore(instance);
  }, []);

  const attachMedia = useCallback((element: HTMLAudioElement | null) => {
    elementRef.current = element;
  }, []);

  return {
    ref: attachHandle,
    core,
    ready: core !== null,
    handleRef,
    elementRef,
    mediaRef: attachMedia,
  };
}
