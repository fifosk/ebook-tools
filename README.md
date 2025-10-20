# ebook-tools

## Documentation

- [Architecture overview](docs/architecture.md)

## Backend setup

### Install dependencies

1. Ensure Python 3.10 or newer is available on your system (the project is
   regularly verified against Python 3.11).
2. Create a virtual environment and install the package dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   python -m pip install --upgrade pip
   pip install -e .
   ```

   The editable install wires up the `ebook-tools-api` console script and pulls in
   the FastAPI/uvicorn runtime declared in `pyproject.toml`. If you plan to run
   the test suite or lint checks, append `[dev]` to install the optional tooling
   bundle (`pip install -e .[dev]`).

### Launch the FastAPI server

With the virtual environment activated you can start the backend with any of the
following commands:

```bash
# Standard uvicorn invocation
uvicorn modules.webapi.application:create_app --factory --reload

# Python module entry point (resolves to the same uvicorn call)
python -m modules.webapi --reload --port 8000

# Installed console script shortcut
ebook-tools-api --reload --log-level debug

# Shell helper (wraps the module runner and adds a --port flag)
./scripts/run-webapi.sh --port 9000
```

Use `--reload` while iterating locally to enable hot-reloading. Once the server
starts, confirm it is reachable:

```bash
curl http://127.0.0.1:8000/
# {"status":"ok"}
```

If you prefer to verify via a browser, open <http://127.0.0.1:8000/>.

### Web API environment variables

Copy `.env.example` to `.env` at the project root and tweak the values before
starting uvicorn. The loader reads multiple files in order, so you can keep
shared defaults in `.env`, overrides in `.env.<name>` (by setting
`EBOOK_ENV=<name>`), and machine-specific tweaks in `.env.local`. Use
`EBOOK_ENV_FILE` to point at any additional file if you need to pull secrets
from a different location. All files are optional; values exported in the shell
still take precedence.

The FastAPI application inspects a few environment variables at startup to
control cross-origin requests and optional static hosting of the bundled
single-page application:

- **`EBOOK_API_CORS_ORIGINS`** – Comma or whitespace separated list of allowed
  origins for CORS. Defaults to the local Vite dev server URLs
  (`http://localhost:5173` and `http://127.0.0.1:5173`) and any IPv4 address on
  the same network (for example `http://192.168.1.10:5173`) so the dev server can
  be accessed from other devices. Set to `*` to allow every origin or to an
  empty string to disable the middleware entirely.
- **`EBOOK_API_STATIC_ROOT`** – Filesystem path to the built web assets. When
  unset, the server looks for `web/dist/` relative to the repository root. Set
  this value to an empty string to run in API-only mode even if the directory
  exists.
- **`EBOOK_API_STATIC_INDEX`** – Filename served for client-side routes when
  static hosting is enabled (default: `index.html`).
- **`EBOOK_API_STATIC_MOUNT`** – URL prefix where the static files are exposed
  (default: `/`).
- **`JOB_STORE_URL`** – Redis (or compatible) URL used to persist job metadata.
  When unset the service stores job state in memory only.

When static hosting is disabled the JSON healthcheck remains available at `/`.
If the frontend bundle is served, the healthcheck can always be reached at
`/_health`.

## Web UI workspace

The React/Vite client lives under `web/` and expects a Node 18+ toolchain.

### Install dependencies

```bash
cd web
npm install
```

### Run or build the client

- `npm run dev` starts the Vite development server on port 5173. Pass
  `-- --host 0.0.0.0` if you need to expose it to other devices on your network.
- `npm run build` produces a production bundle in `web/dist/`. Copy or point the
  backend's `EBOOK_API_STATIC_ROOT` at this directory to serve the build from
  FastAPI.
- `npm run preview` serves the production build for smoke testing.

### Configure the API base URL and storage endpoints

