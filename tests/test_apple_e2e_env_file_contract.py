from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
TESTING_DOC = ROOT / "docs" / "testing.md"


def test_apple_e2e_makefile_uses_configurable_env_file() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "E2E_ENV_FILE ?= $(if $(wildcard .env),.env,$(if $(wildcard .env.local),.env.local,.env))" in makefile
    assert '$(PYTHON) scripts/write_apple_e2e_config.py \\' in makefile
    assert '--env-file "$(E2E_ENV_FILE)"' in makefile
    assert '$(PYTHON) scripts/check_apple_create_readiness.py --env-file "$(E2E_ENV_FILE)"' in makefile
    assert '$(PYTHON) scripts/with_simulator_lock.py -- $(XCBUILD) test \\' in makefile
    assert "--env-file .env \\" not in makefile
    assert "scripts/check_apple_create_readiness.py\n" not in makefile


def test_testing_docs_describe_e2e_env_file_override() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")

    assert "E2E_ENV_FILE" in docs
    assert ".env.local" in docs
    assert "make test-e2e-ipad-create-readiness" in docs
