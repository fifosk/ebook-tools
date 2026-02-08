# Developer Guide

This document is the primary reference for developers working on **ebook-tools**. It covers local setup, configuration, API usage, CLI commands, frontend architecture, and performance tuning.

For high-level architecture diagrams see [architecture.md](architecture.md). For domain-specific deep dives see [sentence_images.md](sentence_images.md), [interactive_reader_metadata.md](interactive_reader_metadata.md), and [frontend-sync.md](frontend-sync.md).

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.10+ | Regularly verified against 3.11 |
| Node.js | 18+ | For the React/Vite frontend |
| FFmpeg | any recent | Required by pydub and the audio pipeline |
| Xcode | latest | iOS/tvOS builds only |
| PostgreSQL | 16+ | Required for Docker deployment; optional for local dev |
| Ollama | optional | Local LLM translation and prompt generation |
| Draw Things | optional | Sentence image generation (Stable Diffusion API) |

---

## Backend Setup

### Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e .                   # runtime dependencies
pip install -e .[dev]              # adds pytest, linting, coverage
```

The editable install wires up the `ebook-tools-api` console script and pulls in the FastAPI/uvicorn runtime declared in `pyproject.toml`.

### Launch the FastAPI server

With the virtual environment activated, start the backend with any of the following:

```bash
# Standard uvicorn invocation
uvicorn modules.webapi.application:create_app --factory --reload --host 0.0.0.0

# Python module entry point (resolves to the same uvicorn call)
python -m modules.webapi --reload --port 8000

# Installed console script shortcut
ebook-tools-api --reload --log-level debug

# Shell helper (wraps the module runner and adds a --port flag)
./scripts/run-webapi.sh --port 9000
```

Use `--reload` while iterating locally to enable hot-reloading. Confirm the server is reachable:

```bash
curl http://127.0.0.1:8000/
# {"status":"ok"}
```

When static hosting is disabled the JSON healthcheck remains at `/`. If the frontend bundle is served, the healthcheck is always reachable at `/_health`.

### HTTPS setup

Uvicorn can terminate TLS directly. Create a development certificate (or use `mkcert`) and pass the files:

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

All entry points (`ebook-tools-api`, `python -m modules.webapi`, `./scripts/run-webapi.sh`) accept `--ssl-certfile`, `--ssl-keyfile`, and `--ssl-keyfile-password`. Production deployments should use a trusted CA or a reverse proxy (Caddy, nginx) that manages TLS termination.

When using `./scripts/run-webapi.sh`, you can opt-in via environment variables:

```bash
EBOOK_API_ENABLE_HTTPS=1 \
EBOOK_API_SSL_CERTFILE=conf/certs/dev.crt \
EBOOK_API_SSL_KEYFILE=conf/certs/dev.key \
./scripts/run-webapi.sh --reload
```

If `EBOOK_API_SSL_CERTFILE`/`EBOOK_API_SSL_KEYFILE` are omitted the script falls back to `conf/certs/dev.{crt,key}` when present. Provide `EBOOK_API_SSL_KEYFILE_PASSWORD` when the key is encrypted.

---

## Frontend Setup

The React/Vite client lives under `web/`.

### Install and run

```bash
cd web
npm install
```

| Command | Description |
|---------|-------------|
| `npm run dev` | Vite dev server on port 5173. Pass `-- --host 0.0.0.0` to expose on LAN. |
| `npm run build` | Production bundle in `web/dist/`. Point `EBOOK_API_STATIC_ROOT` here to serve from FastAPI. |
| `npm run preview` | Serve the production build locally for smoke testing. |

### Configure API endpoints

Duplicate `web/.env.example` to `web/.env` or `web/.env.local`:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_STORAGE_BASE_URL=http://127.0.0.1:8000/storage
```

`VITE_API_BASE_URL` controls where fetch requests are sent. `VITE_STORAGE_BASE_URL` constructs download links to generated artifacts. Environment-specific files like `web/.env.production` are picked up via `npm run build -- --mode production`.

**Important**: `VITE_*` variables are embedded at build time. Changing them requires rebuilding the frontend.

### HTTPS in Vite dev server

Add the following to `web/.env.local` (paths can be absolute or relative to `web/`):

```bash
VITE_DEV_HTTPS=true
VITE_DEV_HTTPS_CERT=../conf/certs/dev.crt
VITE_DEV_HTTPS_KEY=../conf/certs/dev.key
# Optional: provide a CA bundle when mkcert or a corporate CA issues the cert
VITE_DEV_HTTPS_CA=../conf/certs/rootCA.pem
```

Setting `VITE_DEV_HTTPS=true` (or `1`, `yes`, `on`) forces HTTPS. Omitting it defaults to autoloading whenever both cert and key are set. Use `false`/`0` to disable. Once enabled, update `VITE_API_BASE_URL` / `VITE_STORAGE_BASE_URL` to use `https://`.

---

## iOS/tvOS Development

The iOS apps live in `ios/InteractiveReader/`. Use Xcode or command-line builds.

### Schemes

| Scheme | Platform | Purpose |
|--------|----------|---------|
| `InteractiveReader` | iOS (iPhone/iPad) | Main reader app |
| `InteractiveReaderTV` | tvOS (Apple TV) | TV reader app |
| `InteractiveReaderUITests` | iOS | XCUITest E2E suite |
| `InteractiveReaderTVUITests` | tvOS | XCUITest E2E suite |

