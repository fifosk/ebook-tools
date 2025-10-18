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
