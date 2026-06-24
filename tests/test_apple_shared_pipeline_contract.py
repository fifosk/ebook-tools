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
    assert "APPLE_PIPELINE_SMOKE_PROFILES ?= ios ipados tvos" in makefile
    assert "APPLE_PIPELINE_JOURNEY_PROFILE ?= ipados" in makefile
    assert (
        "APPLE_PIPELINE_JOURNEY_PROFILES ?= iphone ipados tvos iphone-create "
        "ipados-create tvos-create ios-uitests-build macos-ipad-style-dry-run macos-ipad-style"
    ) in makefile
    assert "apple-pipeline-contracts:" in makefile
    assert 'scripts/run_app_contract_checks.py --app "$(APPLE_PIPELINE_APP)"' in makefile
    assert "test-apple-language-catalogs:" in makefile
    assert "tests/test_language_catalog_parity.py tests/scripts/test_generate_language_catalogs.py" in makefile
    assert "test-apple-create-readiness-contract:" in makefile
    assert "tests/scripts/test_check_apple_create_readiness.py tests/test_apple_create_readiness_journey.py tests/test_apple_e2e_env_file_contract.py" in makefile
    assert "test-apple-local-surface-contract:" in makefile
    assert "tests/test_apple_ios_build_contract.py tests/test_apple_tvos_build_contract.py tests/test_apple_macos_ipad_style_contract.py tests/test_apple_local_surface_build_contract.py" in makefile
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
    assert "apple-pipeline-simulator-smokes-dry-run:" in makefile
    assert '$(MAKE) apple-pipeline-simulator-smoke-dry-run APPLE_PIPELINE_SMOKE_PROFILE="$$profile"' in makefile
    assert "apple-pipeline-owned-journeys:" in makefile
    assert 'scripts/run_app_owned_journey.py --app "$(APPLE_PIPELINE_APP)" --list' in makefile
    assert "apple-pipeline-owned-journey:" in makefile
    assert "--profile \"$(APPLE_PIPELINE_JOURNEY_PROFILE)\" --use-remote-env" in makefile
    assert "apple-pipeline-owned-journey-dry-run:" in makefile
    assert "--profile \"$(APPLE_PIPELINE_JOURNEY_PROFILE)\" --dry-run" in makefile
    assert "apple-pipeline-owned-journeys-dry-run:" in makefile
    assert '$(MAKE) apple-pipeline-owned-journey-dry-run APPLE_PIPELINE_JOURNEY_PROFILE="$$profile"' in makefile
    assert "apple-pipeline-ipad-create-readiness:" in makefile
    assert "$(MAKE) apple-pipeline-owned-journey APPLE_PIPELINE_JOURNEY_PROFILE=ipados-create" in makefile
    assert "apple-pipeline-ipad-create-readiness-dry-run:" in makefile
    assert "$(MAKE) apple-pipeline-owned-journey-dry-run APPLE_PIPELINE_JOURNEY_PROFILE=ipados-create" in makefile
    assert "apple-pipeline-tvos-create-readiness:" in makefile
    assert "$(MAKE) apple-pipeline-owned-journey APPLE_PIPELINE_JOURNEY_PROFILE=tvos-create" in makefile
    assert "apple-pipeline-tvos-create-readiness-dry-run:" in makefile
    assert "$(MAKE) apple-pipeline-owned-journey-dry-run APPLE_PIPELINE_JOURNEY_PROFILE=tvos-create" in makefile
    assert (
        "apple-pipeline-orchestration-dry-runs: apple-pipeline-simulator-smokes-dry-run "
        "apple-pipeline-owned-journeys apple-pipeline-owned-journeys-dry-run"
    ) in makefile
    assert "apple-device-full-entitlement-plan:" in makefile
    assert "bash scripts/apple_full_entitlement_signing_plan.sh \\" in makefile
    assert '--device "$(APPLE_DEVICE_ID)"' in makefile
    assert '--app-profile "$(FULL_CAPABILITY_IOS_PROFILE)"' in makefile
    assert '--extension-profile "$(WILDCARD_IOS_EXTENSION_PROFILE)"' in makefile
    assert '--signing-identity "$(APPLE_DEVELOPMENT_IDENTITY)"' in makefile
    assert "APPLE_DEVICE_SIGNED_ARTIFACT_PATH ?= test-results/DerivedData-device-full-entitlements/Build/Products/Debug-iphoneos/InteractiveReader.app" in makefile
    assert "APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT ?= 10" in makefile
    assert "apple-device-full-entitlement-fallback-install:" in makefile
    fallback_target = makefile.split("apple-device-full-entitlement-fallback-install:", 1)[1].split("\n\n", 1)[0]
    assert "bash scripts/apple_unattended_device_update.sh" in fallback_target
    assert '--profile "$(APPLE_DEVICE_PROFILE)"' in fallback_target
    assert '--device "$(APPLE_DEVICE_ID)"' in fallback_target
    assert "--install" in fallback_target
    assert "--launch" in fallback_target
    assert '--launch-console-timeout "$(APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT)"' in fallback_target
    assert "--fallback-to-signed-artifact" in fallback_target
    assert '--signed-artifact-path "$(APPLE_DEVICE_SIGNED_ARTIFACT_PATH)"' in fallback_target
    assert "apple-device-full-entitlement-stable-install:" in makefile
    stable_target = makefile.split("apple-device-full-entitlement-stable-install:", 1)[1].split("\n\n", 1)[0]
    assert "bash scripts/apple_unattended_device_update.sh" in stable_target
    assert '--profile "$(APPLE_DEVICE_PROFILE)"' in stable_target
    assert '--device "$(APPLE_DEVICE_ID)"' in stable_target
    assert "--skip-build" in stable_target
    assert '--app-path "$(APPLE_DEVICE_SIGNED_ARTIFACT_PATH)"' in stable_target
    assert "--install" in stable_target
    assert "--launch" in stable_target
    assert '--launch-console-timeout "$(APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT)"' in stable_target
    assert "--fallback-to-signed-artifact" in stable_target
    assert '--signed-artifact-path "$(APPLE_DEVICE_SIGNED_ARTIFACT_PATH)"' in stable_target


