"""Image style templates for sentence diffusion generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional


@dataclass(frozen=True, slots=True)
class ImageStyleTemplate:
    """Template describing prompt + default diffusion tuning for sentence images."""

    template_id: str
    label: str
    description: str
    base_prompt: str
    negative_prompt: str
    default_steps: int
    default_cfg_scale: float
    default_sampler_name: Optional[str] = None
    prompt_markers: tuple[str, ...] = ()
    negative_markers: tuple[str, ...] = ()


_PHOTOREALISTIC_BASE_PROMPT = (
    "photorealistic cinematic film still,\n"
    "cohesive visual style across frames, consistent character appearance,\n"
    "realistic lighting, natural skin texture, subtle film grain,\n"
    "35mm photography, shallow depth of field, sharp focus, no motion blur,\n"
    "rich color, tasteful color grading, high dynamic range,\n"
    "detailed environment, strong sense of place, atmospheric perspective,\n"
    "single frame, no collage, no split panels,\n"
    "no text, no captions, no watermark, no logo"
)

_PHOTOREALISTIC_NEGATIVE_PROMPT = (
    "lowres, blurry, out of focus, jpeg artifacts, noise,\n"
    "watermark, logo, signature, text, letters, words, speech bubble,\n"
    "cartoon, comic, manga, anime, illustration, drawing, painting,\n"
    "cgi, 3d render, unreal engine,\n"
    "cropped, cut off, duplicate, multiple heads, extra limbs,\n"
    "bad anatomy, deformed hands, missing fingers, malformed face,\n"
    "nsfw, nude, nudity, explicit,\n"
    "gore, graphic violence"
)

_COMICS_BASE_PROMPT = (
    "high-quality color comic panel, graphic novel illustration,\n"
    "cohesive visual style across frames, consistent character appearance,\n"
    "clean linework, bold inks, subtle halftone shading,\n"
    "dynamic cinematic composition, sharp focus,\n"
    "single panel, no collage, no split panels,\n"
    "no text, no speech bubbles, no captions, no watermark, no logo"
)

_COMICS_NEGATIVE_PROMPT = (
    "photorealistic, cinematic film still, 35mm photography, realistic skin texture,\n"
    "watermark, logo, signature, text, letters, words, speech bubble,\n"
    "lowres, blurry, out of focus, jpeg artifacts, noise,\n"
    "cgi, 3d render, unreal engine,\n"
    "cropped, cut off, duplicate, multiple heads, extra limbs,\n"
    "bad anatomy, deformed hands, missing fingers, malformed face,\n"
    "nsfw, nude, nudity, explicit,\n"
    "gore, graphic violence"
)

_CHILDREN_BOOK_BASE_PROMPT = (
    "whimsical children's book illustration, storybook art,\n"
    "soft watercolor / gouache texture, warm pastel palette,\n"
    "gentle lighting, friendly expressive characters,\n"
    "cohesive visual style across frames, consistent character appearance,\n"
    "single illustration, no text, no captions, no watermark, no logo"
)

_CHILDREN_BOOK_NEGATIVE_PROMPT = (
    "photorealistic, cinematic film still, 35mm photography, realistic skin texture,\n"
    "dark gritty horror, gore, graphic violence,\n"
    "watermark, logo, signature, text, letters, words,\n"
    "lowres, blurry, out of focus, jpeg artifacts, noise,\n"
    "cgi, 3d render, unreal engine,\n"
    "cropped, cut off, duplicate, multiple heads, extra limbs,\n"
    "bad anatomy, deformed hands, missing fingers, malformed face,\n"
    "nsfw, nude, nudity, explicit"
)

_WIREFRAME_BASE_PROMPT = (
    "wireframe technical drawing, blueprint style, clean line art,\n"
    "simple geometric forms, minimal shading, monochrome,\n"
    "high contrast lines, white background,\n"
    "single frame, no text, no captions, no watermark, no logo"
)

_WIREFRAME_NEGATIVE_PROMPT = (
    "photorealistic, cinematic film still, 35mm photography, realistic skin texture,\n"
    "color, gradients, heavy shading, painterly texture,\n"
    "watermark, logo, signature, text, letters, words,\n"
    "lowres, blurry, out of focus, jpeg artifacts, noise,\n"
    "cgi, 3d render, unreal engine,\n"
    "cropped, cut off, duplicate, multiple heads, extra limbs,\n"
    "bad anatomy, deformed hands, missing fingers, malformed face,\n"
    "nsfw, nude, nudity, explicit,\n"
    "gore, graphic violence"
)


IMAGE_STYLE_TEMPLATES: Mapping[str, ImageStyleTemplate] = {
    "photorealistic": ImageStyleTemplate(
        template_id="photorealistic",
        label="Photorealistic",
        description="Cinematic film-still story reel (slowest, highest fidelity).",
        base_prompt=_PHOTOREALISTIC_BASE_PROMPT,
        negative_prompt=_PHOTOREALISTIC_NEGATIVE_PROMPT,
        default_steps=24,
        default_cfg_scale=7.0,
        prompt_markers=("photorealistic cinematic film still", "35mm photography"),
        negative_markers=("watermark, logo, signature",),
    ),
    "comics": ImageStyleTemplate(
        template_id="comics",
        label="Comics",
        description="Graphic novel comic-panel look with ink lines and halftone shading.",
        base_prompt=_COMICS_BASE_PROMPT,
        negative_prompt=_COMICS_NEGATIVE_PROMPT,
        default_steps=18,
        default_cfg_scale=7.0,
        prompt_markers=("high-quality color comic panel", "graphic novel illustration"),
        negative_markers=("watermark, logo, signature",),
    ),
    "children_book": ImageStyleTemplate(
        template_id="children_book",
        label="Children's book",
        description="Soft watercolor storybook illustration with warm pastel colours.",
        base_prompt=_CHILDREN_BOOK_BASE_PROMPT,
        negative_prompt=_CHILDREN_BOOK_NEGATIVE_PROMPT,
        default_steps=20,
        default_cfg_scale=7.0,
        prompt_markers=("children's book illustration", "storybook art"),
        negative_markers=("watermark, logo, signature",),
    ),
    "wireframe": ImageStyleTemplate(
        template_id="wireframe",
        label="Wireframe",
        description="Blueprint-style monochrome wireframe drawing (fastest).",
        base_prompt=_WIREFRAME_BASE_PROMPT,
        negative_prompt=_WIREFRAME_NEGATIVE_PROMPT,
        default_steps=12,
        default_cfg_scale=6.5,
        prompt_markers=("wireframe technical drawing", "blueprint style"),
        negative_markers=("watermark, logo, signature",),
    ),
}

_STYLE_ALIASES: Mapping[str, str] = {
    "photo realistic": "photorealistic",
    "photo-realistic": "photorealistic",
    "photo_realistic": "photorealistic",
    "realistic": "photorealistic",
    "story reel": "photorealistic",
    "story_reel": "photorealistic",
    "comic": "comics",
    "comic panel": "comics",
    "graphic novel": "comics",
    "storybook": "children_book",
    "children": "children_book",
    "children book": "children_book",
    "children's book": "children_book",
    "wire frame": "wireframe",
    "blueprint": "wireframe",
    "line art": "wireframe",
}


def normalize_image_style_template(value: object | None) -> str:
    """Return a normalized template identifier, falling back to photorealistic."""

    if not isinstance(value, str):
        return "photorealistic"
    candidate = value.strip().lower()
    if not candidate:
        return "photorealistic"
    normalized = " ".join(candidate.replace("_", " ").replace("-", " ").split())
    resolved = _STYLE_ALIASES.get(normalized, normalized)
    if resolved in IMAGE_STYLE_TEMPLATES:
        return resolved
    return "photorealistic"


def resolve_image_style_template(value: object | None) -> ImageStyleTemplate:
    """Return the resolved :class:`ImageStyleTemplate` for ``value``."""

    template_id = normalize_image_style_template(value)
    return IMAGE_STYLE_TEMPLATES[template_id]


__all__ = [
    "IMAGE_STYLE_TEMPLATES",
    "ImageStyleTemplate",
    "normalize_image_style_template",
    "resolve_image_style_template",
]