### Command-line builds

Always use the full Xcode path and explicit `-project` flag (`xcodebuild` fails without `-project` when run from the repo root):

```bash
XCBUILD=/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild
XCPROJ=ios/InteractiveReader/InteractiveReader.xcodeproj

# iOS build -- use generic destination (never hardcode simulator names)
$XCBUILD -project $XCPROJ -scheme InteractiveReader \
  -destination 'generic/platform=iOS Simulator' \
  -quiet build 2>&1 | grep -E "^(error:|Build Failed)" | head -20

# tvOS build
$XCBUILD -project $XCPROJ -scheme InteractiveReaderTV \
  -destination 'generic/platform=tvOS Simulator' \
  -quiet build 2>&1 | grep -E "^(error:|Build Failed)" | head -20

# List available schemes
$XCBUILD -project $XCPROJ -list

# List available simulator destinations
$XCBUILD -project $XCPROJ -scheme InteractiveReader -showdestinations 2>&1 | grep "iOS Simulator"
```

**Build verification**: With `-quiet`, no output means success. Only errors and warnings are printed. Warnings about `@Sendable` or deprecations are safe to ignore -- look for `error:` lines only.

### Adding new Swift files

When creating new Swift files, they must be added to the Xcode project explicitly.

**Recommended: Use the helper script**

```bash
# Add files to both iOS and tvOS targets
python scripts/ios_add_swift_files.py \
    Services/MusicKitCoordinator.swift \
    Features/Music/AppleMusicPickerView.swift

# Preview changes without modifying the project
python scripts/ios_add_swift_files.py --dry-run Services/NewFile.swift
```

Paths are relative to `InteractiveReader/` source root. The script handles PBXFileReference, PBXBuildFile (both targets), PBXGroup membership, and PBXSourcesBuildPhase entries. It creates a `.backup` before writing.

**Alternative: Use Xcode UI** -- right-click the target folder, select "Add Files to InteractiveReader", ensure both targets are checked.

**Warning**: Never manually edit `project.pbxproj` -- the file format is complex and errors corrupt the project.

---

## Configuration System

The project uses a layered configuration approach where each layer overrides the previous:

1. **Default config**: `conf/config.json` (version controlled)
2. **Local overrides**: `conf/config.local.json` (gitignored, per-machine)
3. **Environment variables**: Prefix `EBOOK_*` (higher priority)
4. **CLI flags**: Override all config sources (highest priority)

> `conf/config.local.json` is ignored by Git, so it is safe to add API keys, alternate model names, or other machine-specific values there.

### Directory settings

| Config key | CLI flag | Env var | Default | Description |
|------------|----------|---------|---------|-------------|
| `ebooks_dir` | `--ebooks-dir` | `EBOOKS_DIR` | `storage/ebooks/` | Source EPUB files and cover images |
| `working_dir` | `--working-dir` | `EBOOK_WORKING_DIR` | `output/` | Root for generated artifacts |
| `output_dir` | `--output-dir` | `EBOOK_OUTPUT_DIR` | `output/ebook/` | Generated HTML/PDF/audio output |
| `tmp_dir` | `--tmp-dir` | `EBOOK_TMP_DIR` | `tmp/` | Scratch space for intermediate assets |

The `storage/ebooks/` and `storage/covers/` directories are gitignored. Create them manually if they do not exist.

### External tool settings

| Config key | CLI flag | Env var | Default | Description |
|------------|----------|---------|---------|-------------|
| `ffmpeg_path` | `--ffmpeg-path` | `FFMPEG_PATH` | `ffmpeg` | Path to the FFmpeg binary |
| `audio_bitrate_kbps` | -- | `EBOOK_AUDIO_BITRATE_KBPS` | `320` | Target MP3 bitrate (kbps) |
| `llm_source` | `--llm-source` | `LLM_SOURCE` | `local` | LLM adapter (`local` or `cloud`) |
| `ollama_url` | `--ollama-url` | `OLLAMA_URL` | `http://192.168.1.9:11434/api/chat` | Primary Ollama endpoint |
| `ollama_local_url` | -- | `OLLAMA_LOCAL_URL` | per config | Explicit local Ollama URL |
| `ollama_cloud_url` | -- | `OLLAMA_CLOUD_URL` | per config | Cloud Ollama endpoint |
| `ollama_model` | -- | -- | `kimi-k2:1t-cloud` | Model identifier for translation |
| `translation_fallback_model` | -- | `EBOOK_TRANSLATION_FALLBACK_MODEL` | `gemma3:12b` | Fallback LLM model when primary fails |
| `translation_llm_timeout_seconds` | -- | `EBOOK_TRANSLATION_LLM_TIMEOUT_SECONDS` | `60` | Per-sentence timeout before fallback |
| `tts_fallback_voice` | -- | `EBOOK_TTS_FALLBACK_VOICE` | `macOS-auto` | Voice used when gTTS fails |
| `image_api_base_url` | -- | `EBOOK_IMAGE_API_BASE_URL` | `http://192.168.1.9:7860` | Draw Things / Stable Diffusion URL |
| `image_api_timeout_seconds` | -- | `EBOOK_IMAGE_API_TIMEOUT_SECONDS` | `180` | Timeout for txt2img requests |
| `image_concurrency` | -- | `EBOOK_IMAGE_CONCURRENCY` | `2` | Parallel image generation workers |
| `image_width`, `image_height` | -- | -- | per config | Diffusion image dimensions |
| `image_steps`, `image_cfg_scale`, `image_sampler_name` | -- | -- | per config | Diffusion generation parameters |
| `image_prompt_context_sentences` | -- | -- | per config | Previous sentences fed to LLM for scene continuity |

