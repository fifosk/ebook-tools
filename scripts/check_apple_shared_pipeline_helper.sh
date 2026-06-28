#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAKEFILE="${ROOT_DIR}/Makefile"

assert_contains() {
  local haystack="$1"
  local needle="$2"
  local message="$3"
  if [[ "${haystack}" != *"${needle}"* ]]; then
    echo "ERROR: ${message}" >&2
    echo "Expected to find: ${needle}" >&2
    exit 1
  fi
}

assert_not_contains() {
  local haystack="$1"
  local needle="$2"
  local message="$3"
  if [[ "${haystack}" == *"${needle}"* ]]; then
    echo "ERROR: ${message}" >&2
    echo "Unexpectedly found: ${needle}" >&2
    exit 1
  fi
}

makefile="$(<"${MAKEFILE}")"
contract_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_contract_checks.py --app "$(APPLE_PIPELINE_APP)"'
backend_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/check_app_backend.py --app "$(APPLE_PIPELINE_APP)"'
backend_tests_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_backend_tests.py --app "$(APPLE_PIPELINE_APP)"'
source_sync_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/check_app_source_sync.py --app "$(APPLE_PIPELINE_APP)"'
runtime_fast_forward_line='bash scripts/fast_forward_mac_studio_runtime_checkout.sh'
runtime_ssh_line='bash scripts/check_mac_studio_runtime_checkout.sh'
web_checks_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_web_checks.py --app "$(APPLE_PIPELINE_APP)"'
simulator_smoke_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_simulator_smoke.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_PIPELINE_SMOKE_PROFILE)"'
simulator_smoke_dry_run_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_simulator_smoke.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_PIPELINE_SMOKE_PROFILE)" --dry-run'
simulator_smokes_dry_run_line='$(MAKE) apple-pipeline-simulator-smoke-dry-run APPLE_PIPELINE_SMOKE_PROFILE="$$profile"'
owned_journeys_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_owned_journey.py --app "$(APPLE_PIPELINE_APP)" --list'
owned_journey_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_owned_journey.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_PIPELINE_JOURNEY_PROFILE)" --use-remote-env'
owned_journey_dry_run_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_owned_journey.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_PIPELINE_JOURNEY_PROFILE)" --dry-run'
owned_journeys_dry_run_line='$(MAKE) apple-pipeline-owned-journey-dry-run APPLE_PIPELINE_JOURNEY_PROFILE="$$profile"'
ipad_create_readiness_line='$(MAKE) apple-pipeline-owned-journey APPLE_PIPELINE_JOURNEY_PROFILE=ipados-create'
ipad_create_readiness_dry_run_line='$(MAKE) apple-pipeline-owned-journey-dry-run APPLE_PIPELINE_JOURNEY_PROFILE=ipados-create'
tvos_create_readiness_line='$(MAKE) apple-pipeline-owned-journey APPLE_PIPELINE_JOURNEY_PROFILE=tvos-create'
tvos_create_readiness_dry_run_line='$(MAKE) apple-pipeline-owned-journey-dry-run APPLE_PIPELINE_JOURNEY_PROFILE=tvos-create'
tvos_music_bed_sync_dry_run_line='$(MAKE) apple-pipeline-owned-journey-dry-run APPLE_PIPELINE_JOURNEY_PROFILE=tvos-music-bed-sync'
verify_line="verify-apple-shared-pipeline: apple-pipeline-contracts apple-pipeline-backend apple-pipeline-backend-tests apple-pipeline-web-checks apple-pipeline-orchestration-dry-runs"
dogfood_verify_line="verify-apple-dogfood-pipeline: verify-apple-cross-surface-checkpoint verify-apple-shared-pipeline"
golden_verify_line="verify-apple-golden-pipeline: apple-runtime-fast-forward apple-runtime-ssh-check apple-runtime-xcode-readiness apple-pipeline-source-sync verify-apple-dogfood-pipeline"
deploy_dry_run_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_device_deploy.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_DEVICE_PROFILE)" --dry-run'
signed_build_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_device_deploy.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_DEVICE_PROFILE)" --signed-build-only'
preflight_line='bash scripts/apple_unattended_device_update.sh --profile "$(APPLE_DEVICE_PROFILE)" --device "$(APPLE_DEVICE_ID)" --device-preflight-only'
full_entitlement_plan_line='bash scripts/apple_full_entitlement_signing_plan.sh --device "$(APPLE_DEVICE_ID)"'
conditional_app_profile_line='$(if $(strip $(FULL_CAPABILITY_IOS_PROFILE)),--app-profile "$(FULL_CAPABILITY_IOS_PROFILE)")'
conditional_extension_profile_line='$(if $(strip $(WILDCARD_IOS_EXTENSION_PROFILE)),--extension-profile "$(WILDCARD_IOS_EXTENSION_PROFILE)")'
conditional_signing_identity_line='$(if $(strip $(APPLE_DEVELOPMENT_IDENTITY)),--signing-identity "$(APPLE_DEVELOPMENT_IDENTITY)")'

