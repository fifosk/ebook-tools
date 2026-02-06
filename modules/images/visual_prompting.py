"""Visual canon prompt orchestration for sentence images."""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from modules import logging_manager as log_mgr
from modules.llm_client_manager import client_scope

logger = log_mgr.get_logger().getChild("images.visual_prompting")

GLOBAL_NEGATIVE_CANON = (
    "inconsistent facial features, changing hairstyle, different eye color, extra limbs, "
    "distorted anatomy, anime, cartoon, low detail, overexposed, blurry face"
)

_VISUAL_CANON_MIN_TOKENS = 2000
_VISUAL_CANON_MAX_TOKENS = 6000
_SCENE_MIN_TOKENS = 1500
_SCENE_MAX_TOKENS = 4000
_SENTENCE_DELTA_TIMEOUT_SECONDS = 90
_SCENE_TIMEOUT_SECONDS = 180
_CANON_TIMEOUT_SECONDS = 240
_IMG2IMG_DENOISE = 0.3

_FORBIDDEN_DELTA_PATTERNS = (
    r"\bhair\b",
    r"\bhairstyle\b",
    r"\bface\b",
    r"\bskin\b",
    r"\bethnicity\b",
    r"\brace\b",
    r"\bblack\b",
    r"\bwhite\b",
    r"\basian\b",
    r"\bhispanic\b",
    r"\blatino\b",
    r"\bclothing\b",
    r"\bdress\b",
    r"\bshirt\b",
    r"\bcoat\b",
    r"\bjacket\b",
    r"\bpants\b",
    r"\bskirt\b",
    r"\buniform\b",
    r"\bshoe\b",
    r"\bboot\b",
    r"\bhat\b",
    r"\bscarf\b",
    r"\byoung\b",
    r"\bold\b",
    r"\belderly\b",
    r"\bteen\b",
    r"\bchild\b",
    r"\badult\b",
    r"\bmiddle[- ]aged\b",
    r"\bslender\b",
    r"\bmuscular\b",
    r"\bshort\b",
    r"\btall\b",
    r"\boverweight\b",
    r"\bthin\b",
    r"\broom\b",
    r"\bstreet\b",
    r"\bforest\b",
    r"\bmountain\b",
    r"\briver\b",
    r"\bocean\b",
    r"\bsea\b",
    r"\bcastle\b",
    r"\bvillage\b",
    r"\bcity\b",
    r"\btown\b",
    r"\bhouse\b",
    r"\bkitchen\b",
    r"\bbedroom\b",
    r"\bhall\b",
    r"\bcorridor\b",
    r"\bgarden\b",
    r"\bfield\b",
    r"\bsky\b",
    r"\bsun\b",
    r"\bmoon\b",
)


@dataclass(slots=True)
class VisualCanon:
    style: dict[str, str]
    characters: dict[str, dict[str, str]]
    locations: dict[str, dict[str, str]]


@dataclass(slots=True)
class SceneState:
    scene_id: str
    location_id: str
    time_of_day: str
    weather: str
    mood: str
    present_characters: tuple[str, ...]
    sentence_start: int
    sentence_end: int
    chapter_start_sentence: int
    global_start_sentence: int
    global_end_sentence: int
    base_image_path: str = ""
    last_image_path: Optional[Path] = None
    scene_path: Optional[Path] = None


@dataclass(frozen=True, slots=True)
class VisualPromptResult:
    scene_id: str
    sentence_index: int
    sentence_delta: str
    positive_prompt: str
    negative_prompt: str
    generation_mode: str
    init_image: Optional[Path]
    denoise_strength: float
    reuse_previous_image: bool


def _approx_token_count(text: str) -> int:
    return max(1, len((text or "").strip()) // 4)


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).strip()


def _extract_json_payload(text: str) -> Any:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        brace_start = raw.find("{")
        brace_end = raw.rfind("}")
        bracket_start = raw.find("[")
        bracket_end = raw.rfind("]")
        if bracket_start != -1 and bracket_end != -1 and bracket_end > bracket_start:
            try:
                return json.loads(raw[bracket_start : bracket_end + 1])
            except json.JSONDecodeError:
                pass
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            try:
                return json.loads(raw[brace_start : brace_end + 1])
            except json.JSONDecodeError:
                return None
    return None


def _normalize_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value or "").strip("_")
    return cleaned.lower() or "unknown"


def _format_style(style: Mapping[str, Any]) -> str:
    parts = [
        _collapse_whitespace(str(style.get("medium") or "")),
        _collapse_whitespace(str(style.get("lighting") or "")),
        _collapse_whitespace(str(style.get("palette") or "")),
        _collapse_whitespace(str(style.get("camera") or "")),
    ]
    return ", ".join([part for part in parts if part])


def _format_location(location: Mapping[str, Any]) -> str:
    parts = [
        _collapse_whitespace(str(location.get("architecture") or "")),
        _collapse_whitespace(str(location.get("environment") or "")),
        _collapse_whitespace(str(location.get("props") or "")),
    ]
    return ", ".join([part for part in parts if part])


def _build_character_tokens(characters: Mapping[str, Any]) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for char_id in characters:
        normalized = _normalize_id(str(char_id))
        tokens[normalized] = f"char_{normalized}_v1"
    return tokens


