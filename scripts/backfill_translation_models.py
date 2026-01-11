#!/usr/bin/env python3
"""Backfill translation/transliteration model metadata using effective LLM overrides."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple


def _normalize_label(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _normalize_translation_provider(value: Any) -> Optional[str]:
    label = _normalize_label(value)
    if not label:
        return None
    normalized = label.lower().replace("_", "-")
    if normalized in {"google", "googletrans", "googletranslate", "google-translate", "gtranslate", "gtrans"}:
        return "googletrans"
    if normalized in {"ollama", "llm"}:
        return "llm"
    return normalized


def _normalize_transliteration_mode(value: Any) -> Optional[str]:
    label = _normalize_label(value)
    if not label:
        return None
    normalized = label.lower().replace("_", "-")
    if normalized in {"python", "python-module", "module", "local-module"}:
        return "python"
    return "default"


def _resolve_option(payloads: Iterable[Dict[str, Any]], key: str) -> Optional[str]:
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        inputs = payload.get("inputs")
        for section in (inputs, payload):
            if isinstance(section, dict):
                value = _normalize_label(section.get(key))
                if value:
                    return value
    return None


def _resolve_llm_model(
    request_payload: Optional[Dict[str, Any]],
    resume_context: Optional[Dict[str, Any]],
    result_payload: Optional[Dict[str, Any]],
) -> Optional[str]:
    llm_model: Optional[str] = None
    for payload in (request_payload, resume_context):
        if not isinstance(payload, dict):
            continue
        config_section = payload.get("config")
        if isinstance(config_section, dict):
            llm_model = _normalize_label(config_section.get("ollama_model")) or llm_model
        overrides = payload.get("pipeline_overrides")
        if isinstance(overrides, dict):
            override_model = _normalize_label(overrides.get("ollama_model"))
            if override_model:
                llm_model = override_model
        if llm_model:
            break
    if llm_model is None and isinstance(result_payload, dict):
        pipeline_config = result_payload.get("pipeline_config")
        if isinstance(pipeline_config, dict):
            llm_model = _normalize_label(pipeline_config.get("ollama_model")) or llm_model
    return llm_model


def _set_if_blank_or_override(
    metadata: Dict[str, Any],
    key: str,
    value: Optional[str],
    *,
    requested_key: Optional[str],
) -> bool:
    if not value:
        return False
    existing = metadata.get(key)
    if isinstance(existing, str) and existing.strip():
        existing_trimmed = existing.strip()
        if existing_trimmed == value:
            return False
        if requested_key:
            requested_existing = metadata.get(requested_key)
            if not (isinstance(requested_existing, str) and requested_existing.strip()):
                metadata[requested_key] = existing_trimmed
    metadata[key] = value
    return True


def _apply_model_backfill(
    metadata: Dict[str, Any],
    *,
    translation_provider: Optional[str],
    transliteration_mode: Optional[str],
    llm_model: Optional[str],
) -> Tuple[bool, bool]:
    translation_model: Optional[str] = None
    if translation_provider == "googletrans":
        translation_model = "googletrans"
    elif translation_provider == "llm":
        translation_model = llm_model

    transliteration_model: Optional[str] = None
    if transliteration_mode == "default":
        transliteration_model = llm_model

    updated_translation = _set_if_blank_or_override(
        metadata,
        "translation_model",
        translation_model,
        requested_key="translation_model_requested",
    )
    updated_transliteration = _set_if_blank_or_override(
        metadata,
        "transliteration_model",
        transliteration_model,
        requested_key="transliteration_model_requested",
    )
    return updated_translation, updated_transliteration


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _write_json(path: Path, payload: Dict[str, Any], *, pretty: bool) -> None:
    if pretty:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def backfill_storage(storage_root: Path) -> int:
    if not storage_root.exists():
        print(f"Storage root not found: {storage_root}", file=sys.stderr)
        return 1

    updated_jobs = 0
    updated_books = 0
    scanned = 0

    for job_dir in sorted(storage_root.iterdir()):
        metadata_dir = job_dir / "metadata"
        if not metadata_dir.is_dir():
            continue
        job_path = metadata_dir / "job.json"
        book_path = metadata_dir / "book.json"
        if not job_path.exists() and not book_path.exists():
            continue

        job_payload = _load_json(job_path) if job_path.exists() else None
        book_payload = _load_json(book_path) if book_path.exists() else None
        if job_payload is None and book_payload is None:
            continue

        scanned += 1
        request_payload = None
        request_path = metadata_dir / "request.json"
        if request_path.exists():
            request_payload = _load_json(request_path)
        if request_payload is None and isinstance(job_payload, dict):
            request_payload = job_payload.get("request")
        resume_context = job_payload.get("resume_context") if isinstance(job_payload, dict) else None

        result_payload = None
        if isinstance(job_payload, dict):
            if isinstance(job_payload.get("result"), dict):
                result_payload = job_payload.get("result")
            elif isinstance(job_payload.get("result_payload"), dict):
                result_payload = job_payload.get("result_payload")

        translation_provider_raw = _resolve_option(
            (request_payload or {}, resume_context or {}),
            "translation_provider",
        )
        transliteration_mode_raw = _resolve_option(
            (request_payload or {}, resume_context or {}),
            "transliteration_mode",
        )

        translation_provider = _normalize_translation_provider(translation_provider_raw)
        transliteration_mode = _normalize_transliteration_mode(transliteration_mode_raw)
        llm_model = _resolve_llm_model(request_payload, resume_context, result_payload)

        updated = False
        if isinstance(job_payload, dict):
            result_section = job_payload.get("result")
            if isinstance(result_section, dict):
                book_metadata = result_section.get("book_metadata")
                if isinstance(book_metadata, dict):
                    updated_translation, updated_transliteration = _apply_model_backfill(
                        book_metadata,
                        translation_provider=translation_provider,
                        transliteration_mode=transliteration_mode,
                        llm_model=llm_model,
                    )
                    updated = updated or updated_translation or updated_transliteration

        if updated and job_path.exists():
            _write_json(job_path, job_payload, pretty=False)
            updated_jobs += 1

        if isinstance(book_payload, dict):
            updated_translation, updated_transliteration = _apply_model_backfill(
                book_payload,
                translation_provider=translation_provider,
                transliteration_mode=transliteration_mode,
                llm_model=llm_model,
            )
            if updated_translation or updated_transliteration:
                _write_json(book_path, book_payload, pretty=True)
                updated_books += 1

    print(
        f"Scanned {scanned} job(s). Updated {updated_jobs} job.json file(s) and {updated_books} book.json file(s)."
    )
    return 0


def main() -> int:
    storage_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("storage")
    return backfill_storage(storage_root)


if __name__ == "__main__":
    raise SystemExit(main())
