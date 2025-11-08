import type { TrackTiming, Slide, SentT } from '../types/timing';

export type GateStrategy = "lane-longer" | "lane-shorter" | "fixed";
export type BuildSlidesOpts = {
  strategy: GateStrategy;
  fixedSeconds?: number;   // for "fixed"
  pauseMs?: number;        // padding between slides
  scale?: number;          // optional multiplier
};

function span(s?: SentT): number {
  return s ? Math.max(0, s.end - s.start) : 0;
}

function estimateGate(
  o?: SentT,
  t?: SentT,
  strategy: GateStrategy = "lane-longer",
  fixedSeconds?: number,
  scale = 1
): number {
  const so = span(o), st = span(t);
  let base = 0;
  if (strategy === "fixed" && fixedSeconds && fixedSeconds > 0) base = fixedSeconds;
  else if (strategy === "lane-shorter") base = Math.min(so || Infinity, st || Infinity);
  else base = Math.max(so, st); // default: longer
  if (!isFinite(base)) base = so || st || 0;
  return Math.max(0.01, base * (scale || 1));
}

export function buildSlides(
  orig: TrackTiming | null,
  trans: TrackTiming | null,
  opts: BuildSlidesOpts,
  translit?: TrackTiming | null
): Slide[] {
  const n = Math.max(orig?.sentences.length || 0, trans?.sentences.length || 0);
  const slides: Slide[] = [];
  let cursor = 0;
  for (let i = 0; i < n; i++) {
    const o = orig?.sentences[i];
    const t = trans?.sentences[i];
    const xl = translit?.sentences[i];
    const dur = estimateGate(o, t, opts.strategy, opts.fixedSeconds, opts.scale ?? 1);
    slides.push({
      idx: i,
      orig: o,
      trans: t,
      translit: xl,
      gate: { start: cursor, end: cursor + dur },
    });
    cursor += dur + (opts.pauseMs ?? 0) / 1000;
  }
  return slides;
}
