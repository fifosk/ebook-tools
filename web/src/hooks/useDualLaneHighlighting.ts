import { useEffect } from "react";
import type { Mode } from "@/types/timing";
import { useGateStore } from "@/stores/gateStore";

export function useDualLaneHighlighting(controller: {
  startAt: (idx: number) => void;
  stop: () => void;
  setAudios: (o?: HTMLAudioElement | null, t?: HTMLAudioElement | null) => void;
  setMode: (m: Mode) => void;
  setSimultaneous: (b: boolean) => void;
  onWordChange?: (lane: "orig" | "trans", wordIdx: number | null) => void;
  onGateChange?: (slideIdx: number, phase: "idle" | "running" | "ended") => void;
}) {
  const { mode, slides, activeSlideIdx, setLaneWord } = useGateStore();

  // keep controller in sync with store mode
  useEffect(() => {
    controller.setMode(mode);
  }, [mode]);

  // wire word updates to store
  useEffect(() => {
    controller.onWordChange = (lane, idx) => setLaneWord(lane, idx);
  }, [setLaneWord]);

  // start controller when slides change
  useEffect(() => {
    if (!slides.length) return;
    controller.startAt(activeSlideIdx);
    return () => controller.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slides, activeSlideIdx]);
}
