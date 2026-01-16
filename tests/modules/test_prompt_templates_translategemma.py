from modules import prompt_templates


def test_translategemma_completion_payload_for_lmstudio():
    payload, system_prompt, request_mode = prompt_templates.make_translation_payload(
        "Hello world",
        "English",
        "French",
        model="translategemma-2",
        stream=False,
        llm_source="lmstudio",
    )

    assert request_mode == "completion"
    assert system_prompt is None
    assert payload["prompt"].startswith("<bos><start_of_turn>user")
    assert payload["stop"] == ["<end_of_turn>"]
    assert "English (en) to French (fr)" in payload["prompt"]


def test_translategemma_chat_payload_for_non_lmstudio():
    payload, system_prompt, request_mode = prompt_templates.make_translation_payload(
        "Hello world",
        "English",
        "French",
        model="translategemma-2",
        stream=False,
        llm_source="local",
    )

    assert request_mode == "chat"
    assert system_prompt is None
    messages = payload["messages"]
    assert len(messages) == 1
    user_message = messages[0]
    assert user_message["role"] == "user"
    content = user_message["content"]
    assert isinstance(content, list)
    assert len(content) == 1
    content_item = content[0]
    assert content_item["type"] == "text"
    assert content_item["source_lang_code"] == "en"
    assert content_item["target_lang_code"] == "fr"
    assert content_item["text"] == "Hello world"


def test_translategemma_payload_falls_back_for_unsupported_language():
    payload, system_prompt, request_mode = prompt_templates.make_translation_payload(
        "Hello world",
        "Romani",
        "English",
        model="translategemma-2",
        stream=False,
        llm_source="lmstudio",
    )

    assert request_mode == "completion"
    assert system_prompt is None
    assert "Romani (rom)" in payload["prompt"]
