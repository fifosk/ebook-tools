from modules import language_policies, prompt_templates, translation_engine

import pytest

pytestmark = pytest.mark.translation


def test_script_policy_shared_across_prompt_and_validation():
    policy = language_policies.script_policy_for("Kannada")
    assert policy is not None

    prompt = prompt_templates.make_translation_prompt("English", "Kannada")
    assert policy.instruction in prompt
    assert language_policies.SCRIPT_ENFORCEMENT_SUFFIX in prompt

    mismatch, label = translation_engine._unexpected_script_used("Привет", "Kannada")
    assert mismatch is True
    assert policy.script_label in (label or "")


def test_non_latin_hints_cover_policy_aliases():
    assert language_policies.is_non_latin_language_hint("Punjabi")
    assert language_policies.is_non_latin_language_hint("uk")  # Ukrainian alias
