# Deployment Guide

This guide covers Docker Compose production deployment, which is the primary
runtime environment for ebook-tools. Both the backend (FastAPI) and frontend
(React SPA served by Nginx) run as containers on the same host, managed by
Docker Compose.

## Architecture Overview

```
Internet --> Synology DSM (:443 TLS) --> Frontend Container (Nginx :5173)
                                               |  proxy /api/, /pipelines/, /storage/
                                               v
                                         Backend Container (FastAPI :8000)
                                               |  volumes
                                               v
                                         Host: storage/, config/, NAS mounts
```

The Synology DSM reverse proxy terminates TLS at port 443 and forwards traffic
to the frontend Nginx container on the Mac Mini. Nginx serves the React SPA for
all unmatched routes and reverse-proxies API, pipeline, and storage requests to
the backend container. The backend reads and writes data through Docker volume
mounts that map host directories into the container filesystem.

![System Overview](images/system-overview.svg)

---

## Docker Compose (Production)

### Starting Services

```bash
docker compose up -d              # start backend + frontend (detached)
docker compose logs -f            # follow logs from both containers
docker compose ps                 # check container status
```

The frontend container waits for the backend to pass its health check before
starting (`depends_on: condition: service_healthy`). The backend health check
polls `http://localhost:8000/_health` every 30 seconds with a 10-second startup
grace period.

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

# Frontend serves the React SPA
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/
# Expected: 200
```

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

#### Backend Dockerfile

The backend image is based on `python:3.10-slim-bookworm` and installs:

- **FFmpeg** -- required by pydub for audio format conversion
- **espeak-ng** + **libespeak-ng-dev** -- required by piper-tts for phoneme generation
- **gcc / python3-dev / libc6-dev** -- for building C extensions (psutil, bcrypt)

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

## Synology DSM Reverse Proxy

TLS termination is handled by the Synology DSM reverse proxy, which listens on
port 443 and forwards traffic to the frontend Nginx container on port 5173.

Configure a reverse proxy entry in DSM Control Panel:

| Field | Value |
|---|---|
| Description | ebook-tools frontend |
| Source protocol | HTTPS |
| Source port | 443 |
| Destination hostname | `localhost` (or Mac Mini IP) |
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

python -m modules.webapi --reload \
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

## Troubleshooting

### Container Won't Start / Health Check Fails

```bash
# Check backend startup errors
docker compose logs backend --tail 50

# Check Nginx errors
docker compose logs frontend --tail 20

# Verify Python packages inside the container
docker exec ebook-tools-backend python -c "import modules"

# Shell into the backend container for debugging
docker exec -it ebook-tools-backend bash

# Check if the health endpoint responds
docker exec ebook-tools-backend python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/_health').read())"
```

### NAS Paths Not Accessible

1. **Verify the mount is visible inside the container**:
   ```bash
   docker exec ebook-tools-backend ls /app/nas/ebooks/
   ```

2. **Check that the host path exists** -- the NAS volume must be mounted on the
   Mac Mini at the expected path (e.g., `/Volumes/Data/Download/Ebooks`).

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
