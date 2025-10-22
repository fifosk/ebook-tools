import re
from typing import Any, Dict, List

import pytest


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

    return overrides
