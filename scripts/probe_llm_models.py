#!/usr/bin/env python3
"""
Probe every available LLM model against sample-language translation and JSON
batch requests to surface compatibility debt.

What it checks per model:
  * Translation probes: EN→FR (Latin), EN→AR (RTL), EN→HI (Devanagari),
    EN→ZH (CJK). Records output correctness hints.
  * Structured JSON batch probe: matches the actual `make_sentence_payload`
    shape used by `modules/translation_batch.py`. Flags models that:
      - wrap JSON in markdown fences
      - emit <think>...</think> prefixes
      - return non-JSON prose
      - silently drop the `items` key
      - time out or return empty on the configured timeout
      - require `format=json` native JSON mode, but the Ollama
        chat/completions endpoint doesn't wire it through for that model

The output is a Markdown report (stdout + optional --out file) listing:
    tier | model | translation pass/fail per lang | JSON pass | debt notes

Usage:
    python scripts/probe_llm_models.py                       # all models
    python scripts/probe_llm_models.py --models deepseek-v3.2 gemma4:31b
    python scripts/probe_llm_models.py --timeout 90 --out report.md
    python scripts/probe_llm_models.py --only-cloud

Exit codes:
    0 — all probed models completed (even if some failed probes; failures are
        recorded in the report rather than crashing the run).
    1 — probe harness crashed (network / config / import error).

Run from the repo root with the venv active, or via Docker exec:
    docker exec ebook-tools-backend python3 /app/scripts/probe_llm_models.py --out /app/storage/llm_probe_report.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules import llm_batch, prompt_templates  # noqa: E402
from modules import config_manager as cfg  # noqa: E402
from modules.llm_client import create_client  # noqa: E402
from modules.llm_providers import (  # noqa: E402
    LMSTUDIO_MACBOOK,
    LMSTUDIO_MACSTUDIO,
    LMSTUDIO_PROVIDERS,
    split_llm_model_identifier,
)
from modules.services.llm_models import (  # noqa: E402
    _model_quality_tier,
    list_available_llm_models,
)


# Provider display labels and ordering for the per-host breakdown section. The
# probe report groups results by these tags so the user can compare both LM
# Studio destinations head-to-head.
_PROVIDER_DISPLAY = {
    "ollama_cloud": "Ollama Cloud",
    "ollama_local": "Ollama Local",
    LMSTUDIO_MACSTUDIO: "LM Studio – Mac Studio",
    LMSTUDIO_MACBOOK: "LM Studio – MacBook Pro",
    "lmstudio_local": "LM Studio – Mac Studio (legacy tag)",
}
_PROVIDER_ORDER = [
    "ollama_cloud",
    "ollama_local",
    LMSTUDIO_MACSTUDIO,
    LMSTUDIO_MACBOOK,
    "lmstudio_local",
]


# ---------------------------------------------------------------------------
# Probe definitions
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class TranslationProbe:
    """A single translation probe: source sentence + target language."""

    code: str
    language: str
    sentence: str
    # Heuristic set of characters that should appear in a correct translation.
    # We use unicode ranges rather than exact strings because translations vary.
    expected_script_range: tuple[str, str]

    def script_hit(self, text: str) -> bool:
        lo, hi = self.expected_script_range
        return any(lo <= ch <= hi for ch in text)


TRANSLATION_PROBES: List[TranslationProbe] = [
    TranslationProbe(
        code="fr",
        language="French",
        sentence="The cat sat on the mat and watched the birds.",
        expected_script_range=("\u0041", "\u007a"),  # Latin-only — script_hit always True
    ),
    TranslationProbe(
        code="ar",
        language="Arabic",
        sentence="The cat sat on the mat and watched the birds.",
        expected_script_range=("\u0600", "\u06ff"),  # Arabic block
    ),
    TranslationProbe(
        code="hi",
        language="Hindi",
        sentence="The cat sat on the mat and watched the birds.",
        expected_script_range=("\u0900", "\u097f"),  # Devanagari
    ),
    TranslationProbe(
        code="zh",
        language="Chinese",
        sentence="The cat sat on the mat and watched the birds.",
        expected_script_range=("\u4e00", "\u9fff"),  # CJK Unified
    ),
]


# System prompt matches what `modules/translation_batch.py` produces.
# Kept minimal here to avoid flakiness on models with small context windows.
_TRANSLATION_SYSTEM_PROMPT = (
    "You are a precise translator. Output ONLY the translation in the "
    "requested target language. Do not add notes, explanations, or "
    "quote marks. Preserve punctuation."
)

_JSON_BATCH_SYSTEM_PROMPT = (
    "You are a translation engine. Reply with ONLY a JSON object of the "
    'shape {"items":[{"id":<int>,"translation":"<string>"}]}. '
    "No prose, no markdown fences, no thinking tags."
)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class TranslationResult:
    probe: TranslationProbe
    elapsed: float = 0.0
    ok: bool = False
    reason: str = ""
    output_preview: str = ""
    output_chars: int = 0

    @property
    def chars_per_sec(self) -> float:
        if self.elapsed <= 0:
            return 0.0
        return self.output_chars / self.elapsed


@dataclass(slots=True)
class JsonBatchResult:
    elapsed: float = 0.0
    parsed_ok: bool = False
    items_ok: bool = False
    reason: str = ""
    raw_preview: str = ""
    raw_chars: int = 0
    debt_notes: List[str] = field(default_factory=list)


@dataclass(slots=True)
class ModelReport:
    identifier: str
    tier: int
    translations: List[TranslationResult] = field(default_factory=list)
    json_batch: Optional[JsonBatchResult] = None
    init_error: Optional[str] = None

    # ---- Aggregate metrics --------------------------------------------------
    @property
    def passed_probes(self) -> int:
        count = sum(1 for t in self.translations if t.ok)
        if self.json_batch and self.json_batch.items_ok:
            count += 1
        return count

    @property
    def total_probes(self) -> int:
        total = len(self.translations)
        if self.json_batch is not None:
            total += 1
        return total

    @property
    def avg_latency(self) -> float:
        """Mean latency across all probes that actually ran (seconds)."""
        samples: List[float] = [t.elapsed for t in self.translations if t.elapsed > 0]
        if self.json_batch and self.json_batch.elapsed > 0:
            samples.append(self.json_batch.elapsed)
        return sum(samples) / len(samples) if samples else 0.0

    @property
    def avg_throughput(self) -> float:
        """Mean chars-per-second across passing translation probes."""
        rates = [t.chars_per_sec for t in self.translations if t.ok and t.chars_per_sec > 0]
        return sum(rates) / len(rates) if rates else 0.0

    @property
    def perf_band(self) -> str:
        lat = self.avg_latency
        if lat <= 0:
            return "?"
        if lat < 5:
            return "fast"
        if lat < 15:
            return "med"
        return "slow"

    @property
    def composite_score(self) -> float:
        """
        Combined quality × performance score — higher is better.

        Formula: (pass_rate / tier_weight) × latency_factor
          - pass_rate: fraction of probes that passed (0..1)
          - tier_weight: lower tier (better quality) → smaller divisor.
              tier 10 → /1.0, tier 20 → /1.2, tier 30 → /1.5, tier 50 → /2.2,
              tier 60 → /2.5, tier 70 → /3.0, tier 90 → /5.0
          - latency_factor: 1.0 for ≤3s, linearly dropping to 0.2 at 30s.
        """
        if self.total_probes == 0:
            return 0.0
        pass_rate = self.passed_probes / self.total_probes
        # Piecewise tier weighting that rewards top-tier quality without making
        # lower tiers completely unreachable on good perf.
        if self.tier <= 10:
            tier_weight = 1.0
        elif self.tier <= 25:
            tier_weight = 1.2
        elif self.tier <= 45:
            tier_weight = 1.5
        elif self.tier <= 60:
            tier_weight = 2.2
        elif self.tier <= 80:
            tier_weight = 3.0
        else:
            tier_weight = 5.0
        lat = self.avg_latency
        if lat <= 3:
            latency_factor = 1.0
        elif lat >= 30:
            latency_factor = 0.2
        else:
            latency_factor = 1.0 - (lat - 3) / 27 * 0.8
        return (pass_rate / tier_weight) * latency_factor


# ---------------------------------------------------------------------------
# Probing
# ---------------------------------------------------------------------------


def _first_text_preview(text: str, limit: int = 120) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def _detect_format_debt(raw: str) -> List[str]:
    """Return format-compatibility issues observed in the raw response."""
    notes: List[str] = []
    stripped = raw.strip()
    if not stripped:
        notes.append("empty response")
        return notes
    if stripped.startswith("```"):
        notes.append("markdown code fence (needs fence stripping)")
    lower = stripped.lower()
    if "<think>" in lower or "</think>" in lower:
        notes.append("emits <think> tags (needs reasoning-tag stripping)")
    if stripped.startswith("<") and "</" in stripped:
        # common for models that emit tool/reasoning wrappers
        if "<think>" not in lower and "<|" not in lower:
            notes.append(f"leading XML-like wrapper: {_first_text_preview(stripped, 40)!r}")
    if "<|" in stripped and "|>" in stripped:
        notes.append("chat-template tokens leaked into output")
    return notes


def _run_translation_probe(client: Any, probe: TranslationProbe) -> TranslationResult:
    result = TranslationResult(probe=probe)
    start = time.perf_counter()
    try:
        payload = prompt_templates.make_sentence_payload(
            probe.sentence,
            model=client.model,
            stream=False,
            system_prompt=(
                f"{_TRANSLATION_SYSTEM_PROMPT}\n\nTarget language: {probe.language}."
            ),
        )
        response = client.send_chat_request(payload, max_attempts=1, timeout=60)
        result.elapsed = time.perf_counter() - start
        text = (response.text or "").strip()
        result.output_preview = _first_text_preview(text)
        result.output_chars = len(text)
        if response.error:
            result.reason = f"error: {response.error[:80]}"
            return result
        if not text:
            result.reason = "empty response"
            return result
        # Latin script probe is a pass as long as text is non-empty and
        # doesn't look like an English echo of the source.
        if probe.code == "fr":
            if text.lower().startswith("the cat"):
                result.reason = "echoed English source"
                return result
            result.ok = True
            return result
        if not probe.script_hit(text):
            result.reason = f"no {probe.language} script in output"
            return result
        result.ok = True
        return result
    except Exception as exc:
        result.elapsed = time.perf_counter() - start
        result.reason = f"exception: {type(exc).__name__}: {str(exc)[:80]}"
        return result


def _run_json_batch_probe(client: Any, timeout: float) -> JsonBatchResult:
    result = JsonBatchResult()
    items = [
        {"id": 1, "text": "The cat sat on the mat."},
        {"id": 2, "text": "It watched the birds through the window."},
    ]
    start = time.perf_counter()
    try:
        response = llm_batch.request_json_batch(
            client=client,
            system_prompt=(
                f"{_JSON_BATCH_SYSTEM_PROMPT}\n"
                "Translate each item to French. Keep the same id."
            ),
            items=items,
            timeout_seconds=timeout,
            max_attempts=1,
        )
        result.elapsed = time.perf_counter() - start
        result.raw_preview = _first_text_preview(response.raw_text, limit=200)
        result.raw_chars = len(response.raw_text or "")
        result.debt_notes.extend(_detect_format_debt(response.raw_text))
        if response.payload is None:
            result.reason = response.error or "unparseable JSON"
            return result
        result.parsed_ok = True
        items_field = (
            response.payload.get("items")
            if isinstance(response.payload, dict)
            else None
        )
        if not isinstance(items_field, list) or not items_field:
            result.reason = "response parsed but `items` missing/empty"
            return result
        # Check shape of first item
        first = items_field[0]
        if not isinstance(first, dict) or "id" not in first or "translation" not in first:
            result.reason = "items present but missing id/translation keys"
            return result
        result.items_ok = True
        return result
    except Exception as exc:
        result.elapsed = time.perf_counter() - start
        result.reason = f"exception: {type(exc).__name__}: {str(exc)[:80]}"
        return result


def _probe_model(identifier: str, timeout: float) -> ModelReport:
    provider, model_name = split_llm_model_identifier(identifier)
    tier = _model_quality_tier((model_name or identifier).strip())
    report = ModelReport(identifier=identifier, tier=tier)

    try:
        client = create_client(model=identifier)
    except Exception as exc:
        report.init_error = f"{type(exc).__name__}: {exc}"
        return report

    try:
        with client:
            for probe in TRANSLATION_PROBES:
                report.translations.append(_run_translation_probe(client, probe))
            report.json_batch = _run_json_batch_probe(client, timeout=timeout)
    except Exception as exc:
        report.init_error = f"client error: {type(exc).__name__}: {exc}"

    return report


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _status_emoji(ok: bool) -> str:
    return "✅" if ok else "❌"


def _provider_for_report(r: "ModelReport") -> str:
    provider, _ = split_llm_model_identifier(r.identifier)
    return provider or "other"


def _render_per_host_section(reports: List[ModelReport]) -> List[str]:
    """Render a per-provider breakdown so both LM Studio hosts are easy to compare."""
    lines: List[str] = []
    lines.append("## Per-host breakdown")
    lines.append("")
    try:
        macstudio_url = cfg.get_lmstudio_macstudio_url()
    except Exception:
        macstudio_url = "(unavailable)"
    try:
        macbook_url = cfg.get_lmstudio_macbook_url()
    except Exception:
        macbook_url = "(unavailable)"
    lines.append("LM Studio destinations probed:")
    lines.append(f"- **Mac Studio**: `{macstudio_url}`")
    lines.append(f"- **MacBook Pro**: `{macbook_url}`")
    lines.append("")
    lines.append(
        "Each host's models are scored on the same five-probe suite (FR / AR / HI / "
        "ZH translations + JSON batch). The summary row shows the host's median "
        "latency and pass rate; the rows below it list the top performers on that "
        "host so you can see which Mac is winning the head-to-head."
    )
    lines.append("")
    by_provider: Dict[str, List[ModelReport]] = {}
    for r in reports:
        if r.init_error:
            continue
        by_provider.setdefault(_provider_for_report(r), []).append(r)
    for tag in _PROVIDER_ORDER:
        bucket = by_provider.get(tag) or []
        if not bucket:
            continue
        title = _PROVIDER_DISPLAY.get(tag, tag)
        latencies = sorted(r.avg_latency for r in bucket if r.avg_latency > 0)
        median_lat = latencies[len(latencies) // 2] if latencies else 0.0
        total_passes = sum(r.passed_probes for r in bucket)
        total_probes = sum(r.total_probes for r in bucket)
        ok_count = sum(1 for r in bucket if r.passed_probes == r.total_probes and r.total_probes > 0)
        lines.append(f"### {title}")
        lines.append("")
        lines.append(
            f"- Models probed: **{len(bucket)}** "
            f"(perfect-pass: {ok_count}/{len(bucket)})"
        )
        lines.append(f"- Aggregate pass rate: **{total_passes}/{total_probes}**")
        if median_lat > 0:
            lines.append(f"- Median per-probe latency: **{median_lat:.1f}s**")
        lines.append("")
        lines.append("| Rank | Model | Pass | Avg Latency | Score |")
        lines.append("|-----:|------|:----:|------------:|------:|")
        ranked = sorted(
            bucket, key=lambda x: (-x.composite_score, x.tier, x.identifier.lower())
        )
        for rank, r in enumerate(ranked[:8], 1):
            pass_str = f"{r.passed_probes}/{r.total_probes}"
            lat = f"{r.avg_latency:.1f}s" if r.avg_latency > 0 else "—"
            lines.append(
                f"| {rank} | `{r.identifier}` | {pass_str} | {lat} | "
                f"{r.composite_score:.3f} |"
            )
        if len(ranked) > 8:
            lines.append(f"")
            lines.append(f"_…{len(ranked) - 8} more (see compatibility matrix below)._")
        lines.append("")
    # Head-to-head: if both LM Studio hosts have probes, surface a direct comparison.
    macstudio_reports = by_provider.get(LMSTUDIO_MACSTUDIO) or []
    macbook_reports = by_provider.get(LMSTUDIO_MACBOOK) or []
    if macstudio_reports and macbook_reports:
        lines.append("### LM Studio head-to-head (Mac Studio vs. MacBook Pro)")
        lines.append("")
        lines.append("| Model | Mac Studio | MacBook Pro | Δ Latency |")
        lines.append("|------|:----------:|:-----------:|----------:|")
        macstudio_by_name = {
            (split_llm_model_identifier(r.identifier)[1] or r.identifier): r
            for r in macstudio_reports
        }
        macbook_by_name = {
            (split_llm_model_identifier(r.identifier)[1] or r.identifier): r
            for r in macbook_reports
        }
        common = sorted(set(macstudio_by_name) & set(macbook_by_name))
        if not common:
            lines.append("| _no shared models on both hosts_ | — | — | — |")
        for name in common:
            ms = macstudio_by_name[name]
            mb = macbook_by_name[name]
            ms_cell = f"{ms.passed_probes}/{ms.total_probes} · {ms.avg_latency:.1f}s"
            mb_cell = f"{mb.passed_probes}/{mb.total_probes} · {mb.avg_latency:.1f}s"
            if ms.avg_latency > 0 and mb.avg_latency > 0:
                delta = f"{mb.avg_latency - ms.avg_latency:+.1f}s"
            else:
                delta = "—"
            lines.append(f"| `{name}` | {ms_cell} | {mb_cell} | {delta} |")
        lines.append("")
    return lines


def _render_markdown(reports: List[ModelReport]) -> str:
    lines: List[str] = []
    lines.append("# LLM Model Probe Report")
    lines.append("")
    lines.append(f"Models probed: {len(reports)}")
    lines.append("")
    lines.append(
        "Quality + performance composite: `(pass_rate / tier_weight) × latency_factor`. "
        "Higher is better. Tier is the hand-curated quality prior; latency is the mean "
        "wall-clock per probe (smaller is better)."
    )
    lines.append("")

    # ---- Per-host breakdown -------------------------------------------------
    lines.extend(_render_per_host_section(reports))

    # ---- Leaderboard (quality × performance) --------------------------------
    lines.append("## Leaderboard — Quality × Performance")
    lines.append("")
    lines.append(
        "| Rank | Model | Tier | Pass | Avg Latency | Throughput | Perf | Score |"
    )
    lines.append(
        "|-----:|------|-----:|:----:|------------:|-----------:|:----:|------:|"
    )
    ranked = sorted(
        [r for r in reports if not r.init_error],
        key=lambda x: (-x.composite_score, x.tier, x.identifier.lower()),
    )
    for rank, r in enumerate(ranked, 1):
        pass_str = f"{r.passed_probes}/{r.total_probes}"
        lat = f"{r.avg_latency:.1f}s" if r.avg_latency > 0 else "—"
        tp = f"{r.avg_throughput:.0f} ch/s" if r.avg_throughput > 0 else "—"
        lines.append(
            f"| {rank} | `{r.identifier}` | {r.tier} | {pass_str} | "
            f"{lat} | {tp} | {r.perf_band} | {r.composite_score:.3f} |"
        )
    failed = [r for r in reports if r.init_error]
    if failed:
        lines.append("")
        lines.append("Init failed (excluded from ranking):")
        for r in failed:
            lines.append(f"- `{r.identifier}` — {r.init_error[:100]}")
    lines.append("")

    # ---- Compatibility matrix (sorted by tier) ------------------------------
    lines.append("## Compatibility matrix")
    lines.append("")
    lines.append(
        "| Tier | Model | FR | AR | HI | ZH | JSON | Latency | Debt notes |"
    )
    lines.append(
        "|-----:|------|:--:|:--:|:--:|:--:|:----:|--------:|------------|"
    )
    for r in sorted(reports, key=lambda x: (x.tier, x.identifier.lower())):
        if r.init_error:
            lines.append(
                f"| {r.tier} | `{r.identifier}` | — | — | — | — | — | — | init failed: {r.init_error[:60]} |"
            )
            continue
        by_code = {t.probe.code: t for t in r.translations}
        cells = {
            code: _status_emoji(by_code.get(code).ok if by_code.get(code) else False)
            for code in ("fr", "ar", "hi", "zh")
        }
        json_status = _status_emoji(
            bool(r.json_batch and r.json_batch.parsed_ok and r.json_batch.items_ok)
        )
        debt = "; ".join(r.json_batch.debt_notes) if r.json_batch and r.json_batch.debt_notes else ""
        if r.json_batch and not r.json_batch.parsed_ok and r.json_batch.reason:
            debt = f"{debt + '; ' if debt else ''}{r.json_batch.reason[:50]}"
        lat = f"{r.avg_latency:.1f}s" if r.avg_latency > 0 else "—"
        lines.append(
            f"| {r.tier} | `{r.identifier}` "
            f"| {cells['fr']} | {cells['ar']} | {cells['hi']} | {cells['zh']} "
            f"| {json_status} | {lat} | {debt} |"
        )
    lines.append("")
    lines.append("## Details")
    lines.append("")
    for r in sorted(reports, key=lambda x: (x.tier, x.identifier.lower())):
        lines.append(f"### `{r.identifier}` (tier {r.tier})")
        lines.append("")
        if r.init_error:
            lines.append(f"- Init failed: `{r.init_error}`")
            lines.append("")
            continue
        for t in r.translations:
            status = "PASS" if t.ok else f"FAIL — {t.reason}"
            lines.append(
                f"- **{t.probe.language} ({t.probe.code})** [{t.elapsed:.2f}s] {status}"
            )
            if t.output_preview:
                lines.append(f"  - output: `{t.output_preview}`")
        if r.json_batch:
            jb = r.json_batch
            status = []
            if jb.parsed_ok:
                status.append("parsed=OK")
            else:
                status.append(f"parsed=FAIL ({jb.reason})")
            status.append("items=OK" if jb.items_ok else "items=FAIL")
            lines.append(f"- **JSON batch** [{jb.elapsed:.2f}s] {' | '.join(status)}")
            if jb.debt_notes:
                lines.append(f"  - debt: {'; '.join(jb.debt_notes)}")
            if jb.raw_preview:
                lines.append(f"  - raw: `{jb.raw_preview}`")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models",
        nargs="*",
        help="Subset of model identifiers to probe (default: all available)",
    )
    parser.add_argument(
        "--only-cloud",
        action="store_true",
        help="Restrict to ollama_cloud:* identifiers",
    )
    parser.add_argument(
        "--only-lmstudio",
        action="store_true",
        help=(
            "Restrict to LM Studio identifiers (both Mac Studio and MacBook). "
            "Useful for the two-host head-to-head comparison report."
        ),
    )
    parser.add_argument(
        "--lmstudio-host",
        choices=("macstudio", "macbook"),
        default=None,
        help="Restrict to a single LM Studio host (mutually exclusive with --only-cloud).",
    )
    parser.add_argument(
        "--exclude-tier",
        type=int,
        default=None,
        help="Skip models at or above this tier (e.g. --exclude-tier 90 to skip coding SKUs)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Per-request timeout (seconds). Default 60.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Write Markdown report to this path in addition to stdout",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Write raw per-model JSON results to this path",
    )
    args = parser.parse_args()

    try:
        all_models = list_available_llm_models()
    except Exception as exc:
        print(f"ERROR: could not list LLM models: {exc}", file=sys.stderr)
        return 1

    if args.models:
        wanted = set(args.models)
        targets = [m for m in all_models if m in wanted or m.endswith(tuple(wanted))]
    else:
        targets = list(all_models)

    if args.only_cloud:
        targets = [m for m in targets if m.startswith("ollama_cloud:")]

    if args.only_lmstudio:
        targets = [
            m
            for m in targets
            if (split_llm_model_identifier(m)[0] in LMSTUDIO_PROVIDERS)
        ]

    if args.lmstudio_host == "macstudio":
        targets = [m for m in targets if m.startswith(f"{LMSTUDIO_MACSTUDIO}:")]
    elif args.lmstudio_host == "macbook":
        targets = [m for m in targets if m.startswith(f"{LMSTUDIO_MACBOOK}:")]

    if args.exclude_tier is not None:
        targets = [
            m
            for m in targets
            if _model_quality_tier(split_llm_model_identifier(m)[1] or m) < args.exclude_tier
        ]

    if not targets:
        print("No models to probe after filtering.", file=sys.stderr)
        return 1

    print(f"Probing {len(targets)} models (timeout={args.timeout}s each)...", file=sys.stderr)
    reports: List[ModelReport] = []
    for idx, identifier in enumerate(targets, 1):
        print(f"  [{idx}/{len(targets)}] {identifier}", file=sys.stderr)
        reports.append(_probe_model(identifier, timeout=args.timeout))

    markdown = _render_markdown(reports)
    print(markdown)
    if args.out:
        args.out.write_text(markdown, encoding="utf-8")
        print(f"\nReport saved to {args.out}", file=sys.stderr)

    if args.json_out:
        raw: List[Dict[str, Any]] = []
        for r in reports:
            raw.append(
                {
                    "identifier": r.identifier,
                    "tier": r.tier,
                    "init_error": r.init_error,
                    "passed_probes": r.passed_probes,
                    "total_probes": r.total_probes,
                    "avg_latency_sec": round(r.avg_latency, 3),
                    "avg_throughput_chars_per_sec": round(r.avg_throughput, 1),
                    "perf_band": r.perf_band,
                    "composite_score": round(r.composite_score, 4),
                    "translations": [
                        {
                            "code": t.probe.code,
                            "language": t.probe.language,
                            "ok": t.ok,
                            "elapsed": t.elapsed,
                            "reason": t.reason,
                            "output": t.output_preview,
                        }
                        for t in r.translations
                    ],
                    "json_batch": (
                        {
                            "parsed_ok": r.json_batch.parsed_ok,
                            "items_ok": r.json_batch.items_ok,
                            "elapsed": r.json_batch.elapsed,
                            "reason": r.json_batch.reason,
                            "debt_notes": r.json_batch.debt_notes,
                            "raw": r.json_batch.raw_preview,
                        }
                        if r.json_batch
                        else None
                    ),
                }
            )
        args.json_out.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON results saved to {args.json_out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
