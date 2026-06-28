# Deployment Guide

This guide covers Docker Compose production deployment, which is the primary
runtime environment for ebook-tools. Both the backend (FastAPI) and frontend
(React SPA served by Nginx) run as containers on the same host, managed by
Docker Compose. The monitoring stack (Prometheus, Grafana, PostgreSQL exporter)
runs alongside the application containers.

For the Kubernetes/Helm POC deployment, see [kubernetes.md](kubernetes.md).

## Architecture Overview

```
Internet --> Synology DSM (:443 TLS) --> Frontend Container (Nginx :5173)
                                               |  proxy /api/, /pipelines/, /storage/
                                               v
                                         Backend Container (FastAPI :8000)
                                               |  SQLAlchemy    |  volumes    |  /metrics
                                               v                v             v
                                         PostgreSQL 16     Host: storage/  Prometheus (:9090)
                                               |                               |
                                               v                               v
                                         pg-backup sidecar              Grafana (:3000)
                                         pg-exporter (:9187) ----------┘
```

The Synology DSM reverse proxy terminates TLS at port 443 and forwards traffic
to the frontend Nginx container on the Mac Studio runtime host. Nginx serves the
React SPA for all unmatched routes and reverse-proxies API, pipeline, and
storage requests to the backend container. The backend reads and writes data
through Docker volume mounts that map Mac Studio/NAS-mounted host directories
into the container filesystem.

![System Overview](images/system-overview.png)

---

## Docker Compose (Production)

### Starting Services

```bash
docker compose up -d              # start backend + frontend (detached)
docker compose logs -f            # follow logs from both containers
docker compose ps                 # check container status
```

The frontend container waits for the backend to pass its health check before
starting (`depends_on: condition: service_healthy`). The backend waits for
PostgreSQL to be healthy before starting. The backend health check polls
`http://localhost:8000/_health` every 30 seconds with a 10-second startup grace
period.

### Rebuilding After Code Changes

**Important**: Running `docker compose up -d` alone only recreates containers
from existing images. It does not pick up source code changes. You must pass
`--build` to rebuild the image(s):

```bash
# Rebuild both images and restart
docker compose up -d --build

# Rebuild only the backend (e.g., after Python code changes)
docker compose up -d --build backend

# Rebuild only the frontend (e.g., after React/TypeScript changes)
docker compose up -d --build frontend
```

### Verify

```bash
# Backend health check
curl http://localhost:8000/_health
# Expected: {"status":"ok"}

# Public non-secret runtime descriptor for Apple pipeline preflights
curl http://localhost:8000/api/system/runtime

# Frontend serves the React SPA
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/
# Expected: 200
```

## Apple Device Deployment Recipe

Use simulator and local-surface builds first, then physical devices only after
an explicit deploy request. The unattended helper keeps the device flow
repeatable across iPhone, iPad, and Apple TV:

```bash
# Inspect available CoreDevice targets.
bash scripts/apple_unattended_device_update.sh --list

# Non-mutating health check for the selected device.
APPLE_DEVICE_ID="<device-id-or-name>" \
  bash scripts/apple_unattended_device_update.sh --profile ipad --device-preflight-only

# Build without installing.
APPLE_DEVICE_ID="<device-id-or-name>" \
  bash scripts/apple_unattended_device_update.sh --profile ipad --build-only

# Preview the exact build/install/verify/launch commands.
APPLE_DEVICE_ID="<device-id-or-name>" CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  bash scripts/apple_unattended_device_update.sh --profile ipad --install --launch --dry-run

# Relaunch an already-installed app with console attached; no build or install.
APPLE_DEVICE_ID="<device-id-or-name>" CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  bash scripts/apple_unattended_device_update.sh --profile ipad \
    --launch-only --launch-console-timeout 60
```

When the user has explicitly requested a physical deploy, remove `--dry-run`.
The golden install path is: CoreDevice preflight, build or `--skip-build`,
`devicectl device install app`, installed-bundle metadata verification, then an
optional launch. Add `--launch-console-timeout 10` when validating that the app
does not immediately crash after launch; a console timeout is treated as
success after the app survives the launch window.
For manual playback debugging after the app is already installed, prefer
`--launch-only --launch-console-timeout <seconds>` so CoreDevice terminates and
relaunches the app with console attached, without rebuilding or reinstalling.
Console output is also persisted to
`test-results/apple-device-launch-console-<device>.log` unless
`APPLE_DEVICE_LAUNCH_LOG` overrides the path.

