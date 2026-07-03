"""Generated-book cover image helper for Create routes."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from modules import logging_manager as log_mgr
from modules.images.drawthings import (
    DrawThingsImageRequest,
    normalize_drawthings_base_urls,
    resolve_drawthings_client,
)
from modules.images.prompting import (
    build_sentence_image_negative_prompt,
    build_sentence_image_prompt,
)
from modules.images.style_templates import resolve_image_style_template

from .create_book_context import normalize_optional_text
from .create_book_options import _coerce_float, _coerce_int

logger = log_mgr.get_logger()


def collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).strip()


def generate_cover_image(
    *,
    prompt: str,
    negative_prompt: str | None,
    output_dir: Path,
    config: dict[str, Any],
) -> tuple[str | None, str | None, str | None, str | None]:
    base_urls = normalize_drawthings_base_urls(
        base_url=config.get("image_api_base_url"),
        base_urls=config.get("image_api_base_urls"),
    )
    if not base_urls:
        return None, None, None, "unconfigured"

    style_value = config.get("image_style_template")
    style_template = resolve_image_style_template(style_value)
    prompt_text = collapse_whitespace(prompt)
    if not prompt_text:
        return None, None, None, None

    full_prompt = build_sentence_image_prompt(
        prompt_text,
        style_template=style_template.template_id,
    )
    full_negative = build_sentence_image_negative_prompt(
        collapse_whitespace(negative_prompt or ""),
        style_template=style_template.template_id,
    )

    width = max(64, _coerce_int(config.get("image_width"), 512))
    height = max(64, _coerce_int(config.get("image_height"), 512))
    steps = max(1, _coerce_int(config.get("image_steps"), int(style_template.default_steps)))
    cfg_scale = _coerce_float(config.get("image_cfg_scale"), style_template.default_cfg_scale)
    sampler_name = normalize_optional_text(config.get("image_sampler_name"))
    if not sampler_name:
        sampler_name = style_template.default_sampler_name

    request = DrawThingsImageRequest(
        prompt=full_prompt,
        negative_prompt=full_negative,
        width=width,
        height=height,
        steps=steps,
        cfg_scale=cfg_scale,
        sampler_name=sampler_name,
    )
    timeout_seconds = max(1.0, _coerce_float(config.get("image_api_timeout_seconds"), 180.0))
    client, _available_urls, unavailable_urls = resolve_drawthings_client(
        base_urls=base_urls,
        timeout_seconds=timeout_seconds,
    )
    if unavailable_urls:
        logger.warning(
            "DrawThings endpoints unavailable: %s",
            ", ".join(unavailable_urls),
            extra={
                "event": "webapi.cover.unavailable",
                "attributes": {"unavailable": unavailable_urls},
                "console_suppress": True,
            },
        )
    if client is None:
        return None, None, None, "unavailable"
    image_bytes, _payload = client.txt2img(request)

    output_dir.mkdir(parents=True, exist_ok=True)
    cover_path = output_dir / "cover.png"
    cover_path.write_bytes(image_bytes)
    return str(cover_path), full_prompt, full_negative, None
