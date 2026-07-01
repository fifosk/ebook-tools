import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
CONTRACT_CHECK = ROOT / "scripts" / "check_apple_shared_pipeline_helper.sh"
RUNTIME_SSH_CHECK = ROOT / "scripts" / "check_mac_studio_runtime_checkout.sh"
RUNTIME_FAST_FORWARD = ROOT / "scripts" / "fast_forward_mac_studio_runtime_checkout.sh"
TESTING_DOC = ROOT / "docs" / "testing.md"
DEVELOPER_DOC = ROOT / "docs" / "developer-guide.md"
DEPLOYMENT_DOC = ROOT / "docs" / "deployment.md"
CHANGELOG = ROOT / "CHANGELOG.md"
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
PIPELINE_OWNED_JOURNEY_SCRIPT = (
    Path("/Users/fifo/Projects/home/apple-device-app-pipeline")
    / "scripts"
    / "run_app_owned_journey.py"
)
APP_CHANGELOG_DATA = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Shared"
    / "AppChangelogData.swift"
)

REPO_OWNED_BACKEND_CHECKS = [
    "make test-backend-auth-session",
    "make test-backend-library-search-source-isbn",
    "make test-backend-admin-system-status",
    "make test-backend-pipeline-jobs",
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
    "make test-apple-playback-state-swift",
    "make test-apple-contracts",
]

REPO_OWNED_APP_JOURNEYS = {
    "apple-e2e-journeys": "make check-apple-e2e-journeys",
    "iphone": "make test-e2e-iphone",
    "iphone-create": "make test-e2e-iphone-create-readiness",
    "ipados": "make test-e2e-ipad",
    "ipados-create": "make test-e2e-ipad-create-readiness",
    "ipados-music-bed-sync": "make test-e2e-ipad-music-bed-sync",
    "ios-uitests-build": "make build-apple-ios-uitests",
    "tvos-uitests-build": "make build-apple-tvos-uitests",
    "macos-ipad-style": "make build-apple-macos-ipad-style",
    "macos-ipad-style-dry-run": "make build-apple-macos-ipad-style-dry-run",
    "tvos": "make test-e2e-tvos",
    "tvos-create": "make test-e2e-tvos-create-readiness",
    "tvos-music-bed-sync": "make test-e2e-tvos-music-bed-sync",
    "runtime-xcode-readiness": "make apple-runtime-xcode-readiness",
}

REPO_OWNED_CREDENTIAL_FREE_APP_JOURNEYS = [
    "apple-e2e-journeys",
    "ios-uitests-build",
    "tvos-uitests-build",
    "macos-ipad-style",
    "macos-ipad-style-dry-run",
    "runtime-xcode-readiness",
]

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