assert_contains "${makefile}" "APPLE_PIPELINE_ROOT ?= /Users/fifo/Projects/home/apple-device-app-pipeline" "Makefile should declare the shared Apple pipeline root"
assert_contains "${makefile}" "APPLE_PIPELINE_APP ?= ebook-tools" "Makefile should declare the ebook-tools pipeline app id"
assert_contains "${makefile}" "APPLE_PIPELINE_SMOKE_PROFILE ?= ipados" "Makefile should declare a default shared simulator smoke profile"
assert_contains "${makefile}" "APPLE_PIPELINE_SMOKE_PROFILES ?= ios ipados tvos" "Makefile should declare shared simulator smoke dry-run profiles"
assert_contains "${makefile}" "APPLE_PIPELINE_JOURNEY_PROFILE ?= ipados" "Makefile should declare a default app-owned journey profile"
assert_contains "${makefile}" "APPLE_PIPELINE_JOURNEY_PROFILES ?= apple-e2e-journeys iphone ipados tvos iphone-create ipados-create tvos-create tvos-music-bed-sync runtime-xcode-readiness ios-uitests-build tvos-uitests-build macos-ipad-style-dry-run macos-ipad-style" "Makefile should declare app-owned journey dry-run profiles"
assert_contains "${makefile}" "MAC_STUDIO_SSH_TARGET ?= fifo@192.168.1.9" "Makefile should declare the Mac Studio runtime SSH target"
assert_contains "${makefile}" "MAC_STUDIO_REPO_PATH ?= /Users/fifo/Projects/home/ebook-tools" "Makefile should declare the Mac Studio runtime repo path"
assert_contains "${makefile}" "MAC_STUDIO_BRANCH ?= main" "Makefile should declare the Mac Studio runtime branch"
assert_contains "${makefile}" "APPLE_DEVICE_PROFILE ?= ipad" "Makefile should declare the default attended device profile"
assert_contains "${makefile}" "APPLE_DEVICE_SIGNED_ARTIFACT_PATH ?= test-results/DerivedData-device-full-entitlements/Build/Products/Debug-iphoneos/InteractiveReader.app" "Makefile should declare the default full-entitlement signed artifact path"
assert_contains "${makefile}" "APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT ?= 10" "Makefile should declare a default launch crash-watch timeout"
assert_contains "${makefile}" "apple-pipeline-contracts:" "Makefile should expose the shared pipeline contract runner"
assert_contains "${makefile}" "${contract_line}" "shared pipeline contracts should call run_app_contract_checks"
assert_contains "${makefile}" "test-release-version:" "Makefile should expose a direct release/version contract target"
assert_contains "${makefile}" '$(PYTHON) -m pytest -q tests/test_release_version_contract.py' "release/version target should run the pytest contract"
assert_contains "${makefile}" '$(PYTHON) scripts/check_release_version_contract.py' "release/version target should run the CLI validator"
assert_contains "${makefile}" "check-apple-e2e-journeys:" "Makefile should expose a credential-free Apple journey validator target"
assert_contains "${makefile}" '$(PYTHON) scripts/check_apple_e2e_journeys.py' "Apple journey validator should run the repo-owned script"
assert_contains "${makefile}" '$(MAKE) check-apple-e2e-journeys' "Apple contract lanes should reuse the credential-free journey target"
assert_contains "${makefile}" "test-apple-contracts: test-release-version" "Apple contracts should inherit release/version validation"
assert_contains "${makefile}" "tests/scripts/test_check_apple_e2e_config.py" "Apple contracts should cover E2E config preflight parsing"
assert_contains "${makefile}" "apple-pipeline-backend:" "Makefile should expose the shared pipeline backend check"
assert_contains "${makefile}" "${backend_line}" "shared pipeline backend should call check_app_backend"
assert_contains "${makefile}" "apple-pipeline-backend-tests:" "Makefile should expose the shared pipeline backend test runner"
assert_contains "${makefile}" "${backend_tests_line}" "shared pipeline backend tests should call run_app_backend_tests"
assert_contains "${makefile}" "apple-pipeline-source-sync:" "Makefile should expose the shared pipeline source sync check"
assert_contains "${makefile}" "${source_sync_line}" "shared pipeline source sync should call check_app_source_sync"
assert_contains "${makefile}" "apple-runtime-fast-forward:" "Makefile should expose the Mac Studio runtime fast-forward helper"
assert_contains "${makefile}" "${runtime_fast_forward_line}" "runtime fast-forward should call the repo-owned Mac Studio update helper"
assert_contains "${makefile}" '--branch "$(MAC_STUDIO_BRANCH)"' "runtime fast-forward should use the configured Mac Studio branch"
assert_contains "${makefile}" "apple-runtime-ssh-check:" "Makefile should expose the Mac Studio runtime SSH check"
assert_contains "${makefile}" "${runtime_ssh_line}" "runtime SSH check should call the repo-owned Mac Studio helper"
assert_contains "${makefile}" '--target "$(MAC_STUDIO_SSH_TARGET)"' "runtime SSH check should use the configured Mac Studio target"
assert_contains "${makefile}" '--repo-path "$(MAC_STUDIO_REPO_PATH)"' "runtime SSH check should use the configured Mac Studio repo path"
assert_contains "${makefile}" '--require-head "$$(git rev-parse HEAD)"' "runtime SSH check should require the local Git head"
assert_contains "${makefile}" "apple-runtime-xcode-readiness:" "Makefile should expose the Mac Studio Xcode readiness check"
assert_contains "${makefile}" 'scripts/check_apple_xcode_readiness.py --xcodebuild "$(XCBUILD)" --profile golden-runtime' "runtime Xcode readiness should call the repo-owned first-launch/license preflight"
assert_contains "${makefile}" 'cd "$(MAC_STUDIO_REPO_PATH)"' "runtime Xcode readiness should run from the configured Mac Studio repo path"
assert_contains "${makefile}" "apple-pipeline-web-checks:" "Makefile should expose the shared pipeline Web check runner"
assert_contains "${makefile}" "${web_checks_line}" "shared pipeline Web checks should call run_app_web_checks"
assert_contains "${makefile}" "apple-pipeline-simulator-smoke:" "Makefile should expose shared simulator smokes"
assert_contains "${makefile}" "${simulator_smoke_line}" "simulator smoke wrapper should call run_app_simulator_smoke"
assert_contains "${makefile}" "apple-pipeline-simulator-smoke-dry-run:" "Makefile should expose shared simulator smoke dry-runs"
assert_contains "${makefile}" "${simulator_smoke_dry_run_line}" "simulator smoke dry-run wrapper should call run_app_simulator_smoke --dry-run"
assert_contains "${makefile}" "apple-pipeline-simulator-smokes-dry-run:" "Makefile should expose all shared simulator smoke dry-runs"
assert_contains "${makefile}" "${simulator_smokes_dry_run_line}" "simulator smoke aggregate should invoke the single-profile dry-run wrapper"
assert_contains "${makefile}" "apple-pipeline-owned-journeys-list:" "Makefile should expose registered app-owned journey listing"
assert_contains "${makefile}" "${owned_journeys_line}" "app-owned journey list wrapper should call run_app_owned_journey --list"
assert_contains "${makefile}" "apple-pipeline-owned-journeys: apple-pipeline-owned-journeys-list" "legacy app-owned journey list target should remain a non-mutating alias"
assert_contains "${makefile}" "apple-pipeline-owned-journey:" "Makefile should expose shared app-owned journey execution"
assert_contains "${makefile}" "${owned_journey_line}" "app-owned journey wrapper should call run_app_owned_journey with remote env"
assert_contains "${makefile}" "apple-pipeline-owned-journey-dry-run:" "Makefile should expose app-owned journey dry-runs"
assert_contains "${makefile}" "${owned_journey_dry_run_line}" "app-owned journey dry-run wrapper should call run_app_owned_journey --dry-run"
assert_contains "${makefile}" "apple-pipeline-owned-journeys-dry-run:" "Makefile should expose all app-owned journey dry-runs"
assert_contains "${makefile}" "${owned_journeys_dry_run_line}" "app-owned journey aggregate should invoke the single-profile dry-run wrapper"
assert_contains "${makefile}" "apple-pipeline-ipad-create-readiness:" "Makefile should expose the iPad Create-readiness shared pipeline shortcut"
assert_contains "${makefile}" "${ipad_create_readiness_line}" "iPad Create-readiness shortcut should run the ipados-create app-owned journey"
assert_contains "${makefile}" "apple-pipeline-ipad-create-readiness-dry-run:" "Makefile should expose the iPad Create-readiness dry-run shortcut"
assert_contains "${makefile}" "${ipad_create_readiness_dry_run_line}" "iPad Create-readiness dry-run shortcut should dry-run the ipados-create app-owned journey"
assert_contains "${makefile}" "apple-pipeline-tvos-create-readiness:" "Makefile should expose the tvOS Create-readiness shared pipeline shortcut"
assert_contains "${makefile}" "${tvos_create_readiness_line}" "tvOS Create-readiness shortcut should run the tvos-create app-owned journey"
assert_contains "${makefile}" "apple-pipeline-tvos-create-readiness-dry-run:" "Makefile should expose the tvOS Create-readiness dry-run shortcut"
assert_contains "${makefile}" "${tvos_create_readiness_dry_run_line}" "tvOS Create-readiness dry-run shortcut should dry-run the tvos-create app-owned journey"
assert_contains "${makefile}" "test-e2e-tvos-music-bed-sync-dry-run:" "Makefile should expose a credential-free tvOS Music-bed dry-run"
assert_contains "${makefile}" '$(MAKE) check-apple-e2e-journeys' "tvOS Music-bed dry-run should validate journeys without credentials"
assert_contains "${makefile}" "${tvos_music_bed_sync_dry_run_line}" "tvOS Music-bed dry-run should dry-run the shared app-owned journey"
assert_contains "${makefile}" "apple-pipeline-orchestration-dry-runs: apple-pipeline-simulator-smokes-dry-run apple-pipeline-owned-journeys-list apple-pipeline-owned-journeys-dry-run" "orchestration dry-runs should compose explicit journey listing and dry-run targets"
assert_contains "${makefile}" "${verify_line}" "shared pipeline verification should compose contracts, backend checks, backend tests, Web checks, and orchestration dry-runs"
assert_contains "${makefile}" "${dogfood_verify_line}" "dogfood pipeline verification should compose the local cross-surface checkpoint with the non-physical shared pipeline gate"
assert_contains "${makefile}" "${golden_verify_line}" "golden pipeline verification should fast-forward and source-sync before the non-physical dogfood pipeline gate"
assert_contains "${makefile}" "apple-device-preflight:" "Makefile should expose a non-installing device preflight helper"
assert_contains "${makefile}" "${preflight_line}" "device preflight should route through the repo-owned CoreDevice helper"
assert_contains "${makefile}" "apple-device-signed-build-only:" "Makefile should expose the shared signed-build gate"
assert_contains "${makefile}" "${signed_build_line}" "signed build helper should call the shared deploy pipeline without installing"
assert_contains "${makefile}" "apple-device-deploy-dry-run:" "Makefile should expose shared physical deploy dry-runs"
assert_contains "${makefile}" "${deploy_dry_run_line}" "deploy dry-run helper should call the shared deploy pipeline with --dry-run"
assert_contains "${makefile}" "apple-device-full-entitlement-plan:" "Makefile should expose the full-entitlement signing planner"
assert_contains "${makefile}" "${full_entitlement_plan_line}" "full-entitlement planner should route through the repo-owned planner script"
assert_contains "${makefile}" "${conditional_app_profile_line}" "full-entitlement planner should pass the app provisioning profile only when overridden"
assert_contains "${makefile}" "${conditional_extension_profile_line}" "full-entitlement planner should pass the extension provisioning profile only when overridden"
assert_contains "${makefile}" "${conditional_signing_identity_line}" "full-entitlement planner should pass the signing identity only when overridden"
assert_contains "${makefile}" "apple-device-full-entitlement-fallback-install:" "Makefile should expose the signed-artifact fallback install helper"
assert_contains "${makefile}" "--fallback-to-signed-artifact" "fallback install helper should enable signed-artifact fallback"
assert_contains "${makefile}" '--signed-artifact-path "$(APPLE_DEVICE_SIGNED_ARTIFACT_PATH)"' "fallback install helper should pass the configured signed artifact path"
assert_contains "${makefile}" '--launch-console-timeout "$(APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT)"' "fallback install helper should pass the crash-watch timeout"
assert_contains "${makefile}" "apple-device-full-entitlement-stable-install:" "Makefile should expose the direct signed-artifact stable installer"
assert_contains "${makefile}" '--app-path "$(APPLE_DEVICE_SIGNED_ARTIFACT_PATH)"' "stable install helper should install the configured signed artifact path"
assert_contains "${makefile}" "--skip-build" "stable install helper should skip Xcode rebuilds for current signed artifacts"
assert_not_contains "${verify_line}" "apple-device-update" "shared pipeline verification should not depend on physical-device update targets"
assert_not_contains "${verify_line}" "run_app_device_deploy.py" "shared pipeline verification should not route through physical-device deployment"
assert_not_contains "${verify_line}" "apple-device-full-entitlement-fallback-install" "shared pipeline verification should not install signed artifacts"
assert_not_contains "${verify_line}" "apple-device-full-entitlement-stable-install" "shared pipeline verification should not install stable signed artifacts"
assert_not_contains "${dogfood_verify_line}" "apple-device-update" "dogfood pipeline verification should not depend on physical-device update targets"
assert_not_contains "${dogfood_verify_line}" "run_app_device_deploy.py" "dogfood pipeline verification should not route through physical-device deployment"
assert_not_contains "${dogfood_verify_line}" "apple-device-full-entitlement-fallback-install" "dogfood pipeline verification should not install signed artifacts"
assert_not_contains "${dogfood_verify_line}" "apple-device-full-entitlement-stable-install" "dogfood pipeline verification should not install stable signed artifacts"
assert_not_contains "${golden_verify_line}" "apple-device-update" "golden pipeline verification should not depend on physical-device update targets"
assert_not_contains "${golden_verify_line}" "run_app_device_deploy.py" "golden pipeline verification should not route through physical-device deployment"
assert_not_contains "${golden_verify_line}" "apple-device-full-entitlement-fallback-install" "golden pipeline verification should not install signed artifacts"
assert_not_contains "${golden_verify_line}" "apple-device-full-entitlement-stable-install" "golden pipeline verification should not install stable signed artifacts"

python3 "${ROOT_DIR}/scripts/check_apple_shared_pipeline_manifest.py"

echo "apple shared pipeline helper checks passed"