When both LLM sources are configured, the runtime automatically retries the alternate adapter if the preferred endpoint is unavailable or rate-limited.

### TTS settings

| Config key | Env var | Default | Description |
|------------|---------|---------|-------------|
| `tts_backend` | `EBOOK_TTS_BACKEND` / `EBOOK_AUDIO_BACKEND` | `macos_say` | TTS engine (`macos_say`, `gtts`, `piper`). `auto` picks `macos_say` on macOS, `gtts` elsewhere. |
| `tts_executable_path` | `EBOOK_AUDIO_EXECUTABLE` | `null` | Override for the TTS backend binary |
| `macos_reading_speed` | -- | `100` | Words per minute for macOS TTS |
| `selected_voice` | -- | `macOS-auto` | Voice identifier (gTTS or macOS voice name) |

### Pipeline settings

| Config key | Env var | Default | Description |
|------------|---------|---------|-------------|
| `thread_count` | `EBOOK_THREAD_COUNT` | `5` | Worker thread pool size |
| `queue_size` | `EBOOK_QUEUE_SIZE` | `20` | Translation/media queue depth |
| `pipeline_mode` | `EBOOK_PIPELINE_MODE` | `true` | Enable pipelined processing |
| `use_ramdisk` | `EBOOK_USE_RAMDISK` | `true` | RAM-backed tmp directory (`false` in Docker) |
| `forced_alignment_enabled` | -- | `false` | Enable heuristic forced alignment |
| `forced_alignment_smoothing` | -- | `monotonic_cubic` | Smoothing method (`monotonic_cubic` or `linear`) |
| `char_weighted_highlighting_default` | `EBOOK_CHAR_WEIGHTED_HIGHLIGHTING_DEFAULT` | `false` | Distribute timings by character count |
| `char_weighted_punctuation_boost` | `EBOOK_CHAR_WEIGHTED_PUNCTUATION_BOOST` | `false` | Punctuation-aware padding |

### Example local config

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

### Using the settings

- **Interactive mode** (`ebook-tools interactive` or `python main.py -i`) exposes each knob in the menu and persists new defaults back into `conf/config.local.json`.
- **Non-interactive mode**: CLI flags or environment variables take precedence over the JSON values. Relative paths are resolved against the working copy and directories are created as needed.

---

## Environment Variables

### Backend (runtime)

Copy `.env.example` to `.env` at the project root. The loader reads files in order: `.env` -> `.env.<name>` (via `EBOOK_ENV=<name>`) -> `.env.local`. Values exported in the shell take precedence.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | -- | PostgreSQL connection string (e.g., `postgresql://user:pass@host/db`). When set, all 6 storage domains use PG instead of JSON/SQLite. |
| `EBOOK_API_CORS_ORIGINS` | localhost + Vite dev URLs | Comma/space-separated CORS origins. `*` allows all; empty disables. |
| `EBOOK_API_STATIC_ROOT` | `web/dist/` | Built SPA assets path. Empty string = API-only mode. |
| `EBOOK_API_STATIC_INDEX` | `index.html` | Filename for client-side route fallback |
| `EBOOK_API_STATIC_MOUNT` | `/` | URL prefix for static file serving |
| `EBOOK_TTS_BACKEND` | auto | TTS backend (`macos_say`, `gtts`, `piper`) |
| `EBOOK_AUDIO_BACKEND` | auto | Alias for `EBOOK_TTS_BACKEND` |
| `EBOOK_AUDIO_EXECUTABLE` | per config | Absolute path to the TTS backend binary |
| `EBOOK_USE_RAMDISK` | `true` | RAM-backed tmp directory (`false` in Docker) |
| `JOB_STORAGE_DIR` | `storage` | Base directory for job persistence |
| `JOB_STORE_URL` | -- | Redis URL for job metadata (omit for filesystem) |
| `EBOOK_STORAGE_BASE_URL` | API origin + `/storage` | Public base URL for download links |
| `EBOOK_LIBRARY_ROOT` | per platform | Library sync root directory |
| `EBOOK_EBOOKS_DIR` | `storage/ebooks` | EPUB source directory |
| `YOUTUBE_VIDEO_ROOT` | -- | Downloaded video directory |
| `SUBTITLE_SOURCE_DIR` | -- | Subtitle mirror directory |
| `EBOOK_IMAGE_API_BASE_URL` | per config | Draw Things / SD endpoint URL |
| `EBOOK_IMAGE_API_TIMEOUT_SECONDS` | `180` | Timeout for txt2img requests |
| `EBOOK_IMAGE_CONCURRENCY` | `2` | Parallel image generation workers |
| `OLLAMA_URL` | per config | Ollama LLM endpoint |
| `LLM_SOURCE` | `local` | LLM source (`local` or `cloud`) |
| `EBOOK_THREAD_COUNT` | `5` | Global thread pool size |
| `EBOOK_PIPELINE_MODE` | `true` | Enable pipelined processing |
| `EBOOK_QUEUE_SIZE` | `20` | Translation/media queue depth |
| `EBOOK_HIGHLIGHT_POLICY` | -- | Highlighting policy (`forced`, `prefer_char_weighted`, `allow_uniform`) |
| `EBOOK_AUTH_GOOGLE_CLIENT_IDS` | -- | Google OAuth client IDs (comma-separated) |
| `EBOOK_AUTH_APPLE_CLIENT_IDS` | -- | Apple OAuth client IDs (comma-separated) |
| `EBOOK_PIPER_MODELS_PATH` | default cache | External storage path for Piper voice models |
| `EBOOK_WHISPERX_MODELS_PATH` | default cache | External storage path for WhisperX models |
| `EBOOK_HF_CACHE_PATH` | default cache | External storage path for HuggingFace cache |

