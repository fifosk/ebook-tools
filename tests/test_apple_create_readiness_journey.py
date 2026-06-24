from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATE_READINESS_JOURNEY = ROOT / "tests" / "e2e" / "journeys" / "create_readiness.json"
JOURNEY_RUNNER = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReaderUITests"
    / "JourneyRunner.swift"
)


def test_create_readiness_journey_checks_runtime_create_contract() -> None:
    journey = json.loads(CREATE_READINESS_JOURNEY.read_text(encoding="utf-8"))
    steps = journey["steps"]

    settings_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "browseSectionSettingsButton"
    )
    create_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "browseSectionCreateButton"
    )
    runtime_steps = steps[settings_index:create_index]

    assert any(step.get("selector") == "settingsCreateContractRow" for step in runtime_steps)
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/books/options",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/books/jobs",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/pipelines/files",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/subtitles/delete-source",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/subtitles/jobs",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/subtitles/youtube/dub",
        "timeout": 20,
    } in runtime_steps


def test_create_readiness_journey_checks_generated_book_defaults_before_media_modes() -> None:
    journey = json.loads(CREATE_READINESS_JOURNEY.read_text(encoding="utf-8"))
    steps = journey["steps"]

    generated_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "createJobTypePicker"
        and step.get("text") == "Generate"
    )
    narrate_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "createJobTypePicker"
        and step.get("text") == "Narrate EPUB"
    )
    generated_steps = steps[generated_index:narrate_index]

    assert generated_index < narrate_index
    assert {
        "action": "assert_visible",
        "selector": "createBookTopicField",
        "timeout": 15,
    } in generated_steps
    assert {
        "action": "assert_visible",
        "selector": "createBookTitleField",
        "timeout": 15,
    } in generated_steps
    assert {
        "action": "assert_non_empty_value",
        "selector": "createBookAuthorField",
        "placeholder": "Author",
        "timeout": 15,
    } in generated_steps
    assert {
        "action": "enter_text",
        "selector": "createGeneratedSourceBookTitleField",
        "text": "Inferno",
        "timeout": 15,
    } in generated_steps
    assert {
        "action": "assert_value_contains",
        "selector": "createGeneratedSourceBookAuthorField",
        "text": "Dan Brown",
        "timeout": 15,
    } in generated_steps
    assert {
        "action": "enter_text",
        "selector": "createGeneratedSourceBookGenreField",
        "text": "Conspiracy thriller",
        "timeout": 15,
    } in generated_steps
    assert any(step.get("selector") == "createBookSummaryField" for step in generated_steps)
    assert any(step.get("selector") == "createBookSentenceStepper" for step in generated_steps)
    for selector in [
        "createBookAudioModePicker",
        "createBookWrittenModePicker",
        "createBookSentencesPerFileStepper",
        "createBookTranslationBatchSizeStepper",
    ]:
        assert any(
            step.get("action") == "assert_visible"
            and step.get("selector") == selector
            and step.get("timeout") == 15
            for step in generated_steps
        )


def test_create_readiness_journey_checks_subtitle_job_settings_before_youtube() -> None:
    journey = json.loads(CREATE_READINESS_JOURNEY.read_text(encoding="utf-8"))
    steps = journey["steps"]

    subtitle_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "createJobTypePicker"
        and step.get("text") == "Subtitles"
    )
    youtube_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "createJobTypePicker"
        and step.get("text") == "YouTube Dub"
    )
    subtitle_steps = steps[subtitle_index:youtube_index]

    assert subtitle_index < youtube_index
    assert {
        "action": "assert_non_empty_value",
        "selector": "createSubtitleSourcePathField",
        "placeholder": "Server subtitle path",
        "timeout": 25,
        "screenshot": "subtitle_defaults",
    } in subtitle_steps
    for selector in [
        "createSubtitleOutputFormatPicker",
        "createSubtitleWorkerCountStepper",
        "createSubtitleBatchSizeStepper",
        "createSubtitleTranslationProviderPicker",
    ]:
        assert any(
            step.get("action") == "assert_visible"
            and step.get("selector") == selector
            and step.get("timeout") == 15
            for step in subtitle_steps
        )


def test_create_readiness_journey_checks_youtube_job_settings() -> None:
    journey = json.loads(CREATE_READINESS_JOURNEY.read_text(encoding="utf-8"))
    steps = journey["steps"]

    youtube_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "createJobTypePicker"
        and step.get("text") == "YouTube Dub"
    )
    youtube_steps = steps[youtube_index:]

    assert {
        "action": "assert_non_empty_value",
        "selector": "createYoutubeVideoPathField",
        "placeholder": "Video path",
        "timeout": 25,
    } in youtube_steps
    assert {
        "action": "assert_non_empty_value",
        "selector": "createYoutubeSubtitlePathField",
        "placeholder": "Subtitle path",
        "timeout": 25,
        "screenshot": "youtube_dub_defaults",
    } in youtube_steps
    for selector in [
        "createYoutubeTargetHeightPicker",
        "createYoutubeOriginalMixStepper",
        "createYoutubeFlushSentencesStepper",
        "createYoutubeTranslationBatchSizeStepper",
        "createYoutubeSplitBatchesToggle",
        "createYoutubePreserveAspectRatioToggle",
    ]:
        assert any(
            step.get("action") == "assert_visible"
            and step.get("selector") == selector
            and step.get("timeout") == 15
            for step in youtube_steps
        )
    assert any(
        step.get("action") == "assert_visible"
        and step.get("selector") == "createBookOpenWebCreateButton"
        and step.get("timeout") == 15
        for step in youtube_steps
    )


def test_journey_runner_supports_value_contains_assertion() -> None:
    source = JOURNEY_RUNNER.read_text(encoding="utf-8")

    assert 'case "assert_value_contains":' in source
    assert "private func doAssertValueContains(_ step: JourneyStep)" in source
    assert "localizedCaseInsensitiveContains(expectedText)" in source


def test_journey_runner_scrolls_before_visibility_and_text_steps() -> None:
    source = JOURNEY_RUNNER.read_text(encoding="utf-8")

    assert "private func doAssertVisible(_ step: JourneyStep)" in source
    assert "private func doEnterText(_ step: JourneyStep)" in source
    assert "scrollElementIntoView(element, timeout: min(timeout, 4))" in source
    assert "scrollElementIntoView(element, timeout: 1)" in source
