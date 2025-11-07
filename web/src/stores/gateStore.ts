import { create } from "zustand";
import type { Mode, Slide } from "@/types/timing";

type GateState = {
  mode: Mode;
  slides: Slide[];
  activeSlideIdx: number;
  laneWordIdx: { orig: number | null; trans: number | null };
  setMode: (m: Mode) => void;
  setSlides: (s: Slide[]) => void;
  setActiveSlide: (i: number) => void;
  setLaneWord: (lane: "orig" | "trans", idx: number | null) => void;
};

export const useGateStore = create<GateState>((set) => ({
  mode: "orig+trans",
  slides: [],
  activeSlideIdx: 0,
  laneWordIdx: { orig: null, trans: null },
  setMode: (m) => set({ mode: m }),
  setSlides: (slides) => set({ slides }),
  setActiveSlide: (i) => set({ activeSlideIdx: i }),
  setLaneWord: (lane, idx) =>
    set((s) => ({ laneWordIdx: { ...s.laneWordIdx, [lane]: idx } })),
}));
