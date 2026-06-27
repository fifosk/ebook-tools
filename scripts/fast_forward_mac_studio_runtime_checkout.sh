#!/usr/bin/env bash
set -euo pipefail

TARGET="${MAC_STUDIO_SSH_TARGET:-fifo@192.168.1.9}"
REPO_PATH="${MAC_STUDIO_REPO_PATH:-/Users/fifo/Projects/home/ebook-tools}"
EXPECTED_BRANCH="${MAC_STUDIO_BRANCH:-main}"
CONNECT_TIMEOUT="${MAC_STUDIO_CONNECT_TIMEOUT:-5}"
DRY_RUN=0

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/fast_forward_mac_studio_runtime_checkout.sh [options]

Options:
  --target USER@HOST           SSH target. Defaults to fifo@192.168.1.9.
  --repo-path PATH             Runtime checkout path on the remote host.
                               Defaults to /Users/fifo/Projects/home/ebook-tools.
  --branch NAME                Expected branch to fast-forward. Defaults to main.
  --connect-timeout SECONDS    SSH connect timeout. Defaults to 5.
  --dry-run                    Print the SSH update that would run without connecting.
  -h, --help                   Show this help.

Environment:
  MAC_STUDIO_SSH_TARGET, MAC_STUDIO_REPO_PATH, MAC_STUDIO_BRANCH, and
  MAC_STUDIO_CONNECT_TIMEOUT mirror the options.
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
    --connect-timeout)
      CONNECT_TIMEOUT="${2:?--connect-timeout requires a value}"
      shift 2
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

if [[ -z "${EXPECTED_BRANCH}" ]]; then
  echo "Mac Studio branch is required." >&2
  exit 2
fi

if [[ "${DRY_RUN}" == "1" ]]; then
  echo "Would fast-forward Mac Studio runtime checkout:"
  echo "  target=${TARGET}"
  echo "  repo_path=${REPO_PATH}"
  echo "  branch=${EXPECTED_BRANCH}"
  echo "  ssh_opts=-o BatchMode=yes -o ConnectTimeout=${CONNECT_TIMEOUT}"
  echo "  command=git pull --ff-only origin ${EXPECTED_BRANCH}"
  exit 0
fi

ssh -o BatchMode=yes -o ConnectTimeout="${CONNECT_TIMEOUT}" "${TARGET}" \
  "bash -s -- $(printf '%q' "${REPO_PATH}") $(printf '%q' "${EXPECTED_BRANCH}")" <<'REMOTE'
set -euo pipefail
repo_path="$1"
expected_branch="$2"
cd "${repo_path}"
printf 'repo_path=%s\n' "${PWD}"
branch="$(git rev-parse --abbrev-ref HEAD)"
printf 'branch=%s\n' "${branch}"
if [[ "${branch}" != "${expected_branch}" ]]; then
  echo "Mac Studio runtime checkout is on branch ${branch}; expected ${expected_branch}." >&2
  exit 1
fi

prune_untracked_export_assets() {
  if [[ ! -f "web/export-dist/export.html" || ! -d "web/export-dist/assets" ]]; then
    return
  fi
  referenced_export_asset="$(
    sed -n 's/.*src="\.\/assets\/\(export-[^"]*\.js\)".*/\1/p' web/export-dist/export.html | head -n 1
  )"
  if [[ -z "${referenced_export_asset}" ]]; then
    return
  fi
  for candidate in web/export-dist/assets/export-*.js; do
    [[ -e "${candidate}" ]] || continue
    candidate_name="$(basename "${candidate}")"
    [[ "${candidate_name}" != "${referenced_export_asset}" ]] || continue
    if [[ "$(git status --porcelain=v1 -- "${candidate}" | awk '{print $1}')" == "??" ]]; then
      rm -f -- "${candidate}"
      printf 'pruned_untracked_export_asset=%s\n' "${candidate}"
    fi
  done
}

prune_untracked_export_assets

dirty_lines="$(git status --porcelain=v1)"
if [[ -n "${dirty_lines}" ]]; then
  echo "Mac Studio runtime checkout has local changes; refusing to pull:" >&2
  printf '%s\n' "${dirty_lines}" >&2
  exit 1
fi

printf 'before_head=%s\n' "$(git rev-parse HEAD)"
git fetch --prune origin "${expected_branch}"
git pull --ff-only origin "${expected_branch}"

prune_untracked_export_assets

post_pull_dirty="$(git status --porcelain=v1)"
if [[ -n "${post_pull_dirty}" ]]; then
  echo "Mac Studio runtime checkout has local changes after fast-forward:" >&2
  printf '%s\n' "${post_pull_dirty}" >&2
  exit 1
fi

printf 'after_head=%s\n' "$(git rev-parse HEAD)"
printf 'status_porcelain_begin\n'
git status --porcelain=v1 -b
printf 'status_porcelain_end\n'
REMOTE

echo "Mac Studio runtime checkout fast-forward complete."