### Frontend (build-time -- baked into JS bundle)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | Backend API URL as seen by browsers |
| `VITE_STORAGE_BASE_URL` | `http://127.0.0.1:8000/storage` | Storage URL (must include `/jobs` segment for Docker) |
| `VITE_DEV_HTTPS` | -- | Enable HTTPS in Vite dev server |
| `VITE_GOOGLE_CLIENT_ID` | -- | Google OAuth client ID for web sign-in |
| `VITE_APPLE_CLIENT_ID` | -- | Apple OAuth client ID for web sign-in |
| `VITE_APPLE_REDIRECT_URI` | -- | Apple Sign In redirect URI override |

### Frontend (runtime -- Nginx envsubst)

| Variable | Description |
|----------|-------------|
| `BACKEND_HOST` | Backend hostname/IP for Nginx reverse proxy |

---

## API Reference

All endpoints require authentication unless noted otherwise. Obtain a bearer token via `/api/auth/login` and attach it as `Authorization: Bearer <token>`.

### Authentication

**Login:**

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"secret"}'
# {"token":"<session>","user":{"username":"admin","role":"admin","last_login":"..."}}

export EBOOKTOOLS_SESSION_TOKEN="<session>"
```

**Session management:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Obtain bearer token |
| `GET` | `/api/auth/session` | Restore persisted session |
| `POST` | `/api/auth/logout` | Revoke token |
| `POST` | `/api/auth/password` | Rotate credentials |

**SSE with token**: Browser `EventSource` does not support headers. Pass the token as a query parameter:

```bash
curl -N "http://127.0.0.1:8000/api/pipelines/<job_id>/events?access_token=$EBOOKTOOLS_SESSION_TOKEN"
```

### Pipeline Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/pipelines/jobs` | List all persisted jobs |
| `POST` | `/api/pipelines` | Create new pipeline job |
| `GET` | `/api/pipelines/jobs/{job_id}` | Get job status |
| `GET` | `/api/pipelines/{job_id}/events` | SSE progress stream |
| `POST` | `/api/pipelines/jobs/{job_id}/pause` | Pause job |
| `POST` | `/api/pipelines/jobs/{job_id}/resume` | Resume job |
| `POST` | `/api/pipelines/jobs/{job_id}/cancel` | Cancel job |
| `POST` | `/api/pipelines/jobs/{job_id}/delete` | Delete job |

**Example: job lifecycle**

```bash
# List all jobs
curl -H "Authorization: Bearer $EBOOKTOOLS_SESSION_TOKEN" \
  http://127.0.0.1:8000/api/pipelines/jobs

# Pause a running job
curl -X POST -H "Authorization: Bearer $EBOOKTOOLS_SESSION_TOKEN" \
  http://127.0.0.1:8000/api/pipelines/jobs/<job_id>/pause

# Resume
curl -X POST -H "Authorization: Bearer $EBOOKTOOLS_SESSION_TOKEN" \
  http://127.0.0.1:8000/api/pipelines/jobs/<job_id>/resume

# Cancel
curl -X POST -H "Authorization: Bearer $EBOOKTOOLS_SESSION_TOKEN" \
  http://127.0.0.1:8000/api/pipelines/jobs/<job_id>/cancel

# Delete
curl -X POST -H "Authorization: Bearer $EBOOKTOOLS_SESSION_TOKEN" \
  http://127.0.0.1:8000/api/pipelines/jobs/<job_id>/delete
```

**Pipeline job persistence**: The API keeps a JSON snapshot of each job in `JOB_STORAGE_DIR` when Redis is not configured. Each job gets its own directory containing `metadata/job.json`. Restarting the application automatically reloads JSON files, pausing in-flight work and allowing it to be resumed, cancelled, or cleaned up via the endpoints above. Note: pipeline jobs remain on the filesystem regardless of `DATABASE_URL` -- only users, sessions, library, config, bookmarks, and resume use PostgreSQL.

```bash
# Inspect jobs on disk
ls storage/*/metadata/job.json
# Remove a single job directory
rm -rf storage/<job_id>
```

### Media

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/jobs/{job_id}/timing` | Word timing data (best-effort for legacy jobs) |
| `GET` | `/api/pipelines/jobs/{job_id}/media` | Media metadata |
| `POST` | `/api/media/generate` | Request on-demand media generation |
| `GET` | `/api/pipelines/jobs/{job_id}/media/images/sentences/{n}` | Get sentence image |
| `POST` | `/api/pipelines/jobs/{job_id}/media/images/sentences/{n}/regenerate` | Regenerate sentence image |

**Media generation** requires `admin` or `media_producer` role:

```bash
curl -X POST http://127.0.0.1:8000/api/media/generate \
  -H "Authorization: Bearer $EBOOKTOOLS_SESSION_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
        "job_id": "job-123",
        "media_type": "audio",
        "parameters": {"voice": "demo"},
        "notes": "Regenerate narration with updated script"
      }'
