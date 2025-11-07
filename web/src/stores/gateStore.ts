import { create } from 'zustand';
import type { Mode, Slide } from '../types/timing';

type Lane = 'orig' | 'trans';

type GateState = {
  mode: Mode;
  slides: Slide[];
  activeSlideIdx: number;
  laneWordIdx: { orig: number | null; trans: number | null };
  setMode: (m: Mode) => void;
  setSlides: (slides: Slide[]) => void;
  setActiveSlide: (idx: number) => void;
  setLaneWord: (lane: Lane, idx: number | null) => void;
};

export const useGateStore = create<GateState>()((set) => ({
  mode: 'orig+trans+translit',
  slides: [],
  activeSlideIdx: 0,
  laneWordIdx: { orig: null, trans: null },
  setMode: (mode: Mode) => set({ mode }),
  setSlides: (slides: Slide[]) => set({ slides }),
  setActiveSlide: (activeSlideIdx: number) => set({ activeSlideIdx }),
  setLaneWord: (lane: Lane, idx: number | null) =>
    set((state: GateState) => ({ laneWordIdx: { ...state.laneWordIdx, [lane]: idx } })),
}));
