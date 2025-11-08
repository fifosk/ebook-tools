"""
Dual-track audio build (approx timings, no interleaving).
Produces:
  audio/orig/<chunk>.mp3
  audio/trans/<chunk>.mp3
  timing/orig/<chunk>.timing.json
  timing/trans/<chunk>.timing.json
Each lane has its own timing; the frontend handles gating/mixing.
"""
from __future__ import annotations
import os, json, argparse
from typing import List, Dict, Any
from modules.core.rendering.timing_schema import (
    TrackTiming, SentenceTiming, WordTiming,
    validate_track, save_track_json, round_to_bucket
)

# ---- stubs ---------------------------------------------------------------

def synth_and_concat(sentences: List[Dict[str, Any]], out_path: str) -> float:
    """
    Stub for your TTS/concat layer: here we just sum declared durations.
    Replace with real synth + concat logic later.
    """
    total = sum(float(s["dur"]) for s in sentences)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, "wb").close()  # placeholder file
    return total

def char_weight_words(text: str, start: float, end: float) -> List[WordTiming]:
    """Distribute word spans by character weight inside [start,end]."""
    words = text.split()
    if not words:
        return []
    total_chars = sum(len(w) for w in words)
    span = max(end - start, 0.001)
    cursor = start
    out: List[WordTiming] = []
    for w in words:
        share = len(w) / total_chars
        dur = share * span
        s = cursor
        e = s + dur
        out.append(WordTiming(w=w, s=round_to_bucket(s), e=round_to_bucket(e)))
        cursor = e
    if out:
        out[-1].e = round_to_bucket(end)
    return out

def build_track(chunk_id: str, lang: str, policy: str, sr: int,
                lane: List[Dict[str, Any]]) -> TrackTiming:
    """Assemble a TrackTiming for one lane."""
    sents: List[SentenceTiming] = []
    cursor = 0.0
    for s in lane:
        sdur = float(s["dur"])
        start = round_to_bucket(cursor)
        end = round_to_bucket(cursor + sdur)
        words = char_weight_words(s["text"], start, end)
        sents.append(SentenceTiming(
            sid=int(s["sid"]), text=s["text"], start=start, end=end, words=words,
            approx_quality={"method":"char_weight","bucket_ms":10}
        ))
        cursor += sdur
    duration = round_to_bucket(cursor)
    return TrackTiming(chunk_id, lang, policy, sr, duration, sents)

# ---- main CLI ------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk-id", required=True)
    ap.add_argument("--orig-json", required=True)
    ap.add_argument("--trans-json", required=True)
    ap.add_argument("--out-audio-root", default="audio")
    ap.add_argument("--out-timing-root", default="timing")
    ap.add_argument("--lang-orig", default="xx")
    ap.add_argument("--lang-trans", default="yy")
    ap.add_argument("--sample-rate", type=int, default=22050)
    ap.add_argument("--policy", default="approx-char-weight")
    args = ap.parse_args()

    orig = json.load(open(args.orig_json, "r", encoding="utf-8"))
    trans = json.load(open(args.trans_json, "r", encoding="utf-8"))

    # build audio placeholders
    ao = os.path.join(args.out_audio_root, "orig", f"{args.chunk_id}.mp3")
    at = os.path.join(args.out_audio_root, "trans", f"{args.chunk_id}.mp3")
    synth_and_concat(orig, ao)
    synth_and_concat(trans, at)

    # build timing tracks
    tt_o = build_track(args.chunk_id, args.lang_orig, args.policy, args.sample_rate, orig)
    tt_t = build_track(args.chunk_id, args.lang_trans, args.policy, args.sample_rate, trans)
    validate_track(tt_o, tol_ms=80)
    validate_track(tt_t, tol_ms=80)

    # save JSON
    to = os.path.join(args.out_timing_root, "orig", f"{args.chunk_id}.timing.json")
    tt = os.path.join(args.out_timing_root, "trans", f"{args.chunk_id}.timing.json")
    os.makedirs(os.path.dirname(to), exist_ok=True)
    os.makedirs(os.path.dirname(tt), exist_ok=True)
    save_track_json(tt_o, to)
    save_track_json(tt_t, tt)

    print(json.dumps({
        "chunk": args.chunk_id,
        "audio": {"orig": ao, "trans": at},
        "timing": {"orig": to, "trans": tt},
        "durations": {"orig": tt_o.duration, "trans": tt_t.duration}
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
