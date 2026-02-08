# Claude AI Developer Guide for ebook-tools

## Project Overview

**ebook-tools** is a comprehensive toolkit for processing, translating, and narrating ebooks with multimedia output. The system converts EPUB files into multi-language narrated experiences with synchronized audio, word-level highlighting, and optional AI-generated sentence illustrations.

### Key Capabilities
- Multi-language translation with LLM fallbacks
- Text-to-speech synthesis (macOS `say`, Google TTS)
- Word-level audio synchronization and highlighting
- AI-generated sentence images via Stable Diffusion/Draw Things
- Interactive web reader with real-time word highlighting
- MyLinguist dictionary assistant (LLM-powered word/phrase lookup with structured JSON responses)
- Full-featured REST API with SSE progress streaming
- User authentication and role-based access control
- iOS/tvOS companion apps

## Architecture

### Components
1. **Backend Pipeline** (`modules/`) - Python-based processing engine
2. **Web API** (`modules/webapi/`) - FastAPI REST service with SSE
3. **Web UI** (`web/`) - React/TypeScript SPA with Vite
4. **iOS Apps** (`ios/`) - Native Swift reader applications
5. **CLI** (`modules/cli/`) - Interactive and non-interactive command-line interface

### Tech Stack
- **Backend**: Python 3.10+, FastAPI, uvicorn, pydub, Pillow
- **Frontend**: React, TypeScript, Vite
- **Deployment**: Docker Compose (backend + Nginx frontend), Synology DSM reverse proxy for TLS
- **Storage**: Filesystem-based job storage (Redis optional)
- **Audio**: gTTS, macOS `say`, FFmpeg
- **Images**: Stable Diffusion/Draw Things API integration
- **Translation**: Google Translate, Ollama LLMs with fallback support
- **Auth**: JWT sessions with bcrypt password hashing (dual-format: real bcrypt + legacy SHA-256 shim)

## Directory Structure

```
.
├── conf/                    # Core configuration files
│   ├── config.json         # Default configuration
│   └── config.local.json   # Local overrides (gitignored)
├── config/                  # Runtime configuration
│   ├── users/              # User authentication data
│   └── media.yaml          # Media generation settings
├── docker/                  # Docker deployment
│   ├── backend/Dockerfile  # Python 3.10 + FFmpeg backend image
│   └── frontend/           # Nginx frontend image
│       ├── Dockerfile      # Node build → Nginx serve
│       └── nginx.conf      # SPA routing + API reverse proxy
├── docker-compose.yml       # Production Docker Compose orchestration
├── modules/                 # Python backend modules
│   ├── audio/              # TTS backends and audio pipeline
│   ├── cli/                # Command-line interface
│   ├── core/               # Core processing logic
│   ├── images/             # Sentence image generation
│   ├── metadata_manager.py # Job metadata handling
│   ├── render/             # Audio rendering pipeline
│   ├── translation/        # Translation services
│   ├── user_management/    # Authentication system
│   └── webapi/             # FastAPI application
├── web/                     # React frontend
│   ├── src/                # TypeScript source
│   ├── public/             # Static assets
│   └── dist/               # Production build output
├── ios/                     # iOS/tvOS applications
├── storage/                 # Runtime data (gitignored)
│   ├── ebooks/             # Input EPUB files
│   ├── covers/             # Cover image cache
│   └── jobs/               # Job persistence and output
├── scripts/                 # Development and utility scripts
├── docs/                    # Additional documentation
└── tests/                   # Test suite
```

## Getting Started

### Docker Deployment (Production — Default)

Docker is the primary runtime environment. Both backend and frontend run as containers managed by Docker Compose on the Mac Mini, with Synology DSM reverse proxy handling TLS termination.

```
Internet → Synology DSM (:443 TLS) → Frontend Container (Nginx :5173)
                                            ↕ proxy /api/, /pipelines/, /storage/
                                      Backend Container (FastAPI :8000)
                                            ↕ volumes
                                      Host: storage/, config/, NAS mounts
```