def _validate_sentence_delta(delta: str) -> None:
    candidate = delta.lower()
    for pattern in _FORBIDDEN_DELTA_PATTERNS:
        if re.search(pattern, candidate):
            raise ValueError(f"Sentence delta contains forbidden content: {pattern}")


def _sanitize_sentence_delta(delta: str) -> str:
    cleaned = delta
    for pattern in _FORBIDDEN_DELTA_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.strip(",.;:-")


def _truncate_for_log(text: str, limit: int = 140) -> str:
    cleaned = _collapse_whitespace(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 3)] + "..."


def _fallback_sentence_delta() -> str:
    return "A subtle shift in posture and expression."


def _build_excerpts(sentences: Sequence[str]) -> str:
    cleaned = [str(entry).strip() for entry in sentences if str(entry).strip()]
    if not cleaned:
        return ""
    full_text = " ".join(cleaned)
    if _approx_token_count(full_text) <= _VISUAL_CANON_MAX_TOKENS:
        return full_text

    average_tokens = max(_approx_token_count(full_text) / max(len(cleaned), 1), 1)
    target_count = max(1, int(_VISUAL_CANON_MAX_TOKENS / average_tokens))
    step = max(1, len(cleaned) // target_count)
    sampled = [cleaned[idx] for idx in range(0, len(cleaned), step)]
    if sampled and sampled[-1] != cleaned[-1]:
        sampled.append(cleaned[-1])

    tokens_so_far = 0
    selected: list[str] = []
    for sentence in sampled:
        tokens = _approx_token_count(sentence)
        if tokens_so_far + tokens > _VISUAL_CANON_MAX_TOKENS:
            break
        selected.append(sentence)
        tokens_so_far += tokens
    if tokens_so_far < _VISUAL_CANON_MIN_TOKENS:
        return full_text
    return " ".join(selected)


def _truncate_for_tokens(text: str, max_tokens: int) -> str:
    cleaned = _collapse_whitespace(text)
    if not cleaned:
        return ""
    if _approx_token_count(cleaned) <= max_tokens:
        return cleaned
    words = cleaned.split()
    max_words = max(1, int(max_tokens * 0.8))
    return " ".join(words[:max_words])


def _load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _atomic_write_json(path: Path, payload: Any) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _build_chapter_text(sentences: Sequence[str]) -> str:
    lines = [f"[{idx}] {str(sentence).strip()}" for idx, sentence in enumerate(sentences)]
    return "\n".join(lines)


def _resolve_visual_canon(
    *,
    job_root: Path,
    media_metadata: Mapping[str, Any],
    full_sentences: Sequence[str],
) -> VisualCanon:
    metadata_root = job_root / "metadata"
    path = metadata_root / "visual_canon.json"
    if path.exists():
        payload = _load_json(path)
        if isinstance(payload, Mapping):
            style = payload.get("style")
            characters = payload.get("characters")
            locations = payload.get("locations")
            if isinstance(style, Mapping) and isinstance(characters, Mapping) and isinstance(locations, Mapping):
                return VisualCanon(
                    style={str(k): str(v) for k, v in dict(style).items()},
                    characters={
                        str(k): dict(v) if isinstance(v, Mapping) else {}
                        for k, v in dict(characters).items()
                    },
                    locations={
                        str(k): dict(v) if isinstance(v, Mapping) else {}
                        for k, v in dict(locations).items()
                    },
                )
        raise ValueError("visual_canon.json exists but is invalid or incomplete")

    title = str(media_metadata.get("book_title") or media_metadata.get("title") or "").strip()
    genre = str(media_metadata.get("book_genre") or media_metadata.get("genre") or "").strip()
    period = str(media_metadata.get("historical_period") or media_metadata.get("book_year") or "").strip()
    excerpt_text = _build_excerpts(full_sentences)

    system_prompt = (
        "You generate a VISUAL_CANON for an ebook illustration pipeline.\n"
        "Extract only stable, recurring visual facts.\n"
        "Ignore momentary actions or scene-specific events.\n"
        "Focus on visual style, recurring characters, and recurring locations.\n"
        "Return STRICT JSON ONLY with keys: style, characters, locations.\n"
        "The JSON MUST match this schema:\n"
        '{ "style": { "medium": "...", "lighting": "...", "palette": "...", "camera": "..." },\n'
        '  "characters": { "<CHAR_ID>": { "age": "...", "gender": "...", "hair": "...", "face": "...", "build": "...", "clothing": "..." } },\n'
        '  "locations": { "<LOCATION_ID>": { "architecture": "...", "environment": "...", "props": "..." } } }\n'
    )
    user_payload = {
        "media_metadata": {
            "title": title,
            "genre": genre,
            "historical_period": period,
        },
        "excerpts": excerpt_text,
    }

    with client_scope(None) as client:
        response = client.send_chat_request(
            {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                ],
                "stream": False,
                "options": {"temperature": 0.2, "top_p": 0.9},
            },
            timeout=int(_CANON_TIMEOUT_SECONDS),
        )
    raw = response.text.strip() if response.text else ""
    if response.error:
        raise ValueError(response.error)
    payload = _extract_json_payload(raw)
    if not isinstance(payload, Mapping):
        raise ValueError("Visual canon LLM response was not a JSON object")
    style = payload.get("style")
    characters = payload.get("characters")
    locations = payload.get("locations")
    if not isinstance(style, Mapping) or not isinstance(characters, Mapping) or not isinstance(locations, Mapping):
        raise ValueError("Visual canon LLM response missing required keys")

    canon = VisualCanon(
        style={str(k): str(v) for k, v in dict(style).items()},
        characters={
            str(k): dict(v) if isinstance(v, Mapping) else {}
            for k, v in dict(characters).items()
        },
        locations={
            str(k): dict(v) if isinstance(v, Mapping) else {}
            for k, v in dict(locations).items()
        },
    )
    metadata_root.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(
        path,
        {
            "style": canon.style,
            "characters": canon.characters,
            "locations": canon.locations,
        },
    )
    return canon