For Apple TV, use `--profile appletv`. That selects the `InteractiveReaderTV`
scheme, `com.example.InteractiveReader.tvos` bundle id, and
`Debug-appletvos/InteractiveReaderTV.app` output path. For iPhone/iPad, use
`--profile iphone` or `--profile ipad`, both targeting the
`InteractiveReader` iOS app.

If Xcode CLI signing cannot use the signed-in account but Xcode-managed local
profiles already contain the full iCloud, Sign in with Apple, and Push
capability set, preserve entitlements by building the app with
`CODE_SIGNING_ALLOWED=NO`, embedding the full-capability provisioning profiles,
codesigning nested bundles first and the app last. Device selectors may be
friendly names; the deploy helper resolves them to the hardware UDID before
calling `xcodebuild`. Prefer the repo-owned
planner before hand-running the sequence:

```bash
make apple-device-full-entitlement-plan APPLE_DEVICE_ID="<device-id-or-name>"
```

The planner auto-discovers compatible local profiles from Xcode's provisioning
profile caches, preferring an exact full-capability app profile and a matching
or wildcard extension profile. It also auto-selects the only valid local
`Apple Development:` signing identity; keep `APPLE_DEVELOPMENT_IDENTITY`,
`FULL_CAPABILITY_IOS_PROFILE`, and `WILDCARD_IOS_EXTENSION_PROFILE` for unusual
cases where you need to override that selection, and use
`APPLE_PROVISIONING_PROFILE_DIRS` or repeated `--profile-dir` arguments to point
the planner at a specific profile cache.

When hand-signing the bundle, use merged entitlements rather than the project
entitlements file alone. The app signature needs the profile-generated
`application-identifier`, team id, `get-task-allow`, and keychain group in
addition to the app iCloud/Push/Sign in with Apple values; the notification
extension needs its own app id, team id, `get-task-allow`, and keychain group.
Generate those files with `scripts/apple_merge_entitlements.py`; the
`apple-device-full-entitlement-plan` output includes the exact commands and
uses the generated plist paths in its codesign steps.
Otherwise local `codesign --verify` can pass while device install fails with
`0xe8008015`.

The planner is dry by default. To run the same flow without installing, use:

```bash
make apple-device-full-entitlement-build APPLE_DEVICE_ID="<device-id-or-name>"
```

After an explicit physical-device deploy request, run the guarded install handoff
with:

```bash
CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  make apple-device-full-entitlement-install APPLE_DEVICE_ID="<device-id-or-name>"
```

Do not use the entitlement-stripping fallback when testing iCloud features. It
exists only as an explicit local-signing escape hatch and requires
`APPLE_DEVICE_ALLOW_ENTITLEMENT_STRIPPING=YES`.

If the confirmed install build still fails because command-line Xcode cannot
use the signed-in account, install an already signed full-entitlement bundle
without switching to the entitlement-stripping path:

```bash
CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  make apple-device-full-entitlement-stable-install \
    APPLE_DEVICE_PROFILE=ipad \
    APPLE_DEVICE_ID="<device-id-or-name>" \
    APPLE_DEVICE_SIGNED_ARTIFACT_PATH=test-results/DerivedData-device-full-entitlements/Build/Products/Debug-iphoneos/InteractiveReader.app
```

That shortcut is the preferred "latest stable" path when the signed artifact is
already current. It skips Xcode rebuilds, verifies the app's code signature plus
current bundle id, marketing version, and build number before CoreDevice
preflight/install, installs it, verifies installed metadata, then launches with
the crash-watch timeout. If the target iPhone or iPad is locked, the helper
keeps the verified install as successful and reports that foreground launch was
denied by the lock screen.

If you want the helper to try a command-line Xcode build first and swap to the
signed artifact only after that build fails, use:

```bash
CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  make apple-device-full-entitlement-fallback-install \
    APPLE_DEVICE_PROFILE=ipad \
    APPLE_DEVICE_ID="<device-id-or-name>" \
    APPLE_DEVICE_SIGNED_ARTIFACT_PATH=test-results/DerivedData-device-full-entitlements/Build/Products/Debug-iphoneos/InteractiveReader.app
```

The shortcut delegates to the unattended helper with
`--fallback-to-signed-artifact`; the helper verifies the fallback app's code
signature plus current bundle id, marketing version, and build number before
calling `devicectl install`. Override `APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT`
when the post-launch crash-watch should run longer than the default 10 seconds.

#### Working Local Device Profiles

Last known working iPad Pro unattended profile:

