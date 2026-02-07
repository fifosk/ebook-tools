import re
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

# Configure HuggingFace cache to use external SSD BEFORE any HF imports
# This must happen at module load time, before pytest collects tests
from modules.core.storage_config import configure_hf_environment
configure_hf_environment()


@pytest.fixture(autouse=True, scope="session")
def _disable_ramdisk_globally():
    """Prevent tests from mounting/unmounting real RAMDisks.

    RAMDisk lifecycle is exclusively owned by the API application.  Tests must
    never trigger ``diskutil`` subprocess calls.  Individual tests that need to
    exercise RAMDisk logic should mock at the ``runtime.ramdisk_manager`` level
    (as ``test_runtime_tmp_dir.py`` does) — ``monkeypatch`` overrides this
    session-scoped patch for the duration of that test.
    """
    import modules.ramdisk_manager as rm

    with (
        patch.object(rm, "ensure_ramdisk", return_value=False),
        patch.object(rm, "teardown_ramdisk"),
        patch.object(rm, "is_mounted", return_value=False),
    ):
        yield


def pytest_addoption(parser: pytest.Parser) -> None:  # type: ignore[attr-defined]
    group = parser.getgroup("epub-job")
    group.addoption(
        "--sample-sentence-count",
        action="store",
        type=int,
        dest="sample_sentence_count",
        help=(
            "Number of sentences to request from Ollama when generating the sample EPUB."
        ),
    )
    group.addoption(
        "--sample-input-language",
        action="store",
        dest="sample_input_language",
        help="Input language to assign to the generated EPUB sentences.",
    )
    group.addoption(
        "--sample-target-language",
        action="append",
        dest="sample_target_language",
        help=(
            "Target language(s) to include in the test payload. Repeat the option or "
            "provide a comma/semicolon separated list."
        ),
    )
    group.addoption(
        "--sample-topic",
        action="store",
        dest="sample_topic",
        help="Topic to describe in the generated sample sentences.",
    )

    # CJK tokenization test options
    cjk_group = parser.getgroup("cjk-tokenization")
    cjk_group.addoption(
        "--run-llm",
        action="store_true",
        default=False,
        help="Run tests that require a real LLM connection",
    )
    cjk_group.addoption(
        "--llm-model",
        action="store",
        default=None,
        help="LLM model to use for translation (e.g., mistral:latest)",
    )
    cjk_group.addoption(
        "--save-report",
        action="store",
        default=None,
        help="Path to save JSON test report",
    )


@pytest.fixture(scope="session")
def epub_job_cli_overrides(pytestconfig: pytest.Config) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}

    sentence_count = pytestconfig.getoption("sample_sentence_count")
    if sentence_count is not None:
        overrides["test_sentence_count"] = sentence_count

    languages: List[str] = []
    for raw_value in pytestconfig.getoption("sample_target_language") or []:
        if not raw_value:
            continue
        languages.extend(
            part.strip()
            for part in re.split(r"[,;]", str(raw_value))
            if part and part.strip()
        )
    if languages:
        overrides["test_target_languages"] = languages

    topic = pytestconfig.getoption("sample_topic")
    if topic:
        overrides["test_sentence_topic"] = str(topic).strip()

    input_language = pytestconfig.getoption("sample_input_language")
    if input_language:
        overrides["input_language"] = str(input_language).strip()

    return overrides
