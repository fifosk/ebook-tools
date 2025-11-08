from __future__ import annotations
import argparse, json, sys
from modules.core.rendering.timing_schema import TrackTiming, SentenceTiming, WordTiming, validate_track

def load_track(path: str) -> TrackTiming:
    """Light loader that rehydrates dataclasses from JSON."""
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    sentences = []
    for s in obj.get("sentences", []):
        words = [WordTiming(**w) for w in s.get("words", [])]
        sentences.append(SentenceTiming(
            sid=s["sid"], text=s["text"], start=s["start"], end=s["end"],
            words=words, approx_quality=s.get("approx_quality")
        ))
    return TrackTiming(
        chunk_id=obj["chunk_id"],
        lang=obj["lang"],
        policy=obj["policy"],
        sample_rate=obj.get("sample_rate", 22050),
        duration=obj["duration"],
        sentences=sentences,
        qa=obj.get("qa")
    )

def main():
    ap = argparse.ArgumentParser(description="Validate per-track timing JSON files.")
    ap.add_argument("paths", nargs="+", help="*.timing.json files to validate")
    ap.add_argument("--tol-ms", type=int, default=80)
    args = ap.parse_args()
    ok = True
    for p in args.paths:
        try:
            t = load_track(p)
            validate_track(t, tol_ms=args.tol_ms)
            print(f"OK  {p}  duration={t.duration:.3f}s  sentences={len(t.sentences)}")
        except Exception as e:
            ok = False
            print(f"ERR {p}: {e}", file=sys.stderr)
    sys.exit(0 if ok else 2)

if __name__ == "__main__":
    main()