```bash
# Device visible via: xcrun devicectl list devices
APPLE_DEVICE_PROFILE=ipad
APPLE_DEVICE_ID=BC4A8986-54B2-543C-83CB-4B28F4F73BB2 # Fifo Ipad Pro
APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT=10
APPLE_DEVICE_SIGNED_ARTIFACT_PATH=test-results/DerivedData-device-full-entitlements/Build/Products/Debug-iphoneos/InteractiveReader.app
```

For this iPad Pro, the reliable unattended deploy command is:

```bash
CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  make apple-device-full-entitlement-fallback-install \
    APPLE_DEVICE_PROFILE=ipad \
    APPLE_DEVICE_ID=BC4A8986-54B2-543C-83CB-4B28F4F73BB2 \
    APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT=10
```

As of June 27, 2026, the full-entitlement planner can build, sign, install, and
launch-watch the iPad Pro path without opening Xcode. Reuse the freshly signed
`Debug-iphoneos/InteractiveReader.app` artifact for iPhone with `--skip-build`,
and build tvOS directly with the unattended helper. A 10-second launch console
timeout is the expected app-alive crash-watch success after installed metadata
has verified the current bundle version.

Latest iPad Pro arrow-key validation deploy from June 27, 2026:

```bash
CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
APPLE_DEVICE_PROFILE=ipad \
APPLE_DEVICE_ID=BC4A8986-54B2-543C-83CB-4B28F4F73BB2 \
APPLE_DEVICE_LAUNCH_CONSOLE_TIMEOUT=10 \
  make apple-device-full-entitlement-install
```

That run resolved the physical UDID `00008142-001C71AE3AC2401C`, built and
installed `InteractiveReader` marketing version `2026.6.27` bundle version
`20260627001`, launched the app, registered remote notifications, and reached
the 10-second launch-console timeout, which is the expected app-alive signal.

Latest working June 26, 2026 deployment:

```bash
SIGNING_IDENTITY="Apple Development: Marek Fejo (PW4WQY9RKJ)"

CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  bash scripts/apple_full_entitlement_signing_plan.sh \
    --execute \
    --install \
    --device BC4A8986-54B2-543C-83CB-4B28F4F73BB2 \
    --signing-identity "$SIGNING_IDENTITY" \
    --launch-console-timeout 10

APPLE_DEVICECTL_TIMEOUT=180 \
CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  bash scripts/apple_unattended_device_update.sh \
    --profile iphone \
    --device FD7EB648-3D5F-5766-BDBF-05053E2D4CD7 \
    --skip-build \
    --app-path test-results/DerivedData-device-full-entitlements/Build/Products/Debug-iphoneos/InteractiveReader.app \
    --install \
    --launch \
    --launch-console-timeout 10

CONFIRM_PHYSICAL_DEVICE_UPDATE=YES \
  bash scripts/apple_unattended_device_update.sh \
    --profile appletv \
    --device 5E147DC8-5206-5EF2-A472-5748F7CDF7B0 \
    --install \
    --launch \
    --launch-console-timeout 10 \
    --allow-provisioning-updates
```

That run installed and verified `InteractiveReader` on iPad Pro and iPhone and
`InteractiveReaderTV` on Living Room Apple TV at `2026.6.26` build
`20260626174`. The iPad, iPhone, and Apple TV launch watches reached the
10-second timeout and were treated as app-alive checks. Keep `Cinema` Apple TV
and `iPad Small` out of bulk runs while CoreDevice reports them unavailable.
If iPhone install fails with a transient CoreDevice `IXRemoteErrorDomain`
connection interruption, retrying the same skip-build install with
`APPLE_DEVICECTL_TIMEOUT=180` has been enough to complete the transfer.

Latest Apple TV Music-bed validation deploy from June 27, 2026 used the same
`appletv` helper path against Living Room Apple TV
`5E147DC8-5206-5EF2-A472-5748F7CDF7B0` from commit `79421062`, including
`--allow-provisioning-updates` and a 10-second launch console crash-watch. The
post-install verification reported:

```text
InteractiveReaderTV   com.example.InteractiveReader.tvos   2026.6.27   20260627001
```

Launch logs showed reader Now Playing attaching the sentence player, MusicKit
restoring the persisted bed queue, entering `appleMusicBed`, and reader
Now Playing publishing/reasserting active playback before the launch console
timeout was treated as app-alive. After a launch-console capture, run
`make apple-device-verify-music-bed-launch-log APPLE_DEVICE_ID=<device>` to
check the startup breadcrumbs, or set
`APPLE_MUSIC_BED_LAUNCH_LOG_MODE=pause-release` after a manual Play/Pause
capture to require reader-owned Music pause and tvOS Music surface release
evidence.

