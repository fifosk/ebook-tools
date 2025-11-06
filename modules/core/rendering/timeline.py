"""Lightweight helpers shared by rendering metadata builders."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def build_word_events(meta: Mapping[str, Any] | None) -> list[dict[str, float | str]]:
    """
    Build token timeline events from ``meta["word_tokens"]``.

    Expects an iterable of dicts containing ``text``, ``start``, and ``end`` keys.
    Values are rounded to three decimals to keep payloads compact.
    """

    if not isinstance(meta, Mapping):
        return []

    tokens: Sequence[Mapping[str, Any]] | None = meta.get("word_tokens")  # type: ignore[assignment]
    if not isinstance(tokens, Sequence):
        return []

    events: list[dict[str, float | str]] = []
    for token in tokens:
        if not isinstance(token, Mapping):
            continue
        text = token.get("text")
        start = token.get("start")
        end = token.get("end")
        if text is None or start is None or end is None:
            continue
        try:
            t0 = round(float(start), 3)
            t1 = round(float(end), 3)
        except (TypeError, ValueError):
            continue
        events.append({"token": str(text), "t0": t0, "t1": t1})
    return events


__all__ = ["build_word_events"]
