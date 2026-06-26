import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
CONTRACT_CHECK = ROOT / "scripts" / "check_apple_shared_pipeline_helper.sh"
TESTING_DOC = ROOT / "docs" / "testing.md"
DEVELOPER_DOC = ROOT / "docs" / "developer-guide.md"
DEPLOYMENT_DOC = ROOT / "docs" / "deployment.md"
PLAN_DOC = ROOT / "docs" / "plans" / "cross-surface-parity-and-optimization.md"
SEQUENCE_CONTROLLER = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Services"
    / "SequencePlaybackController.swift"
)
INTERACTIVE_CONTEXT_BUILDER = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "InteractivePlayer"
    / "InteractivePlayerContextBuilder.swift"
)
PIPELINE_MANIFEST = (
    Path("/Users/fifo/Projects/home/apple-device-app-pipeline")
    / "apps"
    / "ebook-tools.json"
)

REPO_OWNED_BACKEND_CHECKS = [
    "make test-backend-auth-session",
    "make test-backend-library-search-source-isbn",
    "make test-backend-admin-system-status",
    "make test-backend-runtime-descriptor",
    "make test-backend-create-book",
    "make test-backend-creation-templates",
    "make test-backend-pipeline-sources",
    "make test-backend-acquisition",
    "make test-backend-audio-routes",
    "make test-backend-reading-beds",
    "make test-backend-notifications",
    "make test-backend-subtitle-router",
    "make test-backend-playback-state",
    "make test-backend-playback-media",
    "make test-backend-offline-export",
    "make test-backend-youtube-dubbing-service",
]

REPO_OWNED_APPLE_CONTRACT_CHECKS = [
    "make test-apple-language-catalogs",
    "make test-apple-create-readiness-contract",
    "make test-apple-local-surface-contract",
    "make test-apple-contracts",
]

REPO_OWNED_APP_JOURNEYS = {
    "iphone": "make test-e2e-iphone",
    "iphone-create": "make test-e2e-iphone-create-readiness",
    "ipados": "make test-e2e-ipad",
    "ipados-create": "make test-e2e-ipad-create-readiness",
    "ios-uitests-build": "make build-apple-ios-uitests",
    "macos-ipad-style": "make build-apple-macos-ipad-style",
    "macos-ipad-style-dry-run": "make build-apple-macos-ipad-style-dry-run",
    "tvos": "make test-e2e-tvos",
    "tvos-create": "make test-e2e-tvos-create-readiness",
}

EXPECTED_DEVICE_PROFILES = {
    "iphone": {
        "device": "Fifo iPhone",
        "platform": "ios",
        "target": "InteractiveReader",
        "productName": "InteractiveReader",
        "bundleId": "com.example.InteractiveReader",
        "deviceSdk": "iphoneos",
        "simulatorSmokeProfile": "ios",
        "buildRootSuffix": "ebook-tools/build-device-iphoneos",
        "embeddedBundleIds": ["com.example.InteractiveReader.NotificationServiceExtension"],
        "requiredCapabilities": ["Push Notifications", "Sign In with Apple", "iCloud"],
    },
    "ipad": {
        "device": "Fifo Ipad Pro",
        "platform": "ipados",
        "target": "InteractiveReader",
        "productName": "InteractiveReader",
        "bundleId": "com.example.InteractiveReader",
        "deviceSdk": "iphoneos",
        "simulatorSmokeProfile": "ipados",
        "buildRootSuffix": "ebook-tools/build-device-ipados",
        "embeddedBundleIds": ["com.example.InteractiveReader.NotificationServiceExtension"],
        "requiredCapabilities": ["Push Notifications", "Sign In with Apple", "iCloud"],
    },
    "appletv": {
        "device": "Living Room",
        "platform": "tvos",
        "target": "InteractiveReaderTV",
        "productName": "InteractiveReaderTV",
        "bundleId": "com.example.InteractiveReader.tvos",
        "deviceSdk": "appletvos",
        "simulatorSmokeProfile": "tvos",
        "buildRootSuffix": "ebook-tools/build-device-appletvos",
    },
    "cinema": {
        "device": "Cinema",
        "platform": "tvos",
        "target": "InteractiveReaderTV",
        "productName": "InteractiveReaderTV",
        "bundleId": "com.example.InteractiveReader.tvos",
        "deviceSdk": "appletvos",
        "simulatorSmokeProfile": "tvos-cinema",
        "buildRootSuffix": "ebook-tools/build-device-cinema-appletvos",
    },
}

