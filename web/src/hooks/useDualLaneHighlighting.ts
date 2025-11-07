import { useEffect } from 'react';
import type { Mode } from '../types/timing';
import { useGateStore } from '../stores/gateStore';

type ControllerBridge = {
  startAt: (idx: number) => void;
  stop: () => void;
  setAudios: (o?: HTMLAudioElement | null, t?: HTMLAudioElement | null) => void;
  setMode: (mode: Mode) => void;
  onWordChange?: (lane: 'orig' | 'trans', wordIdx: number | null) => void;
  onGateChange?: (slideIdx: number, phase: 'idle' | 'running' | 'ended') => void;
};

export function useDualLaneHighlighting(controller: ControllerBridge | null | undefined) {
  const { mode, slides, activeSlideIdx, setLaneWord } = useGateStore();

  useEffect(() => {
    if (!controller) {
      return;
    }
    controller.setMode(mode);
  }, [controller, mode]);

  useEffect(() => {
    if (!controller) {
      return;
    }
    controller.onWordChange = (lane, idx) => setLaneWord(lane, idx);
  }, [controller, setLaneWord]);

  useEffect(() => {
    if (!controller || !slides.length) {
      return;
    }
    controller.startAt(activeSlideIdx);
    return () => controller.stop();
  }, [controller, slides, activeSlideIdx]);
}
