#!/usr/bin/env bash
# postgres-guard-entrypoint.sh — refuse to start Postgres on an empty data dir.
#
# Why: the Postgres data directory is a bind-mount onto an SMB network share
# (/Volumes/Data/Databases/ebook-tools/postgres). If Docker starts this
# container before that share is mounted, the bind target is an *empty*
# directory and the stock postgres entrypoint would silently run `initdb`,
# creating a BLANK database. Worse, the pg-backup sidecar would then dump that
# blank DB over the good backups within a day — turning a transient mount race
# into permanent data loss.
#
# This guard runs before the real entrypoint and aborts (non-zero exit) if the
# data directory has no PG_VERSION marker, unless ALLOW_PG_INIT=true is set for
# a genuine first-time initialization.
#
# Wired in docker-compose.yml as the postgres service `entrypoint`; the
# existing `command:` (postgres + tuning flags) is passed through unchanged.
set -euo pipefail

PGDATA="${PGDATA:-/var/lib/postgresql/data}"

if [ ! -s "${PGDATA}/PG_VERSION" ] && [ "${ALLOW_PG_INIT:-false}" != "true" ]; then
    echo "================================================================" >&2
    echo "FATAL: ${PGDATA}/PG_VERSION is missing or empty." >&2
    echo "The Postgres data volume is almost certainly NOT mounted" >&2
    echo "(expected SMB share /Volumes/Data on the host)." >&2
    echo "" >&2
    echo "Refusing to start to avoid initializing a BLANK database over" >&2
    echo "existing data/backups. Mount the share and restart." >&2
    echo "" >&2
    echo "For a genuine first-time setup, set ALLOW_PG_INIT=true." >&2
    echo "================================================================" >&2
    exit 1
fi

# Hand off to the stock postgres entrypoint with the original command/args.
exec docker-entrypoint.sh "$@"
