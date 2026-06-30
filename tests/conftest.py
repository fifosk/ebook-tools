import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

# Register E2E report plugin early so --e2e-report CLI flag is available
pytest_plugins = ["tests.e2e.report"]

# Configure HuggingFace cache to use external SSD BEFORE any HF imports
# This must happen at module load time, before pytest collects tests
from modules.core.storage_config import configure_hf_environment


_TEST_HF_CACHE_PATH = Path(tempfile.gettempdir()) / "ebook-tools-test-hf-cache"


def _is_writable_directory(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix=".write-check-", dir=path):
            pass
    except OSError:
        return False
    return True


def _prepare_hf_cache_for_tests() -> None:
    """Use a writable local HF cache when workstation env points at offline media."""
    configured_path = os.environ.get("EBOOK_HF_CACHE_PATH")
    if configured_path and _is_writable_directory(Path(configured_path)):
        return

    fallback_path = Path(
        os.environ.get("EBOOK_TEST_HF_CACHE_PATH", str(_TEST_HF_CACHE_PATH))
    )
    if not _is_writable_directory(fallback_path):
        return

    os.environ["EBOOK_HF_CACHE_PATH"] = str(fallback_path)

    for key in ("HF_HOME", "HUGGINGFACE_HUB_CACHE", "HF_DATASETS_CACHE"):
        existing_path = os.environ.get(key)
        if existing_path and _is_writable_directory(Path(existing_path)):
            continue
        os.environ.pop(key, None)


_prepare_hf_cache_for_tests()
configure_hf_environment()

APPLE_MARKER_FILE_NAMES = {
    "test_language_catalog_parity.py",
    "test_release_version_contract.py",
}

APPLE_MARKER_SCRIPT_NAMES = {
    "test_apple_full_entitlement_signing_plan.py",
    "test_apple_merge_entitlements.py",
    "test_apple_pull_device_playback_log.py",
    "test_check_apple_create_readiness.py",
    "test_check_apple_playback_transport_log.py",
    "test_check_poc_readiness.py",
    "test_generate_language_catalogs.py",
    "test_ios_profile_capability_check.py",
    "test_write_apple_e2e_config.py",
}


def _is_apple_contract_path(path: Path) -> bool:
    if path.name.startswith("test_apple_"):
        return True
    if path.parent.name == "scripts" and path.name in APPLE_MARKER_SCRIPT_NAMES:
        return True
    return path.name in APPLE_MARKER_FILE_NAMES


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    apple_marker = pytest.mark.apple
    for item in items:
        path = Path(str(item.path))
        if _is_apple_contract_path(path):
            item.add_marker(apple_marker)


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