def test_shared_pipeline_verification_stays_non_physical() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    target_line = (
        "verify-apple-shared-pipeline: apple-pipeline-contracts "
        "apple-pipeline-backend apple-pipeline-backend-tests apple-pipeline-web-checks "
        "apple-pipeline-orchestration-dry-runs"
    )
    assert target_line in makefile

    target = makefile.split("verify-apple-shared-pipeline:", 1)[1].split("\n\n", 1)[0]
    assert "apple-pipeline-backend-tests" in target
    assert "apple-pipeline-web-checks" in target
    assert "apple-pipeline-orchestration-dry-runs" in target
    assert "apple-pipeline-source-sync" not in target
    assert "apple-device-update" not in target
    assert "run_app_device_deploy.py" not in target
    assert "apple_unattended_device_update.sh" not in target
    assert "apple-device-full-entitlement-stable-install" not in target
    assert "devicectl" not in target


def test_golden_pipeline_verification_includes_source_sync_without_physical_deploy() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    target_line = "verify-apple-golden-pipeline: apple-pipeline-source-sync verify-apple-shared-pipeline"
    assert target_line in makefile

    target = makefile.split("verify-apple-golden-pipeline:", 1)[1].split("\n\n", 1)[0]
    assert "apple-pipeline-source-sync" in target
    assert "verify-apple-shared-pipeline" in target
    assert "apple-device-update" not in target
    assert "run_app_device_deploy.py" not in target
    assert "apple_unattended_device_update.sh" not in target
    assert "apple-device-full-entitlement-stable-install" not in target
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
    assert "verify-apple-golden-pipeline" in contract_check
    assert "physical-device deployment" in contract_check


def test_docs_publish_shared_pipeline_targets() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")
    developer_doc = DEVELOPER_DOC.read_text(encoding="utf-8")
    plan = PLAN_DOC.read_text(encoding="utf-8")

    for command in [
        "make apple-pipeline-contracts",
        "make test-apple-language-catalogs",
        "make test-apple-create-readiness-contract",
        "make test-apple-local-surface-contract",
        "make apple-pipeline-backend",
        "make apple-pipeline-backend-tests",
        "make apple-pipeline-source-sync",
        "make apple-pipeline-web-checks",
        "make apple-pipeline-simulator-smoke-dry-run",
        "make apple-pipeline-simulator-smokes-dry-run",
        "make apple-pipeline-owned-journeys",
        "make apple-pipeline-owned-journey-dry-run",
        "make apple-pipeline-owned-journeys-dry-run",
        "make apple-pipeline-ipad-create-readiness",
        "make apple-pipeline-ipad-create-readiness-dry-run",
        "make apple-pipeline-tvos-create-readiness",
        "make apple-pipeline-tvos-create-readiness-dry-run",
        "make apple-pipeline-orchestration-dry-runs",
        "make verify-apple-shared-pipeline",
        "make verify-apple-golden-pipeline",
        "make apple-device-full-entitlement-plan",
        "make apple-device-full-entitlement-fallback-install",
    ]:
        assert command in docs
        assert command in developer_doc
    assert "shared Apple pipeline preflight targets" in plan
    assert "make apple-device-full-entitlement-plan" in plan
    assert "make apple-device-full-entitlement-fallback-install" in plan
