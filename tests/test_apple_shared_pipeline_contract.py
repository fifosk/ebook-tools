from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
CONTRACT_CHECK = ROOT / "scripts" / "check_apple_shared_pipeline_helper.sh"
TESTING_DOC = ROOT / "docs" / "testing.md"
DEVELOPER_DOC = ROOT / "docs" / "developer-guide.md"
PLAN_DOC = ROOT / "docs" / "plans" / "cross-surface-parity-and-optimization.md"


def test_shared_pipeline_make_targets_call_manifest_driven_scripts() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "APPLE_PIPELINE_ROOT ?= /Users/fifo/Projects/home/apple-device-app-pipeline" in makefile
    assert "APPLE_PIPELINE_APP ?= ebook-tools" in makefile
    assert "APPLE_PIPELINE_SMOKE_PROFILE ?= ipados" in makefile
    assert "APPLE_PIPELINE_JOURNEY_PROFILE ?= ipados" in makefile
    assert "apple-pipeline-contracts:" in makefile
    assert 'scripts/run_app_contract_checks.py --app "$(APPLE_PIPELINE_APP)"' in makefile
    assert "apple-pipeline-backend:" in makefile
    assert 'scripts/check_app_backend.py --app "$(APPLE_PIPELINE_APP)"' in makefile
    assert "apple-pipeline-backend-tests:" in makefile
    assert 'scripts/run_app_backend_tests.py --app "$(APPLE_PIPELINE_APP)"' in makefile
    assert "apple-pipeline-source-sync:" in makefile
    assert 'scripts/check_app_source_sync.py --app "$(APPLE_PIPELINE_APP)"' in makefile
    assert "apple-pipeline-web-checks:" in makefile
    assert 'scripts/run_app_web_checks.py --app "$(APPLE_PIPELINE_APP)"' in makefile
    assert "apple-pipeline-simulator-smoke:" in makefile
    assert 'scripts/run_app_simulator_smoke.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_PIPELINE_SMOKE_PROFILE)"' in makefile
    assert "apple-pipeline-simulator-smoke-dry-run:" in makefile
    assert "--profile \"$(APPLE_PIPELINE_SMOKE_PROFILE)\" --dry-run" in makefile
    assert "apple-pipeline-owned-journeys:" in makefile
    assert 'scripts/run_app_owned_journey.py --app "$(APPLE_PIPELINE_APP)" --list' in makefile
    assert "apple-pipeline-owned-journey:" in makefile
    assert "--profile \"$(APPLE_PIPELINE_JOURNEY_PROFILE)\" --use-remote-env" in makefile
    assert "apple-pipeline-owned-journey-dry-run:" in makefile
    assert "--profile \"$(APPLE_PIPELINE_JOURNEY_PROFILE)\" --dry-run" in makefile


def test_shared_pipeline_verification_stays_non_physical() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    target_line = (
        "verify-apple-shared-pipeline: apple-pipeline-contracts "
        "apple-pipeline-backend apple-pipeline-backend-tests apple-pipeline-web-checks"
    )
    assert target_line in makefile

    target = makefile.split("verify-apple-shared-pipeline:", 1)[1].split("\n\n", 1)[0]
    assert "apple-pipeline-backend-tests" in target
    assert "apple-pipeline-web-checks" in target
    assert "apple-pipeline-source-sync" not in target
    assert "apple-device-update" not in target
    assert "run_app_device_deploy.py" not in target
    assert "apple_unattended_device_update.sh" not in target
    assert "devicectl" not in target


def test_shared_pipeline_contract_check_covers_targets() -> None:
    contract_check = CONTRACT_CHECK.read_text(encoding="utf-8")

    assert "run_app_contract_checks.py" in contract_check
    assert "check_app_backend.py" in contract_check
    assert "run_app_backend_tests.py" in contract_check
    assert "check_app_source_sync.py" in contract_check
    assert "run_app_web_checks.py" in contract_check
    assert "run_app_simulator_smoke.py" in contract_check
    assert "run_app_owned_journey.py" in contract_check
    assert "verify-apple-shared-pipeline" in contract_check
    assert "physical-device deployment" in contract_check


def test_docs_publish_shared_pipeline_targets() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")
    developer_doc = DEVELOPER_DOC.read_text(encoding="utf-8")
    plan = PLAN_DOC.read_text(encoding="utf-8")

    for command in [
        "make apple-pipeline-contracts",
        "make apple-pipeline-backend",
        "make apple-pipeline-backend-tests",
        "make apple-pipeline-source-sync",
        "make apple-pipeline-web-checks",
        "make apple-pipeline-simulator-smoke-dry-run",
        "make apple-pipeline-owned-journeys",
        "make apple-pipeline-owned-journey-dry-run",
        "make verify-apple-shared-pipeline",
    ]:
        assert command in docs
        assert command in developer_doc
    assert "shared Apple pipeline preflight targets" in plan