def _resolve_scenes_for_chapter(
    *,
    job_root: Path,
    chapter_index: int,
    chapter_sentences: Sequence[str],
    character_ids: Sequence[str] = (),
    location_ids: Sequence[str] = (),
) -> list[Mapping[str, Any]]:
    scenes_root = job_root / "metadata" / "scenes"
    scenes_root.mkdir(parents=True, exist_ok=True)
    prefix = f"chapter_{chapter_index:02d}_"
    existing: list[Mapping[str, Any]] = []
    for path in scenes_root.glob("*.json"):
        payload = _load_json(path)
        if not isinstance(payload, Mapping):
            continue
        scene_id = payload.get("scene_id") or payload.get("sceneId")
        if isinstance(scene_id, str) and scene_id.startswith(prefix):
            existing.append(payload)
    if existing:
        return _repair_scene_payloads(
            scenes=existing,
            chapter_length=len(chapter_sentences),
            chapter_index=chapter_index,
            scenes_root=scenes_root,
        )

    chapter_text = _build_chapter_text(chapter_sentences)
    token_count = _approx_token_count(chapter_text)
    if token_count < _SCENE_MIN_TOKENS or token_count > _SCENE_MAX_TOKENS:
        logger.info(
            "Chapter %s token estimate=%s outside target range (%s-%s).",
            chapter_index,
            token_count,
            _SCENE_MIN_TOKENS,
            _SCENE_MAX_TOKENS,
        )

    allowed_characters = [str(item).strip() for item in character_ids if str(item).strip()]
    allowed_locations = [str(item).strip() for item in location_ids if str(item).strip()]
    character_hint = (
        "Use only these character IDs for present_characters: "
        + ", ".join(allowed_characters)
        + ". If none apply, return an empty array.\n"
        if allowed_characters
        else "If no recurring characters are present, return an empty present_characters array.\n"
    )
    location_hint = (
        "Use only these location IDs for location_id: "
        + ", ".join(allowed_locations)
        + ". If none apply, return an empty string.\n"
        if allowed_locations
        else "If no recurring location fits, return an empty location_id.\n"
    )
    system_prompt = (
        "You segment a chapter into visually coherent scenes.\n"
        "Return STRICT JSON ONLY as an array of objects with keys:\n"
        "- scene_id\n"
        "- location_id\n"
        "- time_of_day\n"
        "- weather\n"
        "- mood\n"
        "- present_characters (array of character IDs)\n"
        "- sentence_range (array: [start, end], 0-based, inclusive)\n"
        "Use scene_id format: chapter_{chapter_index:02d}_scene_XX.\n"
        f"{character_hint}{location_hint}"
    ).format(chapter_index=chapter_index)
    user_prompt = chapter_text

    with client_scope(None) as client:
        response = client.send_chat_request(
            {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.2, "top_p": 0.9},
            },
            timeout=int(_SCENE_TIMEOUT_SECONDS),
        )
    raw = response.text.strip() if response.text else ""
    if response.error:
        raise ValueError(response.error)
    payload = _extract_json_payload(raw)
    if not isinstance(payload, list):
        raise ValueError("Scene detection LLM response was not a JSON array")

    scenes_payload: list[Mapping[str, Any]] = []
    for entry in payload:
        if not isinstance(entry, Mapping):
            continue
        scene_id = str(entry.get("scene_id") or entry.get("sceneId") or "").strip()
        location_id = str(entry.get("location_id") or entry.get("locationId") or "").strip()
        time_of_day = str(entry.get("time_of_day") or entry.get("timeOfDay") or "").strip()
        weather = str(entry.get("weather") or "").strip()
        mood = str(entry.get("mood") or "").strip()
        present_raw = entry.get("present_characters") or entry.get("presentCharacters") or []
        if not isinstance(present_raw, Sequence) or isinstance(present_raw, (str, bytes)):
            present_raw = []
        present_characters = [str(item).strip() for item in present_raw if str(item).strip()]
        sentence_range = entry.get("sentence_range") or entry.get("sentenceRange") or []
        if (
            not isinstance(sentence_range, Sequence)
            or isinstance(sentence_range, (str, bytes))
            or len(sentence_range) != 2
        ):
            raise ValueError("Scene sentence_range missing or invalid")
        try:
            start_idx = int(sentence_range[0])
            end_idx = int(sentence_range[1])
        except (TypeError, ValueError):
            raise ValueError("Scene sentence_range values are not integers")
        if not scene_id:
            raise ValueError("Scene scene_id missing")
        scene_payload = {
            "scene_id": scene_id,
            "location_id": location_id,
            "time_of_day": time_of_day,
            "weather": weather,
            "mood": mood,
            "present_characters": present_characters,
            "sentence_range": [start_idx, end_idx],
            "base_image_path": "",
        }
        scenes_payload.append(scene_payload)
    return _repair_scene_payloads(
        scenes=scenes_payload,
        chapter_length=len(chapter_sentences),
        chapter_index=chapter_index,
        scenes_root=scenes_root,
    )


