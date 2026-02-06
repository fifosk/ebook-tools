"""Utilities for extracting and normalizing language metadata from payloads."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from ...transliteration import resolve_local_transliteration_module


def _normalize_language_label(value: Any) -> Optional[str]:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    if isinstance(value, list):
        for entry in value:
            if isinstance(entry, str):
                trimmed = entry.strip()
                if trimmed:
                    return trimmed
    return None


def _normalize_language_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [entry.strip() for entry in value if isinstance(entry, str) and entry.strip()]
    if isinstance(value, str):
        trimmed = value.strip()
        return [trimmed] if trimmed else []
    return []


def _normalize_option_label(value: Any) -> Optional[str]:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    if isinstance(value, list):
        for entry in value:
            if isinstance(entry, str):
                trimmed = entry.strip()
                if trimmed:
                    return trimmed
    return None


def _normalize_translation_provider(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized in {"google", "googletrans", "googletranslate", "google-translate", "gtranslate", "gtrans"}:
        return "googletrans"
    if normalized in {"llm", "ollama", "default"}:
        return "llm"
    return normalized or None


def _normalize_transliteration_mode(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower().replace("_", "-")
    if normalized in {"python", "python-module", "module", "local-module"}:
        return "python"
    if normalized.startswith("local-gemma3") or normalized == "gemma3-12b":
        return "default"
    if normalized in {"llm", "ollama", "default"}:
        return "default"
    return normalized or None


def _read_language_key(section: Mapping[str, Any], key: str) -> Any:
    if key in section:
        return section.get(key)
    camel = "".join(
        [part if idx == 0 else part.capitalize() for idx, part in enumerate(key.split("_"))]
    )
    if camel in section:
        return section.get(camel)
    return None


def _iter_language_sections(payload: Any) -> list[Mapping[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    sections: list[Mapping[str, Any]] = [payload]
    for key in ("inputs", "options", "config", "metadata"):
        candidate = payload.get(key)
        if isinstance(candidate, Mapping):
            sections.append(candidate)
    return sections


def _extract_language_context(
    payloads: tuple[Any, ...],
) -> tuple[Optional[str], Optional[str], Optional[str], list[str]]:
    input_language: Optional[str] = None
    original_language: Optional[str] = None
    target_language: Optional[str] = None
    target_languages: list[str] = []
    media_language: Optional[str] = None
    for payload in payloads:
        for section in _iter_language_sections(payload):
            if input_language is None:
                input_language = _normalize_language_label(
                    _read_language_key(section, "input_language")
                    or _read_language_key(section, "original_language")
                    or _read_language_key(section, "source_language")
                    or _read_language_key(section, "translation_source_language")
                )
            if original_language is None:
                original_language = _normalize_language_label(
                    _read_language_key(section, "original_language")
                )
            if not target_languages:
                target_languages = _normalize_language_list(
                    _read_language_key(section, "target_languages")
                    or _read_language_key(section, "target_language")
                    or _read_language_key(section, "translation_language")
                )
            if target_language is None:
                target_language = _normalize_language_label(
                    _read_language_key(section, "target_language")
                    or _read_language_key(section, "translation_language")
                )
        if media_language is None and isinstance(payload, Mapping):
            media_metadata = payload.get("media_metadata") or payload.get("book_metadata")
            if isinstance(media_metadata, Mapping):
                media_language = _normalize_language_label(
                    media_metadata.get("language")
                    or media_metadata.get("source_language")
                    or media_metadata.get("original_language")
                    or media_metadata.get("input_language")
                )
                if media_language is None:
                    show = media_metadata.get("show")
                    if isinstance(show, Mapping):
                        media_language = _normalize_language_label(show.get("language"))
    if original_language is None:
        original_language = input_language
    if input_language is None and media_language is not None:
        input_language = media_language
        if original_language is None:
            original_language = media_language
    if target_language is None and target_languages:
        target_language = target_languages[0]
    if target_language and not target_languages:
        target_languages = [target_language]
    return input_language, original_language, target_language, target_languages


def _set_if_blank(metadata: Dict[str, Any], key: str, value: Optional[str]) -> None:
    if value is None:
        return
    trimmed = value.strip()
    if not trimmed:
        return
    existing = metadata.get(key)
    if isinstance(existing, str) and existing.strip():
        return
    metadata[key] = trimmed


def _set_if_blank_or_override(
    metadata: Dict[str, Any],
    key: str,
    value: Optional[str],
    *,
    requested_key: Optional[str] = None,
) -> None:
    if value is None:
        return
    trimmed = value.strip()
    if not trimmed:
        return
    existing = metadata.get(key)
    if isinstance(existing, str) and existing.strip():
        existing_trimmed = existing.strip()
        if existing_trimmed != trimmed and requested_key:
            requested_existing = metadata.get(requested_key)
            if not (isinstance(requested_existing, str) and requested_existing.strip()):
                metadata[requested_key] = existing_trimmed
    metadata[key] = trimmed


def _set_list_if_blank(metadata: Dict[str, Any], key: str, values: list[str]) -> None:
    if not values:
        return
    cleaned = [value.strip() for value in values if isinstance(value, str) and value.strip()]
    if not cleaned:
        return
    existing = metadata.get(key)
    if isinstance(existing, list) and any(
        isinstance(entry, str) and entry.strip() for entry in existing
    ):
        return
    if isinstance(existing, str) and existing.strip():
        return
    metadata[key] = cleaned


def apply_language_metadata(
    media_metadata: Dict[str, Any],
    request_payload: Mapping[str, Any] | None,
    resume_context: Mapping[str, Any] | None,
    result_payload: Mapping[str, Any] | None,
) -> None:
    """Apply language-related metadata from various payload sources to media_metadata."""

    subtitle_metadata: Optional[Mapping[str, Any]] = None
    if isinstance(result_payload, Mapping):
        subtitle_section = result_payload.get("subtitle")
        if isinstance(subtitle_section, Mapping):
            metadata_section = subtitle_section.get("metadata")
            if isinstance(metadata_section, Mapping):
                subtitle_metadata = metadata_section

    input_language, original_language, target_language, target_languages = _extract_language_context(
        (
            request_payload,
            resume_context,
            subtitle_metadata,
        )
    )
    _set_if_blank(media_metadata, "input_language", input_language)
    _set_if_blank(media_metadata, "original_language", original_language or input_language)
    _set_if_blank(media_metadata, "target_language", target_language)
    _set_if_blank(media_metadata, "translation_language", target_language)
    _set_list_if_blank(media_metadata, "target_languages", target_languages)

    translation_provider: Optional[str] = None
    transliteration_mode: Optional[str] = None
    transliteration_model: Optional[str] = None
    for payload in (request_payload, resume_context, subtitle_metadata):
        for section in _iter_language_sections(payload):
            if translation_provider is None:
                translation_provider = _normalize_translation_provider(
                    _normalize_option_label(_read_language_key(section, "translation_provider"))
                )
            if transliteration_mode is None:
                transliteration_mode = _normalize_transliteration_mode(
                    _normalize_option_label(_read_language_key(section, "transliteration_mode"))
                )
            if transliteration_model is None:
                transliteration_model = _normalize_option_label(
                    _read_language_key(section, "transliteration_model")
                )

    llm_model: Optional[str] = None
    for payload in (request_payload, resume_context):
        if not isinstance(payload, Mapping):
            continue
        config_section = payload.get("config")
        if isinstance(config_section, Mapping):
            llm_model = _normalize_option_label(config_section.get("ollama_model")) or llm_model
        pipeline_overrides = payload.get("pipeline_overrides")
        if isinstance(pipeline_overrides, Mapping):
            override_model = _normalize_option_label(pipeline_overrides.get("ollama_model"))
            if override_model:
                llm_model = override_model
        if llm_model:
            break

    if llm_model is None and isinstance(result_payload, Mapping):
        pipeline_config = result_payload.get("pipeline_config")
        if isinstance(pipeline_config, Mapping):
            llm_model = _normalize_option_label(pipeline_config.get("ollama_model")) or llm_model

    translation_model = None
    if translation_provider == "googletrans":
        translation_model = "googletrans"
    elif translation_provider == "llm":
        translation_model = llm_model

    resolved_transliteration_model = None
    transliteration_module = None
    if transliteration_mode == "default":
        resolved_transliteration_model = transliteration_model or llm_model
    elif transliteration_mode == "python":
        target_for_module = target_language or (target_languages[0] if target_languages else None)
        if target_for_module:
            transliteration_module = resolve_local_transliteration_module(target_for_module)

    _set_if_blank(media_metadata, "translation_provider", translation_provider)
    _set_if_blank_or_override(
        media_metadata,
        "translation_model",
        translation_model,
        requested_key="translation_model_requested",
    )
    _set_if_blank(media_metadata, "transliteration_mode", transliteration_mode)
    _set_if_blank_or_override(
        media_metadata,
        "transliteration_model",
        resolved_transliteration_model,
        requested_key="transliteration_model_requested",
    )
    _set_if_blank(media_metadata, "transliteration_module", transliteration_module)


__all__ = [
    "apply_language_metadata",
    "_normalize_language_label",
    "_normalize_language_list",
    "_normalize_option_label",
    "_normalize_translation_provider",
    "_normalize_transliteration_mode",
    "_read_language_key",
    "_iter_language_sections",
    "_extract_language_context",
    "_set_if_blank",
    "_set_if_blank_or_override",
    "_set_list_if_blank",
]