EXPECTED_SIMULATOR_PROFILES = {
    "ios": {
        "platform": "ios",
        "target": "InteractiveReader",
        "productName": "InteractiveReader",
        "bundleId": "com.example.InteractiveReader",
        "simulator": "iPhone 17 Pro",
        "simulatorRuntimeVersion": "26.5",
    },
    "ipados": {
        "platform": "ipados",
        "target": "InteractiveReader",
        "productName": "InteractiveReader",
        "bundleId": "com.example.InteractiveReader",
        "simulator": "iPad Pro 13-inch (M5)",
        "simulatorRuntimeVersion": "26.5",
    },
    "tvos": {
        "platform": "tvos",
        "target": "InteractiveReaderTV",
        "productName": "InteractiveReaderTV",
        "bundleId": "com.example.InteractiveReader.tvos",
        "simulator": "Apple TV 4K (3rd generation)",
        "simulatorRuntimeVersion": "26.5",
    },
    "tvos-cinema": {
        "platform": "tvos",
        "target": "InteractiveReaderTV",
        "productName": "InteractiveReaderTV",
        "bundleId": "com.example.InteractiveReader.tvos",
        "simulator": "Apple TV 4K (2nd generation)",
        "simulatorRuntimeVersion": "26.4",
    },
}


def _manifest_commands(group: str) -> list[str]:
    manifest = json.loads(PIPELINE_MANIFEST.read_text(encoding="utf-8"))
    return [
        " ".join(entry["command"])
        for entry in manifest[group]["commands"]
    ]


def _manifest_app_journeys() -> dict[str, str]:
    manifest = json.loads(PIPELINE_MANIFEST.read_text(encoding="utf-8"))
    return dict(manifest["appOwnedJourneys"])


def _manifest() -> dict[str, object]:
    return json.loads(PIPELINE_MANIFEST.read_text(encoding="utf-8"))


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
    assert "apple-pipeline-owned-journeys-list:" in makefile
    assert 'scripts/run_app_owned_journey.py --app "$(APPLE_PIPELINE_APP)" --list' in makefile
    assert "apple-pipeline-owned-journeys: apple-pipeline-owned-journeys-list" in makefile
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
        "apple-pipeline-owned-journeys-list apple-pipeline-owned-journeys-dry-run"
    ) in makefile
    assert "verify-apple-dogfood-pipeline:" in makefile
    assert "apple-device-full-entitlement-plan:" in makefile
    assert 'bash scripts/apple_full_entitlement_signing_plan.sh --device "$(APPLE_DEVICE_ID)"' in makefile
    assert '--device "$(APPLE_DEVICE_ID)"' in makefile
    assert '$(if $(strip $(FULL_CAPABILITY_IOS_PROFILE)),--app-profile "$(FULL_CAPABILITY_IOS_PROFILE)")' in makefile
    assert '$(if $(strip $(WILDCARD_IOS_EXTENSION_PROFILE)),--extension-profile "$(WILDCARD_IOS_EXTENSION_PROFILE)")' in makefile
    assert '$(if $(strip $(APPLE_DEVELOPMENT_IDENTITY)),--signing-identity "$(APPLE_DEVELOPMENT_IDENTITY)")' in makefile
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


def test_shared_pipeline_manifest_runs_all_repo_owned_backend_checks() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    manifest_commands = _manifest_commands("backendTestChecks")

    assert manifest_commands == REPO_OWNED_BACKEND_CHECKS
    for command in REPO_OWNED_BACKEND_CHECKS:
        _, target = command.split(" ", 1)
        assert f"{target}:" in makefile


def test_shared_pipeline_manifest_runs_all_repo_owned_apple_contract_checks() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    manifest_commands = _manifest_commands("contractChecks")

    assert manifest_commands == REPO_OWNED_APPLE_CONTRACT_CHECKS
    for command in REPO_OWNED_APPLE_CONTRACT_CHECKS:
        _, target = command.split(" ", 1)
        assert f"{target}:" in makefile


