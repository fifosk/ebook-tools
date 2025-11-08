import React, { useEffect, useMemo, useRef } from 'react';
import type { TrackTiming, Slide, Mode } from '../../types/timing';
import { buildSlides } from '../../utils/buildSlides';
import { useGateStore } from '../../stores/gateStore';
import { SentenceGateController } from '../../player/SentenceGateController';
import { useDualLaneHighlighting } from '../../hooks/useDualLaneHighlighting';

type Props = {
  origTiming: TrackTiming;
  transTiming: TrackTiming;
  translitTiming?: TrackTiming | null;
  origAudioSrc: string;
  transAudioSrc: string;
};

export default function DualLaneSandbox({
  origTiming,
  transTiming,
  translitTiming,
  origAudioSrc,
  transAudioSrc,
}: Props) {
  const origRef = useRef<HTMLAudioElement>(null);
  const transRef = useRef<HTMLAudioElement>(null);
  const controllerRef = useRef<SentenceGateController>();
  const { setSlides, laneWordIdx, mode, setMode } = useGateStore();

  const slides = useMemo<Slide[]>(
    () =>
      buildSlides(
        origTiming,
        transTiming,
        {
          strategy: 'lane-longer',
          pauseMs: 250,
          scale: 1,
        },
        translitTiming ?? null
      ),
    [origTiming, transTiming, translitTiming]
  );

  useEffect(() => setSlides(slides), [slides, setSlides]);

  useEffect(() => {
    if (!translitTiming && mode === 'orig+trans+translit') {
      setMode('orig+trans');
    }
  }, [mode, setMode, translitTiming]);

  useEffect(() => {
    controllerRef.current = new SentenceGateController({
      mode,
      slides,
      playback: {
        origAudio: origRef.current,
        transAudio: transRef.current,
      },
    });
    return () => controllerRef.current?.stop();
  }, [mode, slides]);

  useEffect(() => {
    controllerRef.current?.setAudios(origRef.current, transRef.current);
  }, [origAudioSrc, transAudioSrc]);

  useDualLaneHighlighting(controllerRef.current);

  const cycleMode = () => {
    const order: Mode[] = translitTiming
      ? ['orig+trans+translit', 'orig+trans', 'trans-only']
      : ['orig+trans', 'trans-only'];
    const idx = order.indexOf(mode);
    if (idx === -1) {
      setMode(order[0]);
      return;
    }
    const next = order[(idx + 1) % order.length];
    setMode(next);
  };

  const showTranslit = mode === 'orig+trans+translit' && Boolean(translitTiming);
  const gridCols = showTranslit ? 'grid-cols-3' : 'grid-cols-2';

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-3">
        <button
          className="px-3 py-1 rounded bg-gray-200"
          onClick={cycleMode}
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

      <div className={`grid ${gridCols} gap-6`}>
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
                        ? 'bg-yellow-200'
                        : revealed
                        ? 'opacity-100'
                        : 'opacity-50'
                    }
                  >
                    {' '}
                    {w.w}
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
                        ? 'bg-yellow-200'
                        : revealed
                        ? 'opacity-100'
                        : 'opacity-50'
                    }
                  >
                    {' '}
                    {w.w}
                  </span>
                );
              })}
            </p>
          ))}
        </div>
        {showTranslit ? (
          <div>
            <h3 className="font-semibold mb-2">Transliteration</h3>
            {slides.map((sl) => (
              <p key={sl.idx} className="mb-2">
                {(sl.translit?.words ?? []).map((w, i) => {
                  const active = i === laneWordIdx.trans;
                  const revealed = (laneWordIdx.trans ?? -1) >= i;
                  return (
                    <span
                      key={i}
                      className={
                        active
                          ? 'bg-yellow-200'
                          : revealed
                          ? 'opacity-100'
                          : 'opacity-50'
                      }
                    >
                      {' '}
                      {w.w}
                    </span>
                  );
                })}
              </p>
            ))}
          </div>
        ) : null}
      </div>

      <p className="text-sm text-gray-500">
        Demo note: this sandbox highlights live word progress per lane; integrate activeSlideIdx later
        for gated slides.
      </p>
    </div>
  );
}