def _repair_scene_payloads(
    *,
    scenes: Sequence[Mapping[str, Any]],
    chapter_length: int,
    chapter_index: int,
    scenes_root: Path,
) -> list[Mapping[str, Any]]:
    if chapter_length <= 0:
        return []

    cleaned: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    skipped = 0

    for entry in scenes:
        if not isinstance(entry, Mapping):
            skipped += 1
            continue
        scene_id = str(entry.get("scene_id") or entry.get("sceneId") or "").strip()
        if not scene_id or scene_id in seen_ids:
            skipped += 1
            continue
        sentence_range = entry.get("sentence_range") or entry.get("sentenceRange")
        if (
            not isinstance(sentence_range, Sequence)
            or isinstance(sentence_range, (str, bytes))
            or len(sentence_range) != 2
        ):
            skipped += 1
            continue
        try:
            start_idx = int(sentence_range[0])
            end_idx = int(sentence_range[1])
        except (TypeError, ValueError):
            skipped += 1
            continue
        start_idx = max(0, start_idx)
        end_idx = min(chapter_length - 1, end_idx)
        if end_idx < start_idx:
            skipped += 1
            continue
        present_raw = entry.get("present_characters") or entry.get("presentCharacters") or []
        if not isinstance(present_raw, Sequence) or isinstance(present_raw, (str, bytes)):
            present_raw = []
        present_characters = [str(item).strip() for item in present_raw if str(item).strip()]
        cleaned.append(
            {
                "scene_id": scene_id,
                "location_id": str(entry.get("location_id") or entry.get("locationId") or "").strip(),
                "time_of_day": str(entry.get("time_of_day") or entry.get("timeOfDay") or "").strip(),
                "weather": str(entry.get("weather") or "").strip(),
                "mood": str(entry.get("mood") or "").strip(),
                "present_characters": present_characters,
                "sentence_range": [start_idx, end_idx],
                "base_image_path": str(entry.get("base_image_path") or entry.get("baseImagePath") or "").strip(),
            }
        )
        seen_ids.add(scene_id)

    if not cleaned:
        fallback = {
            "scene_id": f"chapter_{chapter_index:02d}_scene_01",
            "location_id": "",
            "time_of_day": "",
            "weather": "",
            "mood": "",
            "present_characters": [],
            "sentence_range": [0, chapter_length - 1],
            "base_image_path": "",
        }
        _atomic_write_json(scenes_root / f"{fallback['scene_id']}.json", fallback)
        logger.warning(
            "Scene detection missing; using fallback scene for chapter %s.",
            chapter_index,
            extra={
                "event": "pipeline.image.visual_canon.scene_fallback",
                "attributes": {
                    "chapter_index": chapter_index,
                    "chapter_length": chapter_length,
                },
                "console_suppress": True,
            },
        )
        return [fallback]

    cleaned.sort(key=lambda payload: payload["sentence_range"][0])
    repaired: list[dict[str, Any]] = []
    expected_start = 0
    repair_needed = skipped > 0

    for payload in cleaned:
        start_idx, end_idx = payload["sentence_range"]
        original_start = start_idx
        original_end = end_idx

        if start_idx > expected_start:
            if repaired:
                previous_end = min(chapter_length - 1, start_idx - 1)
                if repaired[-1]["sentence_range"][1] != previous_end:
                    repaired[-1]["sentence_range"][1] = previous_end
                    repair_needed = True
                expected_start = start_idx
            else:
                start_idx = expected_start
                payload["sentence_range"][0] = start_idx
                repair_needed = True
        if start_idx < expected_start:
            start_idx = expected_start
            payload["sentence_range"][0] = start_idx
            repair_needed = True
        if end_idx < start_idx:
            repair_needed = True
            continue
        if end_idx >= chapter_length:
            end_idx = chapter_length - 1
            payload["sentence_range"][1] = end_idx
            repair_needed = True
        if original_start != start_idx or original_end != end_idx:
            repair_needed = True

        repaired.append(payload)
        expected_start = end_idx + 1
        if expected_start >= chapter_length:
            break

    if not repaired:
        fallback = {
            "scene_id": f"chapter_{chapter_index:02d}_scene_01",
            "location_id": "",
            "time_of_day": "",
            "weather": "",
            "mood": "",
            "present_characters": [],
            "sentence_range": [0, chapter_length - 1],
            "base_image_path": "",
        }
        _atomic_write_json(scenes_root / f"{fallback['scene_id']}.json", fallback)
        return [fallback]

    if expected_start < chapter_length:
        last_end = chapter_length - 1
        if repaired[-1]["sentence_range"][1] != last_end:
            repaired[-1]["sentence_range"][1] = last_end
            repair_needed = True

    for payload in repaired:
        scene_path = scenes_root / f"{payload['scene_id']}.json"
        _atomic_write_json(scene_path, payload)

    if repair_needed:
        logger.warning(
            "Scene ranges repaired for chapter %s.",
            chapter_index,
            extra={
                "event": "pipeline.image.visual_canon.scene_repair",
                "attributes": {
                    "chapter_index": chapter_index,
                    "chapter_length": chapter_length,
                    "scene_count": len(repaired),
                    "skipped": skipped,
                },
                "console_suppress": True,
            },
        )

    return repaired


