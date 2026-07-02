import ast
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
TESTING_DOC = ROOT / "docs" / "testing.md"
GITIGNORE = ROOT / ".gitignore"
PYPROJECT = ROOT / "pyproject.toml"
ROOT_CONFTEST = ROOT / "tests" / "conftest.py"
TESTS_DIR = ROOT / "tests"


def _target_body(makefile: str, target: str) -> str:
    return makefile.split(f"{target}:", 1)[1].split("\n\n", 1)[0]


def _conftest_constant_set(name: str) -> set[str]:
    module = ast.parse(ROOT_CONFTEST.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            return set(value)
    raise AssertionError(f"Could not find {name} in {ROOT_CONFTEST}")


def test_pytest_make_targets_use_configured_python() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    bare_pytest_commands = [
        line.strip()
        for line in makefile.splitlines()
        if re.match(r"\s*pytest(?:\s|$)", line)
    ]
    assert bare_pytest_commands == []

    for target in [
        "test",
        "test-fast",
        "test-apple",
        "test-library",
        "test-observability",
        "test-e2e",
        "test-e2e-headless",
        "test-e2e-web",
        "test-e2e-web-headless",
    ]:
        assert "$(PYTHON) -m pytest" in _target_body(makefile, target)
    assert "$(PYTHON) scripts/run_changed_tests.py" in _target_body(
        makefile, "test-changed"
    )
    assert "$(PYTHON) scripts/check_web_e2e_journeys.py" in _target_body(
        makefile, "check-web-e2e-journeys"
    )
    assert "$(PYTHON) -m pytest" in _target_body(makefile, "test-makefile-contract")
    assert "tests/scripts/test_check_web_e2e_journeys.py" in _target_body(
        makefile, "test-makefile-contract"
    )
    assert "tests/test_apple_shared_pipeline_contract.py" in _target_body(
        makefile, "test-makefile-contract"
    )
    assert "tests/test_web_video_dubbing_pipeline_contract.py" in _target_body(
        makefile, "test-makefile-contract"
    )
    assert "tests/scripts/test_run_xcodebuild_e2e.py" in _target_body(
        makefile, "test-makefile-contract"
    )


def test_testing_docs_note_makefile_python_selection() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")
    normalized_docs = re.sub(r"\s+", " ", docs)

    assert "Makefile pytest targets run through `$(PYTHON) -m pytest`" in normalized_docs
    assert "`.venv/bin/python` when available" in normalized_docs
    assert "then the first available Python 3.10+ runtime" in normalized_docs
    assert "`make test-changed` reads staged, unstaged, and untracked Git paths" in docs
    assert "| `make test-changed` | `$(PYTHON) scripts/run_changed_tests.py` |" in docs
    assert "| `make check-web-e2e-journeys` | `$(PYTHON) scripts/check_web_e2e_journeys.py` |" in docs


def test_makefile_python_selector_skips_unsupported_system_python() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    selector = makefile.split("PYTHON ?=", 1)[1].split("APPLE_PIPELINE_ROOT", 1)[0]

    assert ".venv/bin/python" in selector
    assert "python3.13 python3.12 python3.11 python3.10 python3" in selector
    assert "sys.version_info >= (3, 10)" in selector


def test_apple_marker_is_configured_and_collected_by_contract_patterns() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    conftest = ROOT_CONFTEST.read_text(encoding="utf-8")
    docs = TESTING_DOC.read_text(encoding="utf-8")

    assert '"apple: Apple client contracts' in pyproject
    assert "$(PYTHON) -m pytest -m apple" in _target_body(makefile, "test-apple")
    assert "def pytest_collection_modifyitems" in conftest
    assert 'path.name.startswith("test_apple_")' in conftest
    assert '"test_write_apple_e2e_config.py"' in conftest
    assert "| `apple` | Apple |" in docs
    assert "| `make test-apple` | `$(PYTHON) -m pytest -m apple` |" in docs


def test_apple_contract_target_includes_all_apple_marked_contract_files() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    test_apple_contracts = _target_body(makefile, "test-apple-contracts")
    release_version_target = _target_body(makefile, "test-release-version")

    root_contracts = sorted(TESTS_DIR.glob("test_apple_*.py"))
    script_contracts = [
        TESTS_DIR / "scripts" / name
        for name in _conftest_constant_set("APPLE_MARKER_SCRIPT_NAMES")
    ]
    marker_contracts = [
        *(TESTS_DIR / name for name in _conftest_constant_set("APPLE_MARKER_FILE_NAMES")),
        *root_contracts,
        *script_contracts,
    ]

    missing_paths = []
    combined_targets = f"{release_version_target}\n{test_apple_contracts}"
    for path in sorted(set(marker_contracts)):
        relative = path.relative_to(ROOT).as_posix()
        if relative not in combined_targets:
            missing_paths.append(relative)

    assert missing_paths == []


def test_generated_e2e_artifacts_do_not_dirty_source_sync() -> None:
    gitignore = GITIGNORE.read_text(encoding="utf-8")

    assert "test-results/" in gitignore
    assert "!test-results/*-e2e-report.md" not in gitignore


def test_local_checkpoint_bundle_target_uses_repo_python() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    target = _target_body(makefile, "apple-local-checkpoint-bundle")

    assert "$(PYTHON) scripts/write_git_checkpoint_bundle.py" in target
    assert '--base "$(CHECKPOINT_BASE)"' in target
    assert '--output-dir "$(CHECKPOINT_OUTPUT_DIR)"' in target


def test_web_export_player_bundle_is_not_ignored() -> None:
    gitignore = GITIGNORE.read_text(encoding="utf-8")

    assert "web/export-dist/" in gitignore
    assert "!web/export-dist/" in gitignore
    assert "!web/export-dist/assets/" in gitignore
    assert "!web/export-dist/assets/*.js" in gitignore
    assert "!web/export-dist/assets/*.js.map" in gitignore