1. **Start both services**:
   ```bash
   docker compose up -d              # start backend + frontend
   docker compose logs -f            # follow logs
   docker compose ps                 # check status
   ```

2. **Rebuild after code changes**:
   ```bash
   docker compose up -d --build      # rebuild images and restart
   # Or target a single service:
   docker compose up -d --build backend
   docker compose up -d --build frontend
   ```

3. **Verify**:
   ```bash
   curl http://localhost:8000/_health   # backend → {"status":"ok"}
   curl http://localhost:5173/          # frontend → HTML (React SPA)
   ```

4. **Makefile shortcuts**:
   ```bash
   make docker-build                 # build both images
   make docker-up                    # start services
   make docker-down                  # stop services
   make docker-logs                  # follow logs
   make docker-status                # health check summary
   ```

**Key files**:
- `docker-compose.yml` — orchestration, volumes, env vars
- `docker/backend/Dockerfile` — Python 3.10 + FFmpeg + espeak-ng
- `docker/frontend/Dockerfile` — Node build → Nginx 1.27-alpine serve
- `docker/frontend/nginx.conf` — SPA routing + API reverse proxy
- `.env.docker` — optional env var overrides (gitignored; see `.env.docker.example`)

**Volume mounts** (host → container):
| Host Path | Container Path | Mode | Purpose |
|---|---|---|---|
| `./storage` | `/app/storage` | rw | Jobs, ebooks, covers, library |
| `./config/users` | `/app/config/users` | rw | User credentials |
| `./conf/config.local.json` | `/app/conf/config.local.json` | ro | Local config overrides |
| `./conf/certs` | `/app/conf/certs` | ro | APNs keys |
| `./log` | `/app/log` | rw | Structured JSON logs |
| `/Volumes/Data/Download/Ebooks` | `/app/nas/ebooks` | ro | NAS ebook files |
| `/Volumes/Data/Download/DStation` | `/app/nas/videos` | rw | YouTube downloaded videos |
| `/Volumes/Data/Download/Subtitles` | `/app/nas/subtitles` | rw | Subtitle mirror directory |
| (tmpfs) | `/app/tmp` | 1G | Temp workspace (RAM-backed) |

**Docker-specific env vars** (set in `docker-compose.yml`):
| Variable | Value | Why |
|---|---|---|
| `EBOOK_API_STATIC_ROOT=""` | empty | Frontend is separate Nginx container |
| `EBOOK_TTS_BACKEND=gtts` | gtts | macOS `say` unavailable in Linux |
| `EBOOK_USE_RAMDISK=false` | false | Docker tmpfs replaces ramdisk |
| `JOB_STORAGE_DIR=/app/storage` | container path | Override host-relative default |
| `EBOOK_LIBRARY_ROOT=/app/storage/library` | container path | Override macOS default |
| `EBOOK_EBOOKS_DIR=/app/nas/ebooks` | container path | NAS mount |
| `YOUTUBE_VIDEO_ROOT=/app/nas/videos` | container path | NAS mount |
| `SUBTITLE_SOURCE_DIR=/app/nas/subtitles` | container path | NAS mount |

### Local Development (Bare-Metal)

For development with hot-reload, run backend and frontend directly on the host.

**Backend**:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip && pip install -e .
cp .env.example .env  # edit with API keys

# Any of these work:
uvicorn modules.webapi.application:create_app --factory --reload --host 0.0.0.0
ebook-tools-api --reload --log-level debug
python -m modules.webapi --reload --port 8000

curl http://127.0.0.1:8000/  # → {"status":"ok"}
```

**Frontend**:
```bash
cd web
npm install
cp .env.example .env.local  # edit with API URLs
npm run dev                  # → http://localhost:5173
```

### iOS/tvOS Setup

The iOS apps are in `ios/InteractiveReader/`. Use Xcode or command-line builds.

**Available schemes**:
- `InteractiveReader` - iOS app (iPhone/iPad)
- `InteractiveReaderTV` - tvOS app (Apple TV)
- `InteractiveReaderUITests` - iOS XCUITest E2E suite (run via `make test-e2e-iphone` or `make test-e2e-ipad`)
- `InteractiveReaderTVUITests` - tvOS XCUITest E2E suite (run via `make test-e2e-tvos`)

**Command-line builds** — always use the full Xcode path and explicit `-project` flag (xcodebuild fails without `-project` when run from the repo root):

```bash
XCBUILD=/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild
XCPROJ=ios/InteractiveReader/InteractiveReader.xcodeproj