def test_shared_pipeline_manifest_exposes_all_app_owned_journeys() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    manifest_journeys = _manifest_app_journeys()

    assert manifest_journeys == REPO_OWNED_APP_JOURNEYS
    for command in REPO_OWNED_APP_JOURNEYS.values():
        _, target = command.split(" ", 1)
        assert f"{target}:" in makefile


def test_shared_pipeline_manifest_pins_physical_device_profiles() -> None:
    manifest = _manifest()
    device_profiles = manifest["deviceProfiles"]

    assert set(device_profiles) == set(EXPECTED_DEVICE_PROFILES)
    for profile, expected_values in EXPECTED_DEVICE_PROFILES.items():
        actual = device_profiles[profile]
        for key, expected_value in expected_values.items():
            if key == "buildRootSuffix":
                assert actual["buildRoot"].endswith(expected_value)
            else:
                assert actual[key] == expected_value
        assert actual["project"].endswith(
            "ios/InteractiveReader/InteractiveReader.xcodeproj"
        )
        assert actual["configuration"] == "Debug"


def test_shared_pipeline_manifest_pins_simulator_profiles() -> None:
    manifest = _manifest()
    profiles = manifest["profiles"]

    assert set(profiles) == set(EXPECTED_SIMULATOR_PROFILES)
    for profile, expected_values in EXPECTED_SIMULATOR_PROFILES.items():
        actual = profiles[profile]
        for key, expected_value in expected_values.items():
            assert actual[key] == expected_value
        assert actual["project"].endswith(
            "ios/InteractiveReader/InteractiveReader.xcodeproj"
        )
        assert actual["buildTimeoutSeconds"] == 900
        assert actual["stageAppForInstall"] is False
        assert actual["buildRoot"].endswith(f"ebook-tools/build-sim-{profile}")
        assert actual["simEnvDefaults"] == {
            "INTERACTIVE_READER_API_BASE_URL": "https://api.langtools.fifosk.synology.me"
        }
        assert actual["requiredSimEnv"] == ["INTERACTIVE_READER_API_BASE_URL"]


def test_shared_pipeline_manifest_keeps_physical_deploys_on_request() -> None:
    known_gates = "\n".join(_manifest()["knownGates"])

    assert "Physical Apple TV deployment is attended and on-request only" in known_gates
    assert "Physical iPhone/iPad deployment is attended and on-request only" in known_gates
    assert "recursive development loops stop at simulator and build-only proof" in known_gates
    assert "authenticated Xcode account and provisioning profiles" in known_gates
    assert "iCloud, Sign in with Apple, and Push Notifications" in known_gates
    assert "use the attended Xcode GUI fallback only after simulator smoke" in known_gates
    assert "verify the installed build with devicectl and stop the debugger" in known_gates


def test_docs_pin_current_ipad_pro_unattended_profile() -> None:
    deployment_doc = DEPLOYMENT_DOC.read_text(encoding="utf-8")
    testing_doc = TESTING_DOC.read_text(encoding="utf-8")

    for source in (deployment_doc, testing_doc):
        assert "Latest iPad Pro arrow-key validation deploy from June 26, 2026" in source
        assert "APPLE_DEVICE_PROFILE=ipad" in source
        assert "APPLE_DEVICE_ID=BC4A8986-54B2-543C-83CB-4B28F4F73BB2" in source
        assert "APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT=10" in source
        assert "2026.6.26" in source
        assert "20260626183" in source


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

    target_line = "verify-apple-golden-pipeline: apple-pipeline-source-sync verify-apple-dogfood-pipeline"
    assert target_line in makefile

    target = makefile.split("verify-apple-golden-pipeline:", 1)[1].split("\n\n", 1)[0]
    assert "apple-pipeline-source-sync" in target
    assert "verify-apple-dogfood-pipeline" in target
    assert "apple-device-update" not in target
    assert "run_app_device_deploy.py" not in target
    assert "apple_unattended_device_update.sh" not in target
    assert "apple-device-full-entitlement-stable-install" not in target
    assert "devicectl" not in target