Duplicate `web/.env.example` to `web/.env` or `web/.env.local` and update the
values:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_STORAGE_BASE_URL=http://127.0.0.1:8000/storage
```

`VITE_API_BASE_URL` controls where fetch requests are sent, while
`VITE_STORAGE_BASE_URL` is used for constructing download links to generated
artifacts. As with the backend, you can create environment-specific files such
as `web/.env.production` and pick them up by running Vite with the corresponding
mode (`npm run build -- --mode production`).

> **Tip:** The FastAPI loader merges `.env`, `.env.<env>`, and `.env.local` in
> that order. Vite follows a similar pattern based on the active mode, letting
> you keep per-environment tweaks checked in while secrets stay local.

## Run the stack end-to-end

1. **Start the backend.** Activate the Python virtual environment and launch
   uvicorn (`python -m modules.webapi --reload`). Ensure the healthcheck at
   <http://127.0.0.1:8000/> returns `{"status":"ok"}`.
2. **Start the frontend.** In a separate terminal run `npm run dev` from `web/`.
   The app becomes available at <http://127.0.0.1:5173/> and proxies API calls
   to the URL specified by `VITE_API_BASE_URL`.
3. **Submit a pipeline job.** Trigger a run through the UI or by calling the API
   directly:

   ```bash
   curl -X POST http://127.0.0.1:8000/pipelines \
     -H 'Content-Type: application/json' \
     -d @payload.json
   ```

   The response contains a `job_id`.
4. **Watch progress via Server-Sent Events (SSE).** Stream updates with any SSE
   client. For example, `curl -N` keeps the connection open and prints each
   event:

   ```bash
   curl -N http://127.0.0.1:8000/pipelines/<job_id>/events
   ```

   Each message contains a JSON `data:` payload shaped like
   `ProgressEventPayload` (see `modules/webapi/schemas.py`) with fields such as
   `event_type`, `timestamp`, `metadata`, and a `snapshot` describing counts and
   estimated time remaining. The stream automatically closes after a
   `complete` event or when the job tracker finishes emitting updates. In the
   browser, the UI listens to the same endpoint with the native `EventSource`
   API:

   ```ts
   const events = new EventSource(`${API_BASE_URL}/pipelines/${jobId}/events`);
   events.onmessage = (message) => {
     const payload = JSON.parse(message.data);
     console.log(payload.event_type, payload.snapshot);
   };
   ```

## Configuration overview

`main.py` (and the backward-compatible `ebook-tools.py` wrapper) read their
baked-in defaults from `conf/config.json`. To keep
secrets and machine-specific tweaks out of version control, copy any fields you
want to change into `conf/config.local.json`; those overrides are merged on top
of the defaults at runtime. All relative paths are resolved from the repository
directory.

> **Tip:** `conf/config.local.json` is ignored by Git, so it's safe to add API
> keys, alternate model names, or other machine-specific values there.

### Directory settings
- **`ebooks_dir`**: Directory for source EPUB files and optional cover images.
  Defaults to `books/`, which lives next to `conf/`. The script resolves
  `input_file` and `book_cover_file` relative to this folder.
- **`working_dir`**: Root directory for downloaded covers and other
  long-lived artifacts. Defaults to `output/`.
- **`output_dir`**: Location for generated HTML/PDF/EPUB/audio/video files.
  Defaults to `output/ebook/` inside the working directory.
- **`tmp_dir`**: Scratch space for intermediate assets such as slide images
  and concatenation lists. Defaults to `tmp/`.

You can override any of these via the matching CLI flags (`--ebooks-dir`,
`--working-dir`, `--output-dir`, `--tmp-dir`) or environment variables
(`EBOOKS_DIR`, `EBOOK_WORKING_DIR`, `EBOOK_OUTPUT_DIR`, `EBOOK_TMP_DIR`).

The default `books/` directory is ignored by Git so you can drop
`book.epub`, `book_cover.jpg`, and other local assets there without
accidentally committing them. Create the folder manually if it does not
already exist.

### External tool settings
- **`ffmpeg_path`**: Path to the FFmpeg binary used by `pydub` and the video
  stitching helpers. Defaults to whatever `ffmpeg` is on your `PATH`.
- **`ollama_url`**: Base URL for the Ollama chat endpoint. Defaults to
  `http://localhost:11434/api/chat`.

Both values accept overrides through CLI flags (`--ffmpeg-path`,
`--ollama-url`) or the environment variables `FFMPEG_PATH` and `OLLAMA_URL`.

### Using the settings
- Interactive mode (`python main.py -i` or `python ebook-tools.py -i`) exposes each knob in the
  menu, so you can persist new defaults back into `conf/config.local.json`.
- In non-interactive mode, CLI flags or environment variables take precedence
  over the JSON values. The script resolves relative paths against the working
  copy and creates directories as needed.
