#!/usr/bin/env bash
set -euo pipefail

TARGET="${MAC_STUDIO_SSH_TARGET:-fifo@192.168.1.9}"
REPO_PATH="${MAC_STUDIO_REPO_PATH:-/Users/fifo/Projects/home/ebook-tools}"
EXPECTED_BRANCH="${MAC_STUDIO_BRANCH:-main}"
REQUIRE_HEAD="${MAC_STUDIO_REQUIRE_HEAD:-}"
CONNECT_TIMEOUT="${MAC_STUDIO_CONNECT_TIMEOUT:-5}"
ALLOW_DIRTY=0
DRY_RUN=0

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/check_mac_studio_runtime_checkout.sh [options]

Options:
  --target USER@HOST           SSH target. Defaults to fifo@192.168.1.9.
  --repo-path PATH             Runtime checkout path on the remote host.
                               Defaults to /Users/fifo/Projects/home/ebook-tools.
  --branch NAME                Expected branch. Defaults to main.
  --require-head SHA           Require the remote checkout to be at this Git SHA.
  --connect-timeout SECONDS    SSH connect timeout. Defaults to 5.
  --allow-dirty                Do not fail when the remote checkout has local changes.
  --dry-run                    Print the SSH check that would run without connecting.
  -h, --help                   Show this help.

Environment:
  MAC_STUDIO_SSH_TARGET, MAC_STUDIO_REPO_PATH, MAC_STUDIO_BRANCH,
  MAC_STUDIO_REQUIRE_HEAD, and MAC_STUDIO_CONNECT_TIMEOUT mirror the options.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET="${2:?--target requires a value}"
      shift 2
      ;;
    --repo-path)
      REPO_PATH="${2:?--repo-path requires a value}"
      shift 2
      ;;
    --branch)
      EXPECTED_BRANCH="${2:?--branch requires a value}"
      shift 2
      ;;
    --require-head)
      REQUIRE_HEAD="${2:?--require-head requires a value}"
      shift 2
      ;;
    --connect-timeout)
      CONNECT_TIMEOUT="${2:?--connect-timeout requires a value}"
      shift 2
      ;;
    --allow-dirty)
      ALLOW_DIRTY=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${TARGET}" ]]; then
  echo "Mac Studio SSH target is required." >&2
  exit 2
fi

if [[ -z "${REPO_PATH}" ]]; then
  echo "Mac Studio repo path is required." >&2
  exit 2
fi

if [[ "${DRY_RUN}" == "1" ]]; then
  echo "Would check Mac Studio runtime checkout:"
  echo "  target=${TARGET}"
  echo "  repo_path=${REPO_PATH}"
  echo "  expected_branch=${EXPECTED_BRANCH}"
  if [[ -n "${REQUIRE_HEAD}" ]]; then
    echo "  required_head=${REQUIRE_HEAD}"
  fi
  echo "  ssh_opts=-o BatchMode=yes -o ConnectTimeout=${CONNECT_TIMEOUT}"
  exit 0
fi

remote_output="$(
  ssh -o BatchMode=yes -o ConnectTimeout="${CONNECT_TIMEOUT}" "${TARGET}" \
    "bash -s -- $(printf '%q' "${REPO_PATH}")" <<'REMOTE'
set -euo pipefail
repo_path="$1"
cd "${repo_path}"
printf 'repo_path=%s\n' "${PWD}"
printf 'branch=%s\n' "$(git rev-parse --abbrev-ref HEAD)"
printf 'head=%s\n' "$(git rev-parse HEAD)"
printf 'status_porcelain_begin\n'
git status --porcelain=v1 -b
printf 'status_porcelain_end\n'
REMOTE
)"

printf '%s\n' "${remote_output}"

remote_repo_path="$(printf '%s\n' "${remote_output}" | awk -F= '$1 == "repo_path" {print $2; exit}')"
remote_branch="$(printf '%s\n' "${remote_output}" | awk -F= '$1 == "branch" {print $2; exit}')"
remote_head="$(printf '%s\n' "${remote_output}" | awk -F= '$1 == "head" {print $2; exit}')"

if [[ "${remote_repo_path}" != "${REPO_PATH}" ]]; then
  echo "Mac Studio runtime checkout resolved unexpected path: ${remote_repo_path}" >&2
  echo "Expected: ${REPO_PATH}" >&2
  exit 1
fi

if [[ -n "${EXPECTED_BRANCH}" && "${remote_branch}" != "${EXPECTED_BRANCH}" ]]; then
  echo "Mac Studio runtime checkout is on branch ${remote_branch}; expected ${EXPECTED_BRANCH}." >&2
  exit 1
fi

if [[ -n "${REQUIRE_HEAD}" && "${remote_head}" != "${REQUIRE_HEAD}" ]]; then
  echo "Mac Studio runtime checkout is not at the required Git head." >&2
  echo "Remote:   ${remote_head}" >&2
  echo "Required: ${REQUIRE_HEAD}" >&2
  echo "Fast-forward the runtime clone, then rerun the golden pipeline check." >&2
  exit 1
fi

dirty_lines="$(
  printf '%s\n' "${remote_output}" | awk '
    /^status_porcelain_begin$/ { inside = 1; next }
    /^status_porcelain_end$/ { inside = 0; next }
    inside && $0 !~ /^## / { print }
  '
)"

if [[ "${ALLOW_DIRTY}" != "1" && -n "${dirty_lines}" ]]; then
  echo "Mac Studio runtime checkout has local changes:" >&2
  printf '%s\n' "${dirty_lines}" >&2
  exit 1
fi

echo "Mac Studio runtime checkout is reachable and matches the expected revision."