### Makefile Shortcuts

The Makefile provides convenience targets for common Docker operations:

| Target              | Command                          | Description                    |
|---------------------|----------------------------------|--------------------------------|
| `make docker-build` | `docker build ...` (both images) | Build backend + frontend images |
| `make docker-up`    | `docker compose up -d`           | Start services                 |
| `make docker-down`  | `docker compose down`            | Stop services                  |
| `make docker-logs`  | `docker compose logs -f`         | Follow container logs          |
| `make docker-status`| `docker compose ps` + curl checks| Health check summary           |

---

### Volume Mounts

The backend container mounts several host directories for persistent storage,
configuration, and NAS access:

| Host Path | Container Path | Mode | Purpose |
|---|---|---|---|
| `./storage` | `/app/storage` | rw | Jobs, ebooks, covers, library, exports |
| `./config/users` | `/app/config/users` | rw | User credentials (users.json) |
| `./conf/config.local.json` | `/app/conf/config.local.json` | ro | Local config overrides |
| `./.env.local` | `/app/.env.local` | ro | OAuth client IDs, SMTP, ML model paths |
| `./conf/certs` | `/app/conf/certs` | ro | APNs keys and TLS certificates |
| `./log` | `/app/log` | rw | Structured JSON logs |
| `/Volumes/Data/Download/Ebooks` | `/app/nas/ebooks` | ro | NAS ebook files |
| `/Volumes/Data/Download/DStation` | `/app/nas/videos` | rw | YouTube downloaded videos |
| `/Volumes/Data/Download/Subtitles` | `/app/nas/subtitles` | rw | Subtitle mirror directory |
| (tmpfs) | `/app/tmp` | 1 GB | Temp workspace (RAM-backed) |

The tmpfs mount replaces the macOS RAMDisk feature, which is unavailable inside
Linux containers. Set `EBOOK_USE_RAMDISK=false` (already the default in Docker)
to prevent the backend from attempting to mount its own RAMDisk.

---

### Docker Environment Variables

These environment variables are set in `docker-compose.yml` and tuned for the
containerized runtime:

| Variable | Value | Why |
|---|---|---|
| `DATABASE_URL` | `postgresql://ebook_tools:...@postgres/ebook_tools` | PostgreSQL connection string; enables PG backends for all 6 domains |
| `EBOOK_API_STATIC_ROOT` | `""` (empty) | Frontend is a separate Nginx container; disable built-in SPA serving |
| `EBOOK_TTS_BACKEND` | `gtts` | macOS `say` is unavailable in Linux containers |
| `EBOOK_USE_RAMDISK` | `false` | Docker tmpfs replaces the macOS RAMDisk |
| `JOB_STORAGE_DIR` | `/app/storage` | Container path for job persistence |
| `EBOOK_LIBRARY_ROOT` | `/app/storage/library` | Container path for library sync |
| `EBOOK_EBOOKS_DIR` | `/app/nas/ebooks` | NAS mount for EPUB source files |
| `YOUTUBE_VIDEO_ROOT` | `/app/nas/videos` | NAS mount for downloaded videos |
| `SUBTITLE_SOURCE_DIR` | `/app/nas/subtitles` | NAS mount for subtitle files |
| `EBOOK_STORAGE_BASE_URL` | `https://api.langtools.fifosk.synology.me/storage/jobs` | Public URL for media download links |
| `EBOOK_API_CORS_ORIGINS` | (space-separated list) | Allowed CORS origins for the production domain and localhost |

**Backend OAuth variables** (loaded from `.env.local` volume mount):

| Variable | Description |
|---|---|
| `EBOOK_AUTH_GOOGLE_CLIENT_IDS` | Comma-separated Google OAuth client IDs for token verification |
| `EBOOK_AUTH_APPLE_CLIENT_IDS` | Comma-separated Apple Sign In audience identifiers (bundle IDs + web services ID) |

**Frontend build-time variables** (baked into the JS bundle via Vite):

| Variable | Value | Notes |
|---|---|---|
| `VITE_API_BASE_URL` | `https://api.langtools.fifosk.synology.me` | Backend API URL as seen by browsers |
| `VITE_STORAGE_BASE_URL` | `https://api.langtools.fifosk.synology.me/storage/jobs` | Must include the `/jobs` segment |
| `VITE_GOOGLE_CLIENT_ID` | (your Google OAuth client ID) | Enables Google Sign In button on login form |
| `VITE_APPLE_CLIENT_ID` | (your Apple Services ID) | Enables Apple Sign In button on login form |
| `VITE_APPLE_REDIRECT_URI` | (your redirect URI) | Apple Sign In callback URL |
| `BACKEND_HOST` | `backend` | Docker service name; used by Nginx `upstream` block at runtime |