# {"request_id":"...","status":"accepted","job_id":"job-123","media_type":"audio","requested_by":"admin"}
```

### Admin

All admin routes require a bearer token belonging to a user with the `admin` role.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/admin/users` | List accounts with roles/status metadata |
| `POST` | `/api/admin/users` | Create a new user |
| `POST` | `/api/admin/users/{username}/suspend` | Suspend an account |
| `POST` | `/api/admin/users/{username}/password` | Reset password |

```bash
# List accounts
curl -H "Authorization: Bearer $EBOOKTOOLS_SESSION_TOKEN" \
  http://127.0.0.1:8000/api/admin/users

# Create an editor
curl -X POST http://127.0.0.1:8000/api/admin/users \
  -H "Authorization: Bearer $EBOOKTOOLS_SESSION_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"username":"frank","password":"change-me","roles":["editor"],"email":"frank@example.com"}'

# Suspend an account
curl -X POST -H "Authorization: Bearer $EBOOKTOOLS_SESSION_TOKEN" \
  http://127.0.0.1:8000/api/admin/users/frank/suspend

# Reset password
curl -X POST -H "Authorization: Bearer $EBOOKTOOLS_SESSION_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"password":"new-secret"}' \
  http://127.0.0.1:8000/api/admin/users/frank/password
```

Responses include normalised status flags (`status`, `is_active`, `is_suspended`) and audit metadata (`created_at`, `updated_at`, `last_login`).

### Roles

| Role | Permissions |
|------|-------------|
| `admin` | Full access including user management |
| `editor` | Create and manage pipeline jobs |
| `media_producer` | Request media generation |
| Custom | Supported via configuration |

---

## CLI Reference

The refactored CLI lives under the `ebook-tools` console script with explicit sub-commands.

### Pipeline execution

```bash
# Run the pipeline non-interactively
ebook-tools run --config conf/config.local.json

# Launch the interactive configuration menu with overrides
ebook-tools interactive --config conf/config.local.json --ebooks-dir ~/Books --llm-source cloud

# Direct pipeline run with arguments
python -m modules.cli.main run --thread-count 8 path/to/book.epub

# Legacy invocation (still supported)
python modules/ebook_tools.py <input.epub> "English" "Arabic" 10
python main.py --tts-backend macos --selected-voice "Samantha" \
  --tts-executable /usr/bin/say --macos-reading-speed 180
```

Both sub-commands honour overrides (`--ebooks-dir`, `--output-dir`, etc.) and interactive updates save back into `conf/config.local.json` when possible.

### User management

```bash
# Create an admin user
ebook-tools user add admin --role admin --role editor

# Set / rotate password (interactive prompt if --password omitted)
ebook-tools user password admin

# Login (stores token in ~/.ebooktools_active_session)
ebook-tools user login admin

# List registered accounts and their roles
ebook-tools user list

# Logout (revokes token, clears active session file)
ebook-tools user logout
```

Credentials are stored in `config/users/users.json` by default. Bootstrap new environments by copying `config/users/users.sample.json` and immediately rotating the placeholder passwords. Export `EBOOKTOOLS_SESSION_TOKEN` to override automatic token discovery when scripting.

### CLI progress monitoring

When running the legacy CLI (`python main.py` or `ebook-tools`) the progress log includes live system statistics (CPU utilisation, resident memory, I/O rates) sampled roughly every ten seconds via `psutil`.

---

## Audio Backend Architecture

### Registry pattern

Text-to-speech is routed through the `modules.audio.backends` registry. Each backend implements the `BaseTTSBackend` contract and is discovered via `get_tts_backend()`.

Shipped backends:

| Backend | Config value | Platform | Notes |
|---------|-------------|----------|-------|
| macOS `say` | `macos_say` | macOS only | Highest quality local voices |
| Google TTS | `gtts` | Cross-platform | Requires internet |
| Piper | `piper` | Cross-platform | Offline neural TTS |

When `tts_backend` is omitted or set to `auto`, the resolver picks `macos_say` on Darwin hosts and `gtts` everywhere else.

### Adding a custom backend

```python
from modules.audio.backends import BaseTTSBackend, register_backend


class MyCloudBackend(BaseTTSBackend):
    name = "mycloud"

    def synthesize(self, *, text, voice, speed, lang_code, output_path=None):
        ...  # call your API and return an AudioSegment


register_backend(MyCloudBackend.name, MyCloudBackend)
```

Set `tts_backend` to `mycloud` in `conf/config.local.json` and optionally expose custom keyword arguments via your own config loader.

### Forced alignment

Word-level timelines benefit from light smoothing. Enable in `conf/config.local.json`:

```json
{
  "forced_alignment_enabled": true,
  "forced_alignment_smoothing": "monotonic_cubic"
}
```

The WhisperX adapter (`modules/align/backends/whisperx_adapter.py`) auto-detects GPU/MPS/CPU and falls back gracefully on device errors.

