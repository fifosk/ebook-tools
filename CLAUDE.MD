# Claude AI Developer Guide for ebook-tools

## Project Overview

**ebook-tools** is a comprehensive toolkit for processing, translating, and narrating ebooks with multimedia output. The system converts EPUB files into multi-language narrated experiences with synchronized audio, video slides, word-level highlighting, and optional AI-generated sentence illustrations.

### Key Capabilities
- Multi-language translation with LLM fallbacks
- Text-to-speech synthesis (macOS `say`, Google TTS)
- Video slide generation with FFmpeg
- Word-level audio synchronization and highlighting
- AI-generated sentence images via Stable Diffusion/Draw Things
- Interactive web reader with real-time word highlighting
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
- **Storage**: Filesystem-based job storage (Redis optional)
- **Audio**: gTTS, macOS `say`, FFmpeg
- **Images**: Stable Diffusion/Draw Things API integration
- **Translation**: Google Translate, Ollama LLMs with fallback support
- **Auth**: JWT sessions with bcrypt password hashing

## Directory Structure

```
.
├── conf/                    # Core configuration files
│   ├── config.json         # Default configuration
│   └── config.local.json   # Local overrides (gitignored)
├── config/                  # Runtime configuration
│   ├── users/              # User authentication data
│   ├── media.yaml          # Media generation settings
│   └── rendering.yaml      # Rendering pipeline config
├── modules/                 # Python backend modules
│   ├── audio/              # TTS backends and audio pipeline
│   ├── cli/                # Command-line interface
│   ├── core/               # Core processing logic
│   ├── images/             # Sentence image generation
│   ├── metadata_manager.py # Job metadata handling
│   ├── render/             # Audio/video rendering
│   ├── translation/        # Translation services
│   ├── user_management/    # Authentication system
│   ├── video/              # Video slide generation
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

### Backend Setup

1. **Create virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -e .
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

4. **Launch API server**:
   ```bash
   # Standard uvicorn
   uvicorn modules.webapi.application:create_app --factory --reload --host 0.0.0.0

   # Or using console script
   ebook-tools-api --reload --log-level debug

   # Or using Python module
   python -m modules.webapi --reload --port 8000
   ```

5. **Verify server**:
   ```bash
   curl http://127.0.0.1:8000/
   # {"status":"ok"}
   ```

### Frontend Setup

1. **Install dependencies**:
   ```bash
   cd web
   npm install
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env.local
   # Edit with API URLs
   ```

3. **Run dev server**:
   ```bash
   npm run dev
   # Opens at http://localhost:5173
   ```

4. **Build production**:
   ```bash
   npm run build
   # Output to web/dist/
   ```

## Development Guidelines

### Code Organization

#### Backend Modules
- **`modules/audio/backends/`** - TTS backend implementations (gTTS, macOS)
- **`modules/video/backends/`** - Video rendering backends (FFmpeg)
- **`modules/images/`** - Sentence image generation with Draw Things
- **`modules/translation/`** - Translation service adapters
- **`modules/render/`** - Core audio/video pipeline logic
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
  "video_backend": "ffmpeg",
  "image_api_base_url": "http://192.168.1.9:7860",
  "image_concurrency": 4,
  "add_images": true
}
```

### Key Environment Variables

**Backend**:
- `EBOOK_API_CORS_ORIGINS` - CORS allowed origins
- `EBOOK_API_STATIC_ROOT` - Path to built frontend assets
- `JOB_STORE_URL` - Redis URL for job persistence (optional)
- `EBOOK_AUDIO_BACKEND` - TTS backend (`macos_say` | `gtts`)
- `EBOOK_IMAGE_API_BASE_URL` - Draw Things/SD API endpoint
- `EBOOK_IMAGE_CONCURRENCY` - Parallel image generation workers
- `OLLAMA_URL` - Ollama LLM endpoint
- `LLM_SOURCE` - LLM source (`local` | `cloud`)

**Frontend**:
- `VITE_API_BASE_URL` - Backend API URL
- `VITE_STORAGE_BASE_URL` - Storage endpoint URL
- `VITE_DEV_HTTPS` - Enable HTTPS in dev server

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
│   ├── chunk_manifest.json   # Chunk index
│   ├── chunk_0001.json       # Per-chunk metadata
│   ├── content_index.json    # Chapter/section index
│   └── sentences.json        # Fallback sentence list
├── media/
│   ├── audio/                # Audio segments
│   ├── images/               # Sentence illustrations
│   └── video/                # Video slides
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

```bash
# Install dev dependencies
pip install -e .[dev]

# Run all tests
pytest

# Run with coverage
pytest --cov=modules

# Run specific test file
pytest tests/test_audio.py

# Run integration tests
pytest -m integration
```

### Building for Production

**Backend**:
```bash
# API runs directly from source
python -m modules.webapi --host 0.0.0.0 --port 8000
```

**Frontend**:
```bash
cd web
npm run build
# Output in web/dist/

# Point backend at built files
export EBOOK_API_STATIC_ROOT=/path/to/ebook-tools/web/dist
```

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

### API Authentication

1. **Login**:
```bash
curl -X POST http://127.0.0.1:8000/auth/login \
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
  "slide_parallelism": "auto",
  "slide_parallel_workers": 16,
  "image_concurrency": 4
}
```

### Audio Backend Selection

- **macOS `say`**: Highest quality, macOS only
- **gTTS**: Cross-platform, requires internet
- Set via `tts_backend` or `EBOOK_AUDIO_BACKEND`

### Video Rendering

```json
{
  "video_backend": "ffmpeg",
  "video_backend_settings": {
    "ffmpeg": {
      "executable": "/opt/homebrew/bin/ffmpeg",
      "loglevel": "info"
    }
  }
}
```

## Troubleshooting

### Common Issues

**API won't start**:
- Check Python version: `python --version` (need 3.10+)
- Verify dependencies: `pip list`
- Check port availability: `lsof -i :8000`

**Frontend can't reach API**:
- Verify `VITE_API_BASE_URL` in `web/.env.local`
- Check CORS settings: `EBOOK_API_CORS_ORIGINS`
- Ensure API is running: `curl http://127.0.0.1:8000/`

**Audio generation fails**:
- Verify TTS backend: `ffmpeg -version` or `say -v '?'`
- Check permissions on output directories
- Enable debug logging: `--log-level debug`

**Image generation not working**:
- Verify Draw Things is running: `curl http://<ip>:7860/sdapi/v1/txt2img`
- Check `image_api_base_url` configuration
- Increase `image_api_timeout_seconds` for slow models

### Debug Tools

**CLI**:
```bash
# Verbose logging
ebook-tools run --log-level debug

# Benchmark slide rendering
ebook-tools run --benchmark-slide-rendering
```

**Browser Console**:
```javascript
// Enable word highlighting debug overlay
window.__HL_DEBUG__ = { enabled: true };
```

**Validation**:
```bash
# Check word timing accuracy
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