def _load_pipeline_owned_journey_module():
    spec = importlib.util.spec_from_file_location(
        "apple_pipeline_run_app_owned_journey",
        PIPELINE_OWNED_JOURNEY_SCRIPT,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_shared_pipeline_make_targets_call_manifest_driven_scripts() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    assert "APPLE_PIPELINE_ROOT ?= /Users/fifo/Projects/home/apple-device-app-pipeline" in makefile
    assert "APPLE_PIPELINE_APP ?= ebook-tools" in makefile
    assert "APPLE_PIPELINE_SMOKE_PROFILE ?= ipados" in makefile
    assert "APPLE_PIPELINE_SMOKE_PROFILES ?= ios ipados tvos tvos-cinema" in makefile
    assert "APPLE_PIPELINE_JOURNEY_PROFILE ?= ipados" in makefile
    assert (
        "APPLE_PIPELINE_JOURNEY_PROFILES ?= apple-e2e-journeys iphone ipados tvos iphone-create "
        "ipados-create tvos-create ipados-music-bed-sync tvos-music-bed-sync runtime-xcode-readiness ios-uitests-build "
        "tvos-uitests-build macos-ipad-style-dry-run macos-ipad-style"
    ) in makefile
    assert "MAC_STUDIO_SSH_TARGET ?= fifo@192.168.1.9" in makefile
    assert "MAC_STUDIO_REPO_PATH ?= /Users/fifo/Projects/home/ebook-tools" in makefile
    assert "MAC_STUDIO_BRANCH ?= main" in makefile
    assert "apple-runtime-fast-forward:" in makefile
    fast_forward_target = makefile.split("apple-runtime-fast-forward:", 1)[1].split("\n\n", 1)[0]
    assert "bash scripts/fast_forward_mac_studio_runtime_checkout.sh" in fast_forward_target
    assert '--target "$(MAC_STUDIO_SSH_TARGET)"' in fast_forward_target
    assert '--repo-path "$(MAC_STUDIO_REPO_PATH)"' in fast_forward_target
    assert '--branch "$(MAC_STUDIO_BRANCH)"' in fast_forward_target
    assert "devicectl" not in fast_forward_target
    assert "apple_unattended_device_update.sh" not in fast_forward_target
    assert "apple-runtime-ssh-check:" in makefile
    runtime_target = makefile.split("apple-runtime-ssh-check:", 1)[1].split("\n\n", 1)[0]
    assert "bash scripts/check_mac_studio_runtime_checkout.sh" in runtime_target
    assert '--target "$(MAC_STUDIO_SSH_TARGET)"' in runtime_target
    assert '--repo-path "$(MAC_STUDIO_REPO_PATH)"' in runtime_target
    assert '--require-head "$$(git rev-parse HEAD)"' in runtime_target
    assert "apple-runtime-xcode-readiness:" in makefile
    xcode_readiness_target = makefile.split("apple-runtime-xcode-readiness:", 1)[1].split("\n\n", 1)[0]
    assert 'ssh -o BatchMode=yes -o ConnectTimeout="$(MAC_STUDIO_CONNECT_TIMEOUT)" "$(MAC_STUDIO_SSH_TARGET)"' in xcode_readiness_target
    assert 'cd "$(MAC_STUDIO_REPO_PATH)"' in xcode_readiness_target
    assert "scripts/check_apple_xcode_readiness.py" in xcode_readiness_target
    assert '--xcodebuild "$(XCBUILD)"' in xcode_readiness_target
    assert "--profile golden-runtime" in xcode_readiness_target
    assert "devicectl" not in xcode_readiness_target
    assert "apple_unattended_device_update.sh" not in xcode_readiness_target
    assert "apple-local-checkpoint-bundle:" in makefile
    local_checkpoint_target = makefile.split("apple-local-checkpoint-bundle:", 1)[1].split("\n\n", 1)[0]
    assert '$(PYTHON) scripts/write_git_checkpoint_bundle.py --base "$(CHECKPOINT_BASE)" --output-dir "$(CHECKPOINT_OUTPUT_DIR)"' in local_checkpoint_target
    assert "git push" not in local_checkpoint_target
    assert "apple-device-host-readiness:" in makefile
    host_readiness_target = makefile.split("apple-device-host-readiness:", 1)[1].split("\n\n", 1)[0]
    assert "bash scripts/apple_unattended_device_update.sh --host-readiness-only" in host_readiness_target
    assert "--device" not in host_readiness_target
    assert "apple-pipeline-contracts:" in makefile
    assert 'scripts/run_app_contract_checks.py --app "$(APPLE_PIPELINE_APP)"' in makefile
    assert "test-release-version:" in makefile
    assert "$(PYTHON) -m pytest -q tests/test_release_version_contract.py" in makefile
    assert "$(PYTHON) scripts/check_release_version_contract.py" in makefile
    assert "test-apple-contracts: test-release-version" in makefile
    assert "tests/scripts/test_check_apple_e2e_config.py" in makefile
    assert "tests/scripts/test_check_apple_e2e_journeys.py" in makefile
    assert "tests/scripts/test_check_apple_shared_pipeline_manifest.py" in makefile
    assert "$(PYTHON) scripts/check_apple_e2e_journeys.py" in makefile
    assert "check-apple-e2e-journeys:" in makefile
    assert "$(MAKE) check-apple-e2e-journeys" in makefile
    assert "test-apple-language-catalogs:" in makefile
    assert "tests/test_language_catalog_parity.py tests/scripts/test_generate_language_catalogs.py" in makefile
    assert "test-apple-create-readiness-contract:" in makefile
    create_target = makefile.split("test-apple-create-readiness-contract:", 1)[1].split("\n\n", 1)[0]
    assert "tests/scripts/test_check_apple_e2e_journeys.py" in create_target
    assert "$(MAKE) check-apple-e2e-journeys" in create_target
    assert (
        "tests/scripts/test_check_apple_create_readiness.py "
        "tests/scripts/test_check_apple_e2e_journeys.py "
        "tests/test_apple_create_readiness_journey.py "
        "tests/test_apple_e2e_env_file_contract.py"
    ) in makefile
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
    assert "test-e2e-ipad-music-bed-sync-dry-run:" in makefile
    ipad_music_bed_dry_run_target = makefile.split("test-e2e-ipad-music-bed-sync-dry-run:", 1)[1].split("\n\n", 1)[0]
    assert "$(MAKE) check-apple-e2e-journeys" in ipad_music_bed_dry_run_target
    assert "$(MAKE) apple-pipeline-owned-journey-dry-run APPLE_PIPELINE_JOURNEY_PROFILE=ipados-music-bed-sync" in ipad_music_bed_dry_run_target
    assert "test-e2e-ipad" not in ipad_music_bed_dry_run_target
    assert "CHECK_E2E_CONFIG" not in ipad_music_bed_dry_run_target
    assert "test-e2e-tvos-music-bed-sync-dry-run:" in makefile
    music_bed_dry_run_target = makefile.split("test-e2e-tvos-music-bed-sync-dry-run:", 1)[1].split("\n\n", 1)[0]
    assert "$(MAKE) check-apple-e2e-journeys" in music_bed_dry_run_target
    assert "$(MAKE) apple-pipeline-owned-journey-dry-run APPLE_PIPELINE_JOURNEY_PROFILE=tvos-music-bed-sync" in music_bed_dry_run_target
    assert "test-e2e-tvos" not in music_bed_dry_run_target
    assert "CHECK_E2E_CONFIG" not in music_bed_dry_run_target
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
    assert "APPLE_DEVICE_LAUNCH_PRESERVE_RUNNING ?= 0" in makefile
    assert "APPLE_DEVICE_LAUNCH_PRESERVE_RUNNING_FLAG = $(if $(filter 1 YES yes true TRUE,$(APPLE_DEVICE_LAUNCH_PRESERVE_RUNNING)),--preserve-running-app)" in makefile
    assert "APPLE_MUSIC_BED_LAUNCH_LOG_MODE ?= startup" in makefile
    assert "apple-device-launch-console:" in makefile
    launch_console_target = makefile.split("apple-device-launch-console:", 1)[1].split("\n\n", 1)[0]
    assert "bash scripts/apple_unattended_device_update.sh" in launch_console_target
    assert '--profile "$(APPLE_DEVICE_PROFILE)"' in launch_console_target
    assert '--device "$(APPLE_DEVICE_ID)"' in launch_console_target
    assert "--launch-only" in launch_console_target
    assert '--launch-console-timeout "$(APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT)"' in launch_console_target
    assert "$(APPLE_DEVICE_LAUNCH_PRESERVE_RUNNING_FLAG)" in launch_console_target
    assert "apple-device-verify-music-bed-launch-log:" in makefile
    music_bed_log_target = makefile.split("apple-device-verify-music-bed-launch-log:", 1)[1].split("\n\n", 1)[0]
    assert "$(PYTHON) scripts/check_apple_music_bed_launch_log.py" in music_bed_log_target
    assert '--device "$(APPLE_DEVICE_ID)"' in music_bed_log_target
    assert '--mode "$(APPLE_MUSIC_BED_LAUNCH_LOG_MODE)"' in music_bed_log_target
    assert '$(if $(strip $(APPLE_DEVICE_LAUNCH_LOG)),"$(APPLE_DEVICE_LAUNCH_LOG)")' in music_bed_log_target
    assert "apple-device-verify-music-bed-guarded-play-log:" in makefile
    guarded_play_log_target = makefile.split(
        "apple-device-verify-music-bed-guarded-play-log:", 1
    )[1].split("\n\n", 1)[0]
    assert "$(MAKE) apple-device-verify-music-bed-launch-log APPLE_MUSIC_BED_LAUNCH_LOG_MODE=guarded-play" in guarded_play_log_target
    assert "apple-device-pull-playback-log:" in makefile
    pull_playback_log_target = makefile.split("apple-device-pull-playback-log:", 1)[1].split("\n\n", 1)[0]
    assert "bash scripts/apple_pull_device_playback_log.sh" in pull_playback_log_target
    assert '--profile "$(APPLE_DEVICE_PROFILE)"' in pull_playback_log_target
    assert '--device "$(APPLE_DEVICE_ID)"' in pull_playback_log_target
    assert "apple-device-pull-and-verify-playback-transport-log:" in makefile
    pull_verify_playback_target = makefile.split(
        "apple-device-pull-and-verify-playback-transport-log:", 1
    )[1].split("\n\n", 1)[0]
    assert "$(MAKE) apple-device-pull-playback-log" in pull_verify_playback_target
    assert "$(MAKE) apple-device-verify-playback-transport-log" in pull_verify_playback_target
    pull_playback_script = (ROOT / "scripts" / "apple_pull_device_playback_log.sh").read_text(encoding="utf-8")
    assert "Playback transport log archive:" in pull_playback_script
    assert "Playback transport CoreDevice archive:" in pull_playback_script
    assert "APPLE_DEVICE_LOG_TIMESTAMP" in pull_playback_script
    assert "apple-device-pull-and-verify-playback-transport-pause-resume-log:" in makefile
    pull_verify_pause_resume_target = makefile.split(
        "apple-device-pull-and-verify-playback-transport-pause-resume-log:", 1
    )[1].split("\n\n", 1)[0]
    assert (
        "$(MAKE) apple-device-pull-and-verify-playback-transport-log "
        "APPLE_PLAYBACK_TRANSPORT_LOG_MODE=pause-resume"
    ) in pull_verify_pause_resume_target
    assert "apple-device-pull-and-verify-playback-resume-offset-log:" in makefile
    pull_verify_resume_offset_target = makefile.split(
        "apple-device-pull-and-verify-playback-resume-offset-log:", 1
    )[1].split("\n\n", 1)[0]
    assert (
        "$(MAKE) apple-device-pull-and-verify-playback-transport-log "
        "APPLE_PLAYBACK_TRANSPORT_LOG_MODE=resume-offset"
    ) in pull_verify_resume_offset_target
    assert "apple-device-verify-playback-transport-log:" in makefile
    playback_transport_log_target = makefile.split(
        "apple-device-verify-playback-transport-log:", 1
    )[1].split("\n\n", 1)[0]
    assert "$(PYTHON) scripts/check_apple_playback_transport_log.py" in playback_transport_log_target
    assert '--device "$(APPLE_DEVICE_ID)"' in playback_transport_log_target
    assert '--mode "$(APPLE_PLAYBACK_TRANSPORT_LOG_MODE)"' in playback_transport_log_target
    assert "apple-device-verify-playback-resume-offset-log:" in makefile
    testing_doc = TESTING_DOC.read_text(encoding="utf-8")
    deployment_doc = DEPLOYMENT_DOC.read_text(encoding="utf-8")
    assert "first pause episode did not reach narration before the next transport command" in testing_doc
    assert 'old "first click pauses Music, second click pauses track"' in testing_doc
    assert "`requested=true` or `playing=true`" in testing_doc
    assert "standalone `readerPause=true`" in testing_doc
    assert "regression from passing" in testing_doc
    assert "first pause episode did not reach narration before the" in deployment_doc
    assert "next transport command" in deployment_doc
    assert "`requested=true` or\n`playing=true`" in deployment_doc
    assert "lone `readerPause=true` flag is not enough" in deployment_doc
    assert "apple-device-pull-and-verify-playback-resume-offset-log" in testing_doc
    assert "fallback=sentenceStart" in testing_doc
    assert "last spoken position inside\nthe sentence" in testing_doc
    assert "apple-device-pull-and-verify-playback-resume-offset-log" in deployment_doc
    assert 'APPLE_DEVICE_ID="Cinema"' in deployment_doc
    assert "true last-word resume" in deployment_doc
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
    assert "apple-device-update:" in makefile
    device_update_target = makefile.split("apple-device-update:", 1)[1].split("\n\n", 1)[0]
    assert "bash scripts/apple_unattended_device_update.sh" in device_update_target
    assert '--profile "$(APPLE_DEVICE_PROFILE)"' in device_update_target
    assert '--device "$(APPLE_DEVICE_ID)"' in device_update_target
    assert "--install" in device_update_target
    assert '--launch --launch-console-timeout "$(APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT)"' in device_update_target


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
    manifest = _manifest()
    manifest_journeys = _manifest_app_journeys()

    assert manifest_journeys == REPO_OWNED_APP_JOURNEYS
    assert manifest["credentialFreeAppOwnedJourneys"] == REPO_OWNED_CREDENTIAL_FREE_APP_JOURNEYS
    for command in REPO_OWNED_APP_JOURNEYS.values():
        _, target = command.split(" ", 1)
        assert f"{target}:" in makefile


def test_shared_pipeline_wrapper_skips_remote_env_for_credential_free_journeys() -> None:
    manifest = _manifest()
    module = _load_pipeline_owned_journey_module()

    assert "apple-e2e-journeys" in module.credential_free_journeys(manifest)
    assert "ios-uitests-build" in module.credential_free_journeys(manifest)
    assert "runtime-xcode-readiness" in module.credential_free_journeys(manifest)
    assert module.should_load_remote_env(manifest, "apple-e2e-journeys", requested=True) is False
    assert module.should_load_remote_env(manifest, "ios-uitests-build", requested=True) is False
    assert module.should_load_remote_env(manifest, "runtime-xcode-readiness", requested=True) is False
    assert module.should_load_remote_env(manifest, "ipados", requested=True) is True
    assert module.should_load_remote_env(manifest, "ipados", requested=False) is False


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
        assert "Latest iPad Pro arrow-key validation deploy from June 27, 2026" in source
        assert "APPLE_DEVICE_PROFILE=ipad" in source
        assert "APPLE_DEVICE_ID=BC4A8986-54B2-543C-83CB-4B28F4F73BB2" in source
        assert "APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT=10" in source
        assert "2026.6.27" in source
        assert "20260627001" in source


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


def test_living_room_candidate_gate_runs_shared_pipeline_and_tvos_music_bed_without_deploy() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    target_line = (
        "verify-apple-living-room-candidate: verify-apple-shared-pipeline "
        "test-e2e-tvos-music-bed-sync"
    )
    assert target_line in makefile

    phony = makefile.split(".PHONY:", 1)[1].split("\n\n", 1)[0]
    assert "verify-apple-living-room-candidate" in phony

    target = makefile.split("verify-apple-living-room-candidate:", 1)[1].split("\n\n", 1)[0]
    assert "verify-apple-shared-pipeline" in target
    assert "test-e2e-tvos-music-bed-sync" in target
    assert "apple-device-update" not in target
    assert "run_app_device_deploy.py" not in target
    assert "apple_unattended_device_update.sh" not in target
    assert "apple-device-full-entitlement-stable-install" not in target
    assert "devicectl" not in target


def test_living_room_candidate_gate_is_visible_in_apple_changelog() -> None:
    changelog = APP_CHANGELOG_DATA.read_text(encoding="utf-8")

    assert 'id: "2026-06-30"' in changelog
    assert 'id: "living-room-candidate-gate"' in changelog
    assert "Living Room checks are one command" in changelog
    assert "full non-physical shared pipeline" in changelog
    assert "real tvOS Music-bed simulator journey" in changelog


def test_apple_web_create_handoff_source_is_visible_in_changelogs() -> None:
    swift_changelog = APP_CHANGELOG_DATA.read_text(encoding="utf-8")
    markdown_changelog = CHANGELOG.read_text(encoding="utf-8")

    assert 'id: "apple-web-create-handoff-source"' in swift_changelog
    assert "Apple-origin Open Web Create handoffs" in markdown_changelog
    for source in (swift_changelog, markdown_changelog):
        assert "generated-book" in source
        assert "Narrate EPUB" in source
        assert "subtitle" in source
        assert "YouTube dubbing" in source
    assert "handoff_source" in markdown_changelog
    assert "source: web" in markdown_changelog


def test_golden_pipeline_verification_includes_source_sync_without_physical_deploy() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")

    target_line = "verify-apple-golden-pipeline: apple-runtime-fast-forward apple-runtime-ssh-check apple-runtime-xcode-readiness apple-pipeline-source-sync verify-apple-dogfood-pipeline"
    assert target_line in makefile

    target = makefile.split("verify-apple-golden-pipeline:", 1)[1].split("\n\n", 1)[0]
    assert "apple-runtime-fast-forward" in target
    assert "apple-runtime-ssh-check" in target
    assert "apple-runtime-xcode-readiness" in target
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


def test_mac_studio_runtime_fast_forward_helper_is_ff_only_and_non_device() -> None:
    helper = RUNTIME_FAST_FORWARD.read_text(encoding="utf-8")

    assert "fifo@192.168.1.9" in helper
    assert "/Users/fifo/Projects/home/ebook-tools" in helper
    assert 'ssh -o BatchMode=yes -o ConnectTimeout="${CONNECT_TIMEOUT}"' in helper
    assert "git status --porcelain=v1" in helper
    assert 'git fetch --prune origin "${expected_branch}"' in helper
    assert 'git pull --ff-only origin "${expected_branch}"' in helper
    assert "pruned_untracked_export_asset=" in helper
    assert 'git status --porcelain=v1 -- "${candidate}"' in helper
    assert "Mac Studio runtime checkout has local changes after fast-forward" in helper
    assert "--dry-run" in helper
    assert "git reset" not in helper
    assert "git checkout" not in helper
    assert "devicectl" not in helper
    assert "CONFIRM_PHYSICAL_DEVICE_UPDATE" not in helper


def test_shared_pipeline_contract_check_covers_targets() -> None:
    contract_check = CONTRACT_CHECK.read_text(encoding="utf-8")

    assert "check_mac_studio_runtime_checkout.sh" in contract_check
    assert "run_app_contract_checks.py" in contract_check
    assert "check_app_backend.py" in contract_check
    assert "run_app_backend_tests.py" in contract_check
    assert "check_app_source_sync.py" in contract_check
    assert "run_app_web_checks.py" in contract_check
    assert "run_app_simulator_smoke.py" in contract_check
    assert "run_app_owned_journey.py" in contract_check
    assert "check_apple_shared_pipeline_manifest.py" in contract_check
    assert "verify-apple-shared-pipeline" in contract_check
    assert "verify-apple-living-room-candidate" in contract_check
    assert "test-e2e-tvos-music-bed-sync" in contract_check
    assert "verify-apple-dogfood-pipeline" in contract_check
    assert "verify-apple-golden-pipeline" in contract_check
    assert "physical-device deployment" in contract_check


def test_mac_studio_runtime_checkout_helper_is_non_mutating_and_head_checked() -> None:
    helper = RUNTIME_SSH_CHECK.read_text(encoding="utf-8")

    assert "fifo@192.168.1.9" in helper
    assert "/Users/fifo/Projects/home/ebook-tools" in helper
    assert 'ssh -o BatchMode=yes -o ConnectTimeout="${CONNECT_TIMEOUT}"' in helper
    assert "git rev-parse HEAD" in helper
    assert "git status --porcelain=v1 -b" in helper
    assert "Fast-forward the runtime clone" in helper
    assert "--dry-run" in helper
    assert "git pull" not in helper
    assert "devicectl" not in helper
    assert "CONFIRM_PHYSICAL_DEVICE_UPDATE" not in helper


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
        "make apple-runtime-fast-forward",
        "make apple-pipeline-contracts",
        "make test-release-version",
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
        "make apple-runtime-ssh-check",
        "make verify-apple-shared-pipeline",
        "make verify-apple-living-room-candidate",
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


def test_docs_record_latest_shared_pipeline_dogfood_evidence() -> None:
    docs = TESTING_DOC.read_text(encoding="utf-8")
    plan = PLAN_DOC.read_text(encoding="utf-8")

    for source in (docs, plan):
        assert "June 30" in source
        assert "1010eb5fe" in source
        assert "make verify-apple-shared-pipeline" in source
        assert "make verify-apple-living-room-candidate" in source
        assert "backend" in source
        assert "health/runtime" in source
        assert "Web" in source
        assert "Vitest" in source
        assert "production/export build" in source
        assert "make apple-pipeline-orchestration-dry-runs" in source
        assert "make test-e2e-ipad-music-bed-sync" in source
        assert "make test-e2e-tvos-music-bed-sync" in source
        assert "dry-run registry" in source
        assert "without booting simulators" in source
        assert "remote secrets" in source
        assert "physical devices" in source


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
