from __future__ import annotations

from contextlib import contextmanager
import json

import pytest

from modules.images import prompting

pytestmark = pytest.mark.pipeline


class _DummyResponse:
    def __init__(self, text: str, *, error: str | None = None) -> None:
        self.text = text
        self.error = error


class _DummyClient:
    def __init__(self) -> None:
        self.payloads: list[dict] = []

    def send_chat_request(self, payload: dict, *, timeout: int) -> _DummyResponse:
        user_message = payload["messages"][1]["content"]
        start = user_message.find("{")
        end = user_message.rfind("}")
        request_payload = json.loads(user_message[start : end + 1])
        self.payloads.append(request_payload)

        sentences = request_payload.get("sentences") or []
        prompts: list[dict] = []
        for index, sentence in enumerate(sentences):
            cleaned = (sentence or "").strip()
            prompts.append(
                {
                    "index": index,
                    "prompt": cleaned or f"scene {index}",
                    "negative_prompt": "",
                }
            )

        response_payload = {
            "continuity_bible": "Keep the main characters visually consistent.",
            "prompts": prompts,
        }
        return _DummyResponse(json.dumps(response_payload, ensure_ascii=False))


class _MissingRetryClient:
    def __init__(self) -> None:
        self.payloads: list[dict] = []

    def send_chat_request(self, payload: dict, *, timeout: int) -> _DummyResponse:
        user_message = payload["messages"][1]["content"]
        start = user_message.find("{")
        end = user_message.rfind("}")
        request_payload = json.loads(user_message[start : end + 1])
        self.payloads.append(request_payload)

        if "missing" in request_payload:
            prompts: list[dict] = []
            for item in request_payload.get("missing") or []:
                index = item.get("index")
                prompts.append({"index": index, "prompt": f"retry {index}", "negative_prompt": ""})
            response_payload = {"continuity_bible": "Retry continuity.", "prompts": prompts}
            return _DummyResponse(json.dumps(response_payload, ensure_ascii=False))

        sentences = request_payload.get("sentences") or []
        prompts = []
        for index, sentence in enumerate(sentences):
            if index == 3:
                continue
            prompts.append({"index": index, "prompt": (sentence or "").strip(), "negative_prompt": ""})
        response_payload = {"continuity_bible": "Initial continuity.", "prompts": prompts}
        return _DummyResponse(json.dumps(response_payload, ensure_ascii=False))


def test_build_sentence_image_prompt_appends_story_reel_suffix() -> None:
    prompt = prompting.build_sentence_image_prompt("A child runs through a forest at dusk")
    assert "photorealistic cinematic film still" in prompt


def test_build_sentence_image_prompt_supports_style_templates() -> None:
    prompt = prompting.build_sentence_image_prompt(
        "A child runs through a forest at dusk",
        style_template="comics",
    )
    assert "graphic novel illustration" in prompt
    assert "photorealistic cinematic film still" not in prompt


def test_build_sentence_image_prompt_does_not_double_append() -> None:
    base = "A child runs through a forest at dusk, photorealistic cinematic film still"
    assert prompting.build_sentence_image_prompt(base) == base


def test_build_sentence_image_prompt_respects_legacy_glyph_style() -> None:
    legacy = "glyph-style clipart icon, simple scene"
    assert prompting.build_sentence_image_prompt(legacy) == legacy


def test_build_sentence_image_negative_prompt_appends_base() -> None:
    negative = prompting.build_sentence_image_negative_prompt("")
    assert "watermark" in negative.lower()


def test_build_sentence_image_negative_prompt_supports_style_templates() -> None:
    negative = prompting.build_sentence_image_negative_prompt("", style_template="wireframe")
    assert "blueprint" in prompting.build_sentence_image_prompt("", style_template="wireframe").lower()
    assert "watermark" in negative.lower()


def test_sentences_to_diffusion_prompt_map_chunks_and_threads_continuity(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_client = _DummyClient()

    @contextmanager
    def scope(_client):  # noqa: ANN001 - signature must match client_scope
        yield dummy_client

    monkeypatch.setattr(prompting, "client_scope", scope)

    sentences = [f"Sentence {idx}" for idx in range(100)]
    planned = prompting.sentences_to_diffusion_prompt_map(sentences)

    assert len(planned) == 100
    assert planned[0].prompt == "Sentence 0"
    assert planned[-1].prompt == "Sentence 99"
    assert len(dummy_client.payloads) == 2
    assert dummy_client.payloads[0].get("continuity_bible") == ""
    assert dummy_client.payloads[1].get("continuity_bible") == "Keep the main characters visually consistent."


def test_prompt_map_retries_missing_indices(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_client = _MissingRetryClient()

    @contextmanager
    def scope(_client):  # noqa: ANN001 - signature must match client_scope
        yield dummy_client

    monkeypatch.setattr(prompting, "client_scope", scope)

    sentences = [f"Sentence {idx}" for idx in range(10)]
    plan = prompting.sentences_to_diffusion_prompt_plan(sentences)

    assert len(plan.prompts) == 10
    assert plan.sources[3] == "llm_retry"
    assert plan.prompts[3].prompt == "retry 3"
    assert plan.quality["initial_missing"] == 1
    assert plan.quality["final_fallback"] == 0
    assert plan.quality["retry_attempts"] == 1
    assert len(dummy_client.payloads) == 2


def test_sentence_batches_to_diffusion_prompt_plan_groups_sentences(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_client = _DummyClient()

    @contextmanager
    def scope(_client):  # noqa: ANN001 - signature must match client_scope
        yield dummy_client

    monkeypatch.setattr(prompting, "client_scope", scope)

    batches = [
        ["Sentence 1", "Sentence 2"],
        ["Sentence 3"],
    ]

    plan = prompting.sentence_batches_to_diffusion_prompt_plan(batches)

    assert len(plan.prompts) == 2
    assert len(dummy_client.payloads) == 1
    request_sentences = dummy_client.payloads[0].get("sentences") or []
    assert "Batch narrative" in request_sentences[0]
    assert "Sentence 1" in request_sentences[0]
    assert "Sentence 2" in request_sentences[0]