**Warning**: `VITE_*` variables are embedded at build time. Changing them
requires rebuilding the frontend image (`docker compose up -d --build frontend`).

---

### Optional Environment Overrides

Copy `.env.docker.example` to `.env.docker` to override variables without
editing `docker-compose.yml`. The file is gitignored and loaded via the
`env_file` directive. Values set here take precedence over the `environment`
section in the Compose file.

Common overrides include:

```bash
# LLM / Translation
LLM_SOURCE=cloud
OLLAMA_URL=http://host.docker.internal:11434/api/chat

# Image Generation (Draw Things running on the host)
EBOOK_IMAGE_API_BASE_URL=http://host.docker.internal:7860
EBOOK_IMAGE_CONCURRENCY=2

# Performance tuning
EBOOK_THREAD_COUNT=8
EBOOK_QUEUE_SIZE=20
```

Use `host.docker.internal` to reach services running on the Docker host (e.g.,
Ollama or Draw Things).

---

### Key Docker Files

| File | Purpose |
|---|---|
| `docker-compose.yml` | Orchestration, volumes, env vars, health checks |
| `docker/backend/Dockerfile` | Python 3.10-slim + FFmpeg + espeak-ng + pip install |
| `docker/frontend/Dockerfile` | Node 20 (pnpm build) then Nginx 1.27-alpine (serve) |
| `docker/frontend/nginx.conf` | SPA routing + API/pipeline/storage reverse proxy |
| `.env.docker` | Optional env var overrides (gitignored; see `.env.docker.example`) |
| `scripts/docker-entrypoint.sh` | Runs Alembic migrations then starts uvicorn |
| `alembic.ini` + `alembic/` | Database schema migrations (14 tables) |
| `modules/database/` | SQLAlchemy 2.0 models, engine singleton, session factory |

#### Backend Dockerfile

The backend image is based on `python:3.10-slim-bookworm` and installs:

- **FFmpeg** -- required by pydub for audio format conversion
- **espeak-ng** + **libespeak-ng-dev** -- required by piper-tts for phoneme generation
- **libpq-dev** -- PostgreSQL client library (required by psycopg2)
- **gcc / python3-dev / libc6-dev** -- for building C extensions (psutil, bcrypt, psycopg2)

A non-root `appuser` (UID 1000) runs the application. Dependencies are cached
in a separate layer so only source code changes trigger a slow rebuild.

#### Frontend Dockerfile

A two-stage build:

1. **Builder stage** (Node 20-alpine): installs dependencies with pnpm, runs
   TypeScript type checking (`tsc -b`), and builds the SPA with Vite.
2. **Runtime stage** (Nginx 1.27-alpine): copies the built `dist/` into
   `/usr/share/nginx/html` and uses the nginx.conf template.

#### Nginx Configuration

The Nginx config is processed as an `envsubst` template at container startup.
The `${BACKEND_HOST}` variable is substituted with the Docker service name
(`backend`) to configure the upstream proxy.

Key routing rules:

- `/api/`, `/pipelines/`, `/storage/` -- reverse-proxied to the backend with
  SSE support (buffering off, 1-hour read timeout)
- `/assets/` -- 1-year cache with `immutable` header (Vite hashed filenames)
- `/_health` -- passed through to the backend health endpoint
- `/` (catch-all) -- serves `index.html` with no-cache headers for client-side
  routing

---

## PostgreSQL Database

The backend persists users, sessions, library entries, configuration, bookmarks,
and resume positions in a PostgreSQL 16 database. The database runs as a
container alongside the backend and frontend.

### Container Configuration

The `postgres` service in `docker-compose.yml` runs PostgreSQL 16 Alpine with
tuned memory settings:

| Setting | Value | Purpose |
|---------|-------|---------|
| `shared_buffers` | 256 MB | Shared memory for caching |
| `effective_cache_size` | 512 MB | Planner hint for OS page cache |
| `work_mem` | 16 MB | Per-operation sort/hash memory |
| `max_connections` | 50 | Connection pool ceiling |

Data is stored on the NAS at `/Volumes/Data/Databases/ebook-tools/postgres`.

### Schema

The database contains 14 tables across 6 domains:

