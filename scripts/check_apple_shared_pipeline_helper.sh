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
source_sync_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/check_app_source_sync.py --app "$(APPLE_PIPELINE_APP)"'
web_checks_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_web_checks.py --app "$(APPLE_PIPELINE_APP)"'
verify_line="verify-apple-shared-pipeline: apple-pipeline-contracts apple-pipeline-backend"
deploy_dry_run_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_device_deploy.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_DEVICE_PROFILE)" --dry-run'
signed_build_line='cd "$(APPLE_PIPELINE_ROOT)" && $(APPLE_PIPELINE_PYTHON) scripts/run_app_device_deploy.py --app "$(APPLE_PIPELINE_APP)" --profile "$(APPLE_DEVICE_PROFILE)" --signed-build-only'
preflight_line='bash scripts/apple_unattended_device_update.sh --profile "$(APPLE_DEVICE_PROFILE)" --device "$(APPLE_DEVICE_ID)" --device-preflight-only'

assert_contains "${makefile}" "APPLE_PIPELINE_ROOT ?= /Users/fifo/Projects/home/apple-device-app-pipeline" "Makefile should declare the shared Apple pipeline root"
assert_contains "${makefile}" "APPLE_PIPELINE_APP ?= ebook-tools" "Makefile should declare the ebook-tools pipeline app id"
assert_contains "${makefile}" "APPLE_DEVICE_PROFILE ?= ipad" "Makefile should declare the default attended device profile"
assert_contains "${makefile}" "apple-pipeline-contracts:" "Makefile should expose the shared pipeline contract runner"
assert_contains "${makefile}" "${contract_line}" "shared pipeline contracts should call run_app_contract_checks"
assert_contains "${makefile}" "apple-pipeline-backend:" "Makefile should expose the shared pipeline backend check"
assert_contains "${makefile}" "${backend_line}" "shared pipeline backend should call check_app_backend"
assert_contains "${makefile}" "apple-pipeline-source-sync:" "Makefile should expose the shared pipeline source sync check"
assert_contains "${makefile}" "${source_sync_line}" "shared pipeline source sync should call check_app_source_sync"
assert_contains "${makefile}" "apple-pipeline-web-checks:" "Makefile should expose the shared pipeline Web check runner"
assert_contains "${makefile}" "${web_checks_line}" "shared pipeline Web checks should call run_app_web_checks"
assert_contains "${makefile}" "${verify_line}" "shared pipeline verification should compose contracts and backend checks"
assert_contains "${makefile}" "apple-device-preflight:" "Makefile should expose a non-installing device preflight helper"
assert_contains "${makefile}" "${preflight_line}" "device preflight should route through the repo-owned CoreDevice helper"
assert_contains "${makefile}" "apple-device-signed-build-only:" "Makefile should expose the shared signed-build gate"
assert_contains "${makefile}" "${signed_build_line}" "signed build helper should call the shared deploy pipeline without installing"
assert_contains "${makefile}" "apple-device-deploy-dry-run:" "Makefile should expose shared physical deploy dry-runs"
assert_contains "${makefile}" "${deploy_dry_run_line}" "deploy dry-run helper should call the shared deploy pipeline with --dry-run"
assert_not_contains "${verify_line}" "apple-device-update" "shared pipeline verification should not depend on physical-device update targets"
assert_not_contains "${verify_line}" "run_app_device_deploy.py" "shared pipeline verification should not route through physical-device deployment"

echo "apple shared pipeline helper checks passed"
