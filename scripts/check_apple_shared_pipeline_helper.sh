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
web_checks_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_web_checks.py --app "$(APPLE_PIPELINE_APP)"'
simulator_smoke_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_simulator_smoke.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_PIPELINE_SMOKE_PROFILE)"'
simulator_smoke_dry_run_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_simulator_smoke.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_PIPELINE_SMOKE_PROFILE)" --dry-run'
simulator_smokes_dry_run_line='$(MAKE) apple-pipeline-simulator-smoke-dry-run APPLE_PIPELINE_SMOKE_PROFILE="$$profile"'
owned_journeys_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_owned_journey.py --app "$(APPLE_PIPELINE_APP)" --list'
owned_journey_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_owned_journey.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_PIPELINE_JOURNEY_PROFILE)" --use-remote-env'
owned_journey_dry_run_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_owned_journey.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_PIPELINE_JOURNEY_PROFILE)" --dry-run'
owned_journeys_dry_run_line='$(MAKE) apple-pipeline-owned-journey-dry-run APPLE_PIPELINE_JOURNEY_PROFILE="$$profile"'
verify_line="verify-apple-shared-pipeline: apple-pipeline-contracts apple-pipeline-backend apple-pipeline-backend-tests apple-pipeline-web-checks"
deploy_dry_run_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_device_deploy.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_DEVICE_PROFILE)" --dry-run'
signed_build_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_device_deploy.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_DEVICE_PROFILE)" --signed-build-only'
preflight_line='bash scripts/apple_unattended_device_update.sh --profile "$(APPLE_DEVICE_PROFILE)" --device "$(APPLE_DEVICE_ID)" --device-preflight-only'

assert_contains "${makefile}" "APPLE_PIPELINE_ROOT ?= /Users/fifo/Projects/home/apple-device-app-pipeline" "Makefile should declare the shared Apple pipeline root"
assert_contains "${makefile}" "APPLE_PIPELINE_APP ?= ebook-tools" "Makefile should declare the ebook-tools pipeline app id"
assert_contains "${makefile}" "APPLE_PIPELINE_SMOKE_PROFILE ?= ipados" "Makefile should declare a default shared simulator smoke profile"
assert_contains "${makefile}" "APPLE_PIPELINE_SMOKE_PROFILES ?= ios ipados tvos" "Makefile should declare shared simulator smoke dry-run profiles"
assert_contains "${makefile}" "APPLE_PIPELINE_JOURNEY_PROFILE ?= ipados" "Makefile should declare a default app-owned journey profile"
assert_contains "${makefile}" "APPLE_PIPELINE_JOURNEY_PROFILES ?= iphone ipados tvos iphone-create ipados-create ios-uitests-build macos-ipad-style-dry-run macos-ipad-style" "Makefile should declare app-owned journey dry-run profiles"
assert_contains "${makefile}" "APPLE_DEVICE_PROFILE ?= ipad" "Makefile should declare the default attended device profile"
assert_contains "${makefile}" "apple-pipeline-contracts:" "Makefile should expose the shared pipeline contract runner"
assert_contains "${makefile}" "${contract_line}" "shared pipeline contracts should call run_app_contract_checks"
assert_contains "${makefile}" "apple-pipeline-backend:" "Makefile should expose the shared pipeline backend check"
assert_contains "${makefile}" "${backend_line}" "shared pipeline backend should call check_app_backend"
assert_contains "${makefile}" "apple-pipeline-backend-tests:" "Makefile should expose the shared pipeline backend test runner"
assert_contains "${makefile}" "${backend_tests_line}" "shared pipeline backend tests should call run_app_backend_tests"
assert_contains "${makefile}" "apple-pipeline-source-sync:" "Makefile should expose the shared pipeline source sync check"
assert_contains "${makefile}" "${source_sync_line}" "shared pipeline source sync should call check_app_source_sync"
assert_contains "${makefile}" "apple-pipeline-web-checks:" "Makefile should expose the shared pipeline Web check runner"
assert_contains "${makefile}" "${web_checks_line}" "shared pipeline Web checks should call run_app_web_checks"
assert_contains "${makefile}" "apple-pipeline-simulator-smoke:" "Makefile should expose shared simulator smokes"
assert_contains "${makefile}" "${simulator_smoke_line}" "simulator smoke wrapper should call run_app_simulator_smoke"
assert_contains "${makefile}" "apple-pipeline-simulator-smoke-dry-run:" "Makefile should expose shared simulator smoke dry-runs"
assert_contains "${makefile}" "${simulator_smoke_dry_run_line}" "simulator smoke dry-run wrapper should call run_app_simulator_smoke --dry-run"
assert_contains "${makefile}" "apple-pipeline-simulator-smokes-dry-run:" "Makefile should expose all shared simulator smoke dry-runs"
assert_contains "${makefile}" "${simulator_smokes_dry_run_line}" "simulator smoke aggregate should invoke the single-profile dry-run wrapper"
assert_contains "${makefile}" "apple-pipeline-owned-journeys:" "Makefile should expose registered app-owned journey listing"
assert_contains "${makefile}" "${owned_journeys_line}" "app-owned journey list wrapper should call run_app_owned_journey --list"
assert_contains "${makefile}" "apple-pipeline-owned-journey:" "Makefile should expose shared app-owned journey execution"
assert_contains "${makefile}" "${owned_journey_line}" "app-owned journey wrapper should call run_app_owned_journey with remote env"
assert_contains "${makefile}" "apple-pipeline-owned-journey-dry-run:" "Makefile should expose app-owned journey dry-runs"
assert_contains "${makefile}" "${owned_journey_dry_run_line}" "app-owned journey dry-run wrapper should call run_app_owned_journey --dry-run"
assert_contains "${makefile}" "apple-pipeline-owned-journeys-dry-run:" "Makefile should expose all app-owned journey dry-runs"
assert_contains "${makefile}" "${owned_journeys_dry_run_line}" "app-owned journey aggregate should invoke the single-profile dry-run wrapper"
assert_contains "${makefile}" "apple-pipeline-orchestration-dry-runs: apple-pipeline-simulator-smokes-dry-run apple-pipeline-owned-journeys apple-pipeline-owned-journeys-dry-run" "orchestration dry-runs should compose simulator and app-owned journey dry-runs"
assert_contains "${makefile}" "${verify_line}" "shared pipeline verification should compose contracts, backend checks, backend tests, and Web checks"
assert_contains "${makefile}" "apple-device-preflight:" "Makefile should expose a non-installing device preflight helper"
assert_contains "${makefile}" "${preflight_line}" "device preflight should route through the repo-owned CoreDevice helper"
assert_contains "${makefile}" "apple-device-signed-build-only:" "Makefile should expose the shared signed-build gate"
assert_contains "${makefile}" "${signed_build_line}" "signed build helper should call the shared deploy pipeline without installing"
assert_contains "${makefile}" "apple-device-deploy-dry-run:" "Makefile should expose shared physical deploy dry-runs"
assert_contains "${makefile}" "${deploy_dry_run_line}" "deploy dry-run helper should call the shared deploy pipeline with --dry-run"
assert_not_contains "${verify_line}" "apple-device-update" "shared pipeline verification should not depend on physical-device update targets"
assert_not_contains "${verify_line}" "run_app_device_deploy.py" "shared pipeline verification should not route through physical-device deployment"

echo "apple shared pipeline helper checks passed"