| Domain | Tables | Notes |
|--------|--------|-------|
| Users | `users` | Username, bcrypt hash, roles (JSONB), metadata |
| Sessions | `sessions` | Token, user FK, expiry, user agent, IP |
| Library | `library_items`, `books`, `library_item_grants` | tsvector FTS with GIN index, JSONB metadata |
| Config | 6 tables (`config_snapshots`, `config_audit_log`, `config_sensitive_keys`, `config_secrets`, `config_group_settings`, `config_validation_rules`, `config_restart_log`) | JSONB config storage, Fernet encryption for secrets |
| Bookmarks | `bookmarks` | Per-user, per-job playback bookmarks |
| Resume | `resume_positions` | Per-user, per-job resume positions |

### Alembic Migrations

Schema migrations are managed by Alembic and run automatically at container
startup via `scripts/docker-entrypoint.sh`:

```bash
# The entrypoint runs this before starting uvicorn:
python3 -m alembic upgrade head
```

To run migrations manually:

```bash
docker exec ebook-tools-backend python3 -m alembic upgrade head
```

### Backup Sidecar

The `pg-backup` container runs a daily `pg_dump` compressed with gzip. Backups
are stored on the NAS at `/Volumes/Backups/ebook-tools/postgres` with 7-day
retention:

```bash
# Verify backups exist
ls /Volumes/Backups/ebook-tools/postgres/*.sql.gz

# Restore from a backup
gunzip -c /path/to/backup.sql.gz | docker exec -i ebook-tools-postgres \
  psql -U ebook_tools ebook_tools
```

### Database Volume Mounts

| Host Path | Container Path | Mode | Purpose |
|---|---|---|---|
| `/Volumes/Data/Databases/ebook-tools/postgres` | `/var/lib/postgresql/data` | rw | PG data directory |
| `/Volumes/Backups/ebook-tools/postgres` | `/backups` | rw | Daily backup dumps |

### Makefile Database Targets

| Target | Description |
|--------|-------------|
| `make db-shell` | Open `psql` shell in the PostgreSQL container |
| `make db-migrate` | Run `alembic upgrade head` in the backend container |
| `make db-backup` | Trigger an immediate `pg_dump` backup |
| `make db-restore` | Restore from a gzipped SQL dump |

### Dual-Mode Operation

The backend supports running with or without PostgreSQL. When `DATABASE_URL` is
set in the environment, the backend uses PostgreSQL for all 6 domains. When
unset, it falls back to the legacy JSON/SQLite storage backends.

**Rollback**: To revert to legacy storage, unset `DATABASE_URL` in
`docker-compose.yml` and restart. The legacy files (if not archived) are read
immediately. No data migration is needed for rollback.

---

## Monitoring Stack

The observability stack runs alongside the application containers in the same
`docker-compose.yml` and is managed through dedicated Makefile targets.

### Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| Prometheus | `prom/prometheus:v2.51.0` | 9090 | Scrapes backend metrics (10s) and PG exporter (30s) |
| Grafana | `grafana/grafana-oss:11.0.0` | 3000 | 4 auto-provisioned dashboards |
| PG Exporter | `prometheuscommunity/postgres-exporter:v0.15.0` | 9187 | Bridges PostgreSQL stats to Prometheus |

### Makefile Targets

| Target | Description |
|--------|-------------|
| `make monitoring-up` | Start Prometheus, Grafana, and PG exporter |
| `make monitoring-down` | Stop monitoring services |
| `make monitoring-logs` | Follow monitoring container logs |
| `make monitoring-status` | Health check all 3 monitoring services |

### Access

| Service | URL |
|---------|-----|
| Grafana | `https://grafana.langtools.fifosk.synology.me` |
| Prometheus | `https://prometheus.langtools.fifosk.synology.me` |

Grafana credentials: `${GRAFANA_ADMIN_USER:-admin}` / `${GRAFANA_ADMIN_PASSWORD:-ebook_tools_grafana}`

### Data Persistence

| Host Path | Purpose |
|-----------|---------|
| `/Volumes/Data/Monitoring/prometheus` | Prometheus TSDB (90-day retention, 20 GB cap) |
| `/Volumes/Data/Monitoring/grafana` | Grafana database and plugins |

For full details on metrics, dashboards, adding new metrics, and observability
tests, see [observability.md](observability.md).

---

## Synology DSM Reverse Proxy

TLS termination is handled by the Synology DSM reverse proxy, which listens on
port 443 and forwards traffic to the frontend Nginx container on port 5173.

Configure a reverse proxy entry in DSM Control Panel:

| Field | Value |
|---|---|
| Description | ebook-tools frontend |
| Source protocol | HTTPS |
| Source port | 443 |
| Destination hostname | `localhost` (or Mac Studio IP/hostname) |
| Destination port | 5173 |
| Destination protocol | HTTP |