# iOS build — use generic destination (never hardcode simulator names, they change with Xcode versions)
$XCBUILD -project $XCPROJ -scheme InteractiveReader \
  -destination 'generic/platform=iOS Simulator' \
  -quiet build 2>&1 | grep -E "^(error:|Build Failed)" | head -20

# tvOS build
$XCBUILD -project $XCPROJ -scheme InteractiveReaderTV \
  -destination 'generic/platform=tvOS Simulator' \
  -quiet build 2>&1 | grep -E "^(error:|Build Failed)" | head -20

# List available schemes
$XCBUILD -project $XCPROJ -list

# List available simulator destinations (useful for debugging)
$XCBUILD -project $XCPROJ -scheme InteractiveReader -showdestinations 2>&1 | grep "iOS Simulator"
```

**Build verification**: With `-quiet`, no output = success. Only errors and warnings are printed. Warnings about `@Sendable` or deprecations are safe to ignore — look for `error:` lines only.

**Adding New Swift Files to the Project**:

When creating new Swift files, they must be added to the Xcode project explicitly:

1. **Recommended: Use the `ios_add_swift_files.py` script**
   ```bash
   # Add files to both iOS and tvOS targets
   python scripts/ios_add_swift_files.py \
       Services/MusicKitCoordinator.swift \
       Features/Music/AppleMusicPickerView.swift

   # Preview changes without modifying the project
   python scripts/ios_add_swift_files.py --dry-run Services/NewFile.swift
   ```
   Paths are relative to `InteractiveReader/` source root. The script handles
   PBXFileReference, PBXBuildFile (both targets), PBXGroup membership, and
   PBXSourcesBuildPhase entries. Creates a `.backup` before writing.

2. **Alternative: Use Xcode UI**
   - Open `ios/InteractiveReader/InteractiveReader.xcodeproj` in Xcode
   - Right-click the target folder in the Project Navigator
   - Select "Add Files to InteractiveReader"
   - Ensure both targets (InteractiveReader, InteractiveReaderTV) are checked

**Warning**: Never manually edit `project.pbxproj` — the file format is complex and errors corrupt the project.

## Development Guidelines

### Code Organization

#### Backend Modules
- **`modules/audio/backends/`** - TTS backend implementations (gTTS, macOS)
- **`modules/images/`** - Sentence image generation with Draw Things
- **`modules/translation/`** - Translation service adapters
- **`modules/render/`** - Core audio rendering pipeline logic
- **`modules/webapi/`** - FastAPI routes, schemas, middleware
- **`modules/services/job_manager/`** - Job lifecycle and persistence

#### Frontend Structure
- **`web/src/components/`** - React components
- **`web/src/api/`** - API client with TypeScript types
- **`web/src/hooks/`** - Custom React hooks
- **`web/src/stores/`** - State management

### Configuration System

The project uses a layered configuration approach:

1. **Default config**: `conf/config.json` (version controlled)
2. **Local overrides**: `conf/config.local.json` (gitignored, per-machine)
3. **Environment variables**: Prefix `EBOOK_*` (highest priority)
4. **CLI flags**: Override all config sources

Example local config:
```json
{
  "thread_count": 8,
  "tts_backend": "macos_say",
  "tts_executable_path": "/usr/bin/say",
  "image_api_base_url": "http://192.168.1.9:7860",
  "image_concurrency": 4,
  "add_images": true
}
```

### Key Environment Variables

**Backend (runtime)**:
- `EBOOK_API_CORS_ORIGINS` - CORS allowed origins (space-separated)
- `EBOOK_API_STATIC_ROOT` - Path to built frontend assets (empty in Docker)
- `EBOOK_TTS_BACKEND` - TTS backend (`macos_say` | `gtts` | `piper`)
- `EBOOK_USE_RAMDISK` - Enable RAMDisk (`false` in Docker — use tmpfs)
- `JOB_STORAGE_DIR` - Base storage directory (`/app/storage` in Docker)
- `EBOOK_LIBRARY_ROOT` - Library sync root (`/app/storage/library` in Docker)
- `EBOOK_EBOOKS_DIR` - EPUB source directory (`/app/nas/ebooks` in Docker)
- `YOUTUBE_VIDEO_ROOT` - Downloaded video directory (`/app/nas/videos` in Docker)
- `SUBTITLE_SOURCE_DIR` - Subtitle mirror directory (`/app/nas/subtitles` in Docker)
- `EBOOK_STORAGE_BASE_URL` - Public storage URL (used in media metadata responses)
- `JOB_STORE_URL` - Redis URL for job persistence (optional)
- `EBOOK_IMAGE_API_BASE_URL` - Draw Things/SD API endpoint
- `EBOOK_IMAGE_CONCURRENCY` - Parallel image generation workers
- `OLLAMA_URL` - Ollama LLM endpoint
- `LLM_SOURCE` - LLM source (`local` | `cloud`)

**Frontend (build-time — baked into JS bundle)**:
- `VITE_API_BASE_URL` - Backend API URL as seen by browsers
- `VITE_STORAGE_BASE_URL` - Storage URL (must include `/jobs` segment)
- `VITE_DEV_HTTPS` - Enable HTTPS in dev server

**Frontend (runtime — Nginx envsubst)**:
- `BACKEND_HOST` - Backend hostname/IP for Nginx reverse proxy

### Important File Paths

#### Input Files
- EPUBs: `storage/ebooks/` (relative to repo root)
- Covers: `storage/covers/` (auto-generated from EPUBs)

#### Output Structure
Each job creates a directory under `storage/jobs/<job_id>/`:
```
storage/jobs/<job_id>/
├── metadata/
│   ├── job.json              # Job manifest
│   ├── chunk_0001.json       # Per-chunk metadata
│   └── content_index.json    # Chapter/section index
├── media/
│   ├── audio/                # Audio segments
│   └── images/               # Sentence illustrations
└── output/                   # Final deliverables
```

### Metadata Format

**Job Manifest** (`metadata/job.json`):
```json
{
  "job_id": "job-abc123",
  "input_language": "en",
  "target_language": "ar",
  "translation_provider": "google",
  "chunks": [
    {
      "chunk_id": "chunk_0001",
      "sentence_count": 42,
      "highlighting_policy": "backend_tokens"
    }
  ]
}
```

**Chunk Metadata** (`metadata/chunk_XXXX.json`):
```json
{
  "chunk_id": "chunk_0001",
  "sentences": [
    {
      "original": "Hello world.",
      "translation": "مرحبا بالعالم.",
      "image": "sentence_00001.png",
      "image_path": "media/images/range_01/sentence_00001.png"
    }
  ],
  "audioTracks": {
    "orig": { "duration": 2.5, "path": "media/audio/..." },
    "translation": { "duration": 2.8, "path": "media/audio/..." }
  },
  "timingTracks": {
    "orig": [
      { "word": "Hello", "start": 0.0, "end": 0.5 },
      { "word": "world", "start": 0.6, "end": 1.2 }
    ],
    "translation": [...]
  }
}
```

## Common Development Tasks

### Adding a New TTS Backend

1. Create backend class in `modules/audio/backends/`:
```python
from modules.audio.backends.base import BaseTTSBackend

