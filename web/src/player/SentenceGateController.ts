import type { Slide, Mode, SentT } from '../types/timing';

export type Lane = 'orig' | 'trans';
export type GatePhase = 'idle' | 'running' | 'ended';

export type ControllerOpts = {
  mode: Mode;
  slides: Slide[];
  playback: {
    origAudio?: HTMLAudioElement | null;
    transAudio?: HTMLAudioElement | null;
  };
  onWordChange?: (lane: Lane, wordIdx: number | null) => void;
  onGateChange?: (slideIdx: number, phase: GatePhase) => void;
};

export class SentenceGateController {
  private slides: Slide[];
  private mode: Mode;
  private orig?: HTMLAudioElement | null;
  private trans?: HTMLAudioElement | null;
  private idx = 0;
  private rafId: number | null = null;
  private phase: GatePhase = 'idle';
  private origEndedHandler: (() => void) | null = null;

  constructor(opts: ControllerOpts) {
    this.slides = opts.slides;
    this.mode = opts.mode;
    this.orig = opts.playback.origAudio ?? null;
    this.trans = opts.playback.transAudio ?? null;
    this.onWordChange = opts.onWordChange;
    this.onGateChange = opts.onGateChange;
  }

  onWordChange?: (lane: Lane, wordIdx: number | null) => void;
  onGateChange?: (slideIdx: number, phase: GatePhase) => void;

  setMode(m: Mode) {
    this.mode = m;
  }

  setAudios(orig?: HTMLAudioElement | null, trans?: HTMLAudioElement | null) {
    if (this.orig && this.origEndedHandler) {
      this.orig.removeEventListener('ended', this.origEndedHandler);
      this.origEndedHandler = null;
    }
    this.orig = orig ?? null;
    this.trans = trans ?? null;
  }

  private seekSentence(lane: Lane, s?: SentT) {
    const audio = lane === 'orig' ? this.orig : this.trans;
    if (audio && s) {
      audio.currentTime = s.start;
    }
  }

  private activeWordIdx(s: SentT | undefined, tSec: number): number | null {
    if (!s?.words?.length) {
      return null;
    }
    const hit = s.words.findIndex((w) => tSec >= w.s && tSec < w.e);
    if (hit >= 0) {
      return hit;
    }
    const lastWord = s.words.length ? s.words[s.words.length - 1] : undefined;
    if (tSec >= (lastWord?.e ?? s.end)) {
      return s.words.length - 1;
    }
    return null;
  }

  private playTrans(slide: Slide) {
    if (!this.trans || !slide.trans) {
      return;
    }
    this.trans.currentTime = slide.trans.start;
    void this.trans.play();
  }

  private playSequential(slide: Slide) {
    if (this.mode === 'trans-only' || !this.orig || !slide.orig) {
      this.playTrans(slide);
      return;
    }
    const orig = this.orig;
    const handleEnded = () => {
      orig.removeEventListener('ended', handleEnded);
      if (this.origEndedHandler === handleEnded) {
        this.origEndedHandler = null;
      }
      this.playTrans(slide);
    };
    this.origEndedHandler = handleEnded;
    orig.addEventListener('ended', handleEnded);
    orig.currentTime = slide.orig.start;
    void orig.play();
  }

  startAt(idx = 0) {
    this.stop();
    this.idx = Math.min(idx, this.slides.length - 1);
    const slide = this.slides[this.idx];
    this.seekSentence('orig', slide.orig);
    this.seekSentence('trans', slide.trans);
    this.playSequential(slide);

    this.phase = 'running';
    this.onGateChange?.(this.idx, 'running');

    const loop = () => {
      const currentSlide = this.slides[this.idx];
      if (!currentSlide) {
        return;
      }

      if (currentSlide.orig && this.orig) {
        const t = Math.min(this.orig.currentTime, currentSlide.orig.end);
        this.onWordChange?.('orig', this.activeWordIdx(currentSlide.orig, t));
      }
      if (currentSlide.trans && this.trans) {
        const t = Math.min(this.trans.currentTime, currentSlide.trans.end);
        this.onWordChange?.('trans', this.activeWordIdx(currentSlide.trans, t));
      }

      const origDone =
        this.mode === 'trans-only' ||
        !currentSlide.orig ||
        !this.orig ||
        this.orig.currentTime >= (currentSlide.orig?.end ?? 0) - 0.01;
      const transDone =
        !currentSlide.trans ||
        !this.trans ||
        this.trans.currentTime >= (currentSlide.trans?.end ?? 0) - 0.01;

      if (origDone && transDone) {
        this.onGateChange?.(this.idx, 'ended');
        this.next();
        return;
      }
      this.rafId = typeof window !== 'undefined' ? window.requestAnimationFrame(loop) : null;
    };

    this.rafId = typeof window !== 'undefined' ? window.requestAnimationFrame(loop) : null;
  }

  next() {
    this.stopAudios();
    if (++this.idx >= this.slides.length) {
      this.phase = 'ended';
      this.onGateChange?.(this.idx, 'ended');
      return;
    }
    this.startAt(this.idx);
  }

  private stopAudios() {
    if (this.orig && this.origEndedHandler) {
      this.orig.removeEventListener('ended', this.origEndedHandler);
      this.origEndedHandler = null;
    }
    this.orig?.pause?.();
    this.trans?.pause?.();
  }

  stop() {
    if (this.rafId != null && typeof window !== 'undefined') {
      window.cancelAnimationFrame(this.rafId);
    }
    this.rafId = null;
    this.stopAudios();
    this.phase = 'idle';
  }
}