The DSM proxy handles certificate renewal (e.g., via Let's Encrypt) and
presents a trusted certificate to browsers. No TLS configuration is needed in
the Docker containers.

---

## Production API Access

### Getting a Session Token from the CLI

```bash
# Login using the CLI (stores token in ~/.ebooktools_active_session)
python3 -c "from modules.cli.main import main; main(['user', 'login', 'USERNAME'])"

# Or extract the most recent token from the session file:
cat ~/.ebooktools_session.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
sessions = data.get('sessions', {})
latest = max(sessions.items(), key=lambda x: x[1].get('created_at', ''))
print('Token:', latest[0])
"
```

### Using Tokens with curl

```bash
TOKEN="your_session_token"

# Check session
curl -s "https://api.langtools.fifosk.synology.me/api/auth/session" \
  -H "Authorization: Bearer $TOKEN"

# List jobs
curl -s "https://api.langtools.fifosk.synology.me/api/pipelines/jobs" \
  -H "Authorization: Bearer $TOKEN"

# Get media metadata for a job
curl -s "https://api.langtools.fifosk.synology.me/api/pipelines/jobs/{job_id}/media" \
  -H "Authorization: Bearer $TOKEN"

# SSE events (use query parameter for EventSource compatibility)
curl -N "https://api.langtools.fifosk.synology.me/api/pipelines/{job_id}/events?access_token=$TOKEN"
```

---

## HTTPS Configuration

### Production (Recommended)

In production, TLS is handled by the Synology DSM reverse proxy. Neither the
backend nor frontend containers need TLS configuration. Traffic between the DSM
proxy and the frontend container stays on the local network over HTTP.

### Local Development -- Backend

For local development with HTTPS, generate a self-signed certificate and pass it
to uvicorn:

```bash
mkdir -p conf/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -subj "/CN=localhost" \
  -keyout conf/certs/dev.key \
  -out conf/certs/dev.crt

python3 -m modules.webapi --reload \
  --ssl-certfile conf/certs/dev.crt \
  --ssl-keyfile conf/certs/dev.key
```

Or via environment variables with the shell helper:

```bash
EBOOK_API_ENABLE_HTTPS=1 \
EBOOK_API_SSL_CERTFILE=conf/certs/dev.crt \
EBOOK_API_SSL_KEYFILE=conf/certs/dev.key \
./scripts/run-webapi.sh --reload
```

### Local Development -- Frontend

Enable HTTPS in the Vite dev server by adding to `web/.env.local`:

```bash
VITE_DEV_HTTPS=true
VITE_DEV_HTTPS_CERT=../conf/certs/dev.crt
VITE_DEV_HTTPS_KEY=../conf/certs/dev.key
```

---

## Important Gotchas

### VITE_* Variables Are Baked at Build Time

`VITE_API_BASE_URL` and `VITE_STORAGE_BASE_URL` are embedded into the JS bundle
during the Docker image build. Changing these values requires rebuilding the
frontend image:

```bash
docker compose up -d --build frontend
```

Simply restarting the container will not pick up new values.

### Code Changes Require `--build`

Running `docker compose up -d` without `--build` only recreates containers from
existing images. Source code changes (Python, TypeScript, etc.) are not picked
up. Always use:

```bash
docker compose up -d --build
```

### localStorage May Cache Old Paths

The frontend previously used hardcoded macOS NAS paths. If you see "directory is
not accessible" errors after switching to Docker, clear the browser's
localStorage for the site. The frontend now defaults to empty paths and relies
on backend environment variables.

### bcrypt Dual-Format Support

The `local_user_store.py` module supports two password hash formats:

- **Real bcrypt** (`$2b$...`) -- used in Docker (Linux) and production
- **Legacy SHA-256 shim** (`salt$hexdigest`) -- used by the development bcrypt
  shim on some macOS configurations

Users created locally work in Docker and vice versa. If you encounter "Invalid
salt" errors on login, verify that the `users.json` file contains valid bcrypt
hashes. Recreate the user with `ebook-tools user password <username>` if needed.

### Container Rebuild Invalidates Sessions

Rebuilding the backend container does **not** affect PostgreSQL data (sessions
persist in the database). However, if you are still using the legacy JSON session
store, rebuilding the container will lose all in-memory sessions. iOS, tvOS, and
web clients will need to re-login.

### tmpfs "Device or Resource Busy" at Startup

This is normal Docker behavior. The tmpfs mount point cannot be removed by the
application, only cleared. The `ramdisk_manager.py` module handles this
gracefully and falls back to clearing the directory contents instead.

### VITE_STORAGE_BASE_URL Must Include `/jobs`

The storage base URL must include the `/jobs` path segment. Without it, media
download links will be malformed:

```
# Correct
VITE_STORAGE_BASE_URL=https://api.langtools.fifosk.synology.me/storage/jobs

# Wrong -- missing /jobs
VITE_STORAGE_BASE_URL=https://api.langtools.fifosk.synology.me/storage
```

### Docker Host Services

To reach services running on the Docker host (Ollama, Draw Things, etc.) from
inside a container, use `host.docker.internal` instead of `localhost`:

```bash
EBOOK_IMAGE_API_BASE_URL=http://host.docker.internal:7860
OLLAMA_URL=http://host.docker.internal:11434/api/chat
```

---

## Kubernetes Deployment (POC)

An alternative Helm chart deployment to k3s is available as a proof of concept.
It runs in a Lima lightweight Linux VM on macOS and deploys the same four core
services (PostgreSQL, backend, frontend, pg-backup) via Helm templates.

```bash
# Quick start
scripts/k3s-control.sh start   # boot Lima VM + k3s
scripts/k3s-control.sh deploy  # build, import images, helm upgrade
scripts/k3s-control.sh ports   # port-forward to localhost:15173 / :18000
```

| Makefile Target | Description |
|-----------------|-------------|
| `make k8s-deploy` | `helm upgrade --install` with local images |
| `make k8s-status` | `kubectl get pods,svc,ingress,pvc,cronjobs` |
| `make k8s-logs` | Follow backend pod logs |
| `make k8s-teardown` | `helm uninstall` |
| `make k8s-lint` | Validate Helm chart templates |

The monitoring stack stays on Docker Compose and scrapes the k3s backend via
a port-forward (`localhost:18000`). Optional Argo CD integration is available
for GitOps-style deployment.

For the full guide, see [kubernetes.md](kubernetes.md).

---

## Troubleshooting

### Container Won't Start / Health Check Fails

```bash
# Check backend startup errors
docker compose logs backend --tail 50

# Check Nginx errors
docker compose logs frontend --tail 20

# Verify Python packages inside the container
docker exec ebook-tools-backend python3 -c "import modules"

# Shell into the backend container for debugging
docker exec -it ebook-tools-backend bash

# Check if the health endpoint responds
docker exec ebook-tools-backend python3 -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/_health').read())"
```

### NAS Paths Not Accessible

1. **Verify the mount is visible inside the container**:
   ```bash
   docker exec ebook-tools-backend ls /app/nas/ebooks/
   ```

2. **Check that the host path exists** -- the NAS volume must be mounted on the
   Mac Studio runtime host at the expected path (e.g.,
   `/Volumes/Data/Download/Ebooks`).

3. **Clear browser localStorage** -- the frontend may be sending cached macOS
   paths from a previous configuration. Open the browser DevTools, go to
   Application > Local Storage, and clear entries for the site.

4. **Verify backend environment variables**:
   ```bash
   docker exec ebook-tools-backend env | grep -E "EBOOK_EBOOKS|YOUTUBE|SUBTITLE"
   ```

### bcrypt "Invalid salt" on Login

The Docker container uses real bcrypt (via the `bcrypt` Python package on Linux).
If the `users.json` file contains hashes created with the legacy SHA-256 shim,
login may fail. Fix by resetting the password:

```bash
# From the host (with the Python venv activated)
ebook-tools user password <username>
```

The updated hash will work in both local development and Docker.

### Frontend Can't Reach the API

1. Verify `BACKEND_HOST` is set to `backend` (the Docker service name) in the
   frontend container environment.
2. Check that the backend container is running and healthy:
   ```bash
   docker compose ps
   ```
3. Verify the Nginx upstream can resolve the backend:
   ```bash
   docker exec ebook-tools-frontend nslookup backend
   ```
4. Check CORS settings -- the `EBOOK_API_CORS_ORIGINS` variable must include
   the origin the browser is loading from.

### Audio Generation Fails

- Docker only supports `gtts` and `piper` TTS backends. macOS `say` is not
  available inside Linux containers.
- Verify FFmpeg is installed:
  ```bash
  docker exec ebook-tools-backend ffmpeg -version
  ```
- Check permissions on the storage directories.

### Image Generation Not Working

- Verify Draw Things is running on the host:
  ```bash
  curl http://localhost:7860/sdapi/v1/txt2img
  ```
- Use `http://host.docker.internal:7860` as the image API URL in Docker.
- Increase `image_api_timeout_seconds` in `conf/config.local.json` for slow
  models.