class MyTTSBackend(BaseTTSBackend):
    name = "mytts"

    def synthesize(self, *, text, voice, speed, lang_code, output_path=None):
        # Return AudioSegment
        pass
```

2. Register in `modules/audio/backends/__init__.py`:
```python
from .mytts import MyTTSBackend
register_backend(MyTTSBackend.name, MyTTSBackend)
```

3. Configure in `config.local.json`:
```json
{
  "tts_backend": "mytts"
}
```

### Adding a New API Endpoint

1. Define schema in `modules/webapi/schemas/`:
```python
from pydantic import BaseModel

class MyRequest(BaseModel):
    param: str

class MyResponse(BaseModel):
    result: str
```

2. Create route in `modules/webapi/`:
```python
from fastapi import APIRouter, Depends
from .auth_middleware import get_current_user

router = APIRouter(prefix="/api/my", tags=["my"])

@router.post("/endpoint", response_model=MyResponse)
async def my_endpoint(
    request: MyRequest,
    user=Depends(get_current_user)
):
    return MyResponse(result=request.param)
```

3. Register router in `modules/webapi/application.py`:
```python
from .my_routes import router as my_router
app.include_router(my_router)
```

### Running Tests

**Always prefer targeted marker-based tests** over the full suite. Only run the
full suite (`pytest` / `make test`) when changes are wide-ranging (e.g. core
refactors, dependency upgrades, config changes that touch many modules).

```bash
# Install dev dependencies
pip install -e .[dev]