**Pre-downloaded alignment models**: English (en), Arabic (ar), Hindi (hi), Hungarian (hu), Greek (el), Finnish (fi), Turkish (tr).

**Download additional models:**

```python
from whisperx.alignment import load_align_model
model, metadata = load_align_model("LANG_CODE", "cpu")  # e.g., "de", "fr", "es"
```

### Voice selection

- `selected_voice` -- Voice identifier (gTTS language code or macOS voice name like `"Samantha"`).
- `macos_reading_speed` -- Words per minute for macOS TTS (default: 100).
- `tts_fallback_voice` -- Voice used when gTTS fails (default: `macOS-auto`).

### Highlighting policy

Highlight provenance is controlled via two layers:

- `EBOOK_HIGHLIGHT_POLICY` enforces whether a job may fall back to inferred timings. Values: `forced` (fail without real tokens), `prefer_char_weighted` (allow heuristics), `allow_uniform` (tolerate evenly spaced tokens).
- `char_weighted_highlighting_default` and `char_weighted_punctuation_boost` toggle the heuristic that distributes durations based on character counts.

Each chunk stores a `highlighting_policy` summary alongside `timingTracks`.

---

## Running the Full Stack

1. **Start the backend.** Activate the virtual environment and launch uvicorn:
   ```bash
   python -m modules.webapi --reload
   ```
   Verify: `curl http://127.0.0.1:8000/` returns `{"status":"ok"}`.

2. **Start the frontend.** In a separate terminal:
   ```bash
   cd web && npm run dev
   ```
   The app is available at `http://127.0.0.1:5173/` and proxies API calls to `VITE_API_BASE_URL`.

3. **Sign in.** Use the login form or call `POST /api/auth/login` from a terminal. The SPA persists the token in `localStorage` and forwards it automatically.

