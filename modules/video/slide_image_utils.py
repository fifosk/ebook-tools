"""Helpers for working with slide cover images and Pillow runtime capabilities."""

from __future__ import annotations

import io
from typing import Optional

from PIL import Image

from modules import logging_manager as log_mgr

logger = log_mgr.logger


def serialize_cover_image(image: Optional[Image.Image]) -> Optional[bytes]:
    """Convert a Pillow image into raw PNG bytes for transportation across processes."""
    if image is None:
        return None
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def deserialize_cover_image(payload: Optional[bytes]) -> Optional[Image.Image]:
    """Rebuild a Pillow image from the serialized PNG payload."""
    if payload is None:
        return None
    stream = io.BytesIO(payload)
    img = Image.open(stream)
    converted = img.convert("RGB")
    converted.load()
    img.close()
    return converted


def has_simd_support() -> bool:
    """Detect whether Pillow-SIMD features are available."""
    core = getattr(Image, "core", None)
    return bool(getattr(core, "have_simd", False))


_SIMD_STATUS_LOGGED = False


def log_simd_preference(prefer_simd: bool) -> None:
    """Log the SIMD preference once so debugging output stays readable."""
    global _SIMD_STATUS_LOGGED
    if not prefer_simd or _SIMD_STATUS_LOGGED:
        return
    _SIMD_STATUS_LOGGED = True
    if has_simd_support():
        logger.debug(
            "Pillow SIMD acceleration detected for slide rendering.",
            extra={"event": "video.slide.simd", "console_suppress": True},
        )
    else:
        logger.warning(
            "Pillow-SIMD acceleration requested but not available on this installation.",
            extra={"event": "video.slide.simd.missing"},
        )
