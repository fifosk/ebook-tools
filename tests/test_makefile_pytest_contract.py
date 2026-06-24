from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
TESTING_DOC = ROOT / "docs" / "testing.md"
GITIGNORE = ROOT / ".gitignore"


def _target_body(makefile: str, target: str) -> str:
    return makefile.split(f"{target}:", 1)[1].split("\n\n", 1)[0]


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
        "test-library",
        "test-observability",
        "test-e2e",
        "test-e2e-headless",
        "test-e2e-web",
        "test-e2e-web-headless",
    ]:
        assert "$(PYTHON) -m pytest" in _target_body(makefile, target)


def test_testing_docs_note_makefile_python_selection() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")
    normalized_docs = re.sub(r"\s+", " ", docs)

    assert "Makefile pytest targets run through `$(PYTHON) -m pytest`" in normalized_docs
    assert "`.venv/bin/python` when available" in normalized_docs


def test_generated_e2e_artifacts_do_not_dirty_source_sync() -> None:
    gitignore = GITIGNORE.read_text(encoding="utf-8")

    assert "test-results/" in gitignore
    assert "!test-results/*-e2e-report.md" not in gitignore
