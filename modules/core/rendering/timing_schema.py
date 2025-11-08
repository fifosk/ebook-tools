from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import json

@dataclass
class WordTiming:
    w: str
    s: float
    e: float

@dataclass
class SentenceTiming:
    sid: int
    text: str
    start: float
    end: float
    words: List[WordTiming]
    approx_quality: Optional[Dict[str, Any]] = None

@dataclass
class TrackTiming:
    chunk_id: str
    lang: str
    policy: str
    sample_rate: int
    duration: float
    sentences: List[SentenceTiming]
    qa: Optional[Dict[str, Any]] = None

    def to_json(self) -> str:
        """Return compact JSON string."""
        return json.dumps(asdict(self), ensure_ascii=False, separators=(",", ":"))

# --- helpers ---------------------------------------------------------------

def round_to_bucket(x: float, bucket_ms: int = 10) -> float:
    """Round seconds to the nearest millisecond bucket."""
    return round(x * 1000.0 / bucket_ms) * bucket_ms / 1000.0

def validate_track(t: TrackTiming, tol_ms: int = 50) -> None:
    """Basic monotonicity & duration check."""
    for s in t.sentences:
        assert s.start <= s.end, f"Sentence {s.sid}: start > end"
        prev_end = s.start
        for i, w in enumerate(s.words):
            assert w.s <= w.e, f"Word overlap in sentence {s.sid} idx {i}"
            assert w.s >= prev_end - 1e-6, f"Non-monotonic word timing in sentence {s.sid}"
            prev_end = w.e
    last_end = max((s.end for s in t.sentences), default=0.0)
    diff_ms = abs((t.duration - last_end) * 1000.0)
    assert diff_ms <= tol_ms, f"Duration mismatch {diff_ms:.1f} ms > {tol_ms} ms"

def save_track_json(track: TrackTiming, path: str) -> None:
    """Write TrackTiming to disk as JSON."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(track.to_json())