4. **Submit a pipeline job.** Through the UI or directly:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/pipelines \
     -H "Authorization: Bearer $EBOOKTOOLS_SESSION_TOKEN" \
     -H 'Content-Type: application/json' \
     -d @payload.json
   ```

5. **Watch progress via SSE.** Stream updates with any SSE client:
   ```bash
   curl -N -H "Authorization: Bearer $EBOOKTOOLS_SESSION_TOKEN" \
     "http://127.0.0.1:8000/api/pipelines/<job_id>/events?access_token=$EBOOKTOOLS_SESSION_TOKEN"
   ```
   Each message contains a JSON `data:` payload with `event_type`, `timestamp`, `metadata`, and a `snapshot` describing counts and estimated time remaining. The stream closes after a `complete` event.

   In the browser, the UI uses the native `EventSource` API:
   ```ts
   const events = new EventSource(`${API_BASE_URL}/api/pipelines/${jobId}/events`);
   events.onmessage = (message) => {
     const payload = JSON.parse(message.data);
     console.log(payload.event_type, payload.snapshot);
   };
   ```

> **Tip:** The FastAPI loader merges `.env`, `.env.<env>`, and `.env.local` in that order. Vite follows a similar pattern based on the active mode.

---

## Performance Tuning

### Parallel rendering

Translation and media generation can be CPU intensive. Tune throughput in `conf/config.local.json`:

```json
{
  "thread_count": 16,
  "queue_size": 64,
  "pipeline_mode": true,
  "use_ramdisk": true,
  "forced_alignment_enabled": true,
  "forced_alignment_smoothing": "monotonic_cubic"
}
```

Scale `queue_size` with the number of workers so translation and media rendering threads stay saturated.

### Interactive menu

Launch `ebook-tools interactive` -- option **12** controls the global worker thread count (1--10).

### CLI flags

```bash
python -m modules.cli.main run --thread-count 8 path/to/book.epub
```

### Image generation concurrency

Sentence image generation has its own worker cap:

```json
{
  "add_images": true,
  "image_api_base_url": "http://192.168.1.9:7860",
  "image_concurrency": 4
}
```

### RAMDisk

When `use_ramdisk` is `true`, the pipeline mounts a RAM-backed temporary directory. In Docker, use tmpfs instead (`EBOOK_USE_RAMDISK=false`).

---

## Frontend State Management

The React frontend uses **Zustand** for state management with a clean separation of concerns.

### State stores

**jobsStore** (`web/src/stores/jobsStore.ts`):
- Manages all job-related state (pipeline jobs, status, progress events)
- Map-based storage for O(1) lookups
- Separate loading state tracking (`isReloading`, `isMutating`)
- Request deduplication for API calls
- Atomic updates prevent race conditions
- Computed selectors: `getSortedJobs()`, `getJobsByType()`

**uiStore** (`web/src/stores/uiStore.ts`):
- Manages all UI state (selected view, sidebar, player, modals)
- Persists user preferences to `localStorage`
- Pure UI state -- no business logic

### Selective subscriptions

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

### SSE with retry logic

The `useJobEventsWithRetry` hook provides resilient SSE connections:
- Exponential backoff: 2s, 4s, 8s, 16s, 32s
- Max 5 retries (configurable)
- Automatic retry count reset on successful connection
- Graceful degradation on persistent failures

### Error boundaries

Components are wrapped with `<ErrorBoundary>` for graceful error recovery:
- Auto-reset when navigating (via `resetKeys` prop)
- Custom fallback UI
- Error logging callback
- Prevents entire app crashes

### Performance optimizations

- **Shallow comparison** -- Custom equality functions prevent unnecessary updates
- **Computed selectors** -- Memoized derived state in the store
- **Selective subscriptions** -- Components subscribe to minimal state slices
- **Request deduplication** -- Concurrent API calls reuse a single promise
- **Map-based storage** -- O(1) performance for job lookups

### Migration notes

If you encounter old patterns:

| Old pattern | Replace with |
|-------------|-------------|
| `useState` for jobs | `useJobsStore()` |
| `useState` for UI state | `useUIStore()` |
| `usePipelineEvents` | `useJobEventsWithRetry()` |
| Direct API calls | Store actions (`performJobAction`, `refreshJobs`) |

---

## Frontend Capabilities

### Providers

- **`AuthProvider`** (`web/src/components/AuthProvider.tsx`) -- Restores persisted sessions from `localStorage`, surfaces the current user/role, injects bearer tokens into every request, exposes password rotation helpers. Logout events clear the cached token.

- **`ThemeProvider`** (`web/src/components/ThemeProvider.tsx`) -- Persists the preferred colour scheme (`light`, `dark`, `magenta`, or `system`) and sets the `<html data-theme>` attribute so CSS variables adapt instantly.

### Key components

- **`BookNarrationForm`** (`web/src/App.tsx`) -- Pipeline configuration form grouped into source, metadata, language, output, images, performance, and submit sections. Draws defaults from `/api/pipelines/defaults`, supports EPUB upload, and validates before calling `submitPipeline`.

- **`InteractiveTextViewer`** (`web/src/components/InteractiveTextViewer.tsx`) -- Powers the Interactive Reader experience (word highlighting + sentence image reel). Wires the MyPainter regeneration UI so images can be inspected/overwritten per sentence.

- **`UserManagementPanel`** (`web/src/components/admin/UserManagementPanel.tsx`) -- Admin CRUD surface that lists accounts, normalises profile metadata, and issues suspend/activate or password-reset operations.

### Word-highlighting metadata flow

1. **Audio synthesis** -- `modules/render/audio_pipeline.py` produces (and smooths) `word_tokens` plus `original_word_tokens`.
2. **Timeline/exporters** -- Serialise `timingTracks.translation` and `timingTracks.original` into each chunk via `modules/core/rendering/exporters.py`.
3. **Persistence** -- Stores `timingTracks` alongside each `metadata/chunk_XXXX.json` file.
4. **Web API** -- `/api/jobs/{job_id}/timing` is best-effort for legacy jobs; modern flows use chunk metadata directly.
5. **Frontend** -- `InteractiveTextViewer` hydrates chunk metadata lazily (plus timing tracks) and syncs highlights to `<audio>` playback for the active audio lane.
6. **Validation** -- `scripts/validate_word_timing.py` ensures drift stays below 50 ms with no overlaps.

Enable the debug overlay in the browser console:

```js
window.__HL_DEBUG__ = { enabled: true }; // shows frame/index overlay
```

### Audio generation + word highlighting

Audio narration is synthesised sentence-by-sentence in `modules/render/audio_pipeline.py`. Each worker sends the original and translated sentence, target language, tempo, and voice selection to the configured TTS backend. Backends return a `SynthesisResult` with separate `orig` and `translation` `pydub.AudioSegment` tracks. The pipeline persists both and records per-track token timing in `word_tokens` (translation) and `original_word_tokens` (original).

On the frontend, the interactive reader pulls chunk metadata files, builds an in-memory token index, and maps `<audio>` playback time to the nearest token via `AudioSyncController`. No forced alignment is required -- the highlight engine works with sentence-level timing when per-word offsets are unavailable.

### MyLinguist architecture

The MyLinguist dictionary assistant provides LLM-powered word/phrase lookup with structured JSON responses, accessible through the Interactive Reader interface.

---

## Sentence Image Generation

When `add_images` is enabled, the pipeline generates one illustration per sentence in parallel with translation.

- **Backend client**: `modules/images/drawthings.py` talks to a Draw Things / AUTOMATIC1111-compatible `txt2img` endpoint (`/sdapi/v1/txt2img`).
- **Prompting**: `modules/images/prompting.py` asks the configured LLM for a consistent prompt plan, then appends a photorealistic base prompt plus a negative prompt.
- **Storage + metadata**: Images are written under `storage/<job_id>/media/images/<range_fragment>/sentence_00001.png` and referenced from each chunk's `metadata/chunk_XXXX.json`.

For manual inspection/regeneration:

```bash
# Get a sentence image
curl http://127.0.0.1:8000/api/pipelines/jobs/<job_id>/media/images/sentences/1

