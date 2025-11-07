import type { Slide, Mode, SentT } from "@/types/timing";

export type Lane = "orig" | "trans";
export type GatePhase = "idle" | "running" | "ended";

export type ControllerOpts = {
  mode: Mode;
  slides: Slide[];
  playback: {
    origAudio?: HTMLAudioElement | null;
    transAudio?: HTMLAudioElement | null;
    simultaneous?: boolean; // false => sequential orig→trans
  };
  onWordChange?: (lane: Lane, wordIdx: number | null) => void;
  onGateChange?: (slideIdx: number, phase: GatePhase) => void;
};

export class SentenceGateController {
  private slides: Slide[];
  private mode: Mode;
  private orig?: HTMLAudioElement | null;
  private trans?: HTMLAudioElement | null;
  private simultaneous: boolean;
  private idx = 0;
  private rafId: number | null = null;
  private phase: GatePhase = "idle";

  constructor(opts: ControllerOpts) {
    this.slides = opts.slides;
    this.mode = opts.mode;
    this.orig = opts.playback.origAudio ?? null;
    this.trans = opts.playback.transAudio ?? null;
    this.simultaneous = !!opts.playback.simultaneous;
    this.onWordChange = opts.onWordChange;
    this.onGateChange = opts.onGateChange;
  }

  onWordChange?: (lane: Lane, wordIdx: number | null) => void;
  onGateChange?: (slideIdx: number, phase: GatePhase) => void;

  setMode(m: Mode) { this.mode = m; }
  setSimultaneous(b: boolean) { this.simultaneous = b; }
  setAudios(orig?: HTMLAudioElement | null, trans?: HTMLAudioElement | null) {
    this.orig = orig ?? null; this.trans = trans ?? null;
  }

  private seekSentence(lane: Lane, s?: SentT) {
    const a = lane === "orig" ? this.orig : this.trans;
    if (a && s) a.currentTime = s.start;
  }

  private activeWordIdx(s: SentT | undefined, tSec: number): number | null {
    if (!s?.words?.length) return null;
    const i = s.words.findIndex(w => tSec >= w.s && tSec < w.e);
    if (i >= 0) return i;
    if (tSec >= (s.words.at(-1)?.e ?? s.end)) return s.words.length - 1;
    return null;
  }

  startAt(idx = 0) {
    this.stop();
    this.idx = Math.min(idx, this.slides.length - 1);
    const sl = this.slides[this.idx];
    this.seekSentence("orig", sl.orig);
    this.seekSentence("trans", sl.trans);

    // playback control
    if (this.mode === "trans-only") {
      this.trans?.play?.();
    } else if (this.simultaneous) {
      this.orig?.play?.();
      this.trans?.play?.();
    } else {
      const o = this.orig, t = this.trans;
      if (o && sl.orig) {
        o.currentTime = sl.orig.start;
        o.play();
        const onTime = () => {
          if (o.currentTime >= sl.orig!.end - 0.01) {
            o.removeEventListener("timeupdate", onTime);
            if (t && sl.trans) {
              t.currentTime = sl.trans.start;
              t.play();
            }
          }
        };
        o.addEventListener("timeupdate", onTime);
      } else if (t && sl.trans) {
        t.currentTime = sl.trans.start;
        t.play();
      }
    }

    this.phase = "running";
    this.onGateChange?.(this.idx, "running");

    const loop = () => {
      const sl = this.slides[this.idx];
      if (!sl) return;

      if (sl.orig && this.orig) {
        const t = Math.min(this.orig.currentTime, sl.orig.end);
        this.onWordChange?.("orig", this.activeWordIdx(sl.orig, t));
      }
      if (sl.trans && this.trans) {
        const t = Math.min(this.trans.currentTime, sl.trans.end);
        this.onWordChange?.("trans", this.activeWordIdx(sl.trans, t));
      }

      const origDone = !sl.orig || !this.orig || this.orig.currentTime >= (sl.orig?.end ?? 0) - 0.01;
      const transDone = !sl.trans || !this.trans || this.trans.currentTime >= (sl.trans?.end ?? 0) - 0.01;
      const gateDone = this.mode === "trans-only"
        ? transDone
        : this.simultaneous ? (origDone && transDone) : transDone;

      if (gateDone) {
        this.onGateChange?.(this.idx, "ended");
        this.next();
        return;
      }
      this.rafId = requestAnimationFrame(loop);
    };
    this.rafId = requestAnimationFrame(loop);
  }

  next() {
    this.stopAudios();
    if (++this.idx >= this.slides.length) {
      this.phase = "ended";
      this.onGateChange?.(this.idx, "ended");
      return;
    }
    this.startAt(this.idx);
  }

  stopAudios() { this.orig?.pause?.(); this.trans?.pause?.(); }
  stop() {
    if (this.rafId != null) cancelAnimationFrame(this.rafId);
    this.stopAudios();
    this.phase = "idle";
  }
}
