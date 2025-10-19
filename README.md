# ebook-tools

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

## Running the web API

The FastAPI backend can be launched with uvicorn using either the module entry
point or the helper script:

```bash
python -m modules.webapi --reload
# or
./scripts/run-webapi.sh --port 9000
```

Both commands call into the same application factory (`modules.webapi.application.create_app`) and accept the standard uvicorn host/port options. Use the `--reload` flag for local development to enable automatic code reloading.

Once the server is running, open <http://127.0.0.1:8000/> in a browser or use `curl` to hit the built-in healthcheck and confirm the API is reachable:

```bash
curl http://127.0.0.1:8000/
# {"status":"ok"}
```

### Web API environment variables

The FastAPI application inspects a few environment variables at startup to control
cross-origin requests and optional static hosting of the bundled single-page
application:

- **`EBOOK_API_CORS_ORIGINS`** – Comma or whitespace separated list of
  allowed origins for CORS. Defaults to the local Vite dev server URLs
  (`http://localhost:5173` and `http://127.0.0.1:5173`). Set to `*` to allow
  every origin or to an empty string to disable the middleware entirely.
- **`EBOOK_API_STATIC_ROOT`** – Filesystem path to the built web assets. When
  unset, the server looks for `web/dist/` relative to the repository root. Set
  this value to an empty string to run in API-only mode even if the directory
  exists.
- **`EBOOK_API_STATIC_INDEX`** – Filename served for client-side routes when
  static hosting is enabled (default: `index.html`).
- **`EBOOK_API_STATIC_MOUNT`** – URL prefix where the static files are exposed
  (default: `/`).

When static hosting is disabled the JSON healthcheck remains available at `/`.
If the frontend bundle is served, the healthcheck can always be reached at
`/_health`.