def test_dogfood_pipeline_verification_chains_local_checkpoint_and_shared_pipeline_without_physical_deploy() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    target_line = "verify-apple-dogfood-pipeline: verify-apple-cross-surface-checkpoint verify-apple-shared-pipeline"
    assert target_line in makefile
    assert makefile.count(target_line) == 1

    target = makefile.split("verify-apple-dogfood-pipeline:", 1)[1].split("\n\n", 1)[0]
    assert "verify-apple-cross-surface-checkpoint" in target
    assert "verify-apple-shared-pipeline" in target
    assert "apple-pipeline-source-sync" not in target
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
    assert "verify-apple-dogfood-pipeline" in contract_check
    assert "verify-apple-golden-pipeline" in contract_check
    assert "physical-device deployment" in contract_check


def test_apple_sequence_plan_uses_per_sentence_phase_fallback() -> None:
    source = SEQUENCE_CONTROLLER.read_text(encoding="utf-8")

    assert "falling back to per-sentence" in source
    assert "let origDur = sentence.phaseDurations?.original ?? 0" in source
    assert "let transDur = sentence.phaseDurations?.translation" in source
    assert "origCursor = originalEnd" in source
    assert "transCursor = translationEnd" in source
    assert "} else if origDur > 0 {" in source
    assert "} else if transDur > 0 {" in source
    assert "if !hasOriginalGate && origDur > 0" not in source
    assert "if !hasTranslationGate && transDur > 0" not in source


def test_apple_interactive_context_uses_chunk_local_timing_fallbacks() -> None:
    source = INTERACTIVE_CONTEXT_BUILDER.read_text(encoding="utf-8")

    assert 'parseTimingTrackTokens(from: chunk.timingTracks, trackKey: "translation")' in source
    assert 'parseTimingTrackTokens(from: chunk.timingTracks, trackKey: "original")' in source
    assert "chunkTranslationGroupedTokens: translationGroupedTokens" in source
    assert "private static func timingTokensForSentence(" in source
    assert "groupedTokens[localOffset] ?? groupedTokens[globalSentenceIndex] ?? []" in source
    assert "let timingTokens = groupedTokens[sentenceIndex]" in source
    assert "chunkTranslationGroupedTokens" in source
    assert "let originalTimingTokens = timingTokensForSentence(" in source


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
        "make apple-pipeline-owned-journeys-list",
        "make apple-pipeline-owned-journeys",
        "make apple-pipeline-owned-journey-dry-run",
        "make apple-pipeline-owned-journeys-dry-run",
        "make apple-pipeline-ipad-create-readiness",
        "make apple-pipeline-ipad-create-readiness-dry-run",
        "make apple-pipeline-tvos-create-readiness",
        "make apple-pipeline-tvos-create-readiness-dry-run",
        "make apple-pipeline-orchestration-dry-runs",
        "make verify-apple-shared-pipeline",
        "make verify-apple-dogfood-pipeline",
        "make verify-apple-golden-pipeline",
        "make apple-device-full-entitlement-plan",
        "make apple-device-full-entitlement-fallback-install",
    ]:
        assert command in docs
        assert command in developer_doc
    assert "shared Apple pipeline preflight targets" in plan
    assert "make apple-device-full-entitlement-plan" in plan
    assert "make apple-device-full-entitlement-fallback-install" in plan


def test_deployment_docs_record_latest_working_apple_device_recipe() -> None:
    deployment_doc = DEPLOYMENT_DOC.read_text(encoding="utf-8")

    assert "Latest working June 26, 2026 deployment:" in deployment_doc
    assert "bash scripts/apple_full_entitlement_signing_plan.sh" in deployment_doc
    assert "--device BC4A8986-54B2-543C-83CB-4B28F4F73BB2" in deployment_doc
    assert "--device FD7EB648-3D5F-5766-BDBF-05053E2D4CD7" in deployment_doc
    assert "--device 5E147DC8-5206-5EF2-A472-5748F7CDF7B0" in deployment_doc
    assert "--profile iphone" in deployment_doc
    assert "--profile appletv" in deployment_doc
    assert "--skip-build" in deployment_doc
    assert "--allow-provisioning-updates" in deployment_doc
    assert "`2026.6.26` build\n`20260626174`" in deployment_doc
    assert "Keep `Cinema` Apple TV\nand `iPad Small` out of bulk runs" in deployment_doc
    assert "physical devices only after\nan explicit deploy request" in deployment_doc
