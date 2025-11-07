import React, { useEffect, useMemo, useRef } from "react";
import type { TrackTiming } from "@/types/timing";
import { buildSlides } from "@/utils/buildSlides";
import { useGateStore } from "@/stores/gateStore";
import { SentenceGateController } from "@/player/SentenceGateController";
import { useDualLaneHighlighting } from "@/hooks/useDualLaneHighlighting";

type Props = {
  origTiming: TrackTiming;
  transTiming: TrackTiming;
  origAudioSrc: string;
  transAudioSrc: string;
};

export default function DualLaneSandbox({ origTiming, transTiming, origAudioSrc, transAudioSrc }: Props) {
  const origRef = useRef<HTMLAudioElement>(null);
  const transRef = useRef<HTMLAudioElement>(null);
  const controllerRef = useRef<SentenceGateController>();
  const { setSlides, laneWordIdx, mode, setMode } = useGateStore();

  const slides = useMemo(
    () =>
      buildSlides(origTiming, transTiming, {
        strategy: "lane-longer",
        pauseMs: 250,
        scale: 1,
      }),
    [origTiming, transTiming]
  );

  useEffect(() => setSlides(slides), [slides, setSlides]);

  useEffect(() => {
    controllerRef.current = new SentenceGateController({
      mode,
      slides,
      playback: {
        origAudio: origRef.current,
        transAudio: transRef.current,
        simultaneous: false,
      },
    });
    return () => controllerRef.current?.stop();
  }, [mode, slides]);

  useEffect(() => {
    controllerRef.current?.setAudios(origRef.current, transRef.current);
  }, [origRef.current, transRef.current]);

  useDualLaneHighlighting(controllerRef.current!);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-3">
        <button
          className="px-3 py-1 rounded bg-gray-200"
          onClick={() => setMode(mode === "orig+trans" ? "trans-only" : "orig+trans")}
        >
          Mode: {mode}
        </button>
        <button
          className="px-3 py-1 rounded bg-gray-200"
          onClick={() => controllerRef.current?.startAt(0)}
        >
          Restart
        </button>
      </div>

      <audio ref={origRef} src={origAudioSrc} preload="auto" />
      <audio ref={transRef} src={transAudioSrc} preload="auto" />

      <div className="grid grid-cols-2 gap-6">
        <div>
          <h3 className="font-semibold mb-2">Original</h3>
          {slides.map((sl) => (
            <p key={sl.idx} className="mb-2">
              {(sl.orig?.words ?? []).map((w, i) => {
                const active = i === laneWordIdx.orig;
                const revealed = (laneWordIdx.orig ?? -1) >= i;
                return (
                  <span
                    key={i}
                    className={
                      active
                        ? "bg-yellow-200"
                        : revealed
                        ? "opacity-100"
                        : "opacity-50"
                    }
                  >
                    {" "}{w.w}
                  </span>
                );
              })}
            </p>
          ))}
        </div>
        <div>
          <h3 className="font-semibold mb-2">Translation</h3>
          {slides.map((sl) => (
            <p key={sl.idx} className="mb-2">
              {(sl.trans?.words ?? []).map((w, i) => {
                const active = i === laneWordIdx.trans;
                const revealed = (laneWordIdx.trans ?? -1) >= i;
                return (
                  <span
                    key={i}
                    className={
                      active
                        ? "bg-yellow-200"
                        : revealed
                        ? "opacity-100"
                        : "opacity-50"
                    }
                  >
                    {" "}{w.w}
                  </span>
                );
              })}
            </p>
          ))}
        </div>
      </div>

      <p className="text-sm text-gray-500">
        Demo note: this sandbox highlights live word progress per lane; integrate activeSlideIdx later
        for gated slides.
      </p>
    </div>
  );
}