# Regenerate
curl -X POST http://127.0.0.1:8000/api/pipelines/jobs/<job_id>/media/images/sentences/1/regenerate
```

See [sentence_images.md](sentence_images.md) for the full flow and example payloads.

---

## Metadata Format

### Job manifest (`metadata/job.json`)

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

### Chunk metadata (`metadata/chunk_XXXX.json`)

```json
{
  "chunk_id": "chunk_0001",
  "sentences": [
    {
      "original": "Hello world.",
      "translation": "...",
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
    "translation": []
  }
}
```

### Metadata creation flow

`modules/services/job_manager/persistence.py` emits three artefacts per job: (1) `metadata/job.json` -- the compact manifest; (2) `metadata/chunk_manifest.json` -- a helper map for lazy chunk fetching; and (3) `metadata/chunk_XXXX.json` files with token arrays, image references, audio metadata, and timing tracks.

`MetadataLoader` in `modules/metadata_manager.py` abstracts differences between the chunked format and legacy single-file payloads. Downstream APIs call `MetadataLoader.for_job(job_id)` and hand the result to the serializer powering `/api/jobs/{job_id}/timing` and `/api/pipelines/jobs/{job_id}/media`.

---

## User Accounts, Roles, and Sessions

The authentication layer supports two storage backends:

### PostgreSQL mode (Docker default)

When `DATABASE_URL` is set, users and sessions are stored in the `users` and
`sessions` PostgreSQL tables via `PgUserStore` and `PgSessionManager`. This is
the default in Docker deployments. No filesystem credential files are needed.

### Legacy JSON mode (local development)

When `DATABASE_URL` is not set, the bundled `LocalUserStore` keeps credentials
in `config/users/users.json` and stores active sessions in
`~/.ebooktools_session.json`.

- Bootstrap by copying `config/users/users.sample.json` to
  `config/users/users.json`, then **immediately** rotate the placeholder
  passwords with `ebook-tools user password <username>`.
- Pin storage locations in `config/config.local.json`:

```json
{
  "authentication": {
    "user_store": {
      "backend": "local",
      "storage_path": "config/users/users.json"
    },
    "sessions": {
      "session_file": "~/.ebooktools_session.json",
      "active_session_file": "~/.ebooktools_active_session"
    }
  }
}
```

Override paths at runtime with `EBOOKTOOLS_USER_STORE`, `EBOOKTOOLS_SESSION_FILE`, and `EBOOKTOOLS_ACTIVE_SESSION_FILE`. See [user-management.md](user-management.md) for a deeper walkthrough.

### CLI user management

Credentials are managed via `ebook-tools user` sub-commands. These work with
both storage backends -- the active backend is determined by `DATABASE_URL`.

---

## Running Tests

**Always prefer targeted marker-based tests** over the full suite. Only run the full suite when changes are wide-ranging.

```bash
# Install dev dependencies
pip install -e .[dev]

# Targeted runs (preferred)
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
pytest -m database            # PostgreSQL models, repositories, migrations
pytest -m "not slow and not integration"  # fast feedback loop

# Full suite (only for wide-ranging changes)
pytest                        # all 800+ tests
pytest --cov=modules          # with coverage

# Specific file
pytest tests/modules/webapi/test_job_media_routes.py -v

# Makefile shortcuts
make test-fast                # not slow, not integration
make test-webapi              # same as pytest -m webapi
make test-services            # same as pytest -m services
```

### E2E tests (on-demand only)

E2E tests are **not** part of the regular test suite. They require a running API, credentials in `.env`, and external infrastructure.

**Architecture**: Shared JSON user journeys (`tests/e2e/journeys/*.json`) define platform-agnostic test steps. Platform-specific runners interpret them:

- Python `WebJourneyRunner` (Playwright) for Web
- Swift `JourneyRunner` (XCUITest) for iPhone, iPad, Apple TV

```bash
# Web E2E (Playwright)
# Requires: pip install -e .[e2e]  &&  playwright install
make test-e2e-web             # headed, named report
make test-e2e-web-headless    # headless, named report

# Apple E2E (XCUITest)
# Requires: Xcode, Simulators, E2E_USERNAME/E2E_PASSWORD in .env
make test-e2e-iphone          # iPhone 16 Pro simulator
make test-e2e-ipad            # iPad Pro 13-inch (M4) simulator
make test-e2e-tvos            # Apple TV simulator

# All 4 platforms
make test-e2e-all             # Web + iPhone + iPad + tvOS
```

Reports are Markdown with embedded screenshots at `test-results/`. Credentials: `E2E_USERNAME` / `E2E_PASSWORD` in `.env`. Adding a new journey JSON file auto-propagates to all 4 platforms.

---

## Troubleshooting

### API will not start

- Check Python version: `python --version` (need 3.10+)
- Verify dependencies: `pip list`
- Check port availability: `lsof -i :8000`

### Frontend cannot reach API

- Verify `VITE_API_BASE_URL` in `web/.env.local`
- Check CORS settings: `EBOOK_API_CORS_ORIGINS`

### Audio generation fails

- Verify TTS backend: `ffmpeg -version` or `say -v '?'`
- Docker: only `gtts` and `piper` work (no macOS `say`)
- Check permissions on output directories

### Image generation not working

- Verify Draw Things is running: `curl http://<ip>:7860/sdapi/v1/txt2img`
- Docker: use `http://host.docker.internal:7860` to reach host services
- Increase `image_api_timeout_seconds` for slow models

### Debug tools

```bash
# Verbose CLI logging
ebook-tools run --log-level debug

# Word timing validation
python scripts/validate_word_timing.py <job_id>
```

Browser console debug overlay:

```js
window.__HL_DEBUG__ = { enabled: true };
```

---

## Additional Resources

- [Architecture overview](architecture.md)
- [Sentence images (Draw Things / Stable Diffusion)](sentence_images.md)
- [Interactive reader metadata flow](interactive_reader_metadata.md)
- [Frontend sync checklist](frontend-sync.md)
- [Sentence highlighting](sentence_highlighting.md)
- [User management](user-management.md)