# ── Targeted runs (preferred) ──────────────────────────
pytest -m webapi              # FastAPI routes, middleware, auth endpoints
pytest -m services            # job manager, pipeline service, file locator
pytest -m pipeline            # core rendering pipeline, timeline
pytest -m audio               # TTS backends, voice selection, highlighting
pytest -m translation         # translation engine, batch processing, CJK
pytest -m metadata            # metadata enrichment, structured conversion
pytest -m cli                 # command-line interface, args parsing
pytest -m auth                # user management, sessions
pytest -m library             # library sync, indexer, repository
pytest -m render              # output writer, text pipeline, parallel dispatch
pytest -m media               # command runner, media backends
pytest -m config              # config manager, storage settings
pytest -m ramdisk             # RAMDisk lifecycle, guard, mount/unmount
pytest -m "not slow and not integration"  # fast feedback loop

# ── Full suite (only for wide-ranging changes) ─────────
pytest                        # all 800+ tests
pytest --cov=modules          # with coverage

# ── Specific file ──────────────────────────────────────
pytest tests/modules/webapi/test_job_media_routes.py -v

# ── Makefile shortcuts ─────────────────────────────────
make test-fast                # not slow, not integration
make test-webapi              # same as pytest -m webapi
make test-services            # same as pytest -m services
# (see Makefile for all targets)
```

### E2E Tests (on-demand only)

E2E tests are **not** part of the regular test suite. Only run them when explicitly
asked — they require a running API, credentials in `.env`, and external infrastructure.

**Architecture**: Shared JSON user journeys (`tests/e2e/journeys/*.json`) define
platform-agnostic test steps. Platform-specific runners interpret them:
- Python `WebJourneyRunner` (Playwright) for Web
- Swift `JourneyRunner` (XCUITest) for iPhone, iPad, Apple TV

```bash
# ── Web E2E (Playwright) ─────────────────────────────
# Requires: pip install -e .[e2e]  &&  playwright install
# Excluded from `pytest` by default (marker: e2e, addopts = "not e2e")
make test-e2e                 # headed browser, slow-mo 200ms (legacy)
make test-e2e-headless        # headless (legacy)
make test-e2e-web             # headed, named report
make test-e2e-web-headless    # headless, named report
# Report: test-results/web-e2e-report.md

# ── Apple E2E (XCUITest) ─────────────────────────────
# Requires: Xcode, Simulators, E2E_USERNAME/E2E_PASSWORD in .env
make test-e2e-iphone          # iPhone 16 Pro simulator
make test-e2e-ipad            # iPad Pro 13-inch (M4) simulator
make test-e2e-tvos            # Apple TV simulator
make test-e2e-ios             # alias → test-e2e-iphone
# Reports: test-results/{iphone,ipad,tvos}-e2e-report.md

# ── All 4 platforms in parallel ───────────────────────
make test-e2e-all             # Web + iPhone + iPad + tvOS (parallel)
```

All reports are Markdown with embedded screenshots, designed to render on GitHub.
Credentials: `E2E_USERNAME` / `E2E_PASSWORD` in `.env` (same user for all suites).
Adding a new journey JSON file auto-propagates to all 4 platforms.

### Building for Production

Production deployment uses Docker Compose (see [Docker Deployment](#docker-deployment-production--default) above).

```bash
# Build and deploy both containers
docker compose up -d --build

# Or build images only (without starting)
make docker-build

# Frontend build-time args (baked into JS bundle):
#   VITE_API_BASE_URL    — public backend URL as seen by browsers
#   VITE_STORAGE_BASE_URL — public storage URL (must include /jobs segment)
```

**Important**: `VITE_*` variables are embedded at build time. Changing them requires rebuilding the frontend image.

## Authentication & Authorization

### User Management

```bash
# Create admin user
ebook-tools user add admin --role admin

# Set password
ebook-tools user password admin

# Login (creates session token)
ebook-tools user login admin

# List users
ebook-tools user list

# Logout
ebook-tools user logout
```

### Production API Access

When testing against the production API:

- **Production API URL**: `https://api.langtools.fifosk.synology.me`
- **Get session token from CLI**:
  ```bash
  # Login using CLI (stores token in ~/.ebooktools_active_session)
  python3 -c "from modules.cli.main import main; main(['user', 'login', 'USERNAME'])"

  # Or get most recent token from session file:
  cat ~/.ebooktools_session.json | python3 -c "
  import json, sys
  data = json.load(sys.stdin)
  sessions = data.get('sessions', {})
  latest = max(sessions.items(), key=lambda x: x[1].get('created_at', ''))
  print('Token:', latest[0])
  "
  ```

- **Use token with curl**:
  ```bash
  TOKEN="your_session_token"
  curl -s "https://api.langtools.fifosk.synology.me/api/pipelines/jobs/{job_id}/media" \
    -H "Authorization: Bearer $TOKEN"
  ```

### API Authentication

1. **Login**:
```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"secret"}'
# Returns: {"token":"<jwt>", "user":{...}}
```

2. **Use token**:
```bash
curl -H "Authorization: Bearer <jwt>" \
  http://127.0.0.1:8000/pipelines/jobs
```

3. **SSE with token**:
```bash
# Query parameter for EventSource compatibility
curl -N "http://127.0.0.1:8000/pipelines/<job_id>/events?access_token=<jwt>"
```

### Roles

- `admin` - Full access including user management
- `editor` - Can create/manage jobs
- `media_producer` - Can request media generation
- Custom roles supported via configuration

## Performance Tuning

### Parallel Processing

```json
{
  "thread_count": 16,
  "queue_size": 64,
  "pipeline_mode": true,
  "image_concurrency": 4
}
```

### Audio Backend Selection

- **macOS `say`**: Highest quality, macOS only
- **gTTS**: Cross-platform, requires internet
- Set via `tts_backend` or `EBOOK_AUDIO_BACKEND`

### WhisperX Forced Alignment

WhisperX provides word-level timing when TTS backends don't emit character timings.
The adapter (`modules/align/backends/whisperx_adapter.py`) auto-detects GPU/MPS/CPU
and falls back gracefully on device errors.

**Pre-downloaded alignment models:**
- English (en), Arabic (ar), Hindi (hi), Hungarian (hu), Greek (el), Finnish (fi), Turkish (tr)

**Download additional models:**
```python
from whisperx.alignment import load_align_model
model, metadata = load_align_model("LANG_CODE", "cpu")  # e.g., "de", "fr", "es"
```

**Tests:** `pytest tests/modules/test_whisperx_alignment.py`

## Troubleshooting

### Docker Issues

**Container won't start / health check fails**:
```bash
docker compose logs backend --tail 50    # check backend startup errors
docker compose logs frontend --tail 20   # check Nginx errors
docker exec ebook-tools-backend python -c "import modules"  # verify Python packages
```

**NAS paths not accessible** (`"directory is not accessible"`):
- Frontend may be sending hardcoded macOS paths from localStorage — clear browser storage
- Verify mount: `docker exec ebook-tools-backend ls /app/nas/ebooks/`
- Frontend defaults are empty — backend env vars (`YOUTUBE_VIDEO_ROOT`, `SUBTITLE_SOURCE_DIR`, `EBOOK_EBOOKS_DIR`) provide the paths

**Code changes not taking effect**:
- Backend code requires image rebuild: `docker compose up -d --build backend`
- Frontend `VITE_*` changes require frontend rebuild: `docker compose up -d --build frontend`
- `docker compose up -d` (without `--build`) only recreates containers from existing images

**bcrypt "Invalid salt" on login**:
- Docker uses real bcrypt; local dev may use the SHA-256 shim at `bcrypt/__init__.py`
- `local_user_store.py` supports both formats — create user locally, it works in Docker

**tmpfs "Device or resource busy"**:
- Normal at startup — Docker tmpfs mount point can't be removed, only cleared
- `ramdisk_manager.py` handles this gracefully

### Common Issues

**API won't start**:
- Check Python version: `python --version` (need 3.10+)
- Verify dependencies: `pip list`
- Check port availability: `lsof -i :8000`

**Frontend can't reach API**:
- Docker: verify `BACKEND_HOST` env var and Nginx proxy config
- Local dev: verify `VITE_API_BASE_URL` in `web/.env.local`
- Check CORS settings: `EBOOK_API_CORS_ORIGINS`

**Audio generation fails**:
- Verify TTS backend: `ffmpeg -version` or `say -v '?'`
- Docker: only `gtts` and `piper` work (no macOS `say`)
- Check permissions on output directories

**Image generation not working**:
- Verify Draw Things is running: `curl http://<ip>:7860/sdapi/v1/txt2img`
- Docker: use `http://host.docker.internal:7860` to reach host services
- Increase `image_api_timeout_seconds` for slow models

### Debug Tools

**Docker**:
```bash
docker compose logs -f                   # follow all logs
docker compose logs backend --tail 100   # recent backend logs
docker exec ebook-tools-backend ls /app/storage/  # verify mounts
docker exec -it ebook-tools-backend bash # shell into container
```

**CLI**:
```bash
ebook-tools run --log-level debug
```

**Browser Console**:
```javascript
// Enable word highlighting debug overlay
window.__HL_DEBUG__ = { enabled: true };
```

**Validation**:
```bash
python scripts/validate_word_timing.py <job_id>
```

## API Reference

### Core Endpoints

**Job Management**:
- `GET /pipelines/jobs` - List all jobs
- `POST /pipelines` - Create new job
- `GET /pipelines/jobs/{job_id}` - Get job status
- `GET /pipelines/{job_id}/events` - SSE progress stream
- `POST /pipelines/jobs/{job_id}/pause` - Pause job
- `POST /pipelines/jobs/{job_id}/resume` - Resume job
- `POST /pipelines/jobs/{job_id}/cancel` - Cancel job
- `POST /pipelines/jobs/{job_id}/delete` - Delete job

**Media**:
- `GET /api/jobs/{job_id}/timing` - Get word timing data
- `GET /api/pipelines/jobs/{job_id}/media` - Get media metadata
- `POST /api/media/generate` - Request media generation

**Images**:
- `GET /api/pipelines/jobs/{job_id}/media/images/sentences/{n}` - Get image
- `POST /api/pipelines/jobs/{job_id}/media/images/sentences/{n}/regenerate` - Regenerate

**Auth**:
- `POST /auth/login` - Login
- `POST /auth/logout` - Logout
- `GET /auth/session` - Get current session
- `POST /auth/password` - Change password

**Admin**:
- `GET /admin/users` - List users
- `POST /admin/users` - Create user
- `POST /admin/users/{username}/suspend` - Suspend user
- `POST /admin/users/{username}/password` - Reset password

## Additional Resources

- **Architecture**: `docs/architecture.md`
- **Sentence Images**: `docs/sentence_images.md`
- **Word Highlighting**: `docs/interactive_reader_metadata.md`
- **Frontend Sync**: `docs/frontend-sync.md`
- **User Management**: `docs/user-management.md`

## Git Workflow

This is a git worktree:
- **Worktree path**: `/Users/fifo/.claude-worktrees/ebook-tools/compassionate-maxwell`
- **Main repo**: `/Users/fifo/Projects/ebook-tools`
- **Current branch**: `compassionate-maxwell`
- **Main branch**: `main` (use for PRs)

When committing:
```bash
git add <files>
git commit -m "Description

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

## Tips for Claude

1. **Always read files before editing** - Never propose changes to code you haven't seen
2. **Use specialized tools** - Use Read/Edit/Write instead of bash cat/sed/echo
3. **Check configuration layers** - Remember: defaults → local → env vars → CLI flags
4. **Test incrementally** - Start API, test endpoint, then integrate frontend
5. **Respect patterns** - Follow existing naming conventions and module structure
6. **Check both config locations** - `conf/` for defaults, `config/` for runtime
7. **Watch for gitignored files** - `storage/`, `.env.local`, `config.local.json`
8. **Metadata is chunked** - Modern jobs use `chunk_XXXX.json`, not single files
9. **Use MetadataLoader** - Abstracts chunked vs legacy metadata format
10. **HTTPS requires certs** - Both backend and frontend support TLS with cert files
11. **Use targeted tests** - Run `pytest -m <marker>` for the domain you changed (e.g. `pytest -m webapi`). Only run the full 800+ test suite for wide-ranging changes. See `pyproject.toml` for all 15 markers and `Makefile` for shortcuts.

## Frontend State Management Architecture

The React frontend uses **Zustand** for state management with a clean separation of concerns:

### State Stores

1. **jobsStore** (`web/src/stores/jobsStore.ts`)
   - Manages all job-related state (pipeline jobs, status, progress events)
   - Map-based storage for O(1) lookups
   - Separate loading state tracking (isReloading, isMutating)
   - Request deduplication for API calls
   - Atomic updates prevent race conditions
   - Computed selectors: `getSortedJobs()`, `getJobsByType()`

2. **uiStore** (`web/src/stores/uiStore.ts`)
   - Manages all UI state (selected view, sidebar, player, modals)
   - Persists user preferences to localStorage
   - No business logic - pure UI state

### Selective Subscriptions

Use granular hooks to prevent unnecessary re-renders:

```typescript
// Subscribe to specific job (only re-renders when this job changes)
const job = useJobData(jobId);

// Subscribe to loading states only
const { isReloading, isMutating } = useJobLoading(jobId);

// Subscribe to job IDs list only
const jobIds = useJobIds();

// Subscribe to active job ID only
const activeJobId = useActiveJobId();
```

### SSE with Retry Logic

The `useJobEventsWithRetry` hook provides resilient SSE connections:
- Exponential backoff: 2s, 4s, 8s, 16s, 32s
- Max 5 retries (configurable)
- Automatic retry count reset on successful connection
- Graceful degradation on persistent failures

### Error Boundaries

Components are wrapped with `<ErrorBoundary>` for graceful error recovery:
- Auto-reset when navigating (via `resetKeys` prop)
- Custom fallback UI
- Error logging callback
- Prevents entire app crashes

### Performance Optimizations

- **Shallow comparison** - Custom equality functions prevent unnecessary updates
- **Computed selectors** - Memoized derived state in the store
- **Selective subscriptions** - Components subscribe to minimal state slices
- **Request deduplication** - Concurrent API calls reuse single promise
- **Map-based storage** - O(1) performance for job lookups

### Migration Notes

If you encounter old patterns:
- `useState` for jobs → Use `useJobsStore()`
- `useState` for UI state → Use `useUIStore()`
- `usePipelineEvents` → Use `useJobEventsWithRetry()`
- Direct API calls → Use store actions (`performJobAction`, `refreshJobs`)