def _validate_scene_ranges(
    *,
    scenes: Sequence[SceneState],
    chapter_length: int,
) -> None:
    ordered = sorted(scenes, key=lambda scene: scene.sentence_start)
    expected_start = 0
    for scene in ordered:
        if scene.sentence_start != expected_start:
            raise ValueError("Scene boundaries are violated")
        if scene.sentence_end < scene.sentence_start:
            raise ValueError("Scene boundaries are violated")
        expected_start = scene.sentence_end + 1
    if expected_start != chapter_length:
        raise ValueError("Scene boundaries are violated")


class VisualPromptOrchestrator:
    """Build prompts using the visual canon + scene state pipeline."""

    def __init__(
        self,
        *,
        job_root: Path,
        media_metadata: Mapping[str, Any],
        full_sentences: Sequence[str],
        content_index: Optional[Mapping[str, Any]] = None,
        scope_start_sentence: Optional[int] = None,
        scope_end_sentence: Optional[int] = None,
        lazy_scenes: bool = False,
    ) -> None:
        self._job_root = job_root
        self._media_metadata = dict(media_metadata)
        self._full_sentences = list(full_sentences)
        self._content_index = dict(content_index) if isinstance(content_index, Mapping) else None
        self._scope_start_sentence = scope_start_sentence
        self._scope_end_sentence = scope_end_sentence
        self._lazy_scenes = bool(lazy_scenes)
        self._lock = threading.Lock()
        self._prepared = False
        self._visual_canon: Optional[VisualCanon] = None
        self._character_tokens: dict[str, str] = {}
        self._character_lookup: dict[str, str] = {}
        self._location_lookup: dict[str, str] = {}
        self._chapters: list[dict[str, Any]] = []
        self._scene_by_sentence: dict[int, SceneState] = {}
        self._scene_by_id: dict[str, SceneState] = {}
        self._scenes_ready_by_chapter: set[int] = set()
        self._last_sentence_number: Optional[int] = None
        self._last_sentence_text: Optional[str] = None
        self._img2img_available = True

    @property
    def img2img_available(self) -> bool:
        return self._img2img_available

    def mark_img2img_unavailable(self) -> None:
        self._img2img_available = False

    def prepare(self) -> None:
        if self._prepared:
            return
        canon = _resolve_visual_canon(
            job_root=self._job_root,
            media_metadata=self._media_metadata,
            full_sentences=self._full_sentences,
        )
        tokens = _build_character_tokens(canon.characters)
        if not tokens:
            raise ValueError("Character tokens missing")

        self._visual_canon = canon
        self._character_tokens = tokens
        self._character_lookup = {
            _normalize_id(key): key for key in canon.characters.keys()
        }
        self._location_lookup = {
            _normalize_id(key): key for key in canon.locations.keys()
        }

        chapters = self._resolve_chapters()
        self._chapters = chapters
        self._scene_by_sentence = {}
        self._scene_by_id = {}
        self._scenes_ready_by_chapter = set()
        if not self._lazy_scenes:
            for chapter in chapters:
                self._add_scenes_for_chapter(chapter)
        self._prepared = True

    def _resolve_chapters(self) -> list[dict[str, Any]]:
        total_sentences = len(self._full_sentences)
        if total_sentences <= 0:
            return []
        scope_start = self._scope_start_sentence
        scope_end = self._scope_end_sentence
        try:
            scope_start = int(scope_start) if scope_start is not None else 1
        except (TypeError, ValueError):
            scope_start = 1
        try:
            scope_end = int(scope_end) if scope_end is not None else total_sentences
        except (TypeError, ValueError):
            scope_end = total_sentences
        scope_start = max(1, min(scope_start, total_sentences))
        scope_end = max(1, min(scope_end, total_sentences))
        if scope_start > scope_end:
            scope_start = 1
            scope_end = total_sentences
        full_scope = scope_start == 1 and scope_end == total_sentences
        chapters_payload = []
        if self._content_index:
            chapters = self._content_index.get("chapters")
            if isinstance(chapters, list):
                for index, entry in enumerate(chapters, start=1):
                    if not isinstance(entry, Mapping):
                        continue
                    start_sentence = entry.get("start_sentence")
                    end_sentence = entry.get("end_sentence")
                    try:
                        start_idx = int(start_sentence)
                        end_idx = int(end_sentence)
                    except (TypeError, ValueError):
                        continue
                    if start_idx < 1 or end_idx < start_idx or start_idx > total_sentences:
                        continue
                    end_idx = min(end_idx, total_sentences)
                    chapters_payload.append(
                        {
                            "index": index,
                            "start_sentence": start_idx,
                            "end_sentence": end_idx,
                            "sentences": self._full_sentences[start_idx - 1 : end_idx],
                        }
                    )
        if chapters_payload:
            ordered = sorted(chapters_payload, key=lambda chapter: chapter["start_sentence"])
            if full_scope:
                expected_start = 1
                valid = True
                for chapter in ordered:
                    if chapter["start_sentence"] != expected_start:
                        valid = False
                        break
                    expected_start = int(chapter["end_sentence"]) + 1
                if expected_start != total_sentences + 1:
                    valid = False
                if not valid:
                    chapters_payload = []
                else:
                    chapters_payload = ordered
            else:
                scoped = [
                    chapter
                    for chapter in ordered
                    if chapter["end_sentence"] >= scope_start
                    and chapter["start_sentence"] <= scope_end
                ]
                if scoped and self._chapters_cover_scope(scoped, scope_start, scope_end):
                    chapters_payload = scoped
                else:
                    chapters_payload = []
        if not chapters_payload:
            start_sentence = scope_start if not full_scope else 1
            end_sentence = scope_end if not full_scope else total_sentences
            chapters_payload.append(
                {
                    "index": 1,
                    "start_sentence": start_sentence,
                    "end_sentence": end_sentence,
                    "sentences": self._full_sentences[start_sentence - 1 : end_sentence],
                }
            )
        return chapters_payload

    def _chapters_cover_scope(
        self,
        chapters: Sequence[Mapping[str, Any]],
        scope_start: int,
        scope_end: int,
    ) -> bool:
        expected_start = scope_start
        last_end: Optional[int] = None
        for chapter in chapters:
            try:
                start_idx = int(chapter.get("start_sentence"))
                end_idx = int(chapter.get("end_sentence"))
            except (TypeError, ValueError):
                return False
            if last_end is not None and start_idx <= last_end:
                return False
            if start_idx > expected_start:
                return False
            if end_idx < expected_start:
                return False
            last_end = end_idx
            expected_start = end_idx + 1
            if expected_start > scope_end:
                return True
        return expected_start > scope_end

    def _find_chapter_for_sentence(self, sentence_number: int) -> Optional[dict[str, Any]]:
        for chapter in self._chapters:
            if chapter["start_sentence"] <= sentence_number <= chapter["end_sentence"]:
                return chapter
        return None

    def _match_canonical_id(self, raw_id: str, lookup: Mapping[str, str]) -> Optional[str]:
        if not lookup:
            return None
        normalized = _normalize_id(raw_id)
        if not normalized:
            return None
        direct = lookup.get(normalized)
        if direct:
            return direct
        norm_tokens = set(normalized.split("_"))
        best_key: Optional[str] = None
        best_score = 0.0
        best_norm = ""
        for canon_norm, canon_key in lookup.items():
            if not canon_norm:
                continue
            canon_tokens = set(canon_norm.split("_"))
            if not canon_tokens:
                continue
            overlap = norm_tokens & canon_tokens
            score = 0.0
            if overlap:
                score = len(overlap) / len(canon_tokens)
            if canon_norm in normalized or normalized in canon_norm:
                score = max(score, 0.75)
            if score > best_score or (
                score == best_score and score > 0 and len(canon_norm) > len(best_norm)
            ):
                best_score = score
                best_key = canon_key
                best_norm = canon_norm
        if best_score >= 0.6:
            return best_key
        return None

    def _resolve_character_id(self, raw_id: str) -> Optional[str]:
        return self._match_canonical_id(raw_id, self._character_lookup)

    def _resolve_location_id(self, raw_id: str) -> Optional[str]:
        return self._match_canonical_id(raw_id, self._location_lookup)

    def _add_scenes_for_chapter(self, chapter: Mapping[str, Any]) -> None:
        try:
            chapter_index = int(chapter.get("index") or 0)
        except (TypeError, ValueError):
            chapter_index = 0
        if chapter_index <= 0:
            raise ValueError("Chapter index missing")
        chapter_start = int(chapter["start_sentence"])
        chapter_sentences = chapter["sentences"]
        scenes_payload = _resolve_scenes_for_chapter(
            job_root=self._job_root,
            chapter_index=chapter_index,
            chapter_sentences=chapter_sentences,
            character_ids=list(self._visual_canon.characters.keys()) if self._visual_canon else (),
            location_ids=list(self._visual_canon.locations.keys()) if self._visual_canon else (),
        )
        scenes_state: list[SceneState] = []
        for entry in scenes_payload:
            if not isinstance(entry, Mapping):
                continue
            sentence_range = entry.get("sentence_range") or entry.get("sentenceRange")
            if (
                not isinstance(sentence_range, Sequence)
                or isinstance(sentence_range, (str, bytes))
                or len(sentence_range) != 2
            ):
                raise ValueError("Scene sentence_range missing or invalid")
            start_idx = int(sentence_range[0])
            end_idx = int(sentence_range[1])
            if start_idx < 0 or end_idx < 0:
                raise ValueError("Scene sentence_range missing or invalid")
            if start_idx > end_idx:
                raise ValueError("Scene boundaries are violated")
            if end_idx >= len(chapter_sentences):
                raise ValueError("Scene boundaries are violated")
            scene_id = str(entry.get("scene_id") or entry.get("sceneId") or "").strip()
            if not scene_id:
                raise ValueError("Scene scene_id missing")
            present_raw = entry.get("present_characters") or entry.get("presentCharacters") or []
            if not isinstance(present_raw, Sequence) or isinstance(present_raw, (str, bytes)):
                present_raw = []
            raw_characters = [str(item).strip() for item in present_raw if str(item).strip()]
            mapped_characters: list[str] = []
            unknown_characters: list[str] = []
            for raw_id in raw_characters:
                resolved = self._resolve_character_id(raw_id)
                if resolved:
                    mapped_characters.append(resolved)
                else:
                    unknown_characters.append(raw_id)
            if unknown_characters:
                logger.warning(
                    "Scene characters not found in visual canon.",
                    extra={
                        "event": "pipeline.image.visual_canon.character_mapping",
                        "attributes": {
                            "chapter_index": chapter_index,
                            "scene_id": str(entry.get("scene_id") or entry.get("sceneId") or ""),
                            "unknown_characters": unknown_characters,
                        },
                        "console_suppress": True,
                    },
                )
            present_characters = tuple(mapped_characters)
            location_id_raw = str(entry.get("location_id") or entry.get("locationId") or "").strip()
            resolved_location = self._resolve_location_id(location_id_raw)
            if resolved_location:
                location_id = resolved_location
            else:
                location_id = ""
                if location_id_raw and self._location_lookup:
                    logger.warning(
                        "Scene location not found in visual canon.",
                        extra={
                            "event": "pipeline.image.visual_canon.location_mapping",
                            "attributes": {
                                "chapter_index": chapter_index,
                                "scene_id": str(entry.get("scene_id") or entry.get("sceneId") or ""),
                                "unknown_location": location_id_raw,
                            },
                            "console_suppress": True,
                        },
                    )
            time_of_day = str(entry.get("time_of_day") or entry.get("timeOfDay") or "").strip()
            weather = str(entry.get("weather") or "").strip()
            mood = str(entry.get("mood") or "").strip()
            base_image_path = str(entry.get("base_image_path") or entry.get("baseImagePath") or "").strip()
            global_start = chapter_start + start_idx
            global_end = chapter_start + end_idx
            scene_path = (self._job_root / "metadata" / "scenes" / f"{scene_id}.json")
            if (
                location_id != location_id_raw
                or list(present_characters) != raw_characters
            ):
                updated = dict(entry)
                updated["location_id"] = location_id
                updated["present_characters"] = list(present_characters)
                _atomic_write_json(scene_path, updated)
            scenes_state.append(
                SceneState(
                    scene_id=scene_id,
                    location_id=location_id,
                    time_of_day=time_of_day,
                    weather=weather,
                    mood=mood,
                    present_characters=present_characters,
                    sentence_start=start_idx,
                    sentence_end=end_idx,
                    chapter_start_sentence=chapter_start,
                    global_start_sentence=global_start,
                    global_end_sentence=global_end,
                    base_image_path=base_image_path,
                    scene_path=scene_path,
                )
            )

        _validate_scene_ranges(scenes=scenes_state, chapter_length=len(chapter_sentences))

        with self._lock:
            if chapter_index in self._scenes_ready_by_chapter:
                return
            for scene in scenes_state:
                for sentence_number in range(scene.global_start_sentence, scene.global_end_sentence + 1):
                    if sentence_number in self._scene_by_sentence:
                        raise ValueError("Scene boundaries are violated")
                    self._scene_by_sentence[sentence_number] = scene
                self._scene_by_id[scene.scene_id] = scene
            self._scenes_ready_by_chapter.add(chapter_index)

    def _ensure_scenes_for_sentence(self, sentence_number: int) -> None:
        if sentence_number in self._scene_by_sentence:
            return
        chapter = self._find_chapter_for_sentence(sentence_number)
        if chapter is None:
            raise ValueError("Scene boundaries are violated")
        self._add_scenes_for_chapter(chapter)
        if sentence_number not in self._scene_by_sentence:
            raise ValueError("Scene boundaries are violated")

    def build_sentence_prompt(self, *, sentence_number: int, sentence_text: str) -> VisualPromptResult:
        if not self._prepared or self._visual_canon is None:
            raise ValueError("Visual canon missing")

        self._ensure_scenes_for_sentence(sentence_number)
        scene = self._scene_by_sentence.get(sentence_number)
        if scene is None:
            raise ValueError("Scene boundaries are violated")

        previous_sentence: Optional[str] = None
        with self._lock:
            if self._last_sentence_number == sentence_number - 1:
                previous_sentence = self._last_sentence_text

        current_text = _truncate_for_tokens(sentence_text, 60)
        previous_text = _truncate_for_tokens(previous_sentence or "", 60) if previous_sentence else None
        if previous_text and (_approx_token_count(previous_text) + _approx_token_count(current_text) > 60):
            previous_text = None

        system_prompt = (
            "Extract only what visually changes now.\n"
            "Allowed: action, movement, facial expression, interaction, pose change.\n"
            "Forbidden: hair, face, ethnicity, clothing, body type, age, location, environment, static traits.\n"
            "Return JSON only with key: sentence_delta.\n"
        )
        if previous_text:
            user_prompt = f"Previous sentence: {previous_text}\nCurrent sentence: {current_text}"
        else:
            user_prompt = current_text

        with client_scope(None) as client:
            response = client.send_chat_request(
                {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.2, "top_p": 0.9},
                },
                timeout=int(_SENTENCE_DELTA_TIMEOUT_SECONDS),
            )
        raw = response.text.strip() if response.text else ""
        if response.error:
            raise ValueError(response.error)
        payload = _extract_json_payload(raw)
        if not isinstance(payload, Mapping):
            raise ValueError("Sentence delta response was not a JSON object")
        delta = str(payload.get("sentence_delta") or payload.get("sentenceDelta") or "").strip()
        if not delta:
            delta = _fallback_sentence_delta()
            logger.warning(
                "Sentence delta missing; using fallback.",
                extra={
                    "event": "pipeline.image.visual_canon.delta_fallback",
                    "attributes": {
                        "sentence_number": sentence_number,
                        "reason": "missing",
                    },
                    "console_suppress": True,
                },
            )
        else:
            try:
                _validate_sentence_delta(delta)
            except ValueError:
                sanitized = _sanitize_sentence_delta(delta)
                if sanitized:
                    try:
                        _validate_sentence_delta(sanitized)
                        logger.warning(
                            "Sentence delta sanitized to remove forbidden terms.",
                            extra={
                                "event": "pipeline.image.visual_canon.delta_sanitized",
                                "attributes": {
                                    "sentence_number": sentence_number,
                                    "original": _truncate_for_log(delta),
                                    "sanitized": _truncate_for_log(sanitized),
                                },
                                "console_suppress": True,
                            },
                        )
                        delta = sanitized
                    except ValueError:
                        delta = _fallback_sentence_delta()
                        logger.warning(
                            "Sentence delta still invalid after sanitization; using fallback.",
                            extra={
                                "event": "pipeline.image.visual_canon.delta_fallback",
                                "attributes": {
                                    "sentence_number": sentence_number,
                                    "reason": "sanitized_invalid",
                                    "original": _truncate_for_log(delta),
                                },
                                "console_suppress": True,
                            },
                        )
                else:
                    delta = _fallback_sentence_delta()
                    logger.warning(
                        "Sentence delta sanitized to empty; using fallback.",
                        extra={
                            "event": "pipeline.image.visual_canon.delta_fallback",
                            "attributes": {
                                "sentence_number": sentence_number,
                                "reason": "sanitized_empty",
                                "original": _truncate_for_log(delta),
                            },
                            "console_suppress": True,
                        },
                    )

        canon = self._visual_canon
        style_text = _format_style(canon.style)
        if not style_text:
            raise ValueError("Visual canon style missing")

        location_lookup = {
            _normalize_id(key): key for key in canon.locations.keys()
        }
        location_key = location_lookup.get(_normalize_id(scene.location_id or ""))
        location_payload = canon.locations.get(location_key or "")
        if not isinstance(location_payload, Mapping):
            location_payload = {}
        location_text = _format_location(location_payload)

        character_tokens = []
        for raw_id in scene.present_characters:
            normalized = _normalize_id(raw_id)
            token = self._character_tokens.get(normalized)
            if not token:
                raise ValueError("Character tokens missing")
            character_tokens.append(token)
        characters_text = " ".join(character_tokens)

        time_mood_text = ", ".join(
            part
            for part in (
                _collapse_whitespace(scene.time_of_day),
                _collapse_whitespace(scene.weather),
                _collapse_whitespace(scene.mood),
            )
            if part
        )

        positive_prompt = ", ".join(
            part
            for part in (
                style_text,
                location_text,
                characters_text,
                time_mood_text,
                delta,
            )
            if part
        )

        generation_mode = "txt2img" if sentence_number == scene.global_start_sentence else "img2img"
        reuse_previous_image = generation_mode == "img2img"
        init_image = None
        if reuse_previous_image:
            if not self._img2img_available:
                raise ValueError("txt2img used mid-scene")
            init_image = scene.last_image_path
            if init_image is None:
                raise ValueError("txt2img used mid-scene")

        with self._lock:
            self._last_sentence_number = sentence_number
            self._last_sentence_text = sentence_text

        chapter_relative_index = sentence_number - scene.chapter_start_sentence
        return VisualPromptResult(
            scene_id=scene.scene_id,
            sentence_index=chapter_relative_index,
            sentence_delta=delta,
            positive_prompt=positive_prompt,
            negative_prompt=GLOBAL_NEGATIVE_CANON,
            generation_mode=generation_mode,
            init_image=init_image,
            denoise_strength=_IMG2IMG_DENOISE,
            reuse_previous_image=reuse_previous_image,
        )

    def record_image_path(self, *, sentence_number: int, relative_path: str, image_path: Path) -> None:
        scene = self._scene_by_sentence.get(sentence_number)
        if scene is None:
            return
        scene.last_image_path = image_path
        if sentence_number == scene.global_start_sentence:
            scene.base_image_path = relative_path
            if scene.scene_path is not None:
                payload = _load_json(scene.scene_path)
                if isinstance(payload, Mapping):
                    updated = dict(payload)
                else:
                    updated = {
                        "scene_id": scene.scene_id,
                        "location_id": scene.location_id,
                        "time_of_day": scene.time_of_day,
                        "weather": scene.weather,
                        "mood": scene.mood,
                        "present_characters": list(scene.present_characters),
                        "sentence_range": [scene.sentence_start, scene.sentence_end],
                    }
                updated["base_image_path"] = relative_path
                _atomic_write_json(scene.scene_path, updated)
